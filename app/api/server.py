"""Bot ichidagi REST API (aiohttp) — web ilova uchun.

  GET    /api/health                      holat (doim ochiq)
  GET    /api/vacancies?category=&city=&q=&limit=&offset=
  GET    /api/vacancies/{id}
  POST   /api/vacancies                   saytdan vakansiya (kalitsiz -> majburiy moderatsiya)
  DELETE /api/vacancies/{ext_id}          [kalit] saytdagi vakansiyani yopish
  GET    /api/resumes                     [kalit] faol rezyumelar (shaxsiy ma'lumot)
  POST   /api/resumes                     saytdan rezyume (kalitsiz -> majburiy moderatsiya)
  GET    /api/stats                       [kalit] — admin panel dashboard'i uchun; "Web sinxron" o'chiq bo'lsa ham ishlaydi
  GET    /api/buttons                     [kalit] kanal posti tagidagi rangli tugmalar
  PUT    /api/buttons                     [kalit] {"buttons": [{"text", "url", "style"}], "apply_enabled": bool}

Kalit: `X-Api-Key: <WEB_API_KEY>`. Admin paneldagi "Web sinxron" o'chiq bo'lsa health'dan boshqa hammasi 503 qaytaradi.
"""
from __future__ import annotations

import json
import logging
import re
import time
from collections import defaultdict, deque
from functools import partial

from aiogram import Bot
from aiohttp import web

from ..config import Config
from ..db import Database
from ..services import flow, websync

log = logging.getLogger(__name__)
RATE_LIMIT = 20          # kalitsiz POST so'rovlar soni
RATE_WINDOW = 3600       # ... bir soatda, bitta IP uchun
_hits: dict[str, deque] = defaultdict(deque)


def _json(data, status: int = 200) -> web.Response:
    return web.json_response(data, status=status, dumps=partial(json.dumps, ensure_ascii=False))


def _has_key(request: web.Request) -> bool:
    cfg: Config = request.app["config"]
    return bool(cfg.web_api_key) and request.headers.get("X-Api-Key") == cfg.web_api_key


def _rate_ok(request: web.Request) -> bool:
    ip = request.headers.get("X-Forwarded-For", request.remote or "?").split(",")[0].strip()
    q, now = _hits[ip], time.monotonic()
    while q and now - q[0] > RATE_WINDOW:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        return False
    q.append(now)
    return True


@web.middleware
async def cors_middleware(request: web.Request, handler):
    cfg: Config = request.app["config"]
    if request.method == "OPTIONS":
        resp = web.Response()
    else:
        try:
            resp = await handler(request)
        except web.HTTPException as e:
            resp = _json({"error": e.reason}, e.status)
        except Exception:
            log.exception("API xatosi")
            resp = _json({"error": "internal"}, 500)
    resp.headers["Access-Control-Allow-Origin"] = cfg.api_cors
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Api-Key"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return resp


@web.middleware
async def sync_gate(request: web.Request, handler):
    db: Database = request.app["db"]
    # statistika va kanal tugmalari — faqat kalit bilan, ma'lumot almashish emas: sinxron sozlamasidan qat'i nazar ochiq
    if request.path in ("/api/stats", "/api/buttons") and _has_key(request):
        return await handler(request)
    if request.path != "/api/health" and request.method != "OPTIONS" and not db.flag("web_sync"):
        return _json({"error": "web sync disabled"}, 503)
    return await handler(request)


def _need_key(request: web.Request) -> None:
    if not _has_key(request):
        raise web.HTTPUnauthorized(reason="api key required")


def _filters(request: web.Request) -> dict:
    q = request.query
    return {k: q.get(k, "").strip()[:60] for k in ("category", "city", "q") if q.get(k, "").strip()}


def _paging(request: web.Request) -> tuple[int, int]:
    try:
        limit = max(1, min(int(request.query.get("limit", 50)), 200))
        offset = max(0, int(request.query.get("offset", 0)))
    except ValueError:
        raise web.HTTPBadRequest(reason="bad paging")
    return limit, offset


async def health(request: web.Request) -> web.Response:
    db: Database = request.app["db"]
    return _json({"ok": True, "sync": db.flag("web_sync"), "service": "ayolqadam-bot"})


