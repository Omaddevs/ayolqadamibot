"""Handler'lar uchun umumiy yordamchilar."""
from __future__ import annotations

from aiogram.types import Message

from ..keyboards import main_menu
from ..texts import t


async def send_menu(message: Message, user: dict, lang: str, is_admin: bool, text: str | None = None) -> None:
    await message.answer(
        text or t("welcome", lang, name=message.chat.full_name or ""),
        reply_markup=main_menu(lang, user.get("role"), is_admin),
    )


def is_skip(text: str | None, lang: str) -> bool:
    return (text or "").strip() in {t("skip", "uz"), t("skip", "ru")}
