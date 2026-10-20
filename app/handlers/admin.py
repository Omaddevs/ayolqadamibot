"""Admin panel."""
from __future__ import annotations

import asyncio
import csv
import io
import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ..callbacks import Adm, Mod, Pick, SupCb
from ..config import Config
from ..constants import cat_name
from ..db import Database
from ..keyboards import cancel_kb, categories_kb, cities_kb
from ..middlewares import reset_sub_cache
from ..services import flow, notify, websync
from ..states import AdminBroadcast, AdminInput, AdminPost
from ..texts import t, variants
from ..utils import classify_target, first_line_title, h, resume_card, short_date, vacancy_card
from .base import send_menu
from .browse import open_filter

log = logging.getLogger(__name__)
router = Router(name="admin")


async def _admin_only(event, is_admin: bool = False) -> bool:
    return is_admin


router.message.filter(_admin_only)
router.callback_query.filter(_admin_only)

ON, OFF = "✅", "❌"
_broadcast_running = False


def _b(text: str, a: str, v: str = "") -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=Adm(a=a, v=v).pack())


def _back(a: str = "home") -> list[InlineKeyboardButton]:
    return [_b("⬅️ Orqaga", a)]


def _flag(db: Database, key: str) -> str:
    return ON if db.flag(key) else OFF


async def _edit(cb: CallbackQuery, text: str, kb: InlineKeyboardMarkup | None) -> None:
    try:
        await cb.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    except TelegramBadRequest as e:
        if "not modified" in str(e):
            return
        await cb.message.answer(text, reply_markup=kb, disable_web_page_preview=True)


# ---------- bosh sahifa ----------
async def home_view(db: Database) -> tuple[str, InlineKeyboardMarkup]:
    s = await db.stats()
    pending = s["vac_pending"] + s["res_pending"]
    post_ch = len(await db.channels("post"))
    sub_ch = len(await db.channels("sub"))
    text = (
        "🛠 <b>Admin panel</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{s['users']}</b> (bugun +{s['new_day']})\n"
        f"💼 Faol vakansiyalar: <b>{s['vac_active']}</b> · 📄 Faol rezyumelar: <b>{s['res_active']}</b>\n"
        f"🕓 Moderatsiyada: <b>{pending}</b>\n\n"
        f"📡 E'lon kanallari: {post_ch} · 🔒 Majburiy obuna: {_flag(db, 'force_sub')} ({sub_ch} kanal)\n"
        f"🌐 Web sinxron: {_flag(db, 'web_sync')} · 🛡 Moderatsiya: {_flag(db, 'moderation')}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [_b("📢 E'lon joylash", "post"), _b("✉️ Xabar yuborish", "bc")],
        [_b("📊 Statistika", "stats"), _b(f"🕓 Moderatsiya ({pending})", "mod")],
        [_b("📡 E'lon kanallari", "ch", "post"), _b(f"🔒 Majburiy obuna {_flag(db, 'force_sub')}", "ch", "sub")],
        [_b("🔘 Kanal tugmalari", "btns"), _b(f"🌐 Web sinxron {_flag(db, 'web_sync')}", "web")],
        [_b("⚙️ Sozlamalar", "opts"), _b("👤 Foydalanuvchilar", "users")],
        [_b("📋 Vakansiyalar", "vlist"), _b("📄 Rezyumelar", "rlist")],
        [_b("👮 Adminlar", "admins")],
    ])
    return text, kb


@router.message(Command("admin"))
@router.message(F.text.in_(variants("m_admin")))
async def admin_home(message: Message, state: FSMContext, db: Database) -> None:
    await state.set_state(None)
    text, kb = await home_view(db)
    await message.answer(text, reply_markup=kb)


@router.callback_query(Adm.filter(F.a == "home"))
async def admin_home_cb(cb: CallbackQuery, state: FSMContext, db: Database) -> None:
    await state.set_state(None)
    await cb.answer()
    await _edit(cb, *await home_view(db))


