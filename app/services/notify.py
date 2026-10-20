"""Xavfsiz xabar yuborish: bot bloklangan bo'lsa foydalanuvchi belgilanadi, limitda kutiladi."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter

from ..config import Config
from ..db import Database

log = logging.getLogger(__name__)


async def admin_ids(db: Database, cfg: Config) -> set[int]:
    return set(cfg.admin_ids) | await db.db_admins()


async def is_admin(db: Database, cfg: Config, uid: int) -> bool:
    return uid in cfg.admin_ids or uid in await db.db_admins()


async def safe_call(db: Database, uid: int, coro_factory, retries: int = 2) -> bool:
    """coro_factory() — yuborish korutinasi. Muvaffaqiyatli bo'lsa True."""
    if uid <= 0:  # web'dan kelgan (Telegram'siz) foydalanuvchi
        return False
    for _ in range(retries + 1):
        try:
            await coro_factory()
            return True
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after + 0.5)
        except TelegramForbiddenError:
            await db.update_user(uid, is_blocked=1)
            return False
        except TelegramBadRequest as e:
            log.info("Xabar yuborilmadi %s: %s", uid, e)
            return False
        except Exception as e:  # tarmoq xatosi va h.k.
            log.warning("Xabar yuborishda xato %s: %s", uid, e)
            await asyncio.sleep(1)
    return False


async def send(bot: Bot, db: Database, uid: int, text: str, **kw) -> bool:
    return await safe_call(db, uid, lambda: bot.send_message(uid, text, **kw))


async def send_admins(bot: Bot, db: Database, cfg: Config, text: str, **kw) -> None:
    for uid in await admin_ids(db, cfg):
        await send(bot, db, uid, text, **kw)
