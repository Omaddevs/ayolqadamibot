"""«📢 E'lon berish»: shablon tanlash → savollar birma-bir → ko'rib chiqish → serverga (web admin panel) moderatsiyaga.

Shablonlar serverdan keladi (services/adsapi.py). Tasdiqlangach e'lonni server kanallarga joylaydi va
e'lon beruvchiga shu bot orqali xabar yuboradi.
"""
from __future__ import annotations

import html
import logging

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ..callbacks import AdCb
from ..config import Config
from ..db import Database
from ..services import adsapi, notify
from ..states import AdForm
from ..texts import t
from ..utils import normalize_phone, normalize_tg
from .base import send_menu

router = Router(name="ads")
log = logging.getLogger(__name__)

STYLE = "primary"  # loyiha rangiga eng yaqin Telegram tugma rangi (ko'k, oq matn)


def _b(text: str, a: str, v: str | None = None, style: str | None = STYLE) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=AdCb(a=a, v=v).pack(), style=style)


def _label(opt: dict, lang: str) -> str:
    return opt.get("ru" if lang == "ru" else "uz") or opt.get("uz") or opt.get("v", "")


def _options(field: dict, data: dict) -> list[dict]:
    if field["type"] == "choice":
        return field.get("options") or []
    if field["type"] == "category":
        return data.get("categories") or []
    if field["type"] == "city":
        return [{"v": c, "uz": c, "ru": c} for c in data.get("cities") or []]
    return []


def _display(field: dict, value: str, data: dict, lang: str) -> str:
    for o in _options(field, data):
        if o["v"] == value:
            return _label(o, lang)
    return value


async def _ctx(state: FSMContext) -> tuple[dict, dict, dict]:
    st = await state.get_data()
    ad = st.get("ad") or {}
    data = st.get("ad_data") or {}
    tpl = next((x for x in data.get("templates", []) if x["id"] == ad.get("tpl")), None)
    return ad, data, tpl


# ---------- boshlash ----------
async def start_ad(message: Message, state: FSMContext, cfg: Config, user: dict, lang: str) -> None:
    keep = {k: v for k, v in (await state.get_data()).items() if k in ("vf", "rf")}
    await state.clear()
    if keep:
        await state.update_data(**keep)
    if not adsapi.enabled(cfg):
        await message.answer(t("ad_disabled", lang))
        return
    try:
        data = await adsapi.templates(cfg)
    except adsapi.AdsUnavailable as e:
        log.warning("Shablonlar olinmadi: %s", e)
        await message.answer(t("ad_offline", lang).split("«")[0].strip())
        return
    role = user.get("role") or "seeker"
    tpls = sorted(data.get("templates", []), key=lambda x: 0 if role in x.get("roles", []) else 1)
    await state.update_data(ad_data=data)
    # rolga mos kartochka shabloni bo'lsa (ish beruvchi — «ISHCHI KERAK!», ish izlovchi — «ISH IZLAYMAN!») — darhol boshlanadi
    card = next((x for x in tpls if x.get("layout") == "card" and role in x.get("roles", [])), None)
    if card:
        await state.update_data(ad={"tpl": card["id"], "i": 0, "f": {}})
        await state.set_state(AdForm.fill)
        await message.answer(_card_text(card, {}, data, blank=True) + "\n\n" + t("ad_card_intro", lang))
        return await _ask(message, state, user, lang)
    lines = [t("ad_choose", lang), ""]
    rows = []
    for x in tpls:
        name = x["name"]["ru" if lang == "ru" else "uz"]
        lines.append(f"{x['emoji']} <b>{html.escape(name)}</b> — {html.escape(x['hint']['ru' if lang == 'ru' else 'uz'])}")
        rows.append([_b(f"{x['emoji']} {name}", "tpl", x["id"])])
    rows.append([_b(t("ad_cancel", lang), "cancel", style="danger")])
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(AdCb.filter(F.a == "tpl"))
async def on_template(cb: CallbackQuery, callback_data: AdCb, state: FSMContext, user: dict, lang: str) -> None:
    st = await state.get_data()
    data = st.get("ad_data") or {}
    if not any(x["id"] == callback_data.v for x in data.get("templates", [])):
        return await cb.answer("⌛️", show_alert=False)
    await cb.answer()
    await _drop_kb(cb)
    await state.update_data(ad={"tpl": callback_data.v, "i": 0, "f": {}})
    await state.set_state(AdForm.fill)
    await _ask(cb.message, state, user, lang)


