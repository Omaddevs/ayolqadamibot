"""Handler'lar uchun umumiy yordamchilar."""
from __future__ import annotations

from aiogram.types import Message, ReplyKeyboardRemove

from ..keyboards import admin_reply_kb, main_menu_inline
from ..texts import t


async def send_menu(message: Message, user: dict, lang: str, is_admin: bool, text: str | None = None) -> None:
    """1) holat matni — pastki klaviatura bilan (adminga «🛠 Admin panel», boshqalarga olib tashlanadi:
    wizard'lardagi «Bekor qilish» kabi tugmalar qolib ketmasin); 2) asosiy menyu — inline rangli tugmalar."""
    await message.answer(
        text or t("welcome", lang, name=message.chat.full_name or ""),
        reply_markup=admin_reply_kb(lang) if is_admin else ReplyKeyboardRemove(),
    )
    await message.answer(t("menu_pick", lang), reply_markup=main_menu_inline(lang, user.get("role")))


def is_skip(text: str | None, lang: str) -> bool:
    return (text or "").strip() in {t("skip", "uz"), t("skip", "ru")}
