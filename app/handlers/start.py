"""/start: til tanlash -> majburiy obuna -> rol tanlash -> menyu. Deep-link'lar va kanal "telefon" tugmasi."""
from __future__ import annotations

from aiogram import Bot, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ..callbacks import LangCb, Phone, RoleCb, SubCb
from ..db import Database
from ..keyboards import lang_kb, role_kb
from ..middlewares import is_subscribed, send_sub_prompt
from ..texts import t
from ..utils import classify_target
from .base import send_menu
from .browse import show_resume, show_vacancy
from .resume import start_resume
from .vacancy import start_vacancy

router = Router(name="start")


async def proceed(message: Message, state: FSMContext, db: Database, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    """Onboarding'ning keyingi bosqichi yoki kutib turgan deep-link."""
    if db.flag("force_sub") and not is_admin and not await is_subscribed(bot, db, user["id"], use_cache=False):
        await send_sub_prompt(message, db, lang)
        return
    if not user.get("role"):
        await message.answer(t("choose_role", lang), reply_markup=role_kb(lang))
        return
    data = await state.get_data()
    payload = data.get("start_payload")
    if payload:
        await state.update_data(start_payload=None)
        if await handle_payload(message, payload, state, db, bot, user, lang, is_admin):
            return
    await send_menu(message, user, lang, is_admin, t("welcome", lang, name=user.get("full_name") or ""))


async def handle_payload(message: Message, payload: str, state: FSMContext, db: Database, bot: Bot, user: dict, lang: str, is_admin: bool) -> bool:
    kind, _, raw_id = payload.partition("_")
    if kind in ("apply", "vac") and raw_id.isdigit():
        await send_menu(message, user, lang, is_admin, "👇")
        await show_vacancy(message, int(raw_id), db=db, bot=bot, user=user, lang=lang, is_admin=is_admin)
        return True
    if kind == "res" and raw_id.isdigit():
        await send_menu(message, user, lang, is_admin, "👇")
        await show_resume(message, int(raw_id), db=db, bot=bot, user=user, lang=lang, is_admin=is_admin)
        return True
    if kind == "post":
        if user.get("role") == "employer":
            await start_vacancy(message, state, lang)
        else:
            await start_resume(message, state, db, user, lang)
        return True
    return False


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext, db: Database, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    keep = {k: v for k, v in (await state.get_data()).items() if k in ("vf", "rf")}
    await state.clear()
    await state.update_data(start_payload=command.args, **keep)
    if not user.get("lang"):
        await message.answer(t("choose_lang", lang), reply_markup=lang_kb())
        return
    await proceed(message, state, db, bot, user, lang, is_admin)


@router.callback_query(LangCb.filter())
async def on_lang(cb: CallbackQuery, callback_data: LangCb, state: FSMContext, db: Database, bot: Bot, user: dict, is_admin: bool) -> None:
    lang = callback_data.code if callback_data.code in ("uz", "ru") else "uz"
    first_time = not user.get("lang")
    await db.update_user(user["id"], lang=lang)
    user = await db.get_user(user["id"])
    await cb.answer(t("lang_changed", lang))
    try:
        await cb.message.delete()
    except Exception:
        pass
    if first_time:
        await proceed(cb.message, state, db, bot, user, lang, is_admin)
    else:
        await send_menu(cb.message, user, lang, is_admin, t("lang_changed", lang))


@router.callback_query(SubCb.filter())
async def on_sub_check(cb: CallbackQuery, state: FSMContext, db: Database, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    if not user:
        return await cb.answer()
    if not await is_subscribed(bot, db, user["id"], use_cache=False):
        return await cb.answer(t("sub_fail", lang), show_alert=True)
    await cb.answer("✅")
    try:
        await cb.message.delete()
    except Exception:
        pass
    await proceed(cb.message, state, db, bot, user, lang, is_admin)


@router.callback_query(RoleCb.filter())
async def on_role(cb: CallbackQuery, callback_data: RoleCb, state: FSMContext, db: Database, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    first_time = not user.get("role")
    await db.update_user(user["id"], role=callback_data.role)
    user = await db.get_user(user["id"])
    await cb.answer(t("role_changed", lang))
    try:
        await cb.message.delete()
    except Exception:
        pass
    if first_time:
        await proceed(cb.message, state, db, bot, user, lang, is_admin)
    else:
        await send_menu(cb.message, user, lang, is_admin, t("role_changed", lang))


@router.callback_query(Phone.filter())
async def on_phone_button(cb: CallbackQuery, callback_data: Phone, db: Database, lang: str) -> None:
    """Kanal postidagi tugma telefon raqamga sozlangan bo'lsa — raqam alert oynada ko'rinadi."""
    field = "apply_value" if callback_data.kind == "apply" else "post_value"
    v = await db.get_vacancy(callback_data.id) if callback_data.id else None
    value = v[field] if v and v.get(field) is not None else db.setting(f"btn_{field}")
    kind, phone = classify_target(value)
    if kind != "phone":
        return await cb.answer()
    await cb.answer(t("phone_alert", lang, phone=phone), show_alert=True)
