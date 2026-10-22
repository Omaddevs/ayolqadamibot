"""Barcha inline tugmalar rangli: bot yuboradigan har bir so'rovdagi (xabar, rasm, tahrir, kanal posti)
rangsiz inline tugmalarga matniga qarab rang beriladi. Rangi aniq berilgan tugmalarga tegilmaydi.

Rang (Bot API `style`): danger — qizil, success — yashil, primary — ko'k."""
from __future__ import annotations

import re
from typing import Any

from aiogram import Bot
from aiogram.client.session.middlewares.base import BaseRequestMiddleware, NextRequestMiddlewareType
from aiogram.methods import TelegramMethod
from aiogram.methods.base import Response, TelegramType
from aiogram.types import InlineKeyboardMarkup

# bekor qilish, o'chirish, rad etish, yopish — qizil
_DANGER = re.compile(
    r"❌|🗑|🚫|⛔|bekor|o['ʻʼ‘’`]?chir|rad\b|rad et|yopish|yashir|chiqish|отмен|удал|отклон|закры|скры|выйти",
    re.IGNORECASE,
)
# tasdiqlash, joylash, saqlash, yuborish, ariza — yashil
_SUCCESS = re.compile(
    r"✅|✔|💾|📤|tasdiq|joyla|saqla|yubor|ariza|qabul|^ha\b|подтверд|опублик|размест|сохран|отправ|отклик|принят|^да\b",
    re.IGNORECASE,
)


def style_for(text: str) -> str:
    if _DANGER.search(text):
        return "danger"
    if _SUCCESS.search(text):
        return "success"
    return "primary"


def colorize(markup: Any) -> None:
    if not isinstance(markup, InlineKeyboardMarkup):
        return
    for row in markup.inline_keyboard:
        for btn in row:
            if not btn.style:
                btn.style = style_for(btn.text)


class ColorButtons(BaseRequestMiddleware):
    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        colorize(getattr(method, "reply_markup", None))
        return await make_request(bot, method)
