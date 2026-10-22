"""SQLite (aiosqlite) ma'lumotlar qatlami. Bitta ulanish, WAL rejimi — kichik/o'rta bot uchun yetarli va
alohida server talab qilmaydi. Ro'yxat maydonlari JSON matn sifatida saqlanadi."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    lang TEXT,
    role TEXT,
    phone TEXT,
    notify INTEGER NOT NULL DEFAULT 1,
    is_banned INTEGER NOT NULL DEFAULT 0,
    is_blocked INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    last_seen TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_users_role ON users(role);

CREATE TABLE IF NOT EXISTS resumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    full_name TEXT, birth_year INTEGER, phone TEXT, telegram TEXT,
    city TEXT, category TEXT, headline TEXT,
    exp_level TEXT, experience TEXT,
    edu_level TEXT, education TEXT,
    skills TEXT NOT NULL DEFAULT '[]',
    languages TEXT NOT NULL DEFAULT '[]',
    job_types TEXT NOT NULL DEFAULT '[]',
    salary INTEGER, about TEXT, photo_file_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    views INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_resumes_status ON resumes(status, category, city);

CREATE TABLE IF NOT EXISTS vacancies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    source TEXT NOT NULL DEFAULT 'bot',
    ext_id TEXT,
    title TEXT, company TEXT, category TEXT, city TEXT, job_type TEXT,
    salary_from INTEGER, salary_to INTEGER, exp_level TEXT,
    description TEXT, requirements TEXT, conditions TEXT,
    contact_phone TEXT, contact_tg TEXT,
    media_type TEXT, media_file_id TEXT,
    raw_chat_id INTEGER, raw_message_id INTEGER,
    apply_value TEXT, post_value TEXT,
    extra_buttons TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'pending',
    views INTEGER NOT NULL DEFAULT 0,
    channel_posts TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL, expires_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_vac_status ON vacancies(status, category, city);
CREATE UNIQUE INDEX IF NOT EXISTS ux_vac_ext ON vacancies(ext_id) WHERE ext_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vacancy_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    resume_id INTEGER,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL,
    UNIQUE (vacancy_id, user_id)
);

CREATE TABLE IF NOT EXISTS invites (
    employer_id INTEGER NOT NULL,
    resume_id INTEGER NOT NULL,
    vacancy_id INTEGER,
    created_at TEXT NOT NULL,
    PRIMARY KEY (employer_id, resume_id)
);

CREATE TABLE IF NOT EXISTS favorites (
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    item_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, kind, item_id)
);

CREATE TABLE IF NOT EXISTS channels (
    chat_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    title TEXT, link TEXT,
    PRIMARY KEY (chat_id, kind)
);

CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY, added_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS broadcasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER, audience TEXT, total INTEGER, sent INTEGER, failed INTEGER,
    created_at TEXT NOT NULL
);
"""

DEFAULT_SETTINGS = {
    "force_sub": "0",          # majburiy obuna
    "web_sync": "0",           # web bilan ma'lumot almashish
    "moderation": "1",         # foydalanuvchi e'lonlari admin tasdig'idan o'tadimi
    "autopost_vac": "1",       # tasdiqlangan vakansiya kanalga avtomatik chiqadimi
    "autopost_res": "0",       # rezyumelar kanalga chiqadimi
    "notify_match": "1",       # yangi vakansiya mos ish izlovchilarga xabar qilinadimi
    "btn_apply_text": "✅ Ishlamoqchiman",
    "btn_apply_value": "bot",  # bot | https://... | @username | +998...
    "btn_post_text": "📢 E'lon berish",
    "btn_post_value": "bot",
    # Kanal posti tagidagi rangli tugmalar (JSON): [{"text", "url", "style": "" | "primary" | "danger" | "success"}].
    # Sayt admin paneli API orqali o'zgartiradi. url'da: {post} — botda e'lon berish, {site} — sayt, {bot} — bot.
    # Bo'sh ro'yxat "[]" bo'lsa — eski yagona «E'lon berish» tugmasi (btn_post_*) ishlaydi.
    "channel_buttons": json.dumps([
        {"text": "📢 E'lon joylash / Разместить вакансию", "url": "{post}", "style": "primary"},
        {"text": "🗂 Kanallar to'plami / Подборка каналов", "url": "", "style": "danger"},
        {"text": "💼 Website AyolQadami", "url": "{site}", "style": "success"},
    ], ensure_ascii=False),
}