async def list_vacancies(request: web.Request) -> web.Response:
    db: Database = request.app["db"]
    f = _filters(request)
    limit, offset = _paging(request)
    where, params = db._filters("v", f, ("title", "company", "description"))
    rows = await db.fetchall(f"SELECT * FROM vacancies v WHERE {where} ORDER BY v.created_at DESC LIMIT ? OFFSET ?", (*params, limit, offset))
    total = await db.count_vacancies(f)
    me = await flow.bot_username(request.app["bot"])
    return _json({"total": total, "items": [websync.vacancy_to_web(v, me) for v in rows]})


def _parse_id(raw: str) -> int | None:
    raw = raw.removeprefix("tg")
    return int(raw) if raw.isdigit() else None


async def get_vacancy(request: web.Request) -> web.Response:
    db: Database = request.app["db"]
    vid = _parse_id(request.match_info["id"])
    v = await db.get_vacancy(vid) if vid else None
    if not v or v["status"] != "active":
        raise web.HTTPNotFound(reason="not found")
    return _json(websync.vacancy_to_web(v, await flow.bot_username(request.app["bot"])))


async def _body(request: web.Request) -> dict:
    try:
        data = await request.json()
    except Exception:
        raise web.HTTPBadRequest(reason="invalid json")
    if not isinstance(data, dict):
        raise web.HTTPBadRequest(reason="object expected")
    return data


async def post_vacancy(request: web.Request) -> web.Response:
    keyed = _has_key(request)
    if not keyed and not _rate_ok(request):
        raise web.HTTPTooManyRequests(reason="rate limit")
    db: Database = request.app["db"]
    cfg: Config = request.app["config"]
    bot: Bot = request.app["bot"]
    data = websync.web_to_vacancy(await _body(request))
    if not data.get("title") or not (data.get("description") or data.get("contact_phone") or data.get("contact_tg")):
        raise web.HTTPBadRequest(reason="title and description/contact required")
    existing = await db.fetchone("SELECT * FROM vacancies WHERE ext_id=?", (data["ext_id"],)) if data.get("ext_id") else None
    if existing:
        await db.update_vacancy(existing["id"], **data)
        v = await db.get_vacancy(existing["id"])
        return _json({"id": f"tg{v['id']}", "status": v["status"], "updated": True})
    v = await db.create_vacancy({**data, "source": "web", "status": "pending"}, cfg.vacancy_days)
    active = await flow.submit_vacancy(bot, db, cfg, v, force_moderation=not keyed)
    return _json({"id": f"tg{v['id']}", "status": "active" if active else "pending"}, 201)


async def delete_vacancy(request: web.Request) -> web.Response:
    _need_key(request)
    db: Database = request.app["db"]
    ref = request.match_info["id"]
    v = await db.fetchone("SELECT * FROM vacancies WHERE ext_id=?", (ref,))
    if not v and _parse_id(ref):
        v = await db.get_vacancy(_parse_id(ref))
    if not v:
        raise web.HTTPNotFound(reason="not found")
    await db.update_vacancy(v["id"], status="closed")
    await flow.unpublish_vacancy(request.app["bot"], v)
    return _json({"ok": True})


async def list_resumes(request: web.Request) -> web.Response:
    _need_key(request)
    db: Database = request.app["db"]
    f = _filters(request)
    limit, offset = _paging(request)
    where, params = db._filters("r", f, ("headline", "full_name", "skills", "about", "experience"))
    rows = await db.fetchall(f"SELECT * FROM resumes r WHERE {where} ORDER BY r.updated_at DESC LIMIT ? OFFSET ?", (*params, limit, offset))
    return _json({"total": await db.count_resumes(f), "items": [websync.resume_to_web(r) for r in rows]})


