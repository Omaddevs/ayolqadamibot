"""Rezyume yaratish ustasi. Qayta to'ldirishda "⏭ O'tkazib yuborish" eski qiymatni saqlab qoladi."""
from __future__ import annotations

import re
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ..callbacks import Pick
from ..config import Config
from ..constants import cat_name, edu_name, exp_name
from ..db import Database
from ..keyboards import cancel_kb, categories_kb, cities_kb, edu_kb, exp_kb, langs_kb, phone_kb, types_kb
from ..services import files, flow
from ..states import ResumeForm
from ..texts import t
from ..utils import CAPTION_LIMIT, h, normalize_phone, parse_int, resume_card
from .base import is_skip, send_menu

router = Router(name="resume")

# qadam, maydon, turi, majburiymi
STEPS = [
    ("name", "full_name", "text", True),
    ("birth", "birth_year", "year", False),
    ("phone", "phone", "phone", True),
    ("city", "city", "pick", True),
    ("cat", "category", "pick", True),
    ("headline", "headline", "text", True),
    ("exp_level", "exp_level", "pick", True),
    ("exp", "experience", "text", False),
    ("edu_level", "edu_level", "pick", False),
    ("edu", "education", "text", False),
    ("skills", "skills", "list", False),
    ("langs", "languages", "multi", True),
    ("types", "job_types", "multi", True),
    ("salary", "salary", "int", False),
    ("about", "about", "text", False),
    ("photo", "photo_file_id", "photo", False),
]
STEP = {s[0]: s for s in STEPS}
ORDER = [s[0] for s in STEPS]
LIMITS = {"full_name": 80, "headline": 100, "experience": 1500, "education": 300, "about": 1500}
TEXT_STATES = [getattr(ResumeForm, s[0]) for s in STEPS if s[2] in ("text", "year", "int", "list", "phone")]


def _state_name(state: str | None) -> str | None:
    return state.split(":", 1)[1] if state and state.startswith("ResumeForm:") else None


async def start_resume(message: Message, state: FSMContext, db: Database, user: dict, lang: str) -> None:
    old = await db.resume_by_user(user["id"]) or {}
    keep = {k: v for k, v in (await state.get_data()).items() if k in ("vf", "rf")}
    await state.clear()
    await state.update_data(r={}, old=old, **keep)
    await message.answer(t("r_intro", lang), reply_markup=cancel_kb(lang))
    await ask(message, state, "name", lang)


def _hint(old_value, lang: str) -> str:
    if old_value in (None, "", []):
        return ""
    if isinstance(old_value, list):
        old_value = ", ".join(map(str, old_value))
    label = "Текущее" if lang == "ru" else "Hozirgi"
    value = str(old_value)
    return f"\n\n<i>{label}: {h(value[:120])}{'…' if len(value) > 120 else ''}</i>"


async def ask(message: Message, state: FSMContext, step: str, lang: str) -> None:
    _, field, kind, required = STEP[step]
    data = await state.get_data()
    old = (data.get("old") or {}).get(field)
    can_skip = not required or old not in (None, "", [])
    await state.set_state(getattr(ResumeForm, step))
    text = t(f"r_{step}", lang)

    if kind == "pick":
        if step == "city":
            kb, cb_field = cities_kb(lang, "city"), "city"
        elif step == "cat":
            kb, cb_field = categories_kb(lang, "cat"), "cat"
        elif step == "exp_level":
            kb, cb_field = exp_kb(lang, "exp"), "exp"
        else:
            kb, cb_field = edu_kb(lang, "edu"), "edu"
        if can_skip:
            kb.inline_keyboard.append([InlineKeyboardButton(text=t("skip", lang), callback_data=Pick(f=cb_field, v="-").pack())])
        shown = {"cat": cat_name, "exp_level": exp_name, "edu_level": edu_name}.get(step)
        await message.answer(text + _hint(shown(old, lang) if shown and old else old, lang), reply_markup=kb)
        return
    if kind == "multi":
        r = data.get("r") or {}
        selected = r.get(field) or old or (["uz"] if step == "langs" else [])
        r[field] = list(selected)
        await state.update_data(r=r)
        kb = langs_kb(selected, lang) if step == "langs" else types_kb(selected, lang)
        await message.answer(text, reply_markup=kb)
        return
    if kind == "phone":
        await message.answer(text + _hint(old, lang), reply_markup=phone_kb(lang, skip=can_skip))
        return
    await message.answer(text + _hint(old, lang), reply_markup=cancel_kb(lang, skip=can_skip))


