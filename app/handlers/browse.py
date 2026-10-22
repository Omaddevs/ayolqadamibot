"""Vakansiya va rezyumelarni bittadan ko'rish (⬅️/➡️), fayllar, bog'lanish, ariza, saqlash, taklif."""
from __future__ import annotations

import re
from urllib.parse import quote

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaAnimation,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    Message,
)

from ..callbacks import Act, AppCb, Flt, InvCb, MyRes, Nav
from ..config import Config
from ..db import Database
from ..keyboards import filter_kb, filter_values_kb
from ..services import files, flow, notify, websync
from ..states import Browse
from ..texts import t
from ..utils import CAPTION_LIMIT, classify_target, contact_lines, h, normalize_phone, resume_card, short_date, vacancy_card

router = Router(name="browse")

VAC_KINDS = {"v", "fv", "one"}
RES_KINDS = {"r", "fr", "onr"}
MEDIA_INPUT = {"photo": InputMediaPhoto, "video": InputMediaVideo, "document": InputMediaDocument, "animation": InputMediaAnimation}
PHONE_IN_TEXT = re.compile(r"(?:\+?998[\s\-]?)?\(?\d{2}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")
TG_IN_TEXT = re.compile(r"(?<![\w@])@[A-Za-z][A-Za-z0-9_]{3,31}")


# ---------- umumiy chizish ----------
async def send_card(bot: Bot, chat_id: int, text: str, kb, media_type: str | None = None, file_id: str | None = None) -> Message:
    if media_type and file_id:
        method = {"photo": bot.send_photo, "video": bot.send_video, "document": bot.send_document, "animation": bot.send_animation}.get(media_type)
        if method:
            return await method(chat_id, file_id, caption=text, reply_markup=kb)
    return await bot.send_message(chat_id, text, reply_markup=kb, disable_web_page_preview=True)


async def render(event: Message | CallbackQuery, bot: Bot, text: str, kb, media_type: str | None = None, file_id: str | None = None) -> None:
    """Callback'dan kelsa mavjud xabarni tahrirlaydi (iloji bo'lsa), aks holda yangisini yuboradi."""
    if isinstance(event, CallbackQuery) and event.message:
        msg = event.message
        has_media = bool(msg.photo or msg.video or msg.document or msg.animation)
        new_media = bool(media_type and file_id and media_type in MEDIA_INPUT)
        try:
            if not new_media and not has_media:
                await msg.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
                return
            if new_media and has_media:
                await msg.edit_media(MEDIA_INPUT[media_type](media=file_id, caption=text), reply_markup=kb)
                return
        except TelegramBadRequest as e:
            if "not modified" in str(e):
                return
        try:
            await msg.delete()
        except TelegramBadRequest:
            pass
        await send_card(bot, msg.chat.id, text, kb, media_type, file_id)
        return
    await send_card(bot, event.chat.id, text, kb, media_type, file_id)


def _nav_row(kind: str, idx: int, total: int) -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(text="⬅️", callback_data=Nav(kind=kind, i=(idx - 1) % total).pack()),
        InlineKeyboardButton(text=f"{idx + 1} / {total}", callback_data="noop"),
        InlineKeyboardButton(text="➡️", callback_data=Nav(kind=kind, i=(idx + 1) % total).pack()),
    ]


# ---------- ma'lumot olish ----------
async def get_item(db: Database, state: FSMContext, uid: int, kind: str, idx: int) -> tuple[dict | None, int, int]:
    data = await state.get_data()
    if kind == "v":
        f = data.get("vf") or {}
        total = await db.count_vacancies(f)
        if not total:
            return None, 0, 0
        idx %= total
        return await db.vacancy_at(f, idx), total, idx
    if kind == "r":
        f = data.get("rf") or {}
        total = await db.count_resumes(f)
        if not total:
            return None, 0, 0
        idx %= total
        return await db.resume_at(f, idx), total, idx
    fav_kind = "vac" if kind == "fv" else "res"
    ids = await db.fav_ids(uid, fav_kind)
    if not ids:
        return None, 0, 0
    idx %= len(ids)
    item = await (db.get_vacancy(ids[idx]) if kind == "fv" else db.get_resume(ids[idx]))
    if item is None:  # o'chirilgan — ro'yxatdan olib tashlaymiz
        await db.toggle_fav(uid, fav_kind, ids[idx])
        return await get_item(db, state, uid, kind, idx)
    return item, len(ids), idx


