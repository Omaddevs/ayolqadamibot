"""Asosiy menyu tugmalari. Bu router birinchi ulanadi — shuning uchun istalgan holatda (wizard ichida ham)
menyu tugmasi bosilsa, joriy amal bekor bo'lib, tanlangan bo'lim ochiladi."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ..callbacks import MenuCb
from ..config import Config
from ..db import Database
from ..keyboards import role_kb
from ..texts import t, variants
from .base import send_menu
from .browse import open_filter, show
from .cabinet import open_support, show_my_applications, show_my_resume, show_my_vacancies, show_settings, show_web
from .ads import show_my_ads, start_ad

router = Router(name="menu")


async def _reset(state: FSMContext) -> None:
    """Wizard holatini tozalaydi, qidiruv filtrlarini saqlab qoladi."""
    data = await state.get_data()
    await state.clear()
    keep = {k: v for k, v in data.items() if k in ("vf", "rf")}
    if keep:
        await state.update_data(**keep)


@router.message(F.text.in_(variants("cancel")))
@router.message(Command("cancel"))
async def on_cancel(message: Message, state: FSMContext, user: dict, lang: str, is_admin: bool) -> None:
    await _reset(state)
    await send_menu(message, user, lang, is_admin, t("cancelled", lang))


@router.message(Command("menu"))
async def on_menu(message: Message, state: FSMContext, user: dict, lang: str, is_admin: bool) -> None:
    await _reset(state)
    await send_menu(message, user, lang, is_admin, t("main_menu", lang))


@router.message(F.text.in_(variants("m_jobs")))
async def m_jobs(message: Message, state: FSMContext, db: Database, lang: str) -> None:
    await _reset(state)
    await open_filter(message, "v", db, lang)


@router.message(F.text.in_(variants("m_candidates")))
async def m_candidates(message: Message, state: FSMContext, db: Database, lang: str) -> None:
    await _reset(state)
    await open_filter(message, "r", db, lang)


@router.message(F.text.in_(variants("m_resume")))
async def m_resume(message: Message, state: FSMContext, db: Database, bot: Bot, user: dict, lang: str) -> None:
    await _reset(state)
    await show_my_resume(message, db, bot, user, lang)


@router.message(F.text.in_(variants("m_post_vac")))
@router.message(F.text.in_(variants("m_post_ad")))
async def m_post_vac(message: Message, state: FSMContext, config: Config, user: dict, lang: str) -> None:
    # eski «Vakansiya joylash» ham yangi «E'lon berish» (shablonlar, web admin moderatsiyasi) ga olib boradi
    await start_ad(message, state, config, user, lang)


@router.message(F.text.in_(variants("m_my_vacs")))
async def m_my_vacs(message: Message, state: FSMContext, db: Database, bot: Bot, user: dict, lang: str) -> None:
    await _reset(state)
    await show_my_vacancies(message, db, bot, user, lang)


@router.message(F.text.in_(variants("m_apps")))
async def m_apps(message: Message, state: FSMContext, db: Database, lang: str) -> None:
    await _reset(state)
    await show_my_applications(message, db, lang)


@router.message(F.text.in_(variants("m_saved")))
async def m_saved(message: Message, state: FSMContext, db: Database, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    await _reset(state)
    kind = "fr" if user.get("role") == "employer" else "fv"
    await show(message, kind, 0, db=db, state=state, bot=bot, user=user, lang=lang, is_admin=is_admin)


@router.message(F.text.in_(variants("m_settings")))
async def m_settings(message: Message, state: FSMContext, user: dict, lang: str) -> None:
    await _reset(state)
    await show_settings(message, user, lang)


@router.message(F.text.in_(variants("m_help")))
@router.message(Command("help"))
async def m_help(message: Message, state: FSMContext, lang: str) -> None:
    await _reset(state)
    await open_support(message, state, lang)


@router.message(F.text.in_(variants("m_web")))
async def m_web(message: Message, state: FSMContext, config: Config, lang: str) -> None:
    await _reset(state)
    await show_web(message, config, lang)


# ---------- inline asosiy menyu ----------
@router.callback_query(MenuCb.filter())
async def on_menu_cb(cb: CallbackQuery, callback_data: MenuCb, state: FSMContext, db: Database, bot: Bot, config: Config,
                     user: dict, lang: str, is_admin: bool) -> None:
    await cb.answer()
    msg = cb.message
    a = callback_data.a
    if a != "post_ad":
        await _reset(state)
    if a == "jobs":
        await open_filter(msg, "v", db, lang)
    elif a == "candidates":
        await open_filter(msg, "r", db, lang)
    elif a == "resume":
        await show_my_resume(msg, db, bot, user, lang)
    elif a == "post_ad":
        await start_ad(msg, state, config, user, lang)
    elif a == "my_ads":
        await show_my_ads(msg, config, user, lang)
    elif a == "my_vacs":
        await show_my_vacancies(msg, db, bot, user, lang)
    elif a == "apps":
        await show_my_applications(msg, db, lang)
    elif a == "saved":
        kind = "fr" if user.get("role") == "employer" else "fv"
        await show(msg, kind, 0, db=db, state=state, bot=bot, user=user, lang=lang, is_admin=is_admin)
    elif a == "web":
        await show_web(msg, config, lang)
    elif a == "settings":
        await show_settings(msg, user, lang)
    elif a == "help":
        await open_support(msg, state, lang)
    elif a == "role":
        await msg.answer(t("choose_role", lang), reply_markup=role_kb(lang))


@router.message(F.text.in_(variants("m_my_ads")))
async def m_my_ads(message: Message, state: FSMContext, config: Config, user: dict, lang: str) -> None:
    await _reset(state)
    await show_my_ads(message, config, user, lang)
