"""Ish beruvchi uchun vakansiya joylash ustasi."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ..callbacks import Pick
from ..config import Config
from ..db import Database
from ..keyboards import cancel_kb, categories_kb, cities_kb, exp_kb, inline_skip, job_type_kb, phone_kb
from ..services import flow
from ..states import VacancyForm
from ..texts import t
from ..utils import normalize_phone, normalize_tg, parse_salary, vacancy_card
from .base import is_skip, send_menu

router = Router(name="vacancy")

LIMITS = {"title": 100, "company": 100, "description": 2500, "requirements": 1200, "conditions": 1200}


async def start_vacancy(message: Message, state: FSMContext, lang: str) -> None:
    keep = {k: v for k, v in (await state.get_data()).items() if k in ("vf", "rf")}
    await state.clear()
    await state.update_data(v={}, **keep)
    await message.answer(t("v_intro", lang), reply_markup=cancel_kb(lang))
    await state.set_state(VacancyForm.title)
    await message.answer(t("v_title", lang))


async def _set(state: FSMContext, **fields) -> dict:
    data = await state.get_data()
    v = data.get("v") or {}
    v.update(fields)
    await state.update_data(v=v)
    return v


async def _text_value(message: Message, lang: str, field: str, required: bool = True) -> str | None | bool:
    """Matnni tekshiradi: qiymat, None (o'tkazildi) yoki False (xato)."""
    text = (message.text or "").strip()
    if not required and is_skip(text, lang):
        return None
    limit = LIMITS.get(field, 500)
    if len(text) > limit:
        await message.answer(t("too_long", lang, n=limit))
        return False
    if len(text) < 2:
        await message.answer(t("bad_input", lang))
        return False
    return text


@router.message(VacancyForm.title, F.text)
async def v_title(message: Message, state: FSMContext, lang: str) -> None:
    value = await _text_value(message, lang, "title")
    if value is False:
        return
    await _set(state, title=value)
    await state.set_state(VacancyForm.company)
    await message.answer(t("v_company", lang))


@router.message(VacancyForm.company, F.text)
async def v_company(message: Message, state: FSMContext, lang: str) -> None:
    value = await _text_value(message, lang, "company")
    if value is False:
        return
    await _set(state, company=value)
    await state.set_state(VacancyForm.cat)
    await message.answer(t("vq_cat", lang), reply_markup=categories_kb(lang, "vcat"))


@router.callback_query(VacancyForm.cat, Pick.filter(F.f == "vcat"))
async def v_cat(cb: CallbackQuery, callback_data: Pick, state: FSMContext, lang: str) -> None:
    await _set(state, category=callback_data.v)
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    await state.set_state(VacancyForm.city)
    await cb.message.answer(t("vq_city", lang), reply_markup=cities_kb(lang, "vcity"))


@router.callback_query(VacancyForm.city, Pick.filter(F.f == "vcity"))
async def v_city(cb: CallbackQuery, callback_data: Pick, state: FSMContext, lang: str) -> None:
    await _set(state, city=callback_data.v)
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    await state.set_state(VacancyForm.jtype)
    await cb.message.answer(t("vq_type", lang), reply_markup=job_type_kb(lang, "vjt"))


@router.callback_query(VacancyForm.jtype, Pick.filter(F.f == "vjt"))
async def v_jtype(cb: CallbackQuery, callback_data: Pick, state: FSMContext, lang: str) -> None:
    await _set(state, job_type=callback_data.v)
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    await state.set_state(VacancyForm.salary)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("b_negotiable", lang), callback_data=Pick(f="vsal", v="0").pack())]])
    await cb.message.answer(t("v_salary_q", lang), reply_markup=kb)