# ---------- statistika ----------
@router.callback_query(Adm.filter(F.a == "stats"))
async def admin_stats(cb: CallbackQuery, db: Database) -> None:
    s = await db.stats()
    cats = "\n".join(f"   • {h(cat_name(r['category']))}: {r['n']}" for r in s["top_cats"]) or "   —"
    cities = "\n".join(f"   • {h(r['city'])}: {r['n']}" for r in s["top_cities"]) or "   —"
    text = (
        "📊 <b>Statistika</b>\n\n"
        f"<b>👥 Foydalanuvchilar: {s['users']}</b>\n"
        f"   👩 Ish izlovchi: {s['seekers']} · 🏢 Ish beruvchi: {s['employers']}\n"
        f"   🆕 Bugun: +{s['new_day']} · 7 kun: +{s['new_week']} · 30 kun: +{s['new_month']}\n"
        f"   🔥 Faol (24 soat): {s['active_day']} · (7 kun): {s['active_week']}\n"
        f"   🇺🇿 {s['lang_uz']} · 🇷🇺 {s['lang_ru']}\n"
        f"   🚫 Botni bloklagan: {s['blocked']} · ⛔️ Ban: {s['banned']}\n\n"
        f"<b>💼 Vakansiyalar: {s['vac_total']}</b>\n"
        f"   ✅ Faol: {s['vac_active']} · ⏳ Moderatsiya: {s['vac_pending']}\n"
        f"   📢 Admin e'lonlari: {s['vac_admin']} · 🌐 Saytdan: {s['vac_web']}\n\n"
        f"<b>📄 Rezyumelar: {s['res_total']}</b>\n"
        f"   ✅ Faol: {s['res_active']} · ⏳ Moderatsiya: {s['res_pending']}\n\n"
        f"<b>📨 Arizalar: {s['apps']}</b> (7 kun: {s['apps_week']}) · ✉️ Takliflar: {s['invites']}\n\n"
        f"<b>🗂 Top sohalar:</b>\n{cats}\n\n<b>📍 Top shaharlar:</b>\n{cities}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[_b("🔄 Yangilash", "stats"), _b("📥 Userlar CSV", "csv")], _back()])
    await cb.answer()
    await _edit(cb, text, kb)


@router.callback_query(Adm.filter(F.a == "csv"))
async def admin_csv(cb: CallbackQuery, db: Database) -> None:
    await cb.answer("⏳")
    buf = io.StringIO()
    writer = csv.writer(buf)
    cols = ["id", "username", "full_name", "lang", "role", "phone", "notify", "is_blocked", "is_banned", "created_at", "last_seen"]
    writer.writerow(cols)
    for u in await db.all_users():
        writer.writerow([u.get(c) for c in cols])
    rows = buf.getvalue().count("\n") - 1
    data = buf.getvalue().encode("utf-8-sig")
    await cb.message.answer_document(BufferedInputFile(data, filename="ayolqadam_users.csv"), caption=f"👥 {rows} ta foydalanuvchi")


# ---------- sozlamalar ----------
OPTS = [
    ("moderation", "🛡 Moderatsiya (foydalanuvchi e'lonlari tasdiqdan o'tadi)"),
    ("autopost_vac", "📢 Tasdiqlangan vakansiyalar kanalga avtomatik"),
    ("autopost_res", "📄 Rezyumelar kanalga avtomatik"),
    ("notify_match", "🔔 Yangi vakansiya mos nomzodlarga xabar qilinsin"),
    ("force_sub", "🔒 Majburiy obuna"),
    ("web_sync", "🌐 Web bilan sinxronlash"),
]


def _opts_view(db: Database) -> tuple[str, InlineKeyboardMarkup]:
    rows = [[_b(f"{_flag(db, k)} {label}", "tg", k)] for k, label in OPTS]
    rows.append(_back())
    return "⚙️ <b>Sozlamalar</b>\n\nYoqish/o'chirish uchun bosing:", InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(Adm.filter(F.a == "opts"))
async def admin_opts(cb: CallbackQuery, db: Database) -> None:
    await cb.answer()
    await _edit(cb, *_opts_view(db))


@router.callback_query(Adm.filter(F.a == "tg"))
async def admin_toggle(cb: CallbackQuery, callback_data: Adm, db: Database, config: Config) -> None:
    key = callback_data.v
    if key not in {k for k, _ in OPTS}:
        return await cb.answer()
    if key == "force_sub" and not db.flag("force_sub") and not await db.channels("sub"):
        return await cb.answer("Avval majburiy obuna kanalini qo'shing.", show_alert=True)
    new = await db.toggle(key)
    if key == "force_sub":
        reset_sub_cache()
    await cb.answer(f"{'Yoqildi' if new else 'Ochirildi'} {ON if new else OFF}")
    # qaysi sahifadan bosilgan bo'lsa, o'shani yangilaymiz
    origin = (cb.message.text or "")
    if origin.startswith("🔒"):
        await _edit(cb, *await _channels_view(db, "sub"))
    elif origin.startswith("🌐"):
        await _edit(cb, *await _web_view(db, config))
    else:
        await _edit(cb, *_opts_view(db))


# ---------- kanallar ----------
async def _channels_view(db: Database, kind: str) -> tuple[str, InlineKeyboardMarkup]:
    chans = await db.channels(kind)
    if kind == "sub":
        title = (f"🔒 <b>Majburiy obuna</b>: {_flag(db, 'force_sub')}\n\n"
                 "Yoqilganda foydalanuvchi til tanlagach, quyidagi kanallarga obuna bo'lmaguncha botdan foydalana olmaydi.\n"
                 "⚠️ Bot har bir kanalda <b>admin</b> bo'lishi shart.\n\n")
    else:
        title = ("📡 <b>E'lon kanallari</b>\n\nVakansiyalar (va yoqilgan bo'lsa rezyumelar) shu kanallarga "
                 "«Ishlamoqchiman» / «E'lon berish» tugmalari bilan joylanadi.\n⚠️ Bot kanalda <b>admin</b> bo'lishi shart.\n\n")
    title += "\n".join(f"• {h(c['title'])} <code>{c['chat_id']}</code>" for c in chans) or "Hali kanal qo'shilmagan."
    rows = [[_b(f"🗑 {c['title'][:30]}", "ch_del", f"{kind}|{c['chat_id']}")] for c in chans]
    rows.append([_b("➕ Kanal qo'shish", "ch_add", kind)])
    if kind == "sub":
        rows.append([_b(f"{'🔴 Ochirish' if db.flag('force_sub') else '🟢 Yoqish'}", "tg", "force_sub")])
    rows.append(_back())
    return title, InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(Adm.filter(F.a == "ch"))
async def admin_channels(cb: CallbackQuery, callback_data: Adm, db: Database) -> None:
    await cb.answer()
    await _edit(cb, *await _channels_view(db, callback_data.v))


@router.callback_query(Adm.filter(F.a == "ch_del"))
async def admin_channel_del(cb: CallbackQuery, callback_data: Adm, db: Database) -> None:
    kind, _, chat_id = callback_data.v.partition("|")
    await db.remove_channel(int(chat_id), kind)
    if kind == "sub":
        reset_sub_cache()
        if not await db.channels("sub") and db.flag("force_sub"):
            await db.set_setting("force_sub", "0")
    await cb.answer("🗑 O'chirildi")
    await _edit(cb, *await _channels_view(db, kind))


async def _ask_input(cb: CallbackQuery, state: FSMContext, purpose: str, prompt: str) -> None:
    await state.set_state(AdminInput.value)
    await state.update_data(purpose=purpose)
    await cb.answer()
    await cb.message.answer(prompt, reply_markup=cancel_kb("uz"), disable_web_page_preview=True)


@router.callback_query(Adm.filter(F.a == "ch_add"))
async def admin_channel_add(cb: CallbackQuery, callback_data: Adm, state: FSMContext) -> None:
    await _ask_input(cb, state, f"ch_add:{callback_data.v}",
                     "➕ Kanalni qo'shish uchun:\n• kanaldan istalgan postni shu yerga <b>forward</b> qiling, yoki\n"
                     "• kanal <b>@username</b> yoki <b>ID</b>sini (-100...) yuboring.\n\nAvval botni kanalga admin qilib qo'ying.")


async def _resolve_channel(message: Message, bot: Bot):
    origin = message.forward_origin
    chat_ref = None
    if origin is not None and getattr(origin, "chat", None) is not None:
        chat_ref = origin.chat.id
    elif message.forward_from_chat:
        chat_ref = message.forward_from_chat.id
    elif message.text:
        raw = message.text.strip().replace("https://t.me/", "@").split("/")[0]
        chat_ref = int(raw) if raw.lstrip("-").isdigit() else raw if raw.startswith("@") else "@" + raw
    if chat_ref is None:
        return None, "Kanal aniqlanmadi."
    try:
        chat = await bot.get_chat(chat_ref)
    except TelegramBadRequest as e:
        return None, f"Kanal topilmadi yoki bot unga qo'shilmagan: {h(e.message)}"
    try:
        me = await bot.get_chat_member(chat.id, (await bot.me()).id)
        if me.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
            return None, "⚠️ Bot bu kanalda admin emas. Avval botni admin qiling."
    except TelegramBadRequest as e:
        return None, f"Bot kanal a'zolarini tekshira olmadi: {h(e.message)}"
    link = f"https://t.me/{chat.username}" if chat.username else chat.invite_link
    if not link:
        try:
            link = await bot.export_chat_invite_link(chat.id)
        except TelegramBadRequest:
            link = None
    return (chat, link), None


# ---------- kanal tugmalari ----------
BTN_KEYS = [
    ("btn_apply_text", "«Ishlamoqchiman» tugma matni"),
    ("btn_apply_value", "«Ishlamoqchiman» havolasi"),
    ("btn_post_text", "«E'lon berish» tugma matni"),
    ("btn_post_value", "«E'lon berish» havolasi"),
]
VALUE_HELP = (
    "Qiymat formatlari:\n"
    "• <code>bot</code> — bot orqali (ariza / e'lon berish ustasi ochiladi)\n"
    "• <code>https://...</code> — istalgan havola (sayt, forma)\n"
    "• <code>@username</code> — Telegram profil yoki kanal\n"
    "• <code>+998 90 123 45 67</code> — telefon (bosilganda raqam ko'rsatiladi)\n"
    "• <code>-</code> — tugma chiqmasin"
)


def _describe_value(value: str) -> str:
    kind, val = classify_target(value)
    return {"bot": "🤖 bot orqali", "none": "🚫 tugmasiz", "url": f"🔗 {val}", "phone": f"📞 {val}"}[kind]


async def _btns_view(db: Database) -> tuple[str, InlineKeyboardMarkup]:
    text = (
        "🔘 <b>Kanal post tugmalari</b>\n\n"
        f"1️⃣ Matn: <b>{h(db.setting('btn_apply_text'))}</b>\n    Havola: {h(_describe_value(db.setting('btn_apply_value')))}\n\n"
        f"2️⃣ Matn: <b>{h(db.setting('btn_post_text'))}</b>\n    Havola: {h(_describe_value(db.setting('btn_post_value')))}\n\n"
        "Bular standart qiymatlar. Admin e'lon joylashda har bir post uchun alohida havola/telefon berishi mumkin.\n\n" + VALUE_HELP
    )
    rows = [[_b(f"✏️ {label}", "set", key)] for key, label in BTN_KEYS]
    rows.append([_b("👁 Namuna ko'rish", "btn_preview")])
    rows.append(_back())
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(Adm.filter(F.a == "btns"))
async def admin_btns(cb: CallbackQuery, db: Database) -> None:
    await cb.answer()
    await _edit(cb, *await _btns_view(db))


@router.callback_query(Adm.filter(F.a == "btn_preview"))
async def admin_btn_preview(cb: CallbackQuery, db: Database, bot: Bot) -> None:
    await cb.answer()
    kb = await flow.channel_kb(bot, db, {"id": 0, "apply_value": None, "post_value": None})
    await cb.message.answer("👁 <b>Kanal posti namunasi</b>\n\nVakansiya matni shu yerda bo'ladi...", reply_markup=kb)


@router.callback_query(Adm.filter(F.a == "set"))
async def admin_set(cb: CallbackQuery, callback_data: Adm, state: FSMContext, db: Database) -> None:
    key = callback_data.v
    if key not in {k for k, _ in BTN_KEYS}:
        return await cb.answer()
    current = db.setting(key)
    prompt = f"✏️ Yangi qiymatni yuboring.\nHozirgi: <code>{h(current)}</code>"
    if key.endswith("_value"):
        prompt += "\n\n" + VALUE_HELP
    await _ask_input(cb, state, f"set:{key}", prompt)


# ---------- web sinxron ----------
async def _web_view(db: Database, config: Config) -> tuple[str, InlineKeyboardMarkup]:
    api = f"✅ http://{config.api_host}:{config.api_port}/api" if config.api_enabled else "❌ o'chiq (.env: API_ENABLED=1)"
    text = (
        f"🌐 <b>Web bilan bog'lanish</b>: {_flag(db, 'web_sync')}\n\n"
        "Yoqilganda:\n"
        "• bot e'lon/rezyumelari saytga yuboriladi (WEB_API_URL),\n"
        "• sayt botning REST API'si orqali e'lonlarni o'qiydi va joylaydi.\n"
        "O'chirilganda bot to'liq mustaqil ishlaydi.\n\n"
        f"🔌 Bot API serveri: {api}\n"
        f"📤 WEB_API_URL: <code>{h(config.web_api_url or '—')}</code>\n"
        f"🔗 Sayt (WEB_URL): <code>{h(config.web_url or '—')}</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [_b(f"{'🔴 Ochirish' if db.flag('web_sync') else '🟢 Yoqish'}", "tg", "web_sync")],
        [_b("🔄 Ulanishni tekshirish", "web_check"), _b("⬆️ Hammasini yuborish", "web_push")],
        _back(),
    ])
    return text, kb