async def _drop_kb(cb: CallbackQuery) -> None:
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


# ---------- savol ----------
async def _ask(message: Message, state: FSMContext, user: dict, lang: str, note: str | None = None) -> None:
    ad, data, tpl = await _ctx(state)
    if not tpl:
        return
    fields = tpl["fields"]
    if ad["i"] >= len(fields):
        return await _preview(message, state, user, lang)
    f = fields[ad["i"]]
    parts = []
    if note:
        parts.append(note)
    q = t("ad_q", lang, i=ad["i"] + 1, n=len(fields), emoji=f["emoji"], ask=html.escape(f["ask"]["ru" if lang == "ru" else "uz"]))
    if not f.get("required"):
        q += " " + t("ad_optional", lang)
    parts.append(q)
    if f["type"] == "long":
        parts.append(t("ad_long_hint", lang))
    if f.get("example"):
        parts.append(t("ad_example", lang, ex=html.escape(f["example"])))
    current = ad["f"].get(f["key"])
    if current:
        parts.append(f"✏️ <code>{html.escape(_display(f, current, data, lang)[:200])}</code>")

    rows: list[list[InlineKeyboardButton]] = []
    opts = _options(f, data)
    cols = 3 if f["type"] == "city" else 2
    row: list[InlineKeyboardButton] = []
    for idx, o in enumerate(opts):
        row.append(_b(_label(o, lang), "opt", str(idx)))
        if len(row) == cols:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    for idx, o in enumerate(f.get("quick") or []):
        rows.append([_b(_label(o, lang), "quick", str(idx))])
    if f["type"] == "phone" and user.get("phone"):
        rows.append([_b(t("ad_my_phone", lang, p=user["phone"]), "me")])
    if f["type"] == "tg" and user.get("username"):
        rows.append([_b(t("ad_my_tg", lang, u="@" + user["username"]), "me")])
    nav = []
    if ad.get("edit"):
        nav.append(_b(t("ad_back", lang), "prev"))  # tahrirlashda — ko'rib chiqishga qaytish
    elif ad["i"] > 0:
        nav.append(_b(t("ad_back", lang), "back"))
    if not f.get("required"):
        nav.append(_b(t("ad_skip", lang), "skip"))
    nav.append(_b(t("ad_cancel", lang), "cancel", style="danger"))
    rows.append(nav)
    await message.answer("\n\n".join(parts), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


async def _set(message: Message, state: FSMContext, user: dict, lang: str, value: str | None) -> None:
    ad, _, tpl = await _ctx(state)
    f = tpl["fields"][ad["i"]]
    if value:
        ad["f"][f["key"]] = value
    else:
        ad["f"].pop(f["key"], None)
    if ad.pop("edit", False):
        ad["i"] = len(tpl["fields"])  # bitta band tahrirlandi — darhol ko'rib chiqishga
    else:
        ad["i"] += 1
    await state.update_data(ad=ad)
    await _ask(message, state, user, lang)


def _validate(f: dict, text: str, data: dict, lang: str) -> tuple[str | None, str | None]:
    """(qiymat, xato matni)."""
    text = text.strip()
    if not text:
        return None, t("ad_required", lang)
    if f["type"] in ("choice", "category"):
        low = text.lower()
        for o in _options(f, data):
            if low in (o["v"].lower(), _label(o, "uz").lower(), _label(o, "ru").lower()):
                return o["v"], None
        return None, t("ad_pick_only", lang)
    if f.get("max") and len(text) > f["max"]:
        return None, t("ad_too_long", lang, n=f["max"])
    if f["type"] == "phone":
        p = normalize_phone(text)
        return (p, None) if p else (None, t("ad_bad_phone", lang))
    if f["type"] == "tg":
        u = normalize_tg(text)
        return (u, None) if u else (None, t("ad_bad_tg", lang))
    if f["type"] == "age":
        return (text, None) if text.isdigit() and 14 <= int(text) <= 80 else (None, t("ad_bad_age", lang))
    if len(text) < 2:
        return None, t("ad_required", lang)
    return text, None


@router.message(AdForm.fill, F.contact)
async def on_contact(message: Message, state: FSMContext, user: dict, lang: str) -> None:
    ad, _, tpl = await _ctx(state)
    if tpl and tpl["fields"][ad["i"]]["type"] == "phone":
        await _set(message, state, user, lang, normalize_phone(message.contact.phone_number) or message.contact.phone_number)


@router.message(AdForm.fill, F.text)
async def on_text(message: Message, state: FSMContext, user: dict, lang: str) -> None:
    ad, data, tpl = await _ctx(state)
    if not tpl:
        return
    f = tpl["fields"][ad["i"]]
    value, err = _validate(f, message.text or "", data, lang)
    if err:
        await message.answer("⚠️ " + err)
        return
    await _set(message, state, user, lang, value)


@router.callback_query(AdForm.fill, AdCb.filter(F.a.in_({"opt", "quick", "me", "skip", "back"})))
async def on_button(cb: CallbackQuery, callback_data: AdCb, state: FSMContext, user: dict, lang: str) -> None:
    ad, data, tpl = await _ctx(state)
    if not tpl:
        return await cb.answer()
    f = tpl["fields"][ad["i"]]
    a, v = callback_data.a, callback_data.v
    value: str | None = None
    if a == "opt":
        opts = _options(f, data)
        if not (v or "").isdigit() or int(v) >= len(opts):
            return await cb.answer()
        value = opts[int(v)]["v"]
    elif a == "quick":
        q = f.get("quick") or []
        if not (v or "").isdigit() or int(v) >= len(q):
            return await cb.answer()
        value = q[int(v)]["v"]
    elif a == "me":
        value = user.get("phone") if f["type"] == "phone" else ("@" + user["username"] if user.get("username") else None)
    elif a == "skip":
        if f.get("required"):
            return await cb.answer(t("ad_required", lang), show_alert=True)
    elif a == "back":
        await cb.answer()
        await _drop_kb(cb)
        ad["i"] = max(0, ad["i"] - 1)
        await state.update_data(ad=ad)
        return await _ask(cb.message, state, user, lang)
    await cb.answer()
    await _drop_kb(cb)
    await _set(cb.message, state, user, lang, value)


# ---------- ko'rib chiqish va yuborish ----------
def _card_text(tpl: dict, values: dict, data: dict, blank: bool = False) -> str:
    """Kartochka (kanal postidagi bilan bir xil): "📢 ISHCHI KERAK!", har qatorda "emoji <b>Nom:</b> qiymat", oxirida murojaat.
    blank — bo'sh shablon (qiymatlar o'rnida "(...)") — boshida nima so'ralishini ko'rsatish uchun."""
    def line(f: dict) -> str | None:
        v = values.get(f["key"])
        if not v and not blank:
            return None
        shown = html.escape(_display(f, v, data, "uz")) if v else "(...)"
        return f"{f['emoji']} <b>{html.escape(f['label'])}:</b>{chr(10) if chr(10) in shown else ' '}{shown}"

    contact = ("phone", "tg")
    body = [x for x in (line(f) for f in tpl["fields"] if f["key"] not in contact) if x]
    tail = [x for x in (line(f) for f in tpl["fields"] if f["key"] in contact) if x]
    return "\n\n".join(p for p in (f"{tpl['emoji']} <b>{html.escape(tpl['headline'])}</b>", "\n".join(body), "\n".join(tail)) if p)


def _preview_text(tpl: dict, ad: dict, data: dict, lang: str) -> str:
    if tpl.get("layout") == "card":
        return _card_text(tpl, ad["f"], data)
    title_f = next((f for f in tpl["fields"] if f.get("title")), None)
    title = _display(title_f, ad["f"].get(title_f["key"], ""), data, "uz") if title_f else ""
    head = tpl.get("headline") or tpl["name"]["uz"]  # kanal postidagi bilan bir xil sarlavha
    lines = [f"{tpl['emoji']} <b>{html.escape(head)}{': ' + html.escape(title) if title else ''}</b>", ""]
    for f in tpl["fields"]:
        v = ad["f"].get(f["key"])
        if not v or f.get("title"):
            continue
        shown = html.escape(_display(f, v, data, "uz"))
        if f["type"] == "long":
            items = "\n".join(f"• {html.escape(x.strip(' •-*'))}" for x in v.splitlines() if x.strip())
            lines.append(f"{f['emoji']} <b>{html.escape(f['label'])}:</b>\n{items}")
        else:
            lines.append(f"{f['emoji']} {html.escape(f['label'])}: {shown}")
    return "\n".join(lines)


async def _preview(message: Message, state: FSMContext, user: dict, lang: str) -> None:
    ad, data, tpl = await _ctx(state)
    if not ad["f"].get("phone") and not ad["f"].get("tg"):
        ad["i"] = next(i for i, f in enumerate(tpl["fields"]) if f["key"] == "phone")
        await state.update_data(ad=ad)
        return await _ask(message, state, user, lang, note="⚠️ " + t("ad_need_contact", lang))
    await state.set_state(AdForm.confirm)
    await message.answer(t("ad_preview", lang))
    await message.answer(_preview_text(tpl, ad, data, lang), disable_web_page_preview=True)
    await message.answer(t("ad_confirm", lang), reply_markup=_confirm_kb(lang))


def _confirm_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_b(t("ad_restart", lang), "edit"), _b(t("ad_send", lang), "send", style="success")],
        [_b(t("ad_cancel", lang), "cancel", style="danger")],
    ])


