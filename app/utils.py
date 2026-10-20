"""Formatlash va kartochka matnlari."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from html import escape

from .constants import cat_name, edu_name, exp_name, job_type_name, lang_name
from .texts import t

PHONE_RE = re.compile(r"^\+?\d[\d\s\-()]{7,18}\d$")
CAPTION_LIMIT = 1024
TEXT_LIMIT = 4096


def h(value) -> str:
    """HTML parse_mode uchun xavfsiz matn."""
    return escape(str(value or ""), quote=False)


def money(n: int | None) -> str:
    return f"{int(n):,}".replace(",", " ") if n else ""


def salary_text(frm: int | None, to: int | None, lang: str) -> str:
    cur = t("sum", lang)
    if frm and to and frm != to:
        return f"{money(frm)} – {money(to)} {cur}"
    if frm:
        return f"{t('from', lang)} {money(frm)} {cur}" if lang == "ru" else f"{money(frm)} {cur}{t('from', lang)}"
    if to:
        return f"{money(to)} {cur}"
    return t("negotiable", lang)


def parse_int(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text or "")
    if not digits:
        return None
    value = int(digits)
    # "5 mln", "5.5 mln" kabi qisqa yozuvlar
    low = (text or "").lower()
    if ("mln" in low or "млн" in low) and value < 1000:
        whole = re.findall(r"\d+(?:[.,]\d+)?", low)
        value = int(float(whole[0].replace(",", ".")) * 1_000_000) if whole else value * 1_000_000
    return value


def parse_salary(text: str) -> tuple[int | None, int | None]:
    parts = re.split(r"\s*[-–—]\s*|\s+(?:dan|до|to)\s+", (text or "").strip(), maxsplit=1)
    nums = [parse_int(p) for p in parts if p.strip()]
    nums = [n for n in nums if n]
    if not nums:
        return None, None
    if len(nums) == 1:
        return nums[0], None
    a, b = sorted(nums[:2])
    return a, b


def normalize_phone(text: str | None) -> str | None:
    if not text:
        return None
    raw = text.strip()
    if not PHONE_RE.match(raw):
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 9:
        digits = "998" + digits
    if len(digits) < 9 or len(digits) > 15:
        return None
    if digits.startswith("998") and len(digits) == 12:
        return f"+998 {digits[3:5]} {digits[5:8]} {digits[8:10]} {digits[10:12]}"
    return "+" + digits


def normalize_tg(text: str | None) -> str | None:
    if not text:
        return None
    raw = text.strip()
    m = re.match(r"^(?:https?://)?(?:t\.me/|telegram\.me/)?@?([A-Za-z][A-Za-z0-9_]{3,31})$", raw)
    return "@" + m.group(1) if m else None


def short_date(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        d = datetime.fromisoformat(iso)
    except ValueError:
        return iso[:10]
    return d.astimezone().strftime("%d.%m.%Y")


def age_from_year(year: int | None) -> int | None:
    if not year:
        return None
    return datetime.now(timezone.utc).year - int(year)


def cut(text: str | None, n: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def lines_list(text: str | None) -> list[str]:
    return [ln.strip(" •-–—*\t") for ln in (text or "").splitlines() if ln.strip(" •-–—*\t")]


def first_line_title(text: str | None, n: int = 80) -> str:
    for ln in (text or "").splitlines():
        clean = re.sub(r"[#*_`~|]+", "", ln).strip()
        if len(clean) >= 3:
            return cut(clean, n)
    return "E'lon"


# ---------- kartochkalar ----------
def vacancy_card(v: dict, lang: str, limit: int = TEXT_LIMIT, footer: str = "") -> str:
    """Bot ichida va kanalda ko'rsatiladigan vakansiya matni (HTML)."""
    if v.get("source") == "admin" and not v.get("company"):
        # admin joylagan erkin e'lon — matni o'zgarishsiz
        body = h(v.get("description"))
        extra = []
        if v.get("category"):
            extra.append(f"{t('v_cat', lang)}: {h(cat_name(v['category'], lang))}")
        if v.get("city"):
            extra.append(f"{t('v_city', lang)}: {h(v['city'])}")
        tail = ("\n\n" + "\n".join(extra) if extra else "") + (f"\n\n{footer}" if footer else "")
        return cut(body, limit - len(tail) - 5) + tail

    parts = [f"💼 <b>{h(v.get('title'))}</b>"]
    if v.get("company"):
        parts.append(f"🏢 {h(v['company'])}")
    parts.append("")
    parts.append(f"{t('v_salary', lang)}: <b>{h(salary_text(v.get('salary_from'), v.get('salary_to'), lang))}</b>")
    if v.get("city"):
        parts.append(f"{t('v_city', lang)}: {h(v['city'])}")
    if v.get("job_type"):
        parts.append(f"{t('v_type', lang)}: {h(job_type_name(v['job_type'], lang))}")
    if v.get("exp_level"):
        parts.append(f"{t('v_exp', lang)}: {h(exp_name(v['exp_level'], lang))}")
    if v.get("category"):
        parts.append(f"{t('v_cat', lang)}: {h(cat_name(v['category'], lang))}")
    head = "\n".join(parts)

    sections = []
    if v.get("description"):
        sections.append(h(v["description"]))
    req = lines_list(v.get("requirements"))
    if req:
        sections.append(f"<b>{t('v_req', lang)}:</b>\n" + "\n".join(f"• {h(x)}" for x in req))
    cond = lines_list(v.get("conditions"))
    if cond:
        sections.append(f"<b>{t('v_cond', lang)}:</b>\n" + "\n".join(f"• {h(x)}" for x in cond))
    tail = f"\n\n{footer}" if footer else ""
    body = "\n\n".join(sections)
    room = limit - len(head) - len(tail) - 4
    return head + ("\n\n" + cut(body, room) if body and room > 50 else "") + tail


