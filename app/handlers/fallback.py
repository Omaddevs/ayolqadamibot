"""Hech qaysi handler'ga tushmagan xabarlar — foydalanuvchini menyuga qaytaradi."""
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ..keyboards import lang_kb, role_kb
from ..texts import t
from .base import send_menu

router = Router(name="fallback")


@router.message()
async def unknown_message(message: Message, state: FSMContext, user: dict, lang: str, is_admin: bool) -> None:
    if await state.get_state():
        # wizard kutayotgan turdagi xabar emas (masalan, matn o'rniga stiker)
        await message.answer(t("bad_input", lang))
        return
    if not user.get("lang"):
        await message.answer(t("choose_lang", lang), reply_markup=lang_kb())
    elif not user.get("role"):
        await message.answer(t("choose_role", lang), reply_markup=role_kb(lang))
    else:
        await send_menu(message, user, lang, is_admin, t("main_menu", lang))


@router.callback_query()
async def unknown_callback(cb: CallbackQuery) -> None:
    # eski xabardagi tugma yoki wizard tugagandan keyin bosilgan tanlov
    await cb.answer("↻", show_alert=False)
