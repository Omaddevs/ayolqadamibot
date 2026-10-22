"""E'lonlar hayot sikli: yuborish -> (moderatsiya) -> faollashtirish -> kanal + web + bildirishnomalar."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..callbacks import Act, Mod, Phone
from ..config import Config
from ..constants import cat_name
from ..db import Database
from ..texts import t
from ..utils import CAPTION_LIMIT, classify_target, resume_card, vacancy_card
from . import notify, websync

log = logging.getLogger(__name__)
_tasks: set[asyncio.Task] = set()


def background(coro) -> None:
    """Fon vazifasi (havola saqlanadi, aks holda GC uni to'xtatib qo'yishi mumkin)."""
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def bot_username(bot: Bot) -> str:
    return (await bot.me()).username


def _tag(text: str | None) -> str:
    return re.sub(r"[^\w]+", "_", (text or "").replace("'", "").replace("ʻ", "")).strip("_").lower()


async def channel_footer(bot: Bot, v: dict) -> str:
    tags = ["#vakansiya"]
    if v.get("city"):
        tags.append("#" + _tag(v["city"]))
    if v.get("category"):
        tags.append("#" + _tag(cat_name(v["category"]).split()[0]))
    return " ".join(tags) + f"\n\n🤖 @{await bot_username(bot)}"


def _target_button(text: str, value: str | None, deep_link: str, phone_cb: str) -> InlineKeyboardButton | None:
    kind, val = classify_target(value)
    if kind == "none":
        return None
    if kind == "bot":
        return InlineKeyboardButton(text=text, url=deep_link)
    if kind == "url":
        return InlineKeyboardButton(text=text, url=val)
    return InlineKeyboardButton(text=text, callback_data=phone_cb)


BUTTON_STYLES = {"", "primary", "danger", "success"}

# Admin e'lonidagi qo'shimcha tugmalar (hammasi ixtiyoriy): kalit -> (admin paneldagi nom, kanaldagi tugma matni)
EXTRA_SLOTS = {
    "phone": ("📞 Mijoz raqami", "📞 {v}"),
    "client": ("👤 Mijoz URL / @username", "✍️ Murojaat qilish"),
    "admin": ("🛠 Admin URL / @username", "👩‍💼 Admin bilan bog'lanish"),
    "site": ("🌐 Website URL", "🌐 Batafsil"),
}


def extra_rows(v: dict) -> list[list[InlineKeyboardButton]]:
    rows = []
    for b in v.get("extra_buttons") or []:
        slot, val = EXTRA_SLOTS.get(b.get("k")), b.get("v")
        if not slot or not val:
            continue
        if b["k"] == "phone":  # Telegram tugmasi qo'ng'iroq qila olmaydi — bosilganda raqam oynada ko'rinadi
            rows.append([InlineKeyboardButton(text=slot[1].format(v=val), callback_data=Phone(kind="contact", id=v.get("id") or 0).pack())])
            continue
        kind, url = classify_target(val)
        if kind == "url":
            rows.append([InlineKeyboardButton(text=slot[1], url=url)])
    return rows
_URL_RE = re.compile(r"^(https?://|tg://)\S+$")


def load_channel_buttons(db: Database) -> list[dict]:
    """Saqlangan rangli tugmalar ro'yxati (buzilgan JSON bo'lsa — bo'sh)."""
    try:
        items = json.loads(db.setting("channel_buttons") or "[]")
    except ValueError:
        return []
    out = []
    for b in items if isinstance(items, list) else []:
        if isinstance(b, dict) and str(b.get("text") or "").strip():
            style = str(b.get("style") or "")
            out.append({"text": str(b["text"]).strip()[:64], "url": str(b.get("url") or "").strip()[:500],
                        "style": style if style in BUTTON_STYLES else ""})
    return out[:8]