def resume_card(r: dict, lang: str, limit: int = TEXT_LIMIT, footer: str = "", show_contacts: bool = False) -> str:
    parts = [f"👩‍💼 <b>{h(r.get('full_name'))}</b>"]
    if r.get("headline"):
        parts.append(f"💼 <i>{h(r['headline'])}</i>")
    parts.append("")
    if r.get("category"):
        parts.append(f"{t('v_cat', lang)}: {h(cat_name(r['category'], lang))}")
    if r.get("city"):
        parts.append(f"{t('v_city', lang)}: {h(r['city'])}")
    age = age_from_year(r.get("birth_year"))
    if age:
        parts.append(f"{t('r_age', lang)}: {t('r_age_val', lang, n=age)}")
    if r.get("exp_level"):
        parts.append(f"{t('v_exp', lang)}: {h(exp_name(r['exp_level'], lang))}")
    if r.get("edu_level"):
        parts.append(f"{t('r_edu_l', lang)}: {h(edu_name(r['edu_level'], lang))}")
    parts.append(f"{t('r_salary_l', lang)}: <b>{h(salary_text(r.get('salary'), None, lang) if r.get('salary') else t('negotiable', lang))}</b>")
    if r.get("job_types"):
        parts.append(f"{t('r_types_l', lang)}: {h(', '.join(job_type_name(x, lang) for x in r['job_types']))}")
    if r.get("skills"):
        parts.append(f"{t('lbl_skills', lang)}: {h(', '.join(r['skills'][:12]))}")
    if r.get("languages"):
        parts.append(f"{t('lbl_langs', lang)}: {h(', '.join(lang_name(x, lang) for x in r['languages']))}")
    if show_contacts:
        if r.get("phone"):
            parts.append(f"📱 {h(r['phone'])}")
        if r.get("telegram"):
            parts.append(f"✈️ {h(r['telegram'])}")
    head = "\n".join(parts)
    tail = f"\n\n{footer}" if footer else ""
    body = ""
    if r.get("about"):
        body = f"<b>{t('r_about_l', lang)}:</b>\n{h(r['about'])}"
    room = limit - len(head) - len(tail) - 4
    return head + ("\n\n" + cut(body, room) if body and room > 60 else "") + tail


def contact_lines(phone: str | None, tg: str | None, extra: str | None = None) -> str:
    rows = []
    if phone:
        rows.append(f"📱 <code>{h(phone)}</code>")
    if tg:
        rows.append(f"✈️ {h(tg)}")
    if extra:
        rows.append(h(extra))
    return "\n".join(rows)


def classify_target(value: str | None) -> tuple[str, str]:
    """Kanal tugmasi qiymati: ('bot'|'url'|'phone'|'none', normal qiymat)."""
    v = (value or "").strip()
    if not v or v.lower() == "bot":
        return "bot", ""
    if v in {"-", "none", "yo'q", "off"}:
        return "none", ""
    if re.match(r"^(https?|tg)://", v, re.I):
        return "url", v
    if re.match(r"^(t\.me|telegram\.me)/", v, re.I):
        return "url", "https://" + v
    tg = normalize_tg(v) if v.startswith("@") else None
    if tg:
        return "url", f"https://t.me/{tg[1:]}"
    phone = normalize_phone(v)
    if phone:
        return "phone", phone
    if re.match(r"^[\w.-]+\.[a-z]{2,}(/.*)?$", v, re.I):
        return "url", "https://" + v
    return "none", ""