@router.callback_query(Adm.filter(F.a == "web"))
async def admin_web(cb: CallbackQuery, db: Database, config: Config) -> None:
    await cb.answer()
    await _edit(cb, *await _web_view(db, config))


@router.callback_query(Adm.filter(F.a == "web_check"))
async def admin_web_check(cb: CallbackQuery, config: Config) -> None:
    await cb.answer(f"WEB_API_URL: {await websync.check_web(config)}", show_alert=True)


@router.callback_query(Adm.filter(F.a == "web_push"))
async def admin_web_push(cb: CallbackQuery, db: Database, config: Config, bot: Bot) -> None:
    if not db.flag("web_sync") or not config.web_api_url:
        return await cb.answer("Web sinxron o'chiq yoki WEB_API_URL sozlanmagan.", show_alert=True)
    await cb.answer("⏳ Yuborilmoqda...")
    me = await flow.bot_username(bot)
    ok = fail = 0
    for v in await db.list_vacancies("active", limit=5000):
        if await websync.push(db, config, "vacancies", "upsert", websync.vacancy_to_web(v, me)):
            ok += 1
        else:
            fail += 1
    for r in await db.list_resumes("active", limit=5000):
        if await websync.push(db, config, "resumes", "upsert", websync.resume_to_web(r)):
            ok += 1
        else:
            fail += 1
    await cb.message.answer(f"⬆️ Web'ga yuborildi: ✅ {ok} · ❌ {fail}")


