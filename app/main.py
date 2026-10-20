"""Botni yig'ish va ishga tushirish."""
from __future__ import annotations

import asyncio
import logging
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

from .config import BASE_DIR, Config, get_config
from .db import Database
from .handlers import admin, browse, cabinet, fallback, menu, resume, start, vacancy
from .middlewares import SubscriptionMiddleware, UserMiddleware
from .services import flow, websync

log = logging.getLogger("ayolqadam")


def setup_logging() -> None:
    (BASE_DIR / "data").mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler = RotatingFileHandler(BASE_DIR / "data" / "bot.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(fmt)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logging.basicConfig(level=logging.INFO, handlers=[console, file_handler])
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


def make_storage(cfg: Config) -> BaseStorage:
    """REDIS_URL berilsa FSM holatlari qayta ishga tushganda ham saqlanadi."""
    if cfg.redis_url:
        try:
            from aiogram.fsm.storage.redis import RedisStorage
            return RedisStorage.from_url(cfg.redis_url)
        except Exception as e:  # redis o'rnatilmagan yoki ulanib bo'lmadi
            log.warning("Redis ishlamadi (%s) — xotira saqlovchisi ishlatiladi", e)
    return MemoryStorage()


def build_dispatcher(cfg: Config, db: Database) -> Dispatcher:
    dp = Dispatcher(storage=make_storage(cfg), db=db, config=cfg)
    for observer in (dp.message, dp.callback_query):
        observer.outer_middleware(UserMiddleware())
        observer.outer_middleware(SubscriptionMiddleware())
    # tartib muhim: /start va menyu tugmalari har qanday holatda ishlashi kerak
    dp.include_routers(start.router, menu.router, admin.router, resume.router, vacancy.router, cabinet.router, browse.router, fallback.router)
    return dp


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands([
        BotCommand(command="start", description="Boshlash / Начать"),
        BotCommand(command="menu", description="Bosh menyu / Главное меню"),
        BotCommand(command="help", description="Yordam / Помощь"),
        BotCommand(command="cancel", description="Bekor qilish / Отмена"),
    ], scope=BotCommandScopeDefault())


async def main() -> None:
    setup_logging()
    cfg = get_config()
    db = Database(cfg.db_path)
    await db.connect()
    for admin_id in cfg.admin_ids:
        log.info("Bosh admin: %s", admin_id)

    bot = Bot(cfg.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dispatcher(cfg, db)
    me = await bot.me()
    log.info("Bot: @%s", me.username)
    await set_commands(bot)

    api_runner = None
    if cfg.api_enabled:
        from .api.server import start_api
        try:
            api_runner = await start_api(bot, db, cfg)
        except OSError as e:
            log.error("API serverni ishga tushirib bo'lmadi (%s) — bot API'siz ishlaydi", e)

    flow.background(flow.expire_loop(bot, db, cfg))
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        if api_runner:
            await api_runner.cleanup()
        await websync.close()
        await db.close()
        await bot.session.close()


def run() -> None:
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