# ---------- vakansiya kartasi ----------
async def vacancy_view(db: Database, v: dict, lang: str, uid: int, is_admin: bool, kind: str, idx: int = 0, total: int = 1,
                       bot: Bot | None = None):
    status = "" if v["status"] == "active" else f"{t('st_' + v['status'], lang)}\n\n"
    footer = f"🆔 {v['id']} · " + t("v_views", lang, n=v.get("views") or 0, date=short_date(v.get("created_at")))
    has_media = bool(v.get("media_type") and v.get("media_file_id"))
    limit = CAPTION_LIMIT - len(status) if has_media else 4000
    text = status + vacancy_card(v, lang, limit, footer)
    fav = await db.is_fav(uid, "vac", v["id"])
    # «Bog'lanish» — e'lon egasining chati to'g'ridan-to'g'ri ochiladi; aloqa topilmasa — ogohlantirish oynasi
    contact_url = vacancy_contact_url(v)
    contact_btn = (InlineKeyboardButton(text=t("b_contact", lang), url=contact_url) if contact_url
                   else InlineKeyboardButton(text=t("b_contact", lang), callback_data=Act(a="vc", id=v["id"], i=idx, k=kind).pack()))
    rows = [
        [contact_btn, InlineKeyboardButton(text=t("b_apply", lang), callback_data=Act(a="ap", id=v["id"], i=idx, k=kind).pack())],
        [InlineKeyboardButton(text=t("b_vac_pdf", lang), callback_data=Act(a="vp", id=v["id"], i=idx, k=kind).pack()),
         InlineKeyboardButton(text=t("b_vac_doc", lang), callback_data=Act(a="vd", id=v["id"], i=idx, k=kind).pack()),
         InlineKeyboardButton(text=t("b_saved" if fav else "b_save", lang), callback_data=Act(a="vf", id=v["id"], i=idx, k=kind).pack())],
    ]
    if bot and v["status"] == "active":
        rows.append([InlineKeyboardButton(text=t("b_share", lang), url=share_url(await flow.bot_username(bot), v, lang))])
    if kind in ("v", "fv") and total > 1:
        rows.append(_nav_row(kind, idx, total))
    if kind == "v":
        rows.append([InlineKeyboardButton(text=t("b_filter", lang), callback_data=Flt(kind="v", by="menu").pack())])
    if is_admin:
        rows.append([
            InlineKeyboardButton(text="🛠 Yopish", callback_data=Act(a="xvc", id=v["id"], i=idx, k=kind).pack()),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=Act(a="xvd", id=v["id"], i=idx, k=kind).pack()),
        ])
    return text, InlineKeyboardMarkup(inline_keyboard=rows), (v.get("media_type") if has_media else None), v.get("media_file_id")


# ---------- rezyume kartasi ----------
async def resume_view(db: Database, r: dict, lang: str, uid: int, is_admin: bool, kind: str, idx: int = 0, total: int = 1):
    status = "" if r["status"] == "active" else f"{t('st_' + r['status'], lang)}\n\n"
    has_photo = bool(r.get("photo_file_id"))
    limit = CAPTION_LIMIT - len(status) if has_photo else 4000
    text = status + resume_card(r, lang, limit, footer=f"👁 {r.get('views') or 0}")
    fav = await db.is_fav(uid, "res", r["id"])
    rows = [
        [InlineKeyboardButton(text=t("b_res_pdf", lang), callback_data=Act(a="rp", id=r["id"], i=idx, k=kind).pack()),
         InlineKeyboardButton(text=t("b_res_doc", lang), callback_data=Act(a="rd", id=r["id"], i=idx, k=kind).pack())],
        [InlineKeyboardButton(text=t("b_contact", lang), callback_data=Act(a="rc", id=r["id"], i=idx, k=kind).pack()),
         InlineKeyboardButton(text=t("b_invite", lang), callback_data=Act(a="ri", id=r["id"], i=idx, k=kind).pack())],
        [InlineKeyboardButton(text=t("b_saved" if fav else "b_save", lang), callback_data=Act(a="rf", id=r["id"], i=idx, k=kind).pack())],
    ]
    if kind in ("r", "fr") and total > 1:
        rows.append(_nav_row(kind, idx, total))
    if kind == "r":
        rows.append([InlineKeyboardButton(text=t("b_filter", lang), callback_data=Flt(kind="r", by="menu").pack())])
    if is_admin:
        rows.append([
            InlineKeyboardButton(text="🙈 Yashirish", callback_data=Act(a="xrh", id=r["id"], i=idx, k=kind).pack()),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=Act(a="xrd", id=r["id"], i=idx, k=kind).pack()),
        ])
    return text, InlineKeyboardMarkup(inline_keyboard=rows), ("photo" if has_photo else None), r.get("photo_file_id")