def custom_buttons(items: list[dict], me: str) -> list[InlineKeyboardButton]:
    """{post}/{site}/{bot} o'rniga havola qo'yiladi; havolasi bo'sh yoki noto'g'ri tugma tashlab ketiladi."""
    site = os.getenv("WEB_URL", "").strip().rstrip("/")
    links = {"post": f"https://t.me/{me}?start=post", "bot": f"https://t.me/{me}", "site": site}
    out = []
    for b in items:
        url = re.sub(r"\{(\w+)\}", lambda m: links.get(m.group(1), m.group(0)), b["url"])
        if not _URL_RE.match(url) or "{" in url:
            continue
        out.append(InlineKeyboardButton(text=b["text"], url=url, style=b["style"] or None))
    return out


async def channel_kb(bot: Bot, db: Database, v: dict | None = None, resume_id: int | None = None) -> InlineKeyboardMarkup | None:
    """Kanal posti tagidagi tugmalar: "Ishlamoqchiman" + rangli tugmalar (sayt admin panelidan) yoki eski "E'lon berish"."""
    me = await bot_username(bot)
    rows = []
    if v is not None:
        value = v.get("apply_value") if v.get("apply_value") is not None else db.setting("btn_apply_value")
        btn = _target_button(db.setting("btn_apply_text"), value, f"https://t.me/{me}?start=apply_{v['id']}",
                             Phone(kind="apply", id=v["id"]).pack())
        if btn:
            rows.append([btn])
        rows.extend(extra_rows(v))
    if resume_id is not None:
        rows.append([InlineKeyboardButton(text="📄 Rezyume (PDF / Word)", url=f"https://t.me/{me}?start=res_{resume_id}")])
    custom = load_channel_buttons(db)
    if custom:
        rows.extend([b] for b in custom_buttons(custom, me))
        return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None
    post_value = v.get("post_value") if v is not None and v.get("post_value") is not None else db.setting("btn_post_value")
    btn = _target_button(db.setting("btn_post_text"), post_value, f"https://t.me/{me}?start=post", Phone(kind="post", id=v["id"] if v else 0).pack())
    if btn:
        rows.append([btn])
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


# ---------- kanal ----------
async def publish_vacancy(bot: Bot, db: Database, v: dict) -> list[list[int]]:
    channels = await db.channels("post")
    if not channels:
        return []
    kb = await channel_kb(bot, db, v)
    footer = await channel_footer(bot, v)
    posts = []
    for ch in channels:
        try:
            if v.get("source") == "admin" and v.get("raw_chat_id"):
                msg = await bot.copy_message(ch["chat_id"], v["raw_chat_id"], v["raw_message_id"], reply_markup=kb)
                posts.append([ch["chat_id"], msg.message_id])
                continue
            if v.get("media_type") == "photo" and v.get("media_file_id"):
                msg = await bot.send_photo(ch["chat_id"], v["media_file_id"], caption=vacancy_card(v, "uz", CAPTION_LIMIT, footer), reply_markup=kb)
            else:
                msg = await bot.send_message(ch["chat_id"], vacancy_card(v, "uz", footer=footer), reply_markup=kb, disable_web_page_preview=True)
            posts.append([ch["chat_id"], msg.message_id])
        except Exception as e:
            log.warning("Kanalga joylab bo'lmadi %s: %s", ch["chat_id"], e)
    await db.update_vacancy(v["id"], channel_posts=posts)
    return posts


async def unpublish_vacancy(bot: Bot, v: dict, delete: bool = False) -> None:
    for chat_id, msg_id in v.get("channel_posts") or []:
        try:
            if delete:
                await bot.delete_message(chat_id, msg_id)
            else:
                await bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=None)
        except Exception as e:
            log.info("Kanal postini o'zgartirib bo'lmadi: %s", e)


async def publish_resume(bot: Bot, db: Database, r: dict) -> None:
    for ch in await db.channels("post"):
        try:
            kb = await channel_kb(bot, db, None, resume_id=r["id"])
            footer = "#rezyume " + ("#" + _tag(r["city"]) if r.get("city") else "") + f"\n\n🤖 @{await bot_username(bot)}"
            await bot.send_message(ch["chat_id"], resume_card(r, "uz", footer=footer), reply_markup=kb)
        except Exception as e:
            log.warning("Rezyumeni kanalga joylab bo'lmadi: %s", e)


# ---------- moderatsiya ----------
def mod_kb(kind: str, item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=Mod(kind=kind, id=item_id, ok=1).pack()),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=Mod(kind=kind, id=item_id, ok=0).pack()),
    ]])


