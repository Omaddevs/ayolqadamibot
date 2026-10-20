"""Asosiy menyu tugmalari. Bu router birinchi ulanadi — shuning uchun istalgan holatda (wizard ichida ham)
menyu tugmasi bosilsa, joriy amal bekor bo'lib, tanlangan bo'lim ochiladi."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..config import Config
from ..db import Database
from ..texts import t, variants
from .base import send_menu
from .browse import open_filter, show
from .cabinet import open_support, show_my_applications, show_my_resume, show_my_vacancies, show_settings, show_web
from .vacancy import start_vacancy

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
async def m_post_vac(message: Message, state: FSMContext, lang: str) -> None:
    await start_vacancy(message, state, lang)


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
