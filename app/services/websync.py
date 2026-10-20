"""Web ilova bilan ma'lumot almashish.

Ikki yo'nalish:
  1) Bot -> Web: yangi/yangilangan vakansiya va rezyumelar WEB_API_URL ga POST qilinadi (web backend bo'lsa).
  2) Web -> Bot: sayt botning REST API'sidan (app/api/server.py) o'qiydi va unga yozadi.
Ikkalasi ham admin paneldagi "🌐 Web sinxron" kaliti bilan yoqiladi/o'chiriladi. O'chiq bo'lsa bot
butunlay mustaqil ishlaydi — tarmoq xatolari botga hech qachon ta'sir qilmaydi.

Ma'lumot shakli web'dagi src/data/mock.js (vakansiya) va src/data/candidates.js (nomzod) bilan bir xil.
"""
from __future__ import annotations

import logging
import zlib
from datetime import datetime

import aiohttp

from ..config import Config
from ..constants import CATEGORIES, CITIES, JOB_TYPE_WEB, color_for, exp_years
from ..db import Database
from ..utils import lines_list, normalize_phone, normalize_tg

log = logging.getLogger(__name__)
_session: aiohttp.ClientSession | None = None

# web'dagi viloyat id → markaz shahar (src/data/resume.js REGIONS)
REGION_CITY = {
    "tashkent-city": "Toshkent", "tashkent": "Toshkent", "andijan": "Andijon", "bukhara": "Buxoro", "fergana": "Farg'ona",
    "jizzakh": "Jizzax", "khorezm": "Urganch", "namangan": "Namangan", "navoi": "Navoiy", "kashkadarya": "Qarshi",
    "karakalpak": "Nukus", "samarkand": "Samarqand", "syrdarya": "Guliston", "surkhandarya": "Termiz",
}
CITY_REGION = {"Toshkent": "tashkent-city", **{v: k for k, v in REGION_CITY.items() if k not in ("tashkent-city", "tashkent")}}
WEB_EXP = {"0": "none", "1": "lt1", "1-3": "1-3", "3-5": "3-5", "5+": "5+"}
BOT_EXP = {v: k for k, v in WEB_EXP.items()}
WEB_TYPE_BOT = {v: k for k, v in JOB_TYPE_WEB.items()}
LANG_WEB = {"uz": "O'zbek tili", "ru": "Rus tili", "en": "Ingliz tili", "kaa": "Qoraqalpoq tili", "tg": "Tojik tili",
            "kk": "Qozoq tili", "tr": "Turk tili", "ko": "Koreys tili", "ar": "Arab tili", "de": "Nemis tili"}
LANG_BOT = {v: k for k, v in LANG_WEB.items()}
CAT_IDS = {c[0] for c in CATEGORIES}


def _posted(iso: str | None) -> str:
    try:
        d = datetime.fromisoformat(iso)
        return d.astimezone().strftime("%d.%m.%Y")
    except (TypeError, ValueError):
        return "Hozirgina"


def channel_url(v: dict) -> str | None:
    posts = v.get("channel_posts") or []
    if not posts:
        return None
    chat_id, msg_id = posts[0][0], posts[0][1]
    return f"https://t.me/c/{str(chat_id).removeprefix('-100')}/{msg_id}"


# ---------- bot -> web shakli ----------
def vacancy_to_web(v: dict, bot_username: str | None = None) -> dict:
    return {
        "id": f"tg{v['id']}",
        "title": v.get("title") or "",
        "company": v.get("company") or "AyolQadami",
        "color": color_for(v["id"]),
        "category": v.get("category") or "other",
        "city": v.get("city") or "",
        "salaryFrom": v.get("salary_from") or 0,
        "salaryTo": v.get("salary_to") or 0,
        "type": JOB_TYPE_WEB.get(v.get("job_type") or "", "To'liq stavka"),
        "experience": exp_years(v.get("exp_level")),
        "tags": ["Telegram"] if v.get("source") != "web" else [],
        "posted": _posted(v.get("created_at")),
        "createdAt": v.get("created_at"),
        "applicants": 0,
        "views": v.get("views") or 0,
        "skills": [],
        "description": v.get("description") or "",
        "requirements": lines_list(v.get("requirements")),
        "conditions": lines_list(v.get("conditions")),
        "contact": {"phone": v.get("contact_phone"), "telegram": v.get("contact_tg")},
        "source": v.get("source"),
        "status": v.get("status"),
        "botUrl": f"https://t.me/{bot_username}?start=vac_{v['id']}" if bot_username else None,
        "channelUrl": channel_url(v),
    }


def resume_to_web(r: dict) -> dict:
    parts = (r.get("full_name") or "").split(maxsplit=1)
    return {
        "id": f"tg{r['id']}",
        "firstName": parts[0] if parts else "",
        "lastName": parts[1] if len(parts) > 1 else "",
        "birthDate": f"{r['birth_year']}-01-01" if r.get("birth_year") else "",
        "phone": r.get("phone") or "",
        "telegram": r.get("telegram") or "",
        "region": CITY_REGION.get(r.get("city") or "", ""),
        "city": r.get("city") or "",
        "category": r.get("category") or "other",
        "headline": r.get("headline") or "",
        "expLevel": WEB_EXP.get(r.get("exp_level") or "", "none"),
        "years": exp_years(r.get("exp_level")),
        "salary": r.get("salary") or 0,
        "employment": [x for x in (r.get("job_types") or []) if x in ("full", "part")],
        "workMode": [x for x in (r.get("job_types") or []) if x in ("remote", "hybrid")],
        "about": r.get("about") or "",
        "experience": [{"role": ln, "company": "", "desc": ""} for ln in lines_list(r.get("experience"))],
        "educations": [{"level": r.get("edu_level") or "", "school": r.get("education") or ""}] if r.get("education") else [],
        "skillsDetail": [{"name": s, "level": ""} for s in r.get("skills") or []],
        "langs": [{"lang": LANG_WEB.get(x, x), "level": ""} for x in r.get("languages") or []],
        "searchStatus": "active" if r.get("status") == "active" else "off",
        "source": "telegram",
        "updatedAt": r.get("updated_at"),
    }


