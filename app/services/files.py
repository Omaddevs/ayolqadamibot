"""Telegram'dan rasmni olish va PDF/DOCX fayllarni tayyorlash (og'ir ish alohida thread'da)."""
from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from io import BytesIO

from aiogram import Bot
from aiogram.types import BufferedInputFile

from . import docs

log = logging.getLogger(__name__)
_photo_cache: "OrderedDict[str, bytes]" = OrderedDict()
_PHOTO_CACHE_SIZE = 64


async def photo_bytes(bot: Bot, file_id: str | None) -> bytes | None:
    if not file_id:
        return None
    if file_id in _photo_cache:
        _photo_cache.move_to_end(file_id)
        return _photo_cache[file_id]
    try:
        buf = BytesIO()
        await bot.download(file_id, destination=buf)
        data = buf.getvalue()
    except Exception as e:  # fayl o'chgan yoki boshqa bot file_id'si
        log.warning("Rasmni yuklab bo'lmadi: %s", e)
        return None
    _photo_cache[file_id] = data
    if len(_photo_cache) > _PHOTO_CACHE_SIZE:
        _photo_cache.popitem(last=False)
    return data


async def resume_file(bot: Bot, r: dict, lang: str, fmt: str) -> BufferedInputFile:
    photo = await photo_bytes(bot, r.get("photo_file_id"))
    base = docs.safe_filename(r.get("full_name") or "", "Resume")
    if fmt == "pdf":
        data = await asyncio.to_thread(docs.resume_pdf, r, lang, photo)
        return BufferedInputFile(data, filename=base + ".pdf")
    data = await asyncio.to_thread(docs.resume_docx, r, lang, photo)
    return BufferedInputFile(data, filename=base + ".docx")


async def vacancy_file(v: dict, lang: str, fmt: str) -> BufferedInputFile:
    base = docs.safe_filename(v.get("title") or "", "Vakansiya")
    if fmt == "pdf":
        data = await asyncio.to_thread(docs.vacancy_pdf, v, lang)
        return BufferedInputFile(data, filename=base + ".pdf")
    data = await asyncio.to_thread(docs.vacancy_docx, v, lang)
    return BufferedInputFile(data, filename=base + ".docx")
