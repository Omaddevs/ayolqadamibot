"""Reply va inline klaviaturalar."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from .callbacks import Flt, LangCb, Pick, RoleCb, SubCb
from .constants import CATEGORIES, CITIES, EDU_LEVELS, EXP_LEVELS, JOB_TYPES, LANGUAGES
from .texts import t


def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data=LangCb(code="uz").pack()),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data=LangCb(code="ru").pack()),
    ]])


def role_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("role_seeker", lang), callback_data=RoleCb(role="seeker").pack())],
        [InlineKeyboardButton(text=t("role_employer", lang), callback_data=RoleCb(role="employer").pack())],
    ])


def sub_kb(channels: list[dict], lang: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"➕ {ch['title'] or 'Kanal'}", url=ch["link"])] for ch in channels if ch.get("link")]
    rows.append([InlineKeyboardButton(text=t("sub_check", lang), callback_data=SubCb().pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_menu(lang: str, role: str | None, is_admin: bool = False) -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    if role == "employer":
        b.button(text=t("m_candidates", lang))
        b.button(text=t("m_post_vac", lang))
        b.button(text=t("m_my_vacs", lang))
        b.button(text=t("m_saved", lang))
    else:
        b.button(text=t("m_jobs", lang))
        b.button(text=t("m_resume", lang))
        b.button(text=t("m_apps", lang))
        b.button(text=t("m_saved", lang))
    b.button(text=t("m_web", lang))
    b.button(text=t("m_settings", lang))
    b.button(text=t("m_help", lang))
    if is_admin:
        b.button(text=t("m_admin", lang))
    b.adjust(2, 2, 2, 2)
    return b.as_markup(resize_keyboard=True, input_field_placeholder="AyolQadami")


def cancel_kb(lang: str, skip: bool = False, extra: list[str] | None = None) -> ReplyKeyboardMarkup:
    rows = []
    for text in extra or []:
        rows.append([KeyboardButton(text=text)])
    if skip:
        rows.append([KeyboardButton(text=t("skip", lang))])
    rows.append([KeyboardButton(text=t("cancel", lang))])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def phone_kb(lang: str, skip: bool = False) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=t("send_phone", lang), request_contact=True)]]
    if skip:
        rows.append([KeyboardButton(text=t("skip", lang))])
    rows.append([KeyboardButton(text=t("cancel", lang))])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def _grid(items: list[tuple[str, str]], field: str, cols: int = 2, extra: list[InlineKeyboardButton] | None = None) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for value, label in items:
        b.button(text=label, callback_data=Pick(f=field, v=value).pack())
    b.adjust(cols)
    for btn in extra or []:
        b.row(btn)
    return b.as_markup()


def _skip_btn(field: str, lang: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=t("skip", lang), callback_data=Pick(f=field, v="-").pack())


def categories_kb(lang: str, field: str = "cat", skip: bool = False) -> InlineKeyboardMarkup:
    items = [(c[0], c[2] if lang == "ru" else c[1]) for c in CATEGORIES]
    return _grid(items, field, 2, [_skip_btn(field, lang)] if skip else None)


def cities_kb(lang: str, field: str = "city", skip: bool = False) -> InlineKeyboardMarkup:
    return _grid([(c, c) for c in CITIES], field, 3, [_skip_btn(field, lang)] if skip else None)


def job_type_kb(lang: str, field: str = "jt") -> InlineKeyboardMarkup:
    return _grid([(j[0], j[2] if lang == "ru" else j[1]) for j in JOB_TYPES], field, 2)


def exp_kb(lang: str, field: str = "exp") -> InlineKeyboardMarkup:
    return _grid([(e[0], e[2] if lang == "ru" else e[1]) for e in EXP_LEVELS], field, 2)


def edu_kb(lang: str, field: str = "edu") -> InlineKeyboardMarkup:
    return _grid([(e[0], e[2] if lang == "ru" else e[1]) for e in EDU_LEVELS], field, 1)


def multi_kb(items: list[tuple], selected: list[str], field: str, lang: str, cols: int = 2) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for item in items:
        label = item[2] if lang == "ru" else item[1]
        mark = "✅ " if item[0] in selected else "▫️ "
        b.button(text=mark + label, callback_data=Pick(f=field, v=item[0]).pack())
    b.adjust(cols)
    b.row(InlineKeyboardButton(text=t("done", lang), callback_data=Pick(f=field, v="_done").pack()))
    return b.as_markup()


def langs_kb(selected: list[str], lang: str) -> InlineKeyboardMarkup:
    return multi_kb(LANGUAGES, selected, "lng", lang)


def types_kb(selected: list[str], lang: str) -> InlineKeyboardMarkup:
    return multi_kb(JOB_TYPES, selected, "jts", lang)


def inline_skip(field: str, lang: str, extra: list[tuple[str, str]] | None = None) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=label, callback_data=Pick(f=field, v=value).pack())] for value, label in extra or []]
    rows.append([_skip_btn(field, lang)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def filter_kb(kind: str, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("f_all", lang), callback_data=Flt(kind=kind, by="all").pack())
    if kind == "v":
        b.button(text=t("f_match", lang), callback_data=Flt(kind=kind, by="match").pack())
    b.button(text=t("f_cat", lang), callback_data=Flt(kind=kind, by="cat").pack())
    b.button(text=t("f_city", lang), callback_data=Flt(kind=kind, by="city").pack())
    b.button(text=t("f_q", lang), callback_data=Flt(kind=kind, by="q").pack())
    b.adjust(2 if kind == "v" else 1, 2, 1)
    return b.as_markup()


def filter_values_kb(kind: str, by: str, lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if by == "cat":
        for c in CATEGORIES:
            b.button(text=c[2] if lang == "ru" else c[1], callback_data=Flt(kind=kind, by="cat", v=c[0]).pack())
        b.adjust(2)
    else:
        for c in CITIES:
            b.button(text=c, callback_data=Flt(kind=kind, by="city", v=c).pack())
        b.adjust(3)
    b.row(InlineKeyboardButton(text=t("back", lang), callback_data=Flt(kind=kind, by="menu").pack()))
    return b.as_markup()


def web_kb(url: str, lang: str) -> InlineKeyboardMarkup:
    btn = (
        InlineKeyboardButton(text=t("web_open", lang), web_app=WebAppInfo(url=url))
        if url.startswith("https://")
        else InlineKeyboardButton(text=t("web_open", lang), url=url)
    )
    return InlineKeyboardMarkup(inline_keyboard=[[btn]])