JSON_FIELDS = {"skills", "languages", "job_types", "channel_posts", "extra_buttons"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _row(row: aiosqlite.Row | None) -> dict | None:
    if row is None:
        return None
    d = dict(row)
    for k in JSON_FIELDS & d.keys():
        try:
            d[k] = json.loads(d[k] or "[]")
        except (TypeError, ValueError):
            d[k] = []
    return d


def _dump(data: dict) -> dict:
    return {k: (json.dumps(v, ensure_ascii=False) if k in JSON_FIELDS else v) for k, v in data.items()}


RESUME_FIELDS = {
    "full_name", "birth_year", "phone", "telegram", "city", "category", "headline", "exp_level", "experience",
    "edu_level", "education", "skills", "languages", "job_types", "salary", "about", "photo_file_id", "status",
}
VACANCY_FIELDS = {
    "user_id", "source", "ext_id", "title", "company", "category", "city", "job_type", "salary_from", "salary_to",
    "exp_level", "description", "requirements", "conditions", "contact_phone", "contact_tg", "media_type",
    "media_file_id", "raw_chat_id", "raw_message_id", "apply_value", "post_value", "status", "channel_posts", "expires_at",
    "extra_buttons",
}


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.conn: aiosqlite.Connection | None = None
        self._settings: dict[str, str] = {}

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.execute("PRAGMA foreign_keys=ON")
        await self.conn.executescript(SCHEMA)
        await self._migrate()
        for k, v in DEFAULT_SETTINGS.items():
            await self.conn.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)", (k, v))
        await self.conn.commit()
        async with self.conn.execute("SELECT key, value FROM settings") as cur:
            self._settings = {r["key"]: r["value"] for r in await cur.fetchall()}

    async def _migrate(self) -> None:
        """Telefon orqali ro'yxatdan o'tish uchun ustunlar (eski bazalarda yo'q bo'lishi mumkin)."""
        async with self.conn.execute("PRAGMA table_info(users)") as cur:
            cols = {r[1] for r in await cur.fetchall()}
        if "verified_at" not in cols:
            await self.conn.execute("ALTER TABLE users ADD COLUMN verified_at TEXT")
        if "phone_key" not in cols:
            await self.conn.execute("ALTER TABLE users ADD COLUMN phone_key TEXT")
        # bitta raqam — bitta faol hisob
        await self.conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_users_phone_key ON users(phone_key) WHERE phone_key IS NOT NULL")
        # admin e'lonidagi qo'shimcha tugmalar: [{"k": phone|client|admin|site, "v": qiymat}]
        async with self.conn.execute("PRAGMA table_info(vacancies)") as cur:
            if "extra_buttons" not in {r[1] for r in await cur.fetchall()}:
                await self.conn.execute("ALTER TABLE vacancies ADD COLUMN extra_buttons TEXT NOT NULL DEFAULT '[]'")

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    # ---------- past darajadagi yordamchilar ----------
    async def fetchone(self, sql: str, params: tuple | list = ()) -> dict | None:
        async with self.conn.execute(sql, params) as cur:
            return _row(await cur.fetchone())

    async def fetchall(self, sql: str, params: tuple | list = ()) -> list[dict]:
        async with self.conn.execute(sql, params) as cur:
            return [_row(r) for r in await cur.fetchall()]

    async def scalar(self, sql: str, params: tuple | list = ()) -> Any:
        async with self.conn.execute(sql, params) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

    async def execute(self, sql: str, params: tuple | list = ()) -> int:
        cur = await self.conn.execute(sql, params)
        await self.conn.commit()
        return cur.lastrowid

    # ---------- sozlamalar ----------
    def setting(self, key: str) -> str:
        return self._settings.get(key, DEFAULT_SETTINGS.get(key, ""))

    def flag(self, key: str) -> bool:
        return self.setting(key) == "1"

    async def set_setting(self, key: str, value: str) -> None:
        self._settings[key] = value
        await self.execute("INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    async def toggle(self, key: str) -> bool:
        new = not self.flag(key)
        await self.set_setting(key, "1" if new else "0")
        return new

    # ---------- foydalanuvchilar ----------
    async def upsert_user(self, uid: int, username: str | None, full_name: str) -> dict:
        ts = now()
        await self.conn.execute(
            """INSERT INTO users(id, username, full_name, created_at, last_seen) VALUES(?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET username=excluded.username, full_name=excluded.full_name,
               last_seen=excluded.last_seen, is_blocked=0""",
            (uid, username, full_name, ts, ts),
        )
        await self.conn.commit()
        return await self.get_user(uid)

    async def get_user(self, uid: int) -> dict | None:
        return await self.fetchone("SELECT * FROM users WHERE id=?", (uid,))

    async def update_user(self, uid: int, **fields) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k}=?" for k in fields)
        await self.execute(f"UPDATE users SET {cols} WHERE id=?", (*fields.values(), uid))

    async def user_by_phone_key(self, key: str) -> dict | None:
        return await self.fetchone("SELECT * FROM users WHERE phone_key=?", (key,))

    async def claim_phone(self, uid: int, phone: str, key: str) -> dict:
        """Foydalanuvchi o'z raqamini tasdiqladi. Shu raqam bilan avval boshqa Telegram hisobda ro'yxatdan
        o'tilgan bo'lsa — o'sha hisobning ma'lumotlari (rezyume, arizalar, vakansiyalar, saqlanganlar, rol) shu hisobga
        ko'chiriladi. Natija: {"restored": bool, "resume": bool, "apps": n, "vacs": n, "favs": n}."""
        old = await self.user_by_phone_key(key)
        result = {"restored": False, "resume": False, "apps": 0, "vacs": 0, "favs": 0}
        conn = self.conn
        try:
            if old and old["id"] != uid:
                result = await self._merge_user(old, uid)
                # eski hisob raqamdan ajratiladi (unique indeks bo'shaydi)
                await conn.execute("UPDATE users SET phone_key=NULL, verified_at=NULL WHERE id=?", (old["id"],))
            await conn.execute("UPDATE users SET phone=?, phone_key=?, verified_at=? WHERE id=?", (phone, key, now(), uid))
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
        return result

    async def _merge_user(self, old: dict, new_id: int) -> dict:
        """old hisobdagi hamma narsani new_id ga ko'chiradi (commit chaqiruvchida)."""
        conn, old_id = self.conn, old["id"]

        async def one(sql: str, params: tuple) -> Any:
            async with conn.execute(sql, params) as cur:
                row = await cur.fetchone()
                return row[0] if row else None

        res = {"restored": True, "resume": False, "apps": 0, "vacs": 0, "favs": 0}
        # --- rezyume: ikkalasida bo'lsa — eng so'nggi yangilangani qoladi ---
        old_r = await self.fetchone("SELECT id, updated_at FROM resumes WHERE user_id=?", (old_id,))
        new_r = await self.fetchone("SELECT id, updated_at FROM resumes WHERE user_id=?", (new_id,))
        if old_r:
            res["resume"] = True
            if new_r:
                keep, drop = (old_r, new_r) if (old_r["updated_at"] or "") >= (new_r["updated_at"] or "") else (new_r, old_r)
                await conn.execute("UPDATE applications SET resume_id=? WHERE resume_id=?", (keep["id"], drop["id"]))
                await conn.execute("UPDATE OR IGNORE invites SET resume_id=? WHERE resume_id=?", (keep["id"], drop["id"]))
                await conn.execute("UPDATE OR IGNORE favorites SET item_id=? WHERE kind='res' AND item_id=?", (keep["id"], drop["id"]))
                await conn.execute("DELETE FROM invites WHERE resume_id=?", (drop["id"],))
                await conn.execute("DELETE FROM favorites WHERE kind='res' AND item_id=?", (drop["id"],))
                await conn.execute("DELETE FROM resumes WHERE id=?", (drop["id"],))
                await conn.execute("UPDATE resumes SET user_id=? WHERE id=?", (new_id, keep["id"]))
            else:
                await conn.execute("UPDATE resumes SET user_id=? WHERE id=?", (new_id, old_r["id"]))
        # --- vakansiyalar ---
        res["vacs"] = await one("SELECT COUNT(*) FROM vacancies WHERE user_id=?", (old_id,)) or 0
        await conn.execute("UPDATE vacancies SET user_id=? WHERE user_id=?", (new_id, old_id))
        # --- arizalar, saqlanganlar, takliflar (takrorlanadiganlari tashlab yuboriladi) ---
        res["apps"] = await one("SELECT COUNT(*) FROM applications WHERE user_id=?", (old_id,)) or 0
        await conn.execute("UPDATE OR IGNORE applications SET user_id=? WHERE user_id=?", (new_id, old_id))
        await conn.execute("DELETE FROM applications WHERE user_id=?", (old_id,))
        res["favs"] = await one("SELECT COUNT(*) FROM favorites WHERE user_id=?", (old_id,)) or 0
        await conn.execute("UPDATE OR IGNORE favorites SET user_id=? WHERE user_id=?", (new_id, old_id))
        await conn.execute("DELETE FROM favorites WHERE user_id=?", (old_id,))
        await conn.execute("UPDATE OR IGNORE invites SET employer_id=? WHERE employer_id=?", (new_id, old_id))
        await conn.execute("DELETE FROM invites WHERE employer_id=?", (old_id,))
        # --- profil: rol va bildirishnoma sozlamasi; ban — yangi hisob orqali chetlab o'tib bo'lmaydi ---
        await conn.execute(
            "UPDATE users SET role=COALESCE(role, ?), notify=?, is_banned=MAX(is_banned, ?) WHERE id=?",
            (old.get("role"), old.get("notify", 1), old.get("is_banned", 0), new_id),
        )
        return res

    async def user_ids(self, audience: str = "all") -> list[int]:
        where = "is_blocked=0 AND is_banned=0"
        if audience in ("seeker", "employer"):
            where += f" AND role='{audience}'"
        async with self.conn.execute(f"SELECT id FROM users WHERE {where}") as cur:
            return [r[0] for r in await cur.fetchall()]

    async def all_users(self) -> list[dict]:
        return await self.fetchall("SELECT * FROM users ORDER BY created_at")

    # ---------- adminlar ----------
    async def db_admins(self) -> set[int]:
        async with self.conn.execute("SELECT user_id FROM admins") as cur:
            return {r[0] for r in await cur.fetchall()}

    async def add_admin(self, uid: int) -> None:
        await self.execute("INSERT OR IGNORE INTO admins(user_id, added_at) VALUES(?, ?)", (uid, now()))

    async def remove_admin(self, uid: int) -> None:
        await self.execute("DELETE FROM admins WHERE user_id=?", (uid,))

    # ---------- kanallar ----------
    async def channels(self, kind: str) -> list[dict]:
        return await self.fetchall("SELECT * FROM channels WHERE kind=? ORDER BY rowid", (kind,))

    async def add_channel(self, chat_id: int, kind: str, title: str, link: str | None) -> None:
        await self.execute(
            "INSERT INTO channels(chat_id, kind, title, link) VALUES(?, ?, ?, ?) "
            "ON CONFLICT(chat_id, kind) DO UPDATE SET title=excluded.title, link=excluded.link",
            (chat_id, kind, title, link),
        )

    async def remove_channel(self, chat_id: int, kind: str) -> None:
        await self.execute("DELETE FROM channels WHERE chat_id=? AND kind=?", (chat_id, kind))

    # ---------- rezyumelar ----------
    async def get_resume(self, rid: int) -> dict | None:
        return await self.fetchone("SELECT * FROM resumes WHERE id=?", (rid,))

    async def resume_by_user(self, uid: int) -> dict | None:
        return await self.fetchone("SELECT * FROM resumes WHERE user_id=?", (uid,))

    async def save_resume(self, uid: int, data: dict) -> dict:
        data = _dump({k: v for k, v in data.items() if k in RESUME_FIELDS})
        ts = now()
        existing = await self.resume_by_user(uid)
        if existing:
            cols = ", ".join(f"{k}=?" for k in data)
            await self.execute(f"UPDATE resumes SET {cols}, updated_at=? WHERE id=?", (*data.values(), ts, existing["id"]))
            return await self.get_resume(existing["id"])
        cols = ", ".join(data)
        marks = ", ".join("?" for _ in data)
        rid = await self.execute(
            f"INSERT INTO resumes(user_id, {cols}, created_at, updated_at) VALUES(?, {marks}, ?, ?)",
            (uid, *data.values(), ts, ts),
        )
        return await self.get_resume(rid)

    async def set_resume_status(self, rid: int, status: str) -> None:
        await self.execute("UPDATE resumes SET status=?, updated_at=? WHERE id=?", (status, now(), rid))

    async def delete_resume(self, rid: int) -> None:
        await self.execute("DELETE FROM resumes WHERE id=?", (rid,))
        await self.execute("DELETE FROM favorites WHERE kind='res' AND item_id=?", (rid,))

    @staticmethod
    def _filters(table_alias: str, f: dict, text_cols: tuple[str, ...]) -> tuple[str, list]:
        where, params = [f"{table_alias}.status='active'"], []
        if f.get("category"):
            where.append(f"{table_alias}.category=?")
            params.append(f["category"])
        if f.get("city"):
            where.append(f"{table_alias}.city=?")
            params.append(f["city"])
        if f.get("q"):
            like = " OR ".join(f"LOWER({table_alias}.{c}) LIKE ?" for c in text_cols)
            where.append(f"({like})")
            params.extend([f"%{f['q'].lower()}%"] * len(text_cols))
        return " AND ".join(where), params

    async def count_resumes(self, f: dict) -> int:
        where, params = self._filters("r", f, ("headline", "full_name", "skills", "about", "experience"))
        return await self.scalar(f"SELECT COUNT(*) FROM resumes r WHERE {where}", params)

    async def resume_at(self, f: dict, index: int) -> dict | None:
        where, params = self._filters("r", f, ("headline", "full_name", "skills", "about", "experience"))
        return await self.fetchone(f"SELECT * FROM resumes r WHERE {where} ORDER BY r.updated_at DESC LIMIT 1 OFFSET ?", (*params, index))

    async def list_resumes(self, status: str | None = "active", limit: int = 100, offset: int = 0) -> list[dict]:
        if status:
            return await self.fetchall("SELECT * FROM resumes WHERE status=? ORDER BY updated_at DESC LIMIT ? OFFSET ?", (status, limit, offset))
        return await self.fetchall("SELECT * FROM resumes ORDER BY updated_at DESC LIMIT ? OFFSET ?", (limit, offset))

    async def bump_resume_views(self, rid: int) -> None:
        await self.execute("UPDATE resumes SET views=views+1 WHERE id=?", (rid,))

    # ---------- vakansiyalar ----------
    async def get_vacancy(self, vid: int) -> dict | None:
        return await self.fetchone("SELECT * FROM vacancies WHERE id=?", (vid,))

    async def create_vacancy(self, data: dict, days: int = 30) -> dict:
        data = _dump({k: v for k, v in data.items() if k in VACANCY_FIELDS})
        data.setdefault("expires_at", (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec="seconds"))
        cols = ", ".join(data)
        marks = ", ".join("?" for _ in data)
        vid = await self.execute(f"INSERT INTO vacancies({cols}, created_at) VALUES({marks}, ?)", (*data.values(), now()))
        return await self.get_vacancy(vid)

    async def update_vacancy(self, vid: int, **fields) -> None:
        fields = _dump({k: v for k, v in fields.items() if k in VACANCY_FIELDS})
        if fields:
            cols = ", ".join(f"{k}=?" for k in fields)
            await self.execute(f"UPDATE vacancies SET {cols} WHERE id=?", (*fields.values(), vid))

    async def delete_vacancy(self, vid: int) -> None:
        await self.execute("DELETE FROM vacancies WHERE id=?", (vid,))
        await self.execute("DELETE FROM applications WHERE vacancy_id=?", (vid,))
        await self.execute("DELETE FROM favorites WHERE kind='vac' AND item_id=?", (vid,))

    async def count_vacancies(self, f: dict) -> int:
        where, params = self._filters("v", f, ("title", "company", "description"))
        return await self.scalar(f"SELECT COUNT(*) FROM vacancies v WHERE {where}", params)

    async def vacancy_at(self, f: dict, index: int) -> dict | None:
        where, params = self._filters("v", f, ("title", "company", "description"))
        return await self.fetchone(f"SELECT * FROM vacancies v WHERE {where} ORDER BY v.created_at DESC LIMIT 1 OFFSET ?", (*params, index))

    async def list_vacancies(self, status: str | None = "active", limit: int = 100, offset: int = 0, user_id: int | None = None) -> list[dict]:
        where, params = [], []
        if status:
            where.append("status=?")
            params.append(status)
        if user_id is not None:
            where.append("user_id=?")
            params.append(user_id)
        sql = "SELECT * FROM vacancies" + (" WHERE " + " AND ".join(where) if where else "")
        return await self.fetchall(sql + " ORDER BY created_at DESC LIMIT ? OFFSET ?", (*params, limit, offset))

    async def user_vacancies(self, uid: int) -> list[dict]:
        return await self.fetchall(
            """SELECT v.*, (SELECT COUNT(*) FROM applications a WHERE a.vacancy_id=v.id) AS apps
               FROM vacancies v WHERE v.user_id=? AND v.source!='admin' ORDER BY v.created_at DESC""",
            (uid,),
        )

    async def bump_vacancy_views(self, vid: int) -> None:
        await self.execute("UPDATE vacancies SET views=views+1 WHERE id=?", (vid,))

    async def expire_vacancies(self) -> list[dict]:
        rows = await self.fetchall("SELECT * FROM vacancies WHERE status='active' AND expires_at IS NOT NULL AND expires_at < ?", (now(),))
        if rows:
            await self.execute("UPDATE vacancies SET status='closed' WHERE status='active' AND expires_at < ?", (now(),))
        return rows

    async def match_seekers(self, category: str, city: str | None, limit: int = 300) -> list[int]:
        sql = """SELECT r.user_id FROM resumes r JOIN users u ON u.id=r.user_id
                 WHERE r.status='active' AND r.category=? AND u.notify=1 AND u.is_blocked=0 AND u.is_banned=0"""
        params: list = [category]
        if city:
            sql += " AND r.city=?"
            params.append(city)
        async with self.conn.execute(sql + " LIMIT ?", (*params, limit)) as cur:
            return [r[0] for r in await cur.fetchall()]

    # ---------- arizalar ----------
    async def apply(self, vid: int, uid: int, rid: int | None) -> int | None:
        try:
            return await self.execute(
                "INSERT INTO applications(vacancy_id, user_id, resume_id, created_at) VALUES(?, ?, ?, ?)", (vid, uid, rid, now())
            )
        except aiosqlite.IntegrityError:
            return None

    async def get_application(self, aid: int) -> dict | None:
        return await self.fetchone("SELECT * FROM applications WHERE id=?", (aid,))

    async def set_application_status(self, aid: int, status: str) -> None:
        await self.execute("UPDATE applications SET status=? WHERE id=?", (status, aid))

    async def user_applications(self, uid: int) -> list[dict]:
        return await self.fetchall(
            """SELECT a.*, v.title, v.company, v.status AS vac_status FROM applications a
               LEFT JOIN vacancies v ON v.id=a.vacancy_id WHERE a.user_id=? ORDER BY a.created_at DESC LIMIT 30""",
            (uid,),
        )

    async def vacancy_applications(self, vid: int) -> list[dict]:
        return await self.fetchall(
            """SELECT a.*, r.full_name, r.headline FROM applications a
               LEFT JOIN resumes r ON r.id=a.resume_id WHERE a.vacancy_id=? ORDER BY a.created_at DESC""",
            (vid,),
        )

    # ---------- takliflar ----------
    async def invite(self, employer_id: int, rid: int, vid: int | None) -> bool:
        try:
            await self.execute("INSERT INTO invites(employer_id, resume_id, vacancy_id, created_at) VALUES(?, ?, ?, ?)", (employer_id, rid, vid, now()))
            return True
        except aiosqlite.IntegrityError:
            return False

    # ---------- saqlanganlar ----------
    async def toggle_fav(self, uid: int, kind: str, item_id: int) -> bool:
        exists = await self.scalar("SELECT 1 FROM favorites WHERE user_id=? AND kind=? AND item_id=?", (uid, kind, item_id))
        if exists:
            await self.execute("DELETE FROM favorites WHERE user_id=? AND kind=? AND item_id=?", (uid, kind, item_id))
            return False
        await self.execute("INSERT INTO favorites(user_id, kind, item_id, created_at) VALUES(?, ?, ?, ?)", (uid, kind, item_id, now()))
        return True

    async def is_fav(self, uid: int, kind: str, item_id: int) -> bool:
        return bool(await self.scalar("SELECT 1 FROM favorites WHERE user_id=? AND kind=? AND item_id=?", (uid, kind, item_id)))

    async def fav_ids(self, uid: int, kind: str) -> list[int]:
        async with self.conn.execute("SELECT item_id FROM favorites WHERE user_id=? AND kind=? ORDER BY created_at DESC", (uid, kind)) as cur:
            return [r[0] for r in await cur.fetchall()]

    # ---------- statistika ----------
    async def stats(self) -> dict:
        day = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(timespec="seconds")
        week = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(timespec="seconds")
        month = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(timespec="seconds")
        q = self.scalar
        return {
            "users": await q("SELECT COUNT(*) FROM users"),
            "seekers": await q("SELECT COUNT(*) FROM users WHERE role='seeker'"),
            "employers": await q("SELECT COUNT(*) FROM users WHERE role='employer'"),
            "new_day": await q("SELECT COUNT(*) FROM users WHERE created_at>=?", (day,)),
            "new_week": await q("SELECT COUNT(*) FROM users WHERE created_at>=?", (week,)),
            "new_month": await q("SELECT COUNT(*) FROM users WHERE created_at>=?", (month,)),
            "active_day": await q("SELECT COUNT(*) FROM users WHERE last_seen>=?", (day,)),
            "active_week": await q("SELECT COUNT(*) FROM users WHERE last_seen>=?", (week,)),
            "blocked": await q("SELECT COUNT(*) FROM users WHERE is_blocked=1"),
            "banned": await q("SELECT COUNT(*) FROM users WHERE is_banned=1"),
            "lang_uz": await q("SELECT COUNT(*) FROM users WHERE lang='uz'"),
            "lang_ru": await q("SELECT COUNT(*) FROM users WHERE lang='ru'"),
            "res_total": await q("SELECT COUNT(*) FROM resumes"),
            "res_active": await q("SELECT COUNT(*) FROM resumes WHERE status='active'"),
            "res_pending": await q("SELECT COUNT(*) FROM resumes WHERE status='pending'"),
            "vac_total": await q("SELECT COUNT(*) FROM vacancies"),
            "vac_active": await q("SELECT COUNT(*) FROM vacancies WHERE status='active'"),
            "vac_pending": await q("SELECT COUNT(*) FROM vacancies WHERE status='pending'"),
            "vac_admin": await q("SELECT COUNT(*) FROM vacancies WHERE source='admin'"),
            "vac_web": await q("SELECT COUNT(*) FROM vacancies WHERE source='web'"),
            "apps": await q("SELECT COUNT(*) FROM applications"),
            "apps_week": await q("SELECT COUNT(*) FROM applications WHERE created_at>=?", (week,)),
            "invites": await q("SELECT COUNT(*) FROM invites"),
            "top_cats": await self.fetchall(
                "SELECT category, COUNT(*) AS n FROM vacancies WHERE status='active' GROUP BY category ORDER BY n DESC LIMIT 5"
            ),
            "top_cities": await self.fetchall(
                "SELECT city, COUNT(*) AS n FROM vacancies WHERE status='active' AND city IS NOT NULL GROUP BY city ORDER BY n DESC LIMIT 5"
            ),
        }

    async def stats_extra(self) -> dict:
        """Admin panel dashboard'i uchun qo'shimcha: kunlik dinamika (14 kun, UTC+5) va tarqatishlar."""
        since = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat(timespec="seconds")

        async def daily(sql: str) -> dict:
            async with self.conn.execute(sql, (since,)) as cur:
                return {r[0]: r[1] for r in await cur.fetchall()}

        # created_at — ISO UTC; Toshkent kuni bo'yicha guruhlash
        day = "date(datetime(substr(created_at, 1, 19), '+5 hours'))"
        last = await self.fetchone("SELECT total, sent, failed, created_at FROM broadcasts ORDER BY id DESC LIMIT 1")
        return {
            "verified": await self.scalar("SELECT COUNT(*) FROM users WHERE verified_at IS NOT NULL"),
            "daily_users": await daily(f"SELECT {day}, COUNT(*) FROM users WHERE created_at>=? GROUP BY 1"),
            "daily_apps": await daily(f"SELECT {day}, COUNT(*) FROM applications WHERE created_at>=? GROUP BY 1"),
            "broadcasts": await self.scalar("SELECT COUNT(*) FROM broadcasts"),
            "last_broadcast": last,
        }

    async def log_broadcast(self, admin_id: int, audience: str, total: int, sent: int, failed: int) -> None:
        await self.execute(
            "INSERT INTO broadcasts(admin_id, audience, total, sent, failed, created_at) VALUES(?, ?, ?, ?, ?, ?)",
            (admin_id, audience, total, sent, failed, now()),
        )