async def next_step(message: Message, state: FSMContext, current: str, lang: str, db: Database, bot: Bot) -> None:
    data = await state.get_data()
    r = data.get("r") or {}
    i = ORDER.index(current) + 1
    while i < len(ORDER):
        step = ORDER[i]
        if step == "exp" and r.get("exp_level") == "0":
            r["experience"] = None
            i += 1
            continue
        if step == "edu" and not r.get("edu_level"):
            r["education"] = (data.get("old") or {}).get("education")
            i += 1
            continue
        break
    await state.update_data(r=r)
    if i >= len(ORDER):
        await show_preview(message, state, lang, bot)
        return
    await ask(message, state, ORDER[i], lang)


async def _set(state: FSMContext, field: str, value) -> None:
    data = await state.get_data()
    r = data.get("r") or {}
    r[field] = value
    await state.update_data(r=r)


async def _keep_old(state: FSMContext, field: str):
    data = await state.get_data()
    return (data.get("old") or {}).get(field)


# ---------- matnli qadamlar ----------
@router.message(StateFilter(*TEXT_STATES), F.text)
async def on_text(message: Message, state: FSMContext, db: Database, bot: Bot, lang: str) -> None:
    step = _state_name(await state.get_state())
    _, field, kind, required = STEP[step]
    text = message.text.strip()

    if is_skip(text, lang):
        old = await _keep_old(state, field)
        if required and old in (None, "", []):
            await message.answer(t("bad_input", lang))
            return
        await _set(state, field, old)
        await next_step(message, state, step, lang, db, bot)
        return

    if kind == "text":
        limit = LIMITS.get(field, 500)
        if len(text) > limit:
            await message.answer(t("too_long", lang, n=limit))
            return
        if len(text) < 2:
            await message.answer(t("bad_input", lang))
            return
        value = text
    elif kind == "year":
        year = int(text) if re.fullmatch(r"\d{4}", text) else 0
        if not 1950 <= year <= datetime.now().year - 14:
            await message.answer(t("bad_year", lang))
            return
        value = year
    elif kind == "phone":
        value = normalize_phone(text)
        if not value:
            await message.answer(t("bad_phone", lang))
            return
    elif kind == "int":
        value = parse_int(text)
        if not value or value < 100_000 or value > 1_000_000_000:
            await message.answer(t("bad_number", lang))
            return
    else:  # list
        items, seen = [], set()
        for raw in re.split(r"[,;\n]+", text):
            s = raw.strip(" .•-")[:40]
            if len(s) >= 2 and s.lower() not in seen:
                seen.add(s.lower())
                items.append(s)
        if not items:
            await message.answer(t("bad_input", lang))
            return
        value = items[:20]
    await _set(state, field, value)
    await next_step(message, state, step, lang, db, bot)


@router.message(ResumeForm.phone, F.contact)
async def on_contact(message: Message, state: FSMContext, db: Database, bot: Bot, user: dict, lang: str) -> None:
    phone = normalize_phone(message.contact.phone_number) or message.contact.phone_number
    await _set(state, "phone", phone)
    if message.contact.user_id == user["id"]:
        await db.update_user(user["id"], phone=phone)
    await next_step(message, state, "phone", lang, db, bot)


@router.message(ResumeForm.photo, F.photo)
async def on_photo(message: Message, state: FSMContext, db: Database, bot: Bot, lang: str) -> None:
    await _set(state, "photo_file_id", message.photo[-1].file_id)
    await next_step(message, state, "photo", lang, db, bot)


@router.message(ResumeForm.photo, F.text)
async def on_photo_text(message: Message, state: FSMContext, db: Database, bot: Bot, lang: str) -> None:
    if is_skip(message.text, lang):
        await _set(state, "photo_file_id", await _keep_old(state, "photo_file_id"))
        await next_step(message, state, "photo", lang, db, bot)
    else:
        await message.answer(t("r_photo", lang))