async def _ask_exp(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(VacancyForm.exp)
    await message.answer(t("v_exp_q", lang), reply_markup=exp_kb(lang, "vexp"))


@router.message(VacancyForm.salary, F.text)
async def v_salary(message: Message, state: FSMContext, lang: str) -> None:
    frm, to = parse_salary(message.text)
    if not frm or frm < 100_000 or (to and to > 2_000_000_000):
        await message.answer(t("bad_number", lang))
        return
    await _set(state, salary_from=frm, salary_to=to)
    await _ask_exp(message, state, lang)


@router.callback_query(VacancyForm.salary, Pick.filter(F.f == "vsal"))
async def v_salary_neg(cb: CallbackQuery, state: FSMContext, lang: str) -> None:
    await _set(state, salary_from=None, salary_to=None)
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    await _ask_exp(cb.message, state, lang)


@router.callback_query(VacancyForm.exp, Pick.filter(F.f == "vexp"))
async def v_exp(cb: CallbackQuery, callback_data: Pick, state: FSMContext, lang: str) -> None:
    await _set(state, exp_level=callback_data.v)
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    await state.set_state(VacancyForm.desc)
    await cb.message.answer(t("v_desc", lang))


@router.message(VacancyForm.desc, F.text)
async def v_desc(message: Message, state: FSMContext, lang: str) -> None:
    value = await _text_value(message, lang, "description")
    if value is False:
        return
    await _set(state, description=value)
    await state.set_state(VacancyForm.req)
    await message.answer(t("v_req_q", lang), reply_markup=cancel_kb(lang, skip=True))


@router.message(VacancyForm.req, F.text)
async def v_req(message: Message, state: FSMContext, lang: str) -> None:
    value = await _text_value(message, lang, "requirements", required=False)
    if value is False:
        return
    await _set(state, requirements=value)
    await state.set_state(VacancyForm.cond)
    await message.answer(t("v_cond_q", lang), reply_markup=cancel_kb(lang, skip=True))


@router.message(VacancyForm.cond, F.text)
async def v_cond(message: Message, state: FSMContext, user: dict, lang: str) -> None:
    value = await _text_value(message, lang, "conditions", required=False)
    if value is False:
        return
    await _set(state, conditions=value)
    await state.set_state(VacancyForm.phone)
    await message.answer(t("v_phone", lang), reply_markup=phone_kb(lang, skip=True))


async def _ask_tg(message: Message, state: FSMContext, user: dict, lang: str) -> None:
    await state.set_state(VacancyForm.tg)
    extra = [(f"@{user['username']}", t("use_my_tg", lang, u=user["username"]))] if user.get("username") else []
    await message.answer(t("v_tg", lang), reply_markup=cancel_kb(lang, skip=True))
    if extra:
        await message.answer("👇", reply_markup=inline_skip("vtg", lang, extra))


@router.message(VacancyForm.phone, F.contact)
async def v_phone_contact(message: Message, state: FSMContext, user: dict, lang: str) -> None:
    await _set(state, contact_phone=normalize_phone(message.contact.phone_number) or message.contact.phone_number)
    await _ask_tg(message, state, user, lang)


@router.message(VacancyForm.phone, F.text)
async def v_phone(message: Message, state: FSMContext, user: dict, lang: str) -> None:
    if is_skip(message.text, lang):
        await _set(state, contact_phone=None)
    else:
        phone = normalize_phone(message.text)
        if not phone:
            await message.answer(t("bad_phone", lang))
            return
        await _set(state, contact_phone=phone)
    await _ask_tg(message, state, user, lang)


async def _finish_tg(message: Message, state: FSMContext, tg: str | None, lang: str) -> None:
    v = await _set(state, contact_tg=tg)
    if not v.get("contact_phone") and not tg:
        # kamida bitta aloqa usuli bo'lishi shart
        await state.set_state(VacancyForm.phone)
        await message.answer(t("v_phone", lang), reply_markup=phone_kb(lang))
        return
    await state.set_state(VacancyForm.confirm)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("v_publish", lang), callback_data=Pick(f="vc", v="ok").pack())],
        [InlineKeyboardButton(text=t("r_restart", lang), callback_data=Pick(f="vc", v="restart").pack()),
         InlineKeyboardButton(text=t("cancel", lang), callback_data=Pick(f="vc", v="cancel").pack())],
    ])
    await message.answer(vacancy_card(v, lang), disable_web_page_preview=True)
    await message.answer(t("v_preview", lang), reply_markup=kb)


@router.message(VacancyForm.tg, F.text)
async def v_tg(message: Message, state: FSMContext, lang: str) -> None:
    if is_skip(message.text, lang):
        await _finish_tg(message, state, None, lang)
        return
    tg = normalize_tg(message.text)
    if not tg:
        await message.answer(t("bad_input", lang))
        return
    await _finish_tg(message, state, tg, lang)


@router.callback_query(VacancyForm.tg, Pick.filter(F.f == "vtg"))
async def v_tg_pick(cb: CallbackQuery, callback_data: Pick, state: FSMContext, lang: str) -> None:
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    await _finish_tg(cb.message, state, None if callback_data.v == "-" else callback_data.v, lang)


@router.callback_query(StateFilter(VacancyForm.confirm), Pick.filter(F.f == "vc"))
async def v_confirm(cb: CallbackQuery, callback_data: Pick, state: FSMContext, db: Database, config: Config, bot: Bot,
                    user: dict, lang: str, is_admin: bool) -> None:
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    if callback_data.v == "restart":
        await start_vacancy(cb.message, state, lang)
        return
    if callback_data.v == "cancel":
        await state.clear()
        await send_menu(cb.message, user, lang, is_admin, t("cancelled", lang))
        return
    data = await state.get_data()
    await state.set_state(None)
    v = await db.create_vacancy({**(data.get("v") or {}), "user_id": user["id"], "source": "bot", "status": "pending"}, config.vacancy_days)
    active = await flow.submit_vacancy(bot, db, config, v)
    await send_menu(cb.message, user, lang, is_admin, t("v_saved_active" if active else "v_saved_pending", lang))
