"""/start: til tanlash -> telefon raqam (ro'yxatdan o'tish / kirish) -> majburiy obuna -> rol tanlash -> menyu.
Deep-link'lar va kanal "telefon" tugmasi."""
from __future__ import annotations

import logging
import re

from aiogram import Bot, F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from ..callbacks import LangCb, Phone, RoleCb, SubCb
from ..db import Database
from ..keyboards import lang_kb, role_kb
from ..middlewares import is_subscribed, needs_phone, send_phone_prompt, send_sub_prompt
from ..texts import t
from ..utils import classify_target, normalize_phone
from .base import send_menu
from .browse import show_resume, show_vacancy
from .resume import start_resume

router = Router(name="start")
log = logging.getLogger(__name__)


async def proceed(message: Message, state: FSMContext, db: Database, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    """Onboarding'ning keyingi bosqichi yoki kutib turgan deep-link."""
    if needs_phone(user, is_admin):
        await send_phone_prompt(message, lang)
        return
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
    # kind == "post" (kanal postidagi «E'lon joylash») — alohida ishlanmaydi: oddiy /start kabi salomlashuv va
    # bosh menyu chiqadi, e'lon menyudagi «📢 E'lon berish» orqali beriladi
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
    if callback_data.kind == "contact":  # admin e'lonidagi «📞 Mijoz raqami»
        v = await db.get_vacancy(callback_data.id) if callback_data.id else None
        phone = next((b["v"] for b in (v or {}).get("extra_buttons") or [] if b.get("k") == "phone"), None)
        if not phone:
            return await cb.answer()
        return await cb.answer(t("phone_alert", lang, phone=phone), show_alert=True)
    field = "apply_value" if callback_data.kind == "apply" else "post_value"
    v = await db.get_vacancy(callback_data.id) if callback_data.id else None
    value = v[field] if v and v.get(field) is not None else db.setting(f"btn_{field}")
    kind, phone = classify_target(value)
    if kind != "phone":
        return await cb.answer()
    await cb.answer(t("phone_alert", lang, phone=phone), show_alert=True)


async def _unverified(message: Message, user: dict | None, is_admin: bool) -> bool:
    return needs_phone(user, is_admin)


@router.message(F.contact, _unverified)
async def on_auth_contact(message: Message, state: FSMContext, db: Database, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    """Ro'yxatdan o'tish / kirish. Faqat o'z raqami qabul qilinadi — birovning kontaktini yuborib, uning
    hisobiga (rezyume, arizalar) kirib bo'lmaydi."""
    contact = message.contact
    if contact.user_id != message.from_user.id:
        await message.answer(t("auth_not_own", lang))
        return await send_phone_prompt(message, lang)
    key = re.sub(r"\D", "", contact.phone_number or "")
    if len(key) < 9:
        await message.answer(t("auth_bad", lang))
        return await send_phone_prompt(message, lang)
    phone = normalize_phone(contact.phone_number) or "+" + key
    try:
        res = await db.claim_phone(user["id"], phone, key)
    except Exception:
        log.exception("Raqamni saqlab bo'lmadi (user=%s)", user["id"])
        await message.answer(t("auth_bad", lang))
        return await send_phone_prompt(message, lang)
    user = await db.get_user(user["id"])
    if res["restored"]:
        log.info("Hisob tiklandi: %s -> %s (%s)", key[-4:], user["id"], res)
        items = [t("auth_r_profile", lang)]
        if res["resume"]:
            items.append(t("auth_r_resume", lang))
        if res["apps"]:
            items.append(t("auth_r_apps", lang, n=res["apps"]))
        if res["vacs"]:
            items.append(t("auth_r_vacs", lang, n=res["vacs"]))
        if res["favs"]:
            items.append(t("auth_r_favs", lang, n=res["favs"]))
        text = t("auth_restored", lang, items="\n".join(f"• {i}" for i in items))
    else:
        text = t("auth_new", lang)
    await message.answer(text, reply_markup=ReplyKeyboardRemove())
    if user.get("is_banned") and not is_admin:
        return await message.answer(t("banned", lang))
    await proceed(message, state, db, bot, user, lang, is_admin)
