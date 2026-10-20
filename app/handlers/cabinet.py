"""Shaxsiy kabinet: rezyumem, vakansiyalarim, arizalarim, sozlamalar, yordam."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ..callbacks import Act, AppCb, MyRes, MyVac, SetCb, SupCb
from ..config import Config
from ..db import Database, now
from ..keyboards import cancel_kb, lang_kb, role_kb, web_kb
from ..services import flow, notify, websync
from ..states import Support
from ..texts import t
from ..utils import h, resume_card, short_date
from .base import send_menu
from .browse import render, vacancy_view
from .resume import start_resume

router = Router(name="cabinet")


# ---------- mening rezyumem ----------
def _my_resume_kb(r: dict, lang: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=t("b_res_pdf", lang), callback_data=Act(a="rp", id=r["id"], k="onr").pack()),
         InlineKeyboardButton(text=t("b_res_doc", lang), callback_data=Act(a="rd", id=r["id"], k="onr").pack())],
        [InlineKeyboardButton(text=t("b_edit", lang), callback_data=MyRes(a="edit").pack())],
    ]
    if r["status"] == "active":
        rows.append([InlineKeyboardButton(text=t("b_hide", lang), callback_data=MyRes(a="hide").pack())])
    elif r["status"] == "hidden":
        rows.append([InlineKeyboardButton(text=t("b_show", lang), callback_data=MyRes(a="show").pack())])
    rows.append([InlineKeyboardButton(text=t("b_delete", lang), callback_data=MyRes(a="del").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_my_resume(event: Message | CallbackQuery, db: Database, bot: Bot, user: dict, lang: str) -> None:
    r = await db.resume_by_user(user["id"])
    if not r:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("b_create_resume", lang), callback_data=MyRes(a="create").pack())]])
        await render(event, bot, t("no_resume", lang), kb)
        return
    head = t("my_resume", lang, status=t("st_" + r["status"], lang), views=r.get("views") or 0)
    has_photo = bool(r.get("photo_file_id"))
    text = head + "\n\n" + resume_card(r, lang, 1024 - len(head) - 4 if has_photo else 3800, show_contacts=True)
    await render(event, bot, text, _my_resume_kb(r, lang), "photo" if has_photo else None, r.get("photo_file_id"))


@router.callback_query(MyRes.filter())
async def my_resume_action(cb: CallbackQuery, callback_data: MyRes, state: FSMContext, db: Database, config: Config, bot: Bot, user: dict, lang: str) -> None:
    a = callback_data.a
    if a in ("create", "edit"):
        await cb.answer()
        await start_resume(cb.message, state, db, user, lang)
        return
    r = await db.resume_by_user(user["id"])
    if not r:
        return await cb.answer(t("not_found", lang), show_alert=True)
    if a == "hide":
        await db.set_resume_status(r["id"], "hidden")
        flow.background(websync.push(db, config, "resumes", "delete", {"id": f"tg{r['id']}"}))
    elif a == "show":
        await db.set_resume_status(r["id"], "active")
        flow.background(websync.push(db, config, "resumes", "upsert", websync.resume_to_web(await db.get_resume(r["id"]))))
    elif a == "del":
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("yes", lang), callback_data=MyRes(a="del_yes").pack()),
            InlineKeyboardButton(text=t("no", lang), callback_data=MyRes(a="view").pack()),
        ]])
        await cb.answer()
        await render(cb, bot, t("confirm_delete", lang), kb)
        return
    elif a == "del_yes":
        await db.delete_resume(r["id"])
        flow.background(websync.push(db, config, "resumes", "delete", {"id": f"tg{r['id']}"}))
        await cb.answer(t("deleted", lang))
        await render(cb, bot, t("deleted", lang), None)
        return
    await cb.answer()
    await show_my_resume(cb, db, bot, user, lang)


# ---------- mening vakansiyalarim ----------
async def show_my_vacancies(event: Message | CallbackQuery, db: Database, bot: Bot, user: dict, lang: str) -> None:
    vacs = await db.user_vacancies(user["id"])
    if not vacs:
        await render(event, bot, t("no_vacs", lang), None)
        return
    icons = {"active": "🟢", "pending": "⏳", "closed": "🔒", "rejected": "❌"}
    rows = [[InlineKeyboardButton(text=f"{icons.get(v['status'], '•')} {v['title'][:34]} · 👥 {v['apps']}", callback_data=MyVac(a="open", id=v["id"]).pack())]
            for v in vacs[:30]]
    await render(event, bot, t("my_vacs", lang, n=len(vacs)), InlineKeyboardMarkup(inline_keyboard=rows))


def _my_vac_kb(v: dict, apps: int, lang: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=t("b_apps", lang, n=apps), callback_data=MyVac(a="apps", id=v["id"]).pack())],
            [InlineKeyboardButton(text=t("b_vac_pdf", lang), callback_data=Act(a="vp", id=v["id"]).pack()),
             InlineKeyboardButton(text=t("b_vac_doc", lang), callback_data=Act(a="vd", id=v["id"]).pack())]]
    if v["status"] == "active":
        rows.append([InlineKeyboardButton(text=t("b_close", lang), callback_data=MyVac(a="close", id=v["id"]).pack())])
    elif v["status"] == "closed":
        rows.append([InlineKeyboardButton(text=t("b_reopen", lang), callback_data=MyVac(a="reopen", id=v["id"]).pack())])
    rows.append([InlineKeyboardButton(text=t("b_delete", lang), callback_data=MyVac(a="del", id=v["id"]).pack())])
    rows.append([InlineKeyboardButton(text=t("back", lang), callback_data=MyVac(a="list").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(MyVac.filter())
async def my_vac_action(cb: CallbackQuery, callback_data: MyVac, db: Database, config: Config, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    a = callback_data.a
    if a == "list":
        await cb.answer()
        await show_my_vacancies(cb, db, bot, user, lang)
        return
    if a == "app":
        app = await db.get_application(callback_data.id)
        v = await db.get_vacancy(app["vacancy_id"]) if app else None
        r = await db.get_resume(app["resume_id"]) if app and app.get("resume_id") else None
        if not app or not v or v.get("user_id") != user["id"] or not r:
            return await cb.answer(t("not_found", lang), show_alert=True)
        if app["status"] == "new":
            await db.set_application_status(app["id"], "viewed")
        await cb.answer()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("b_res_pdf", lang), callback_data=Act(a="rp", id=r["id"], k="app").pack()),
             InlineKeyboardButton(text=t("b_res_doc", lang), callback_data=Act(a="rd", id=r["id"], k="app").pack())],
            [InlineKeyboardButton(text=t("b_accept", lang), callback_data=AppCb(id=app["id"], s="invited").pack())],
            [InlineKeyboardButton(text=t("b_reject", lang), callback_data=AppCb(id=app["id"], s="rejected").pack())],
            [InlineKeyboardButton(text=t("back", lang), callback_data=MyVac(a="apps", id=v["id"]).pack())],
        ])
        status = t("app_" + app["status"], lang) if app["status"] != "new" else ""
        text = (status + "\n\n" if status else "") + resume_card(r, lang, 1000 if r.get("photo_file_id") else 3800, show_contacts=True)
        await render(cb, bot, text, kb, "photo" if r.get("photo_file_id") else None, r.get("photo_file_id"))
        return

    v = await db.get_vacancy(callback_data.id)
    if not v or (v.get("user_id") != user["id"] and not is_admin):
        return await cb.answer(t("not_found", lang), show_alert=True)

    if a == "apps":
        apps = await db.vacancy_applications(v["id"])
        if not apps:
            return await cb.answer(t("no_apps", lang), show_alert=True)
        await cb.answer()
        icons = {"new": "🆕", "viewed": "👀", "invited": "🎉", "rejected": "❌"}
        rows = [[InlineKeyboardButton(text=f"{icons.get(x['status'], '•')} {(x.get('full_name') or '—')[:24]} · {(x.get('headline') or '')[:18]}",
                                      callback_data=MyVac(a="app", id=x["id"]).pack())] for x in apps[:40]]
        rows.append([InlineKeyboardButton(text=t("back", lang), callback_data=MyVac(a="open", id=v["id"]).pack())])
        await render(cb, bot, t("apps_list", lang, title=h(v["title"]), n=len(apps)), InlineKeyboardMarkup(inline_keyboard=rows))
        return
    if a == "close":
        await db.update_vacancy(v["id"], status="closed")
        await flow.unpublish_vacancy(bot, v)
        flow.background(websync.push(db, config, "vacancies", "delete", {"id": f"tg{v['id']}"}))
    elif a == "reopen":
        expires = (datetime.now(timezone.utc) + timedelta(days=config.vacancy_days)).isoformat(timespec="seconds")
        await db.update_vacancy(v["id"], expires_at=expires, channel_posts=[])
        await flow.activate_vacancy(bot, db, config, await db.get_vacancy(v["id"]))
    elif a == "del":
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t("yes", lang), callback_data=MyVac(a="del_yes", id=v["id"]).pack()),
            InlineKeyboardButton(text=t("no", lang), callback_data=MyVac(a="open", id=v["id"]).pack()),
        ]])
        await cb.answer()
        await render(cb, bot, t("confirm_delete", lang), kb)
        return
    elif a == "del_yes":
        await flow.unpublish_vacancy(bot, v, delete=True)
        await db.delete_vacancy(v["id"])
        flow.background(websync.push(db, config, "vacancies", "delete", {"id": f"tg{v['id']}"}))
        await cb.answer(t("deleted", lang))
        await show_my_vacancies(cb, db, bot, user, lang)
        return
    await cb.answer()
    v = await db.get_vacancy(v["id"])
    apps = len(await db.vacancy_applications(v["id"]))
    text, _, media_type, file_id = await vacancy_view(db, v, lang, user["id"], False, "one")
    status_line = t("st_" + v["status"], lang) + f" · ⏰ {short_date(v.get('expires_at'))}\n\n"
    await render(cb, bot, status_line + text, _my_vac_kb(v, apps, lang), media_type, file_id)


# ---------- arizalarim ----------
async def show_my_applications(message: Message, db: Database, lang: str) -> None:
    apps = await db.user_applications(message.chat.id)
    if not apps:
        await message.answer(t("no_my_apps", lang))
        return
    lines = []
    rows = []
    for a in apps:
        lines.append(f"{t('app_' + a['status'], lang)} — <b>{h(a.get('title') or '—')}</b>" + (f" · {h(a['company'])}" if a.get("company") else "")
                     + f"\n<i>{short_date(a['created_at'])}</i>")
        if a.get("vac_status") == "active" and len(rows) < 10:
            rows.append([InlineKeyboardButton(text=f"💼 {(a.get('title') or '')[:40]}", callback_data=Act(a="open", id=a["vacancy_id"]).pack())])
    await message.answer(t("my_apps", lang, lines="\n\n".join(lines)), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows) if rows else None)


# ---------- sozlamalar ----------
def _settings_view(user: dict, lang: str) -> tuple[str, InlineKeyboardMarkup]:
    role = t("role_employer" if user.get("role") == "employer" else "role_seeker", lang)
    notif = t("on" if user.get("notify", 1) else "off", lang)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("s_lang", lang), callback_data=SetCb(a="lang").pack())],
        [InlineKeyboardButton(text=t("s_role", lang), callback_data=SetCb(a="role").pack())],
        [InlineKeyboardButton(text=f"{t('s_notif', lang)}: {notif}", callback_data=SetCb(a="notif").pack())],
    ])
    return t("settings", lang, role=role, notif=notif), kb


async def show_settings(message: Message, user: dict, lang: str) -> None:
    text, kb = _settings_view(user, lang)
    await message.answer(text, reply_markup=kb)


@router.callback_query(SetCb.filter())
async def settings_action(cb: CallbackQuery, callback_data: SetCb, db: Database, user: dict, lang: str) -> None:
    await cb.answer()
    if callback_data.a == "lang":
        await cb.message.edit_text(t("choose_lang", lang), reply_markup=lang_kb())
    elif callback_data.a == "role":
        await cb.message.edit_text(t("choose_role", lang), reply_markup=role_kb(lang))
    else:
        await db.update_user(user["id"], notify=0 if user.get("notify", 1) else 1)
        text, kb = _settings_view(await db.get_user(user["id"]), lang)
        await cb.message.edit_text(text, reply_markup=kb)


# ---------- yordam (adminga yozish) ----------
async def open_support(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(Support.message)
    await message.answer(t("help", lang), reply_markup=cancel_kb(lang))


@router.message(Support.message)
async def support_message(message: Message, state: FSMContext, db: Database, config: Config, bot: Bot, user: dict, lang: str, is_admin: bool) -> None:
    await state.set_state(None)
    head = (f"✉️ <b>Yordam so'rovi</b>\n👤 {h(user.get('full_name'))}" + (f" (@{user['username']})" if user.get("username") else "")
            + f"\n🆔 <code>{user['id']}</code> · {user.get('role') or '—'} · {short_date(now())}")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💬 Javob berish", callback_data=SupCb(uid=user["id"]).pack())]])
    for admin_id in await notify.admin_ids(db, config):
        if await notify.send(bot, db, admin_id, head, reply_markup=kb):
            await notify.safe_call(db, admin_id, lambda aid=admin_id: message.copy_to(aid))
    await send_menu(message, user, lang, is_admin, t("sup_sent", lang))


# ---------- sayt ----------
async def show_web(message: Message, config: Config, lang: str) -> None:
    if not config.web_url:
        await message.answer(t("web_none", lang))
        return
    await message.answer(t("web_text", lang), reply_markup=web_kb(config.web_url, lang))