async def post_resume(request: web.Request) -> web.Response:
    keyed = _has_key(request)
    if not keyed and not _rate_ok(request):
        raise web.HTTPTooManyRequests(reason="rate limit")
    db: Database = request.app["db"]
    cfg: Config = request.app["config"]
    uid, data = websync.web_to_resume(await _body(request))
    if not data.get("full_name") or not (data.get("phone") or data.get("telegram")):
        raise web.HTTPBadRequest(reason="name and phone/telegram required")
    r = await db.save_resume(uid, {**data, "status": "pending"})
    active = await flow.submit_resume(request.app["bot"], db, cfg, r, force_moderation=not keyed)
    return _json({"id": f"tg{r['id']}", "status": "active" if active else "pending"}, 201)


async def stats(request: web.Request) -> web.Response:
    _need_key(request)
    db = request.app["db"]
    s = await db.stats()
    out = {k: v for k, v in s.items() if not isinstance(v, list)}
    out["top_cats"], out["top_cities"] = s["top_cats"], s["top_cities"]
    out.update(await db.stats_extra())
    return _json(out)


def _buttons_out(db: Database) -> dict:
    return {
        "buttons": flow.load_channel_buttons(db),
        "apply_text": db.setting("btn_apply_text"),
        "apply_enabled": db.setting("btn_apply_value").strip().lower() not in {"-", "none", "yo'q", "off"},
    }


async def get_buttons(request: web.Request) -> web.Response:
    _need_key(request)
    return _json(_buttons_out(request.app["db"]))


async def put_buttons(request: web.Request) -> web.Response:
    """Kanal posti tagidagi tugmalar — sayt admin panelidan. Keyingi postlarga ta'sir qiladi."""
    _need_key(request)
    db: Database = request.app["db"]
    data = await _body(request)
    items = data.get("buttons")
    if not isinstance(items, list) or len(items) > 8:
        raise web.HTTPBadRequest(reason="buttons: list (max 8) expected")
    clean = []
    for b in items:
        if not isinstance(b, dict) or not str(b.get("text") or "").strip():
            raise web.HTTPBadRequest(reason="button text required")
        url, style = str(b.get("url") or "").strip(), str(b.get("style") or "")
        if style not in flow.BUTTON_STYLES:
            raise web.HTTPBadRequest(reason=f"bad style: {style}")
        if url and not (re.match(r"^(https?://|tg://)\S+$", url) or re.match(r"^\{(post|site|bot)\}\S*$", url)):
            raise web.HTTPBadRequest(reason=f"bad url: {url[:60]}")
        clean.append({"text": str(b["text"]).strip()[:64], "url": url[:500], "style": style})
    await db.set_setting("channel_buttons", json.dumps(clean, ensure_ascii=False))
    if isinstance(data.get("apply_enabled"), bool):
        off = db.setting("btn_apply_value").strip().lower() in {"-", "none", "yo'q", "off"}
        if data["apply_enabled"] and off:
            await db.set_setting("btn_apply_value", "bot")
        elif not data["apply_enabled"] and not off:
            await db.set_setting("btn_apply_value", "none")
    if isinstance(data.get("apply_text"), str) and data["apply_text"].strip():
        await db.set_setting("btn_apply_text", data["apply_text"].strip()[:64])
    return _json(_buttons_out(db))


def build_app(bot: Bot, db: Database, config: Config) -> web.Application:
    app = web.Application(middlewares=[cors_middleware, sync_gate], client_max_size=256 * 1024)
    app["bot"], app["db"], app["config"] = bot, db, config
    app.router.add_get("/api/health", health)
    app.router.add_get("/api/vacancies", list_vacancies)
    app.router.add_get("/api/vacancies/{id}", get_vacancy)
    app.router.add_post("/api/vacancies", post_vacancy)
    app.router.add_delete("/api/vacancies/{id}", delete_vacancy)
    app.router.add_get("/api/resumes", list_resumes)
    app.router.add_post("/api/resumes", post_resume)
    app.router.add_get("/api/stats", stats)
    app.router.add_get("/api/buttons", get_buttons)
    app.router.add_put("/api/buttons", put_buttons)
    return app


async def start_api(bot: Bot, db: Database, config: Config) -> web.AppRunner:
    runner = web.AppRunner(build_app(bot, db, config), access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, config.api_host, config.api_port)
    await site.start()
    log.info("REST API ishga tushdi: http://%s:%s/api", config.api_host, config.api_port)
    return runner