# ---------- moderatsiya ----------
async def _show_next_pending(message: Message, db: Database) -> None:
    pv = await db.list_vacancies("pending", limit=1)
    pr = await db.list_resumes("pending", limit=1)
    if pv:
        v = pv[0]
        await message.answer("🕓 <b>Moderatsiya — vakansiya</b>\n\n" + vacancy_card(v, "uz", 3500), reply_markup=flow.mod_kb("v", v["id"]), disable_web_page_preview=True)
    elif pr:
        r = pr[0]
        await message.answer("🕓 <b>Moderatsiya — rezyume</b>\n\n" + resume_card(r, "uz", 3500, show_contacts=True), reply_markup=flow.mod_kb("r", r["id"]))
    else:
        await message.answer("✅ Moderatsiyada hech narsa yo'q.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[_back()]))


@router.callback_query(Adm.filter(F.a == "mod"))
async def admin_mod(cb: CallbackQuery, db: Database) -> None:
    await cb.answer()
    await _show_next_pending(cb.message, db)


@router.callback_query(Mod.filter())
async def on_mod(cb: CallbackQuery, callback_data: Mod, db: Database, config: Config, bot: Bot) -> None:
    ok = bool(callback_data.ok)
    if callback_data.kind == "v":
        v = await db.get_vacancy(callback_data.id)
        if not v or v["status"] != "pending":
            await cb.answer("Allaqachon ko'rib chiqilgan.", show_alert=True)
            return await cb.message.edit_reply_markup(reply_markup=None)
        if ok:
            await flow.activate_vacancy(bot, db, config, v, notify_owner=True)
        else:
            await db.update_vacancy(v["id"], status="rejected")
            if v.get("user_id"):
                owner = await db.get_user(v["user_id"])
                await notify.send(bot, db, v["user_id"], t("n_vac_no", (owner or {}).get("lang"), title=h(v.get("title"))))
    else:
        r = await db.get_resume(callback_data.id)
        if not r or r["status"] != "pending":
            await cb.answer("Allaqachon ko'rib chiqilgan.", show_alert=True)
            return await cb.message.edit_reply_markup(reply_markup=None)
        if ok:
            await flow.activate_resume(bot, db, config, r, notify_owner=True)
        else:
            await db.set_resume_status(r["id"], "rejected")
            owner = await db.get_user(r["user_id"])
            await notify.send(bot, db, r["user_id"], t("n_res_no", (owner or {}).get("lang")))
    await cb.answer("✅ Tasdiqlandi" if ok else "❌ Rad etildi")
    by = cb.from_user.full_name
    try:
        await cb.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=f"{'✅ Tasdiqlandi' if ok else '❌ Rad etildi'} — {by}", callback_data="noop")
        ]]))
    except TelegramBadRequest:
        pass
    await _show_next_pending(cb.message, db)


# ---------- vakansiya/rezyumelar ro'yxati ----------
@router.callback_query(Adm.filter(F.a.in_({"vlist", "rlist"})))
async def admin_lists(cb: CallbackQuery, callback_data: Adm, db: Database) -> None:
    await cb.answer()
    await open_filter(cb.message, "v" if callback_data.a == "vlist" else "r", db, "uz")


# ---------- foydalanuvchilar ----------
@router.callback_query(Adm.filter(F.a == "users"))
async def admin_users(cb: CallbackQuery, state: FSMContext) -> None:
    await _ask_input(cb, state, "user_find", "👤 Foydalanuvchi <b>ID</b> yoki <b>@username</b> ini yuboring\n(yoki uning xabarini forward qiling):")