# ---------- web -> bot shakli ----------
def _int(v) -> int | None:
    try:
        n = int(float(v))
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _text(v, n: int = 4000) -> str | None:
    if v is None:
        return None
    if isinstance(v, list):
        v = "\n".join(str(x) for x in v if x)
    s = str(v).strip()
    return s[:n] if s else None


def web_to_vacancy(d: dict) -> dict:
    contact = d.get("contact") or {}
    cat = d.get("category") if d.get("category") in CAT_IDS else "other"
    city = d.get("city") if d.get("city") in CITIES else _text(d.get("city"), 60)
    years = _int(d.get("experience")) or 0
    exp = "5+" if years >= 5 else "3-5" if years >= 3 else "1-3" if years >= 1 else "0"
    return {
        "ext_id": _text(d.get("id"), 64),
        "title": _text(d.get("title"), 120) or "Vakansiya",
        "company": _text(d.get("company"), 120),
        "category": cat,
        "city": city,
        "job_type": WEB_TYPE_BOT.get(d.get("type"), "full"),
        "salary_from": _int(d.get("salaryFrom")),
        "salary_to": _int(d.get("salaryTo")),
        "exp_level": exp,
        "description": _text(d.get("description")),
        "requirements": _text(d.get("requirements")),
        "conditions": _text(d.get("conditions")),
        "contact_phone": normalize_phone(str(contact.get("phone") or d.get("phone") or "")) if (contact.get("phone") or d.get("phone")) else None,
        "contact_tg": normalize_tg(str(contact.get("telegram") or d.get("telegram") or "")),
    }


def web_to_resume(d: dict) -> tuple[int, dict]:
    """Web rezyumesi uchun Telegram ID yo'q — tashqi id'dan barqaror manfiy user_id yasaymiz."""
    ext = str(d.get("id") or d.get("phone") or "")
    uid = -(zlib.crc32(ext.encode()) or 1)
    name = " ".join(x for x in (d.get("firstName"), d.get("lastName")) if x) or _text(d.get("name"), 80) or "Nomzod"
    birth = str(d.get("birthDate") or "")[:4]
    types = [x for x in (d.get("employment") or []) + (d.get("workMode") or []) if x in JOB_TYPE_WEB]
    return uid, {
        "full_name": name[:80],
        "birth_year": int(birth) if birth.isdigit() else None,
        "phone": normalize_phone(str(d.get("phone") or "")),
        "telegram": normalize_tg(str(d.get("telegram") or "")),
        "city": REGION_CITY.get(d.get("region"), d.get("city") if d.get("city") in CITIES else None),
        "category": d.get("category") if d.get("category") in CAT_IDS else "other",
        "headline": _text(d.get("headline"), 120),
        "exp_level": BOT_EXP.get(d.get("expLevel"), "0"),
        "experience": "\n".join(
            " — ".join(x for x in (e.get("from", ""), e.get("company", ""), e.get("role", "")) if x) for e in d.get("experience") or []
        ) or None,
        "education": "\n".join(f"{e.get('school', '')} {e.get('faculty', '')}".strip() for e in d.get("educations") or []) or None,
        "skills": [s.get("name") for s in d.get("skillsDetail") or [] if s.get("name")][:20],
        "languages": [LANG_BOT[x["lang"]] for x in d.get("langs") or [] if x.get("lang") in LANG_BOT],
        "job_types": types,
        "salary": _int(d.get("salary")),
        "about": _text(d.get("about"), 1500),
    }


# ---------- bot -> web push ----------
async def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
    return _session


async def push(db: Database, cfg: Config, kind: str, action: str, payload: dict) -> bool:
    """kind: vacancies | resumes; action: upsert | delete. Xato bo'lsa jimgina False."""
    if not db.flag("web_sync") or not cfg.web_api_url:
        return False
    url = f"{cfg.web_api_url}/{kind}"
    headers = {"X-Api-Key": cfg.web_api_key} if cfg.web_api_key else {}
    try:
        session = await _get_session()
        if action == "delete":
            async with session.delete(f"{url}/{payload['id']}", headers=headers) as resp:
                ok = resp.status < 400
        else:
            async with session.post(url, json=payload, headers=headers) as resp:
                ok = resp.status < 400
        if not ok:
            log.warning("Web sync %s %s: HTTP %s", kind, action, resp.status)
        return ok
    except Exception as e:
        log.warning("Web sync xatosi (%s): %s", url, e)
        return False


async def check_web(cfg: Config) -> str:
    if not cfg.web_api_url:
        return "WEB_API_URL sozlanmagan"
    try:
        session = await _get_session()
        async with session.get(cfg.web_api_url, headers={"X-Api-Key": cfg.web_api_key} if cfg.web_api_key else {}) as resp:
            return f"HTTP {resp.status}"
    except Exception as e:
        return f"ulanib bo'lmadi ({type(e).__name__})"


async def close() -> None:
    if _session and not _session.closed:
        await _session.close()
