"""Inline tugmalar uchun callback_data fabrikalari (64 bayt chegarasiga sig'adi).

Eslatma: bo'sh bo'lishi mumkin bo'lgan maydonlar Optional bo'lishi shart — aiogram "" ni None qilib qaytaradi.
"""
from typing import Optional

from aiogram.filters.callback_data import CallbackData


class LangCb(CallbackData, prefix="lang"):
    code: str


class RoleCb(CallbackData, prefix="role"):
    role: str


class SubCb(CallbackData, prefix="sub"):
    action: str = "check"


class Pick(CallbackData, prefix="pk"):
    """Wizard tanlovlari: f — maydon, v — qiymat."""
    f: str
    v: str


class Flt(CallbackData, prefix="flt"):
    """Qidiruv filtri: kind — v (vakansiya) | r (rezyume); by — all|match|cat|city|q|fav."""
    kind: str
    by: str
    v: Optional[str] = None


class Nav(CallbackData, prefix="nav"):
    kind: str
    i: int


class Act(CallbackData, prefix="act"):
    """Kartochkadagi amallar. a — amal, id — vakansiya/rezyume id, i — ro'yxatdagi o'rin, k — ro'yxat turi."""
    a: str
    id: int
    i: int = 0
    k: Optional[str] = None


class Phone(CallbackData, prefix="ph"):
    """Kanal postidagi "telefon" tugmasi — bosilganda raqam alert'da ko'rinadi."""
    kind: str  # apply | post
    id: int = 0


class Mod(CallbackData, prefix="mod"):
    kind: str  # v | r
    id: int
    ok: int


class AppCb(CallbackData, prefix="app"):
    id: int
    s: str  # view | invited | rejected


class MyVac(CallbackData, prefix="mv"):
    a: str
    id: int = 0


class MyRes(CallbackData, prefix="mr"):
    a: str


class InvCb(CallbackData, prefix="inv"):
    rid: int
    vid: int = 0


class SetCb(CallbackData, prefix="set"):
    a: str


class Adm(CallbackData, prefix="adm"):
    a: str
    v: Optional[str] = None


class SupCb(CallbackData, prefix="sup"):
    uid: int