async def _user_card(db: Database, uid: int) -> tuple[str, InlineKeyboardMarkup] | None:
    u = await db.get_user(uid)
    if not u:
        return None
    r = await db.resume_by_user(uid)
    vacs = await db.user_vacancies(uid)
    text = (
        f"👤 <b>{h(u.get('full_name'))}</b>" + (f" (@{h(u['username'])})" if u.get("username") else "") + "\n"
        f"🆔 <code>{u['id']}</code> · <a href=\"tg://user?id={u['id']}\">profil</a>\n"
        f"Rol: {u.get('role') or '—'} · Til: {u.get('lang') or '—'}\n"
        f"📱 {h(u.get('phone') or '—')}\n"
        f"📅 Ro'yxatdan: {short_date(u['created_at'])} · Oxirgi: {short_date(u['last_seen'])}\n"
        f"📄 Rezyume: {r['status'] if r else '—'} · 💼 Vakansiyalar: {len(vacs)}\n"
        f"{'⛔️ BAN' if u['is_banned'] else ''} {'🚫 botni bloklagan' if u['is_blocked'] else ''}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [_b("✅ Bandan chiqarish" if u["is_banned"] else "⛔️ Ban qilish", "ban", str(uid)), _b("✉️ Xabar yozish", "msg", str(uid))],
        _back(),
    ])
    return text, kb


@router.callback_query(Adm.filter(F.a == "ban"))
async def admin_ban(cb: CallbackQuery, callback_data: Adm, db: Database, config: Config) -> None:
    uid = int(callback_data.v)
    if uid in config.admin_ids:
        return await cb.answer("Bosh adminni ban qilib bo'lmaydi.", show_alert=True)
    u = await db.get_user(uid)
    await db.update_user(uid, is_banned=0 if u and u["is_banned"] else 1)
    await cb.answer("✅")
    card = await _user_card(db, uid)
    if card:
        await _edit(cb, *card)


@router.callback_query(Adm.filter(F.a == "msg"))
async def admin_msg(cb: CallbackQuery, callback_data: Adm, state: FSMContext) -> None:
    await _ask_input(cb, state, f"msg:{callback_data.v}", "✉️ Foydalanuvchiga yuboriladigan xabarni yozing (matn, rasm, fayl — istalgan):")


@router.callback_query(SupCb.filter())
async def admin_support_reply(cb: CallbackQuery, callback_data: SupCb, state: FSMContext) -> None:
    await _ask_input(cb, state, f"reply:{callback_data.uid}", "💬 Javobingizni yozing:")


# ---------- adminlar ----------
async def _admins_view(db: Database, config: Config) -> tuple[str, InlineKeyboardMarkup]:
    extra = await db.db_admins()
    lines = [f"👑 <code>{x}</code> (.env)" for x in sorted(config.admin_ids)] + [f"👮 <code>{x}</code>" for x in sorted(extra)]
    rows = [[_b(f"🗑 {x}", "adm_del", str(x))] for x in sorted(extra)]
    rows.append([_b("➕ Admin qo'shish", "adm_add")])
    rows.append(_back())
    return "👮 <b>Adminlar</b>\n\n" + ("\n".join(lines) or "—") + "\n\n.env dagi bosh adminlar faqat serverda o'zgartiriladi.", InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(Adm.filter(F.a == "admins"))
async def admin_admins(cb: CallbackQuery, db: Database, config: Config) -> None:
    await cb.answer()
    await _edit(cb, *await _admins_view(db, config))


@router.callback_query(Adm.filter(F.a == "adm_add"))
async def admin_add_admin(cb: CallbackQuery, state: FSMContext, config: Config) -> None:
    if cb.from_user.id not in config.admin_ids:
        return await cb.answer("Faqat bosh admin (.env) admin qo'sha oladi.", show_alert=True)
    await _ask_input(cb, state, "admin_add", "👮 Yangi admin <b>ID</b> raqamini yuboring (u avval botga /start bosgan bo'lishi kerak):")


@router.callback_query(Adm.filter(F.a == "adm_del"))
async def admin_del_admin(cb: CallbackQuery, callback_data: Adm, db: Database, config: Config) -> None:
    if cb.from_user.id not in config.admin_ids:
        return await cb.answer("Faqat bosh admin (.env) adminlarni o'chira oladi.", show_alert=True)
    await db.remove_admin(int(callback_data.v))
    await cb.answer("🗑")
    await _edit(cb, *await _admins_view(db, config))