@router.callback_query(AdForm.confirm, AdCb.filter(F.a == "edit"))
async def on_edit(cb: CallbackQuery, state: FSMContext, lang: str) -> None:
    """«✏️ Tahrirlash» — qaysi bandni o'zgartirishni tanlash."""
    _, _, tpl = await _ctx(state)
    if not tpl:
        return await cb.answer()
    await cb.answer()
    btns = [_b(f"{f['emoji']} {f['label']}", "field", str(i)) for i, f in enumerate(tpl["fields"])]
    rows = [btns[i:i + 2] for i in range(0, len(btns), 2)] + [[_b(t("ad_back", lang), "prev")]]
    try:
        await cb.message.edit_text(t("ad_edit_pick", lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    except Exception:
        await cb.message.answer(t("ad_edit_pick", lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(AdForm.confirm, AdCb.filter(F.a == "field"))
async def on_edit_field(cb: CallbackQuery, callback_data: AdCb, state: FSMContext, user: dict, lang: str) -> None:
    ad, _, tpl = await _ctx(state)
    v = callback_data.v or ""
    if not tpl or not v.isdigit() or int(v) >= len(tpl["fields"]):
        return await cb.answer()
    await cb.answer()
    await _drop_kb(cb)
    ad["i"], ad["edit"] = int(v), True
    await state.update_data(ad=ad)
    await state.set_state(AdForm.fill)
    await _ask(cb.message, state, user, lang)


@router.callback_query(AdCb.filter(F.a == "prev"))
async def on_prev(cb: CallbackQuery, state: FSMContext, user: dict, lang: str) -> None:
    """Tahrirlash menyusidan yoki tahrirlanayotgan savoldan — ko'rib chiqishga qaytish."""
    ad, _, tpl = await _ctx(state)
    if not tpl:
        return await cb.answer()
    await cb.answer()
    if await state.get_state() == AdForm.confirm.state:
        try:
            return await cb.message.edit_text(t("ad_confirm", lang), reply_markup=_confirm_kb(lang))
        except Exception:
            pass
    await _drop_kb(cb)
    ad.pop("edit", None)
    ad["i"] = len(tpl["fields"])
    await state.update_data(ad=ad)
    await _ask(cb.message, state, user, lang)


@router.callback_query(AdForm.confirm, AdCb.filter(F.a == "send"))
async def on_send(cb: CallbackQuery, state: FSMContext, db: Database, config: Config, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    ad, data, tpl = await _ctx(state)
    if not tpl:
        return await cb.answer()
    await cb.answer("⏳")
    try:
        res = await adsapi.submit(config, tpl["id"], ad["f"], user)
    except adsapi.AdsRejected as e:
        if e.code == "rate_limited":
            await _drop_kb(cb)
            await state.clear()
            return await send_menu(cb.message, user, lang, is_admin, t("ad_limit", lang))
        key = next(iter(e.fields), None)
        idx = next((i for i, f in enumerate(tpl["fields"]) if f["key"] == key), None)
        if idx is None:
            return await cb.message.answer(t("ad_fix", lang, msg=html.escape(e.args[0] or e.code)))
        await _drop_kb(cb)
        ad["i"] = idx
        await state.update_data(ad=ad)
        await state.set_state(AdForm.fill)
        label = tpl["fields"][idx]["label"]
        return await _ask(cb.message, state, user, lang, note=t("ad_fix", lang, msg=html.escape(f"{label} — {e.fields[key]}")))
    except adsapi.AdsUnavailable as e:
        log.warning("E'lon yuborilmadi: %s", e)
        kb = InlineKeyboardMarkup(inline_keyboard=[[_b(t("ad_retry", lang), "send", style="success")], [_b(t("ad_cancel", lang), "cancel", style="danger")]])
        return await cb.message.answer(t("ad_offline", lang), reply_markup=kb)

    await _drop_kb(cb)
    await state.clear()
    if res.get("duplicate"):
        return await send_menu(cb.message, user, lang, is_admin, t("ad_dup", lang, n=res.get("number")))
    await send_menu(cb.message, user, lang, is_admin, t("ad_sent", lang, n=res.get("number")))
    # adminlarga: yangi e'lon (admin panel havolasi bilan)
    who = html.escape(user.get("full_name") or "") + (f" (@{user['username']})" if user.get("username") else "")
    warn = "".join(f"\n⚠️ {html.escape(w)}" for w in res.get("warnings") or [])
    text = t("ad_admin_new", "uz", n=res.get("number"), tpl=html.escape(tpl["name"]["uz"]), title=html.escape(res.get("title") or ""), who=who, warn=warn)
    url = res.get("adminUrl") or ""
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("ad_admin_open", "uz"), url=url, style=STYLE)]]) if url.startswith("https://") else None
    if url and not kb:
        text += f"\n\n🛠 {html.escape(url)}"
    await notify.send_admins(bot, db, config, text, reply_markup=kb, disable_web_page_preview=True)


@router.callback_query(AdCb.filter(F.a == "cancel"))
async def on_cancel(cb: CallbackQuery, state: FSMContext, user: dict, lang: str, is_admin: bool) -> None:
    await cb.answer()
    await _drop_kb(cb)
    keep = {k: v for k, v in (await state.get_data()).items() if k in ("vf", "rf")}
    await state.clear()
    if keep:
        await state.update_data(**keep)
    await send_menu(cb.message, user, lang, is_admin, t("cancelled", lang))


@router.callback_query(AdCb.filter(F.a == "new"))
async def on_new(cb: CallbackQuery, state: FSMContext, config: Config, user: dict, lang: str) -> None:
    await cb.answer()
    await start_ad(cb.message, state, config, user, lang)


@router.callback_query(AdCb.filter())
async def on_stale(cb: CallbackQuery, lang: str) -> None:
    """Eski xabardagi tugma (shakl allaqachon yuborilgan yoki bekor qilingan)."""
    await cb.answer("⌛️ " + ("Устарело" if lang == "ru" else "Eskirgan"), show_alert=False)


# ---------- mening e'lonlarim ----------
async def show_my_ads(message: Message, config: Config, user: dict, lang: str) -> None:
    if not adsapi.enabled(config):
        return await message.answer(t("ad_disabled", lang))
    try:
        items = await adsapi.my_ads(config, user["id"])
    except (adsapi.AdsUnavailable, adsapi.AdsRejected):
        return await message.answer(t("ad_offline", lang).split("«")[0].strip())
    if not items:
        kb = InlineKeyboardMarkup(inline_keyboard=[[_b(t("m_post_ad", lang), "new")]])
        return await message.answer(t("ad_my_title", lang) + "\n\n" + t("ad_my_empty", lang), reply_markup=kb)
    lines = [t("ad_my_title", lang), ""]
    for a in items[:15]:
        st = t(f"ad_st_{a['status']}", lang)
        line = f"<b>#{a['number']}</b> · {html.escape(a['title'])}\n{st}"
        if a.get("rejectReason"):
            line += f" — {html.escape(a['rejectReason'])}"
        for link in a.get("links") or []:
            line += f"\n🔗 {html.escape(link)}"
        lines.append(line)
    kb = InlineKeyboardMarkup(inline_keyboard=[[_b(t("m_post_ad", lang), "new")]])
    await message.answer("\n\n".join(lines), reply_markup=kb, disable_web_page_preview=True)