async def show(event: Message | CallbackQuery, kind: str, idx: int, *, db: Database, state: FSMContext, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    item, total, idx = await get_item(db, state, user["id"], kind, idx)
    if item is None:
        empty = t("saved_none" if kind in ("fv", "fr") else "no_results", lang)
        kb = filter_kb(kind, lang) if kind in ("v", "r") else None
        await render(event, bot, empty, kb)
        return
    if kind in VAC_KINDS:
        if item.get("user_id") != user["id"]:
            await db.bump_vacancy_views(item["id"])
        view = await vacancy_view(db, item, lang, user["id"], is_admin, kind, idx, total, bot=bot)
    else:
        if item.get("user_id") != user["id"]:
            await db.bump_resume_views(item["id"])
        view = await resume_view(db, item, lang, user["id"], is_admin, kind, idx, total)
    await render(event, bot, *view)


async def show_vacancy(event: Message | CallbackQuery, vid: int, *, db: Database, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    v = await db.get_vacancy(vid)
    if not v or (v["status"] != "active" and v.get("user_id") != user["id"] and not is_admin):
        target = event.message if isinstance(event, CallbackQuery) else event
        await target.answer(t("not_found", lang))
        return
    if v.get("user_id") != user["id"]:
        await db.bump_vacancy_views(vid)
    await render(event, bot, *await vacancy_view(db, v, lang, user["id"], is_admin, "one", bot=bot))


async def show_resume(event: Message | CallbackQuery, rid: int, *, db: Database, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    r = await db.get_resume(rid)
    if not r or (r["status"] != "active" and r.get("user_id") != user["id"] and not is_admin):
        target = event.message if isinstance(event, CallbackQuery) else event
        await target.answer(t("not_found", lang))
        return
    if r.get("user_id") != user["id"]:
        await db.bump_resume_views(rid)
    await render(event, bot, *await resume_view(db, r, lang, user["id"], is_admin, "onr"))


# ---------- menyudan kirish ----------
async def open_filter(message: Message, kind: str, db: Database, lang: str) -> None:
    if kind == "v":
        n = await db.count_vacancies({})
        await message.answer(t("jobs_filter", lang, n=n), reply_markup=filter_kb("v", lang))
    else:
        n = await db.count_resumes({})
        await message.answer(t("cands_filter", lang, n=n), reply_markup=filter_kb("r", lang))


@router.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery) -> None:
    await cb.answer()


@router.callback_query(Flt.filter())
async def on_filter(cb: CallbackQuery, callback_data: Flt, state: FSMContext, db: Database, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    kind, by, v = callback_data.kind, callback_data.by, callback_data.v
    key = "vf" if kind == "v" else "rf"
    if by == "menu":
        n = await (db.count_vacancies({}) if kind == "v" else db.count_resumes({}))
        await render(cb, bot, t("jobs_filter" if kind == "v" else "cands_filter", lang, n=n), filter_kb(kind, lang))
        return await cb.answer()
    if by in ("cat", "city") and not v:
        await render(cb, bot, t("choose_cat" if by == "cat" else "choose_city", lang), filter_values_kb(kind, by, lang))
        return await cb.answer()
    if by == "q":
        await state.set_state(Browse.query)
        await state.update_data(qkind=kind)
        await cb.message.answer(t("ask_q", lang))
        return await cb.answer()
    if by == "match":
        r = await db.resume_by_user(user["id"])
        if not r:
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("b_create_resume", lang), callback_data=MyRes(a="create").pack())]])
            await cb.message.answer(t("need_match_resume", lang), reply_markup=kb)
            return await cb.answer()
        f = {"category": r.get("category"), "city": r.get("city")}
        if not await db.count_vacancies(f):
            f = {"category": r.get("category")}
    elif by == "all":
        f = {}
    else:
        f = {"category" if by == "cat" else "city": v}
    await state.update_data(**{key: f})
    await cb.answer()
    await show(cb, kind, 0, db=db, state=state, bot=bot, user=user, lang=lang, is_admin=is_admin)


