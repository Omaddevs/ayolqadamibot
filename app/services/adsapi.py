"""AyolQadami serveri (web admin panel) bilan aloqa: «E'lon berish» shablonlari, e'lon yuborish, foydalanuvchi e'lonlari.

Shablonlar serverda (server/src/lib/ad-templates.ts) — bot savollarni shu yerdan oladi va 5 daqiqa keshlaydi.
E'lon serverga moderatsiyaga tushadi; admin tasdiqlab kanallarni tanlagach server o'zi joylaydi va
e'lon beruvchiga shu bot orqali natijani yuboradi.
"""
from __future__ import annotations

import logging
import time

import aiohttp

from ..config import Config

log = logging.getLogger(__name__)
_cache: dict = {"at": 0.0, "data": None}
TTL = 300


class AdsUnavailable(Exception):
    """Server sozlanmagan yoki javob bermayapti."""


class AdsRejected(Exception):
    """Server e'lonni qabul qilmadi (validatsiya, limit)."""

    def __init__(self, code: str, message: str, fields: dict | None = None):
        super().__init__(message)
        self.code, self.fields = code, fields or {}


def enabled(cfg: Config) -> bool:
    return bool(cfg.server_url and cfg.server_api_key)


async def _request(cfg: Config, method: str, path: str, **kw) -> dict:
    if not enabled(cfg):
        raise AdsUnavailable("SERVER_URL / SERVER_API_KEY berilmagan")
    headers = {"X-Api-Key": cfg.server_api_key, "Accept": "application/json"}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
            async with s.request(method, f"{cfg.server_url}/api/v1{path}", headers=headers, **kw) as r:
                data = await r.json(content_type=None) if r.content_length != 0 else {}
                if r.status >= 500 or r.status in (401, 503):
                    raise AdsUnavailable(f"HTTP {r.status}: {(data or {}).get('error')}")
                if r.status >= 400:
                    err = (data or {}).get("error") or {}
                    raise AdsRejected(err.get("code") or str(r.status), err.get("message") or "", err.get("fields"))
                return data or {}
    except (aiohttp.ClientError, TimeoutError) as e:
        raise AdsUnavailable(str(e)) from e


async def templates(cfg: Config) -> dict:
    """{templates: [...], categories: [...], cities: [...]} — 5 daqiqa keshlanadi; server yo'q bo'lsa eski kesh."""
    if _cache["data"] and time.monotonic() - _cache["at"] < TTL:
        return _cache["data"]
    try:
        data = await _request(cfg, "GET", "/bot/ad-templates")
    except AdsUnavailable:
        if _cache["data"]:
            return _cache["data"]
        raise
    _cache.update(at=time.monotonic(), data=data)
    return data


async def submit(cfg: Config, template: str, fields: dict, user: dict) -> dict:
    payload = {
        "template": template,
        "fields": fields,
        "user": {
            "id": str(user["id"]),
            "username": user.get("username"),
            "name": user.get("full_name") or "",
            "phone": user.get("phone"),
            "lang": user.get("lang") if user.get("lang") in ("uz", "ru") else "uz",
        },
    }
    return await _request(cfg, "POST", "/bot/ads", json=payload)


async def my_ads(cfg: Config, tg_user_id: int) -> list[dict]:
    data = await _request(cfg, "GET", "/bot/ads", params={"tgUserId": str(tg_user_id)})
    return data.get("items") or []


async def upload_image(cfg: Config, data: bytes) -> str:
    """Rasmni serverga yuklaydi va ochiq havolasini qaytaradi (kanal postida havola ko'rinishi sifatida ko'rsatiladi)."""
    url = (await _request(cfg, "POST", "/bot/media", data=data)).get("url") or ""
    if not url.startswith("https://"):
        raise AdsUnavailable(f"Rasm havolasi noto'g'ri: {url!r}")
    return url