# ---------- bitta qiymat kiritish ----------
@router.message(AdminInput.value)
async def admin_input(message: Message, state: FSMContext, db: Database, config: Config, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    data = await state.get_data()
    purpose = data.get("purpose", "")
    await state.set_state(None)
    done = lambda text: send_menu(message, user, lang, is_admin, text)  # noqa: E731

    if purpose.startswith("ch_add:"):
        kind = purpose.split(":", 1)[1]
        result, error = await _resolve_channel(message, bot)
        if error:
            await state.set_state(AdminInput.value)
            await message.answer(error + "\n\nQayta urinib ko'ring yoki «❌ Bekor qilish».")
            return
        chat, link = result
        if kind == "sub" and not link:
            await done("⚠️ Kanal havolasini olib bo'lmadi (botga «Invite users» huquqini bering).")
            return
        await db.add_channel(chat.id, kind, chat.title or str(chat.id), link)
        reset_sub_cache()
        await done(f"✅ Qo'shildi: <b>{h(chat.title)}</b>")
        text, kb = await _channels_view(db, kind)
        await message.answer(text, reply_markup=kb)
        return

    if purpose.startswith("set:"):
        key = purpose.split(":", 1)[1]
        value = (message.text or "").strip()
        if not value or len(value) > 200:
            await done("⚠️ Noto'g'ri qiymat.")
            return
        if key.endswith("_value") and value not in ("-", "bot") and classify_target(value)[0] == "none":
            await state.set_state(AdminInput.value)
            await message.answer("⚠️ Havola, @username yoki telefon tanilmadi. Qayta yuboring.\n\n" + VALUE_HELP)
            return
        await db.set_setting(key, value)
        await done("✅ Saqlandi")
        text, kb = await _btns_view(db)
        await message.answer(text, reply_markup=kb, disable_web_page_preview=True)
        return

    if purpose == "user_find":
        uid = None
        origin = message.forward_origin
        if origin is not None and getattr(origin, "sender_user", None):
            uid = origin.sender_user.id
        raw = (message.text or "").strip()
        if uid is None and raw.lstrip("-").isdigit():
            uid = int(raw)
        elif uid is None and raw:
            row = await db.fetchone("SELECT id FROM users WHERE LOWER(username)=?", (raw.lstrip("@").lower(),))
            uid = row["id"] if row else None
        card = await _user_card(db, uid) if uid else None
        await done("👤")
        if not card:
            await message.answer("Foydalanuvchi topilmadi.")
            return
        await message.answer(card[0], reply_markup=card[1])
        return

    if purpose.startswith("msg:") or purpose.startswith("reply:"):
        uid = int(purpose.split(":", 1)[1])
        if purpose.startswith("reply:") and message.text:
            target = await db.get_user(uid)
            ok = await notify.send(bot, db, uid, t("sup_answer", (target or {}).get("lang"), text=h(message.text)))
        else:
            ok = await notify.safe_call(db, uid, lambda: message.copy_to(uid))
        await done("✅ Yuborildi" if ok else "❌ Yuborib bo'lmadi (foydalanuvchi botni bloklagan bo'lishi mumkin)")
        return

    if purpose == "admin_add":
        raw = (message.text or "").strip()
        if not raw.isdigit():
            await done("⚠️ ID faqat raqamlardan iborat bo'lishi kerak.")
            return
        await db.add_admin(int(raw))
        await done(f"✅ Admin qo'shildi: <code>{raw}</code>")
        return

    await done("🤷")


# ---------- xabar tarqatish ----------
@router.callback_query(Adm.filter(F.a == "bc"))
async def admin_broadcast(cb: CallbackQuery, db: Database) -> None:
    if _broadcast_running:
        return await cb.answer("Hozir boshqa xabar tarqatilmoqda, kuting.", show_alert=True)
    counts = {a: len(await db.user_ids(a)) for a in ("all", "seeker", "employer")}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [_b(f"👥 Hammaga ({counts['all']})", "bc_aud", "all")],
        [_b(f"👩 Ish izlovchilarga ({counts['seeker']})", "bc_aud", "seeker")],
        [_b(f"🏢 Ish beruvchilarga ({counts['employer']})", "bc_aud", "employer")],
        _back(),
    ])
    await cb.answer()
    await _edit(cb, "✉️ <b>Xabar yuborish</b>\n\nKimga yuboramiz?", kb)


@router.callback_query(Adm.filter(F.a == "bc_aud"))
async def admin_bc_aud(cb: CallbackQuery, callback_data: Adm, state: FSMContext) -> None:
    await state.update_data(bc_aud=callback_data.v)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [_b("📨 Oddiy xabar (nusxa)", "bc_mode", "copy")],
        [_b("↪️ Forward (manbasi ko'rinadi)", "bc_mode", "forward")],
        _back("bc"),
    ])
    await cb.answer()
    await _edit(cb, "Qanday ko'rinishda yuboramiz?\n\n📨 <b>Oddiy</b> — bot nomidan, tugma qo'shish mumkin.\n↪️ <b>Forward</b> — asl manba (kanal/foydalanuvchi) ko'rinadi.", kb)


@router.callback_query(Adm.filter(F.a == "bc_mode"))
async def admin_bc_mode(cb: CallbackQuery, callback_data: Adm, state: FSMContext) -> None:
    await state.update_data(bc_mode=callback_data.v)
    await state.set_state(AdminBroadcast.message)
    await cb.answer()
    await cb.message.answer("📝 Yuboriladigan xabarni yuboring yoki forward qiling (matn, rasm, video, fayl, ovozli...):", reply_markup=cancel_kb("uz"))


@router.message(AdminBroadcast.message)
async def admin_bc_message(message: Message, state: FSMContext) -> None:
    await state.update_data(bc_chat=message.chat.id, bc_msg=message.message_id, bc_btn=None)
    data = await state.get_data()
    if data.get("bc_mode") == "copy":
        await state.set_state(AdminBroadcast.button)
        await message.answer("🔘 Xabar tagiga tugma qo'shasizmi?\nFormat: <code>Tugma matni - https://havola</code>\n\nKerak bo'lmasa «⏭ O'tkazib yuborish».",
                             reply_markup=cancel_kb("uz", skip=True))
        return
    await _bc_confirm(message, state)


@router.message(AdminBroadcast.button, F.text)
async def admin_bc_button(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    if text not in variants("skip"):
        label, sep, url = text.rpartition(" - ")
        kind, link = classify_target(url.strip())
        if not sep or not label.strip() or kind != "url":
            await message.answer("⚠️ Format: <code>Tugma matni - https://havola</code>")
            return
        await state.update_data(bc_btn=[label.strip()[:60], link])
    await _bc_confirm(message, state)


def _bc_markup(btn) -> InlineKeyboardMarkup | None:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=btn[0], url=btn[1])]]) if btn else None


async def _bc_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(AdminBroadcast.confirm)
    await message.answer("👁 Namuna:", reply_markup=cancel_kb("uz"))
    if data["bc_mode"] == "forward":
        await message.bot.forward_message(message.chat.id, data["bc_chat"], data["bc_msg"])
    else:
        await message.bot.copy_message(message.chat.id, data["bc_chat"], data["bc_msg"], reply_markup=_bc_markup(data.get("bc_btn")))
    aud = {"all": "hammaga", "seeker": "ish izlovchilarga", "employer": "ish beruvchilarga"}[data["bc_aud"]]
    kb = InlineKeyboardMarkup(inline_keyboard=[[_b("🚀 Yuborish", "bc_go"), _b("❌ Bekor", "bc_cancel")]])
    await message.answer(f"Xabar <b>{aud}</b> yuboriladi. Tasdiqlaysizmi?", reply_markup=kb)