@router.message(Browse.query, F.text)
async def on_query(message: Message, state: FSMContext, db: Database, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    data = await state.get_data()
    kind = data.get("qkind", "v")
    q = message.text.strip()[:60]
    await state.set_state(None)
    await state.update_data(**{"vf" if kind == "v" else "rf": {"q": q}})
    await show(message, kind, 0, db=db, state=state, bot=bot, user=user, lang=lang, is_admin=is_admin)


@router.callback_query(Nav.filter())
async def on_nav(cb: CallbackQuery, callback_data: Nav, state: FSMContext, db: Database, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    await cb.answer()
    await show(cb, callback_data.kind, callback_data.i, db=db, state=state, bot=bot, user=user, lang=lang, is_admin=is_admin)


# ---------- vakansiya amallari ----------
def _contact_parts(v: dict) -> tuple[str | None, str | None, str | None]:
    """(telefon, @telegram, boshqa havola) — e'lon maydonlaridan, bo'lmasa tugma sozlamasi va matnidan."""
    phone, tg, extra = v.get("contact_phone"), v.get("contact_tg"), None
    if not phone and not tg:
        kind, val = classify_target(v.get("apply_value"))
        if kind == "phone":
            phone = val
        elif kind == "url":
            extra = val
        text = v.get("description") or ""
        if not phone:
            m = PHONE_IN_TEXT.search(text)
            phone = m.group(0).strip() if m else None
        if not tg and not extra:
            m = TG_IN_TEXT.search(text)
            tg = m.group(0) if m else None
    return phone, tg, extra


def _vacancy_contacts(v: dict) -> str:
    return contact_lines(*_contact_parts(v))


def vacancy_contact_url(v: dict) -> str | None:
    """«Bog'lanish» havolasi: Telegram bo'lsa — o'sha chat, boshqa havola — o'sha, faqat raqam bo'lsa — shu raqamdagi
    Telegram hisobi (t.me/+998...). Telegram tugmasi to'g'ridan-to'g'ri qo'ng'iroq qila olmaydi."""
    phone, tg, extra = _contact_parts(v)
    if tg:
        kind, url = classify_target("@" + tg.strip().lstrip("@"))
        if kind == "url":
            return url
    if extra:
        return extra
    digits = re.sub(r"\D", "", normalize_phone(phone) or "")
    return f"https://t.me/+{digits}" if len(digits) >= 11 else None


def share_url(me: str, v: dict, lang: str) -> str:
    """«Ulashish»: Telegram'ning ulashish oynasi; do'st havolani bossa bot shu e'lonni (ID bo'yicha) ochadi."""
    link = f"https://t.me/{me}?start=vac_{v['id']}"
    text = t("share_text", lang, id=v["id"], title=v.get("title") or "")
    return f"https://t.me/share/url?url={quote(link, safe='')}&text={quote(text, safe='')}"


@router.callback_query(Act.filter(F.a == "open"))
async def act_open(cb: CallbackQuery, callback_data: Act, db: Database, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    await cb.answer()
    await show_vacancy(cb, callback_data.id, db=db, bot=bot, user=user, lang=lang, is_admin=is_admin)


@router.callback_query(Act.filter(F.a == "vc"))
async def act_vac_contact(cb: CallbackQuery, callback_data: Act, db: Database, lang: str) -> None:
    v = await db.get_vacancy(callback_data.id)
    if not v:
        return await cb.answer(t("not_found", lang), show_alert=True)
    lines = _vacancy_contacts(v)
    if not lines:  # chatga xabar yozilmaydi — faqat kichik oyna
        return await cb.answer(t("no_contact", lang), show_alert=True)
    await cb.answer()
    await cb.message.answer(
        t("contact_info", lang, lines=lines) if lines else t("no_contact", lang),
        reply_to_message_id=cb.message.message_id, disable_web_page_preview=True,
    )


@router.callback_query(Act.filter(F.a.in_({"vp", "vd"})))
async def act_vac_file(cb: CallbackQuery, callback_data: Act, db: Database, bot: Bot, lang: str) -> None:
    v = await db.get_vacancy(callback_data.id)
    if not v:
        return await cb.answer(t("not_found", lang), show_alert=True)
    await cb.answer(t("loading", lang))
    await bot.send_chat_action(cb.message.chat.id, "upload_document")
    doc = await files.vacancy_file(v, lang, "pdf" if callback_data.a == "vp" else "docx")
    await cb.message.answer_document(doc, caption=f"💼 <b>{h(v.get('title'))}</b>")


@router.callback_query(Act.filter(F.a == "vf"))
async def act_vac_fav(cb: CallbackQuery, callback_data: Act, state: FSMContext, db: Database, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    added = await db.toggle_fav(user["id"], "vac", callback_data.id)
    await cb.answer(t("fav_added" if added else "fav_removed", lang))
    v = await db.get_vacancy(callback_data.id)
    if not v:
        return
    kind = callback_data.k or "one"
    total = 1
    if kind in ("v", "fv"):
        _, total, _ = await get_item(db, state, user["id"], kind, callback_data.i)
    _, kb, _, _ = await vacancy_view(db, v, lang, user["id"], is_admin, kind, callback_data.i, max(total, 1), bot=bot)
    try:
        await cb.message.edit_reply_markup(reply_markup=kb)
    except TelegramBadRequest:
        pass


def _app_kb(aid: int, rid: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("b_res_pdf", lang), callback_data=Act(a="rp", id=rid, k="app").pack()),
         InlineKeyboardButton(text=t("b_res_doc", lang), callback_data=Act(a="rd", id=rid, k="app").pack())],
        [InlineKeyboardButton(text=t("b_accept", lang), callback_data=AppCb(id=aid, s="invited").pack())],
        [InlineKeyboardButton(text=t("b_reject", lang), callback_data=AppCb(id=aid, s="rejected").pack())],
    ])


@router.callback_query(Act.filter(F.a == "ap"))
async def act_apply(cb: CallbackQuery, callback_data: Act, db: Database, config: Config, bot: Bot, user: dict, lang: str) -> None:
    v = await db.get_vacancy(callback_data.id)
    if not v or v["status"] != "active":
        return await cb.answer(t("not_found", lang), show_alert=True)
    if v.get("user_id") == user["id"]:
        return await cb.answer(t("own_vacancy", lang), show_alert=True)
    r = await db.resume_by_user(user["id"])
    if not r:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("b_create_resume", lang), callback_data=MyRes(a="create").pack())]])
        await cb.answer()
        await cb.message.answer(t("need_resume", lang), reply_markup=kb)
        return
    if r["status"] != "active":
        return await cb.answer(t("resume_inactive", lang), show_alert=True)
    aid = await db.apply(v["id"], user["id"], r["id"])
    if aid is None:
        return await cb.answer(t("already_applied", lang), show_alert=True)
    await cb.answer(t("applied", lang), show_alert=True)

    recipients = [v["user_id"]] if v.get("user_id") else list(await notify.admin_ids(db, config))
    for uid in recipients:
        owner = await db.get_user(uid)
        olang = (owner or {}).get("lang") or "uz"
        text = t("n_new_app", olang, title=h(v.get("title")), name=h(r.get("full_name")), headline=h(r.get("headline") or "")) + "\n\n" + resume_card(r, olang, 3000, show_contacts=True)
        await notify.send(bot, db, uid, text, reply_markup=_app_kb(aid, r["id"], olang))


