"""Muhit sozlamalari (.env). Ish vaqtida o'zgaradigan sozlamalar DB dagi `settings` jadvalida."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _ids(raw: str) -> set[int]:
    return {int(x) for x in raw.replace(";", ",").split(",") if x.strip().lstrip("-").isdigit()}


def _bool(raw: str | None, default: bool = False) -> bool:
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "ha"}


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: set[int] = field(default_factory=set)
    db_path: Path = BASE_DIR / "data" / "bot.db"
    redis_url: str = ""

    # Web ilova bilan bog'lanish
    web_url: str = ""            # saytning ochiq manzili (menyuda "Saytni ochish" tugmasi, Mini App)
    web_api_url: str = ""        # web backend (bo'lsa) — yangi vakansiya/rezyumelar shu yerga POST qilinadi
    web_api_key: str = ""        # ikki tomonlama so'rovlar uchun maxfiy kalit (X-Api-Key)

    # Botning o'z REST API serveri (sayt bot bazasidan o'qishi uchun)
    api_enabled: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    api_cors: str = "*"

    vacancy_days: int = 30       # vakansiya necha kundan keyin avtomatik yopiladi

    # AyolQadami serveri (Next.js, web admin panel): «E'lon berish» shablonlari va moderatsiya
    server_url: str = ""         # masalan https://api.ayolqadami.uz (lokal: http://localhost:3100)
    server_api_key: str = ""     # serverdagi BOT_API_KEY bilan bir xil


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("BOT_TOKEN topilmadi. .env.example dan .env yarating va tokenni kiriting.")
    db_path = os.getenv("DB_PATH", "").strip()
    return Config(
        bot_token=token,
        admin_ids=_ids(os.getenv("ADMIN_IDS", "")),
        db_path=Path(db_path) if db_path else BASE_DIR / "data" / "bot.db",
        redis_url=os.getenv("REDIS_URL", "").strip(),
        web_url=os.getenv("WEB_URL", "").strip().rstrip("/"),
        web_api_url=os.getenv("WEB_API_URL", "").strip().rstrip("/"),
        web_api_key=os.getenv("WEB_API_KEY", "").strip(),
        api_enabled=_bool(os.getenv("API_ENABLED"), False),
        api_host=os.getenv("API_HOST", "0.0.0.0").strip(),
        api_port=int(os.getenv("API_PORT", "8080") or 8080),
        api_cors=os.getenv("API_CORS", "*").strip() or "*",
        vacancy_days=int(os.getenv("VACANCY_DAYS", "30") or 30),
        server_url=os.getenv("SERVER_URL", "").strip().rstrip("/"),
        server_api_key=(os.getenv("SERVER_API_KEY", "") or os.getenv("WEB_API_KEY", "")).strip(),
    )


config: Config | None = None


def get_config() -> Config:
    global config
    if config is None:
        config = load_config()
    return config