@router.callback_query(AdminBroadcast.confirm, Adm.filter(F.a.in_({"bc_go", "bc_cancel"})))
async def admin_bc_go(cb: CallbackQuery, callback_data: Adm, state: FSMContext, db: Database, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    global _broadcast_running
    data = await state.get_data()
    await state.set_state(None)
    await cb.message.edit_reply_markup(reply_markup=None)
    if callback_data.a == "bc_cancel":
        await cb.answer()
        await send_menu(cb.message, user, lang, is_admin, "Bekor qilindi.")
        return
    if _broadcast_running:
        return await cb.answer("Boshqa tarqatish davom etmoqda.", show_alert=True)
    await cb.answer("🚀")
    await send_menu(cb.message, user, lang, is_admin, "🚀 Tarqatish boshlandi. Yakunida hisobot yuboriladi.")
    _broadcast_running = True
    flow.background(_run_broadcast(bot, db, cb.from_user.id, data))


async def _run_broadcast(bot: Bot, db: Database, admin_id: int, data: dict) -> None:
    global _broadcast_running
    try:
        ids = await db.user_ids(data["bc_aud"])
        total, sent, failed = len(ids), 0, 0
        progress = await bot.send_message(admin_id, f"⏳ Yuborilmoqda: 0 / {total}")
        markup = _bc_markup(data.get("bc_btn"))
        for i, uid in enumerate(ids, 1):
            if data["bc_mode"] == "forward":
                ok = await notify.safe_call(db, uid, lambda: bot.forward_message(uid, data["bc_chat"], data["bc_msg"]))
            else:
                ok = await notify.safe_call(db, uid, lambda: bot.copy_message(uid, data["bc_chat"], data["bc_msg"], reply_markup=markup))
            sent += ok
            failed += not ok
            await asyncio.sleep(0.04)  # ~25 xabar/soniya — Telegram limitidan past
            if i % 200 == 0:
                try:
                    await bot.edit_message_text(f"⏳ Yuborilmoqda: {i} / {total}\n✅ {sent} · ❌ {failed}",
                                                chat_id=admin_id, message_id=progress.message_id)
                except TelegramBadRequest:
                    pass
        await db.log_broadcast(admin_id, data["bc_aud"], total, sent, failed)
        await bot.edit_message_text(f"✅ <b>Tarqatish yakunlandi</b>\n\nJami: {total}\n✅ Yetkazildi: {sent}\n❌ Yetkazilmadi: {failed}",
                                    chat_id=admin_id, message_id=progress.message_id)
    except Exception:
        log.exception("Broadcast xatosi")
        await notify.send(bot, db, admin_id, "❌ Tarqatishda xato yuz berdi, loglarni tekshiring.")
    finally:
        _broadcast_running = False


# ---------- admin e'lon joylash ----------
@router.callback_query(Adm.filter(F.a == "post"))
async def admin_post(cb: CallbackQuery, state: FSMContext, db: Database) -> None:
    channels = await db.channels("post")
    warn = "" if channels else "\n\n⚠️ E'lon kanali qo'shilmagan — e'lon faqat botga va saytga joylanadi."
    await state.set_state(AdminPost.message)
    await cb.answer()
    await cb.message.answer(
        "📢 <b>E'lon joylash</b>\n\nKanal, bot va saytga joylanadigan e'lonni yuboring: matn, rasm, video yoki fayl. "
        "Boshqa kanaldan <b>forward</b> qilsangiz ham bo'ladi — kanalga bot nomidan, tugmalar bilan chiqadi." + warn,
        reply_markup=cancel_kb("uz"),
    )


@router.message(AdminPost.message)
async def admin_post_message(message: Message, state: FSMContext) -> None:
    media_type = media_id = None
    if message.photo:
        media_type, media_id = "photo", message.photo[-1].file_id
    elif message.video:
        media_type, media_id = "video", message.video.file_id
    elif message.animation:
        media_type, media_id = "animation", message.animation.file_id
    elif message.document:
        media_type, media_id = "document", message.document.file_id
    text = message.text or message.caption or ""
    if not text and not media_id:
        await message.answer("⚠️ Bu turdagi xabarni e'lon sifatida joylab bo'lmaydi. Matn yoki media yuboring.")
        return
    await state.update_data(ap={
        "raw_chat_id": message.chat.id, "raw_message_id": message.message_id, "description": text,
        "media_type": media_type, "media_file_id": media_id,
    })
    if message.media_group_id:
        await message.answer("ℹ️ Albomdan faqat shu bitta element joylanadi.")
    await state.set_state(AdminPost.cat)
    await message.answer("🗂 Soha (botdagi qidiruv va sayt uchun):", reply_markup=categories_kb("uz", "acat", skip=True))


@router.callback_query(AdminPost.cat, Pick.filter(F.f == "acat"))
async def admin_post_cat(cb: CallbackQuery, callback_data: Pick, state: FSMContext) -> None:
    data = await state.get_data()
    data["ap"]["category"] = None if callback_data.v == "-" else callback_data.v
    await state.update_data(ap=data["ap"])
    await state.set_state(AdminPost.city)
    await cb.answer()
    await cb.message.edit_text("📍 Shahar:", reply_markup=cities_kb("uz", "acity", skip=True))


def _target_kb(field: str, default_value: str, allow_bot: bool) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"⭐ Standart: {_describe_value(default_value)}"[:60], callback_data=Pick(f=field, v="def").pack())]]
    if allow_bot:
        rows.append([InlineKeyboardButton(text="🤖 Bot orqali ariza", callback_data=Pick(f=field, v="bot").pack())])
    rows.append([InlineKeyboardButton(text="🔗 Havola / @username / telefon kiritish", callback_data=Pick(f=field, v="input").pack())])
    rows.append([InlineKeyboardButton(text="🚫 Tugmasiz", callback_data=Pick(f=field, v="none").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(AdminPost.city, Pick.filter(F.f == "acity"))
async def admin_post_city(cb: CallbackQuery, callback_data: Pick, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    data["ap"]["city"] = None if callback_data.v == "-" else callback_data.v
    await state.update_data(ap=data["ap"])
    await state.set_state(AdminPost.apply)
    await cb.answer()
    await cb.message.edit_text(f"1️⃣ «{h(db.setting('btn_apply_text'))}» tugmasi qayerga olib borsin?",
                               reply_markup=_target_kb("aap", db.setting("btn_apply_value"), True))


async def _ask_post_btn(message: Message, state: FSMContext, db: Database) -> None:
    await state.set_state(AdminPost.post)
    await message.answer(f"2️⃣ «{h(db.setting('btn_post_text'))}» tugmasi qayerga olib borsin?",
                         reply_markup=_target_kb("apo", db.setting("btn_post_value"), False))


async def _choose_target(cb: CallbackQuery, callback_data: Pick, state: FSMContext, db: Database, key: str, input_state, after) -> None:
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    if callback_data.v == "input":
        await state.set_state(input_state)
        await cb.message.answer("🔗 Havola, @username yoki telefon raqamini yuboring:\n\n" + VALUE_HELP, disable_web_page_preview=True)
        return
    data = await state.get_data()
    data["ap"][key] = {"def": None, "bot": "bot", "none": "-"}[callback_data.v]
    await state.update_data(ap=data["ap"])
    await after(cb.message, state, db)


async def _input_target(message: Message, state: FSMContext, db: Database, key: str, after) -> None:
    value = (message.text or "").strip()
    if classify_target(value)[0] in ("none", "bot"):
        await message.answer("⚠️ Tanilmadi. Masalan: <code>https://t.me/hr_admin</code>, <code>@hr_admin</code> yoki <code>+998901234567</code>")
        return
    data = await state.get_data()
    data["ap"][key] = value
    await state.update_data(ap=data["ap"])
    await after(message, state, db)


@router.callback_query(AdminPost.apply, Pick.filter(F.f == "aap"))
async def admin_post_apply(cb: CallbackQuery, callback_data: Pick, state: FSMContext, db: Database) -> None:
    await _choose_target(cb, callback_data, state, db, "apply_value", AdminPost.apply_input, _ask_post_btn)


@router.message(AdminPost.apply_input, F.text)
async def admin_post_apply_input(message: Message, state: FSMContext, db: Database) -> None:
    await _input_target(message, state, db, "apply_value", _ask_post_btn)


async def _post_preview(message: Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    ap = data["ap"]
    await state.set_state(AdminPost.confirm)
    kb = await flow.channel_kb(message.bot, db, {"id": 0, "apply_value": ap.get("apply_value"), "post_value": ap.get("post_value")})
    await message.answer("👁 <b>Kanalda shunday ko'rinadi:</b>")
    try:
        await message.bot.copy_message(message.chat.id, ap["raw_chat_id"], ap["raw_message_id"], reply_markup=kb)
    except TelegramBadRequest as e:
        await message.answer(f"⚠️ Xabarni nusxalab bo'lmadi: {h(e.message)}")
        await state.set_state(None)
        return
    channels = await db.channels("post")
    where = ", ".join(h(c["title"]) for c in channels) or "kanal yo'q"
    extra = []
    if ap.get("category"):
        extra.append(cat_name(ap["category"]))
    if ap.get("city"):
        extra.append(ap["city"])
    kb2 = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Joylash", callback_data=Pick(f="aok", v="1").pack()),
        InlineKeyboardButton(text="❌ Bekor", callback_data=Pick(f="aok", v="0").pack()),
    ]])
    await message.answer(f"📡 Kanallar: {where}\n🤖 Bot va 🌐 sayt: ha" + (f"\n🏷 {h(' · '.join(extra))}" if extra else "") + "\n\nJoylaymizmi?", reply_markup=kb2)


@router.callback_query(AdminPost.post, Pick.filter(F.f == "apo"))
async def admin_post_post(cb: CallbackQuery, callback_data: Pick, state: FSMContext, db: Database) -> None:
    await _choose_target(cb, callback_data, state, db, "post_value", AdminPost.post_input, _post_preview)


@router.message(AdminPost.post_input, F.text)
async def admin_post_post_input(message: Message, state: FSMContext, db: Database) -> None:
    await _input_target(message, state, db, "post_value", _post_preview)


@router.callback_query(AdminPost.confirm, Pick.filter(F.f == "aok"))
async def admin_post_confirm(cb: CallbackQuery, callback_data: Pick, state: FSMContext, db: Database, config: Config, bot: Bot,
                             user: dict, lang: str, is_admin: bool) -> None:
    data = await state.get_data()
    await state.set_state(None)
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    if callback_data.v != "1":
        await send_menu(cb.message, user, lang, is_admin, "Bekor qilindi.")
        return
    ap = data["ap"]
    v = await db.create_vacancy({
        **ap, "user_id": None, "source": "admin", "status": "pending",
        "title": first_line_title(ap.get("description") or "") if ap.get("description") else "E'lon",
    }, config.vacancy_days)
    posts = await flow.publish_vacancy(bot, db, v)
    await flow.activate_vacancy(bot, db, config, await db.get_vacancy(v["id"]))
    channels = {c["chat_id"]: c for c in await db.channels("post")}
    links = []
    for chat_id, msg_id in posts:
        ch = channels.get(chat_id) or {}
        link = ch.get("link") or ""
        url = f"{link}/{msg_id}" if link.startswith("https://t.me/") and "+" not in link and "joinchat" not in link else f"https://t.me/c/{str(chat_id).removeprefix('-100')}/{msg_id}"
        links.append(f"• <a href=\"{url}\">{h(ch.get('title') or chat_id)}</a>")
    report = f"✅ <b>E'lon joylandi</b> (#{v['id']})\n\n" + (("📡 Kanallar:\n" + "\n".join(links)) if links else "📡 Kanalga joylanmadi (kanal yo'q yoki xato).")
    await send_menu(cb.message, user, lang, is_admin, report)