async def submit_vacancy(bot: Bot, db: Database, cfg: Config, v: dict, force_moderation: bool = False) -> bool:
    """True — darhol e'lon qilindi, False — moderatsiyaga ketdi."""
    if force_moderation or db.flag("moderation"):
        await db.update_vacancy(v["id"], status="pending")
        text = "🕓 <b>Yangi vakansiya — moderatsiya</b>\n" + (f"Manba: {v['source']}\n" if v.get("source") != "bot" else "") + "\n" + vacancy_card(v, "uz", 3500)
        await notify.send_admins(bot, db, cfg, text, reply_markup=mod_kb("v", v["id"]), disable_web_page_preview=True)
        return False
    await activate_vacancy(bot, db, cfg, v)
    return True


async def activate_vacancy(bot: Bot, db: Database, cfg: Config, v: dict, notify_owner: bool = False) -> dict:
    await db.update_vacancy(v["id"], status="active")
    v = await db.get_vacancy(v["id"])
    if db.flag("autopost_vac") and not v.get("channel_posts"):
        await publish_vacancy(bot, db, v)
        v = await db.get_vacancy(v["id"])
    background(websync.push(db, cfg, "vacancies", "upsert", websync.vacancy_to_web(v, await bot_username(bot))))
    if notify_owner and v.get("user_id"):
        owner = await db.get_user(v["user_id"])
        await notify.send(bot, db, v["user_id"], t("n_vac_ok", owner and owner.get("lang"), title=v.get("title")))
    if db.flag("notify_match") and v.get("category"):
        background(notify_matches(bot, db, v))
    return v


async def notify_matches(bot: Bot, db: Database, v: dict) -> None:
    ids = await db.match_seekers(v["category"], v.get("city"))
    for uid in ids:
        if uid == v.get("user_id"):
            continue
        user = await db.get_user(uid)
        lang = (user or {}).get("lang") or "uz"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="👀 " + ("Подробнее" if lang == "ru" else "Batafsil"), callback_data=Act(a="open", id=v["id"]).pack())
        ]])
        text = t("n_match", lang) + "\n\n" + vacancy_card(v, lang, 1500)
        await notify.send(bot, db, uid, text, reply_markup=kb, disable_web_page_preview=True)
        await asyncio.sleep(0.05)


async def submit_resume(bot: Bot, db: Database, cfg: Config, r: dict, force_moderation: bool = False) -> bool:
    if force_moderation or db.flag("moderation"):
        await db.set_resume_status(r["id"], "pending")
        text = "🕓 <b>Yangi rezyume — moderatsiya</b>\n\n" + resume_card(r, "uz", 3500, show_contacts=True)
        await notify.send_admins(bot, db, cfg, text, reply_markup=mod_kb("r", r["id"]))
        return False
    await activate_resume(bot, db, cfg, r)
    return True


async def activate_resume(bot: Bot, db: Database, cfg: Config, r: dict, notify_owner: bool = False) -> dict:
    await db.set_resume_status(r["id"], "active")
    r = await db.get_resume(r["id"])
    if db.flag("autopost_res"):
        await publish_resume(bot, db, r)
    background(websync.push(db, cfg, "resumes", "upsert", websync.resume_to_web(r)))
    if notify_owner:
        owner = await db.get_user(r["user_id"])
        await notify.send(bot, db, r["user_id"], t("n_res_ok", (owner or {}).get("lang")))
    return r


async def expire_loop(bot: Bot, db: Database, cfg: Config) -> None:
    """Har soatda muddati o'tgan vakansiyalarni yopadi va egasiga xabar beradi."""
    while True:
        try:
            for v in await db.expire_vacancies():
                await unpublish_vacancy(bot, v)
                background(websync.push(db, cfg, "vacancies", "delete", {"id": f"tg{v['id']}"}))
                if v.get("user_id"):
                    owner = await db.get_user(v["user_id"])
                    await notify.send(bot, db, v["user_id"], t("n_expired", (owner or {}).get("lang"), title=v.get("title")))
        except Exception:
            log.exception("expire_loop xatosi")
        await asyncio.sleep(3600)
