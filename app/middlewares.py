"""Har bir yangilanish uchun: foydalanuvchini bazaga yozish, til/rol/admin ma'lumotini uzatish,
bloklanganlarni to'xtatish va majburiy obunani tekshirish."""
from __future__ import annotations

import logging
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.types import CallbackQuery, Message, TelegramObject

from .db import Database
from .keyboards import auth_phone_kb, sub_kb
from .services.notify import is_admin
from .texts import t

log = logging.getLogger(__name__)

# majburiy obunadan qat'i nazar ishlaydigan callback prefikslari
OPEN_CALLBACKS = {"lang", "sub", "ph"}
_sub_cache: dict[int, float] = {}
SUB_CACHE_TTL = 120


def _chat_type(event: TelegramObject) -> str | None:
    if isinstance(event, Message):
        return event.chat.type
    if isinstance(event, CallbackQuery) and event.message:
        return event.message.chat.type
    return ChatType.PRIVATE if isinstance(event, CallbackQuery) else None


class UserMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]) -> Any:
        from_user = data.get("event_from_user")
        chat_type = _chat_type(event)
        if chat_type == ChatType.CHANNEL and isinstance(event, CallbackQuery):
            # kanal postidagi tugma — foydalanuvchini bazaga yozmaymiz (u botni ishga tushirmagan bo'lishi mumkin)
            data.update(user=None, lang="uz", is_admin=False)
            return await handler(event, data)
        if chat_type != ChatType.PRIVATE or not from_user or from_user.is_bot:
            return None  # guruh va kanallardagi xabarlarni e'tiborsiz qoldiramiz

        db: Database = data["db"]
        user = await db.upsert_user(from_user.id, from_user.username, from_user.full_name)
        admin = await is_admin(db, data["config"], from_user.id)
        lang = user.get("lang") or ("ru" if (from_user.language_code or "").startswith("ru") else "uz")
        data.update(user=user, lang=lang, is_admin=admin)

        if user.get("is_banned") and not admin:
            if isinstance(event, CallbackQuery):
                await event.answer(t("banned", lang), show_alert=True)
            else:
                await event.answer(t("banned", lang))
            return None
        return await handler(event, data)


def needs_phone(user: dict | None, is_admin: bool) -> bool:
    """Til tanlangan, lekin raqam hali tasdiqlanmagan (adminlar .env'dagi ID bo'yicha — ularga talab yo'q)."""
    return bool(user) and not is_admin and bool(user.get("lang")) and not user.get("verified_at")


async def send_phone_prompt(target: Message, lang: str) -> None:
    await target.answer(t("auth_phone", lang), reply_markup=auth_phone_kb(lang))


class PhoneMiddleware(BaseMiddleware):
    """Ro'yxatdan o'tish majburiy: raqam yuborilmaguncha botning boshqa bo'limlari yopiq."""

    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]) -> Any:
        if not needs_phone(data.get("user"), data.get("is_admin", False)):
            return await handler(event, data)
        lang = data["lang"]
        if isinstance(event, Message):
            if event.contact or (event.text or "").startswith("/start"):
                return await handler(event, data)
            await send_phone_prompt(event, lang)
            return None
        if isinstance(event, CallbackQuery):
            if (event.data or "").split(":", 1)[0] in {"lang", "ph"}:
                return await handler(event, data)
            await event.answer(t("auth_need", lang), show_alert=True)
            if event.message:
                await send_phone_prompt(event.message, lang)
            return None
        return await handler(event, data)


async def is_subscribed(bot: Bot, db: Database, uid: int, use_cache: bool = True) -> bool:
    channels = await db.channels("sub")
    if not channels:
        return True
    if use_cache and _sub_cache.get(uid, 0) > time.monotonic():
        return True
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch["chat_id"], uid)
        except Exception as e:
            # bot kanalda admin emas yoki kanal o'chgan — foydalanuvchini qamab qo'ymaymiz
            log.warning("Obunani tekshirib bo'lmadi (%s): %s", ch["chat_id"], e)
            continue
        status = member.status
        if status in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED):
            return False
        if status == ChatMemberStatus.RESTRICTED and not getattr(member, "is_member", True):
            return False
    _sub_cache[uid] = time.monotonic() + SUB_CACHE_TTL
    return True


def reset_sub_cache() -> None:
    _sub_cache.clear()


async def send_sub_prompt(target: Message, db: Database, lang: str) -> None:
    await target.answer(t("sub_required", lang), reply_markup=sub_kb(await db.channels("sub"), lang))


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]) -> Any:
        db: Database = data["db"]
        user = data.get("user")
        if not db.flag("force_sub") or not user or data.get("is_admin") or not user.get("lang") or not user.get("verified_at"):
            return await handler(event, data)
        if isinstance(event, Message) and (event.text or "").startswith("/start"):
            return await handler(event, data)
        if isinstance(event, CallbackQuery) and (event.data or "").split(":", 1)[0] in OPEN_CALLBACKS:
            return await handler(event, data)
        bot: Bot = data["bot"]
        if await is_subscribed(bot, db, user["id"]):
            return await handler(event, data)
        lang = data["lang"]
        if isinstance(event, CallbackQuery):
            await event.answer(t("sub_fail", lang), show_alert=True)
            if event.message:
                await send_sub_prompt(event.message, db, lang)
        else:
            await send_sub_prompt(event, db, lang)
        return None