# ---------- tanlov qadamlari ----------
PICK_STEP = {"city": "city", "cat": "cat", "exp": "exp_level", "edu": "edu_level"}


@router.callback_query(StateFilter(ResumeForm.city, ResumeForm.cat, ResumeForm.exp_level, ResumeForm.edu_level), Pick.filter(F.f.in_(PICK_STEP.keys())))
async def on_pick(cb: CallbackQuery, callback_data: Pick, state: FSMContext, db: Database, bot: Bot, lang: str) -> None:
    step = PICK_STEP[callback_data.f]
    if _state_name(await state.get_state()) != step:
        return await cb.answer()
    _, field, _, required = STEP[step]
    value = callback_data.v
    if value == "-":
        value = await _keep_old(state, field)
        if required and not value:
            return await cb.answer(t("pick_one", lang), show_alert=True)
    await _set(state, field, value)
    await cb.answer()
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await next_step(cb.message, state, step, lang, db, bot)


@router.callback_query(StateFilter(ResumeForm.langs, ResumeForm.types), Pick.filter(F.f.in_({"lng", "jts"})))
async def on_multi(cb: CallbackQuery, callback_data: Pick, state: FSMContext, db: Database, bot: Bot, lang: str) -> None:
    step = "langs" if callback_data.f == "lng" else "types"
    if _state_name(await state.get_state()) != step:
        return await cb.answer()
    field = STEP[step][1]
    data = await state.get_data()
    r = data.get("r") or {}
    selected = list(r.get(field) or [])
    if callback_data.v == "_done":
        if not selected:
            return await cb.answer(t("pick_one", lang), show_alert=True)
        await cb.answer()
        await cb.message.edit_reply_markup(reply_markup=None)
        await next_step(cb.message, state, step, lang, db, bot)
        return
    if callback_data.v in selected:
        selected.remove(callback_data.v)
    else:
        selected.append(callback_data.v)
    r[field] = selected
    await state.update_data(r=r)
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=langs_kb(selected, lang) if step == "langs" else types_kb(selected, lang))


# ---------- ko'rib chiqish va saqlash ----------
def _confirm_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("r_save", lang), callback_data=Pick(f="rc", v="save").pack())],
        [InlineKeyboardButton(text=t("r_restart", lang), callback_data=Pick(f="rc", v="restart").pack()),
         InlineKeyboardButton(text=t("cancel", lang), callback_data=Pick(f="rc", v="cancel").pack())],
    ])


async def show_preview(message: Message, state: FSMContext, lang: str, bot: Bot) -> None:
    await state.set_state(ResumeForm.confirm)
    data = await state.get_data()
    r = data.get("r") or {}
    if r.get("photo_file_id"):
        await message.answer_photo(r["photo_file_id"], caption=resume_card(r, lang, CAPTION_LIMIT, show_contacts=True))
    else:
        await message.answer(resume_card(r, lang, show_contacts=True))
    await message.answer(t("r_preview", lang), reply_markup=_confirm_kb(lang))


@router.callback_query(ResumeForm.confirm, Pick.filter(F.f == "rc"))
async def on_confirm(cb: CallbackQuery, callback_data: Pick, state: FSMContext, db: Database, config: Config, bot: Bot,
                     user: dict, lang: str, is_admin: bool) -> None:
    await cb.answer()
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    if callback_data.v == "restart":
        await start_resume(cb.message, state, db, user, lang)
        return
    if callback_data.v == "cancel":
        await state.clear()
        await send_menu(cb.message, user, lang, is_admin, t("cancelled", lang))
        return
    data = await state.get_data()
    r = dict(data.get("r") or {})
    r["status"] = "pending"
    await state.set_state(None)
    saved = await db.save_resume(user["id"], r)
    active = await flow.submit_resume(bot, db, config, saved)
    await send_menu(cb.message, user, lang, is_admin, t("r_saved_active" if active else "r_saved_pending", lang))

    await bot.send_chat_action(cb.message.chat.id, "upload_document")
    saved = await db.get_resume(saved["id"])
    await cb.message.answer(t("r_files_ready", lang))
    for fmt in ("pdf", "docx"):
        await cb.message.answer_document(await files.resume_file(bot, saved, lang, fmt))