@router.callback_query(AppCb.filter())
async def app_answer(cb: CallbackQuery, callback_data: AppCb, db: Database, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    app = await db.get_application(callback_data.id)
    v = await db.get_vacancy(app["vacancy_id"]) if app else None
    if not app or not v:
        return await cb.answer(t("not_found", lang), show_alert=True)
    if v.get("user_id") != user["id"] and not is_admin:
        return await cb.answer("⛔️", show_alert=True)
    status = callback_data.s
    await db.set_application_status(app["id"], status)
    seeker = await db.get_user(app["user_id"])
    slang = (seeker or {}).get("lang") or "uz"
    if status == "invited":
        contact = _vacancy_contacts(v)
        if not contact and v.get("user_id"):
            owner = await db.get_user(v["user_id"])
            if owner and owner.get("username"):
                contact = f"✈️ @{owner['username']}"
        text = t("n_invited", slang, title=h(v.get("title")), contact=contact)
    else:
        text = t("n_rejected", slang, title=h(v.get("title")))
    await notify.send(bot, db, app["user_id"], text, disable_web_page_preview=True)
    await cb.answer(t("app_done", lang))
    label = t("app_invited" if status == "invited" else "app_rejected", lang)
    try:
        kb = cb.message.reply_markup.inline_keyboard[:1] if cb.message.reply_markup else []
        kb = kb + [[InlineKeyboardButton(text=label, callback_data="noop")]]
        await cb.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    except TelegramBadRequest:
        pass


# ---------- rezyume amallari ----------
async def _can_see_resume(db: Database, r: dict, user: dict, is_admin: bool, k: str) -> bool:
    return is_admin or r.get("user_id") == user["id"] or user.get("role") == "employer" or k in ("onr", "app")


@router.callback_query(Act.filter(F.a.in_({"rp", "rd"})))
async def act_res_file(cb: CallbackQuery, callback_data: Act, db: Database, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    r = await db.get_resume(callback_data.id)
    if not r:
        return await cb.answer(t("not_found", lang), show_alert=True)
    if not await _can_see_resume(db, r, user, is_admin, callback_data.k):
        return await cb.answer("⛔️", show_alert=True)
    await cb.answer(t("loading", lang))
    await bot.send_chat_action(cb.message.chat.id, "upload_document")
    doc = await files.resume_file(bot, r, lang, "pdf" if callback_data.a == "rp" else "docx")
    await cb.message.answer_document(doc, caption=f"👩‍💼 <b>{h(r.get('full_name'))}</b> — {h(r.get('headline') or '')}")


@router.callback_query(Act.filter(F.a == "rc"))
async def act_res_contact(cb: CallbackQuery, callback_data: Act, db: Database, user: dict, lang: str, is_admin: bool) -> None:
    r = await db.get_resume(callback_data.id)
    if not r:
        return await cb.answer(t("not_found", lang), show_alert=True)
    if not await _can_see_resume(db, r, user, is_admin, callback_data.k):
        return await cb.answer("⛔️", show_alert=True)
    tg = r.get("telegram")
    if not tg and r.get("user_id", 0) > 0:
        owner = await db.get_user(r["user_id"])
        tg = f"@{owner['username']}" if owner and owner.get("username") else None
    lines = contact_lines(r.get("phone"), tg)
    if r.get("user_id", 0) > 0 and not tg:
        lines += f"\n🔗 <a href=\"tg://user?id={r['user_id']}\">Telegram profil</a>"
    await cb.answer()
    await cb.message.answer(t("contact_info", lang, lines=lines.strip()) if lines.strip() else t("no_contact", lang), reply_to_message_id=cb.message.message_id)


@router.callback_query(Act.filter(F.a == "rf"))
async def act_res_fav(cb: CallbackQuery, callback_data: Act, state: FSMContext, db: Database, user: dict, lang: str, is_admin: bool) -> None:
    added = await db.toggle_fav(user["id"], "res", callback_data.id)
    await cb.answer(t("fav_added" if added else "fav_removed", lang))
    r = await db.get_resume(callback_data.id)
    if not r:
        return
    kind = callback_data.k or "onr"
    total = 1
    if kind in ("r", "fr"):
        _, total, _ = await get_item(db, state, user["id"], kind, callback_data.i)
    _, kb, _, _ = await resume_view(db, r, lang, user["id"], is_admin, kind, callback_data.i, max(total, 1))
    try:
        await cb.message.edit_reply_markup(reply_markup=kb)
    except TelegramBadRequest:
        pass


@router.callback_query(Act.filter(F.a == "ri"))
async def act_invite(cb: CallbackQuery, callback_data: Act, db: Database, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    r = await db.get_resume(callback_data.id)
    if not r:
        return await cb.answer(t("not_found", lang), show_alert=True)
    if r.get("user_id") == user["id"]:
        return await cb.answer("🙂", show_alert=False)
    vacs = [v for v in await db.user_vacancies(user["id"]) if v["status"] == "active"]
    if not vacs:
        await _send_invite(cb, bot, db, user, lang, r, None)
        return
    rows = [[InlineKeyboardButton(text=f"💼 {v['title'][:40]}", callback_data=InvCb(rid=r["id"], vid=v["id"]).pack())] for v in vacs[:10]]
    rows.append([InlineKeyboardButton(text=t("invite_general", lang), callback_data=InvCb(rid=r["id"], vid=0).pack())])
    await cb.answer()
    await cb.message.answer(t("invite_pick", lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(InvCb.filter())
async def on_invite_pick(cb: CallbackQuery, callback_data: InvCb, db: Database, bot: Bot, user: dict, lang: str) -> None:
    r = await db.get_resume(callback_data.rid)
    if not r:
        return await cb.answer(t("not_found", lang), show_alert=True)
    v = await db.get_vacancy(callback_data.vid) if callback_data.vid else None
    if v and v.get("user_id") != user["id"]:
        v = None
    await _send_invite(cb, bot, db, user, lang, r, v)
    try:
        await cb.message.delete()
    except TelegramBadRequest:
        pass


async def _send_invite(cb: CallbackQuery, bot: Bot, db: Database, user: dict, lang: str, r: dict, v: dict | None) -> None:
    if not await db.invite(user["id"], r["id"], v["id"] if v else None):
        return await cb.answer(t("invite_dup", lang), show_alert=True)
    seeker = await db.get_user(r["user_id"]) if r.get("user_id", 0) > 0 else None
    slang = (seeker or {}).get("lang") or "uz"
    employer = (v or {}).get("company") or user.get("full_name") or "Ish beruvchi"
    contact = contact_lines((v or {}).get("contact_phone"), (v or {}).get("contact_tg") or (f"@{user['username']}" if user.get("username") else None))
    if not contact:
        contact = f"🔗 <a href=\"tg://user?id={user['id']}\">{h(user.get('full_name'))}</a>"
    vac_line = f"💼 {h(v['title'])}\n" if v else ""
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👀 " + ("Вакансия" if slang == "ru" else "Vakansiyani ko'rish"),
                                                                     callback_data=Act(a="open", id=v["id"]).pack())]]) if v else None
    sent = await notify.send(bot, db, r["user_id"], t("n_invite", slang, employer=h(employer), vac=vac_line, contact=contact), reply_markup=kb)
    if not sent and r.get("phone"):
        # Telegram'siz (web) nomzod — ish beruvchiga telefonni ko'rsatamiz
        await cb.message.answer(t("contact_info", lang, lines=contact_lines(r.get("phone"), r.get("telegram"))))
    await cb.answer(t("invite_sent", lang), show_alert=True)


# ---------- admin tezkor amallari ----------
@router.callback_query(Act.filter(F.a.in_({"xvc", "xvd", "xrh", "xrd"})))
async def act_admin(cb: CallbackQuery, callback_data: Act, state: FSMContext, db: Database, config: Config, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    if not is_admin:
        return await cb.answer("⛔️", show_alert=True)
    a, item_id = callback_data.a, callback_data.id
    if a in ("xvc", "xvd"):
        v = await db.get_vacancy(item_id)
        if not v:
            return await cb.answer(t("not_found", lang), show_alert=True)
        await flow.unpublish_vacancy(bot, v, delete=(a == "xvd"))
        if a == "xvd":
            await db.delete_vacancy(item_id)
        else:
            await db.update_vacancy(item_id, status="closed")
        flow.background(websync.push(db, config, "vacancies", "delete", {"id": f"tg{item_id}"}))
    else:
        r = await db.get_resume(item_id)
        if not r:
            return await cb.answer(t("not_found", lang), show_alert=True)
        if a == "xrd":
            await db.delete_resume(item_id)
        else:
            await db.set_resume_status(item_id, "hidden")
        flow.background(websync.push(db, config, "resumes", "delete", {"id": f"tg{item_id}"}))
    await cb.answer("✅ Bajarildi")
    kind = callback_data.k
    if kind in ("v", "r", "fv", "fr"):
        await show(cb, kind, callback_data.i, db=db, state=state, bot=bot, user=user, lang=lang, is_admin=is_admin)
    else:
        try:
            await cb.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
