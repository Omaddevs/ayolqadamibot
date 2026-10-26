"""Ma'lumotnomalar — web ilovadagi (src/data/mock.js, resume.js) ro'yxatlar bilan bir xil id'lar.
Shu tufayli bot va sayt o'rtasida ma'lumot almashganda soha/shahar/format mos keladi."""

# (id, uz, ru) — id'lar web'dagi CATEGORIES bilan bir xil
CATEGORIES = [
    ("office", "Ofis ishlari", "Офисная работа"),
    ("edu", "Ta'lim va pedagogika", "Образование"),
    ("med", "Tibbiyot", "Медицина"),
    ("nanny", "Enaga va bola parvarishi", "Няня, уход за детьми"),
    ("housekeeper", "Uy xizmatchisi", "Домработница"),
    ("cleaning", "Tozalik xodimi", "Уборка"),
    ("cook", "Oshpaz", "Повар"),
    ("caregiver", "Keksalar parvarishi", "Сиделка"),
    ("sales", "Savdo va mijozlar", "Продажи"),
    ("beauty", "Go'zallik va parvarish", "Красота"),
    ("it", "IT va dizayn", "IT и дизайн"),
    ("home", "Maishiy xizmatlar", "Бытовые услуги"),
    ("remote", "Masofaviy ish", "Удалённая работа"),
    ("production", "Ishlab chiqarish", "Производство"),
    ("food", "Restoran va mehmonxona", "Ресторан и отель"),
    ("marketing", "Marketing va media", "Маркетинг"),
    ("finance", "Moliya va buxgalteriya", "Финансы"),
    ("law", "Huquq", "Юриспруденция"),
    ("logistics", "Logistika", "Логистика"),
    ("other", "Boshqa", "Другое"),
]

# Qiymat — viloyat markazi (web'dagi CITIES bilan bir xil), "Toshkent viloyati" — alohida
CITIES = [
    "Toshkent", "Toshkent viloyati", "Andijon", "Buxoro", "Farg'ona", "Jizzax", "Urganch", "Namangan", "Navoiy",
    "Qarshi", "Nukus", "Samarqand", "Guliston", "Termiz",
]
# Tugmalarda viloyat nomi ko'rinadi — "Qarshi" emas, "Qashqadaryo" deb qidiriladi
CITY_LABELS = {
    "Toshkent": "Toshkent shahri", "Urganch": "Xorazm (Urganch)", "Qarshi": "Qashqadaryo (Qarshi)",
    "Nukus": "Qoraqalpog'iston (Nukus)", "Guliston": "Sirdaryo (Guliston)", "Termiz": "Surxondaryo (Termiz)",
}


def city_label(city: str) -> str:
    return CITY_LABELS.get(city, city)

# id, uz, ru — `web` maydoni saytdagi JOB_TYPES yozuvi
JOB_TYPES = [
    ("full", "To'liq stavka", "Полный день"),
    ("part", "Yarim stavka", "Неполный день"),
    ("remote", "Masofaviy", "Удалённо"),
    ("hybrid", "Gibrid", "Гибрид"),
]
JOB_TYPE_WEB = {"full": "To'liq stavka", "part": "Yarim stavka", "remote": "Masofaviy", "hybrid": "Gibrid"}

# tajriba: id, uz, ru, yillar (web'dagi job.experience soni)
EXP_LEVELS = [
    ("0", "Tajribasiz", "Без опыта", 0),
    ("1", "1 yilgacha", "До 1 года", 0),
    ("1-3", "1–3 yil", "1–3 года", 1),
    ("3-5", "3–5 yil", "3–5 лет", 3),
    ("5+", "5 yildan ortiq", "Более 5 лет", 5),
]

EDU_LEVELS = [
    ("school", "O'rta (maktab)", "Среднее"),
    ("college", "O'rta maxsus (kollej)", "Среднее специальное"),
    ("bachelor", "Oliy — bakalavr", "Высшее — бакалавр"),
    ("master", "Oliy — magistr", "Высшее — магистр"),
    ("courses", "Kasbiy kurslar", "Профессиональные курсы"),
]

LANGUAGES = [
    ("uz", "O'zbek tili", "Узбекский"),
    ("ru", "Rus tili", "Русский"),
    ("en", "Ingliz tili", "Английский"),
    ("kaa", "Qoraqalpoq tili", "Каракалпакский"),
    ("tg", "Tojik tili", "Таджикский"),
    ("kk", "Qozoq tili", "Казахский"),
    ("tr", "Turk tili", "Турецкий"),
    ("ko", "Koreys tili", "Корейский"),
    ("ar", "Arab tili", "Арабский"),
    ("de", "Nemis tili", "Немецкий"),
]

# web'dagi `color` maydoni uchun (kompaniya logotipi o'rnida)
COLORS = ["#6366F6", "#F59E0B", "#10B981", "#EF4444", "#8B5CF6", "#EC4899", "#14B8A6", "#3B82F6"]


def _find(items, key):
    return next((x for x in items if x[0] == key), None)


def _label(items, key, lang):
    item = _find(items, key)
    if not item:
        return key or ""
    return item[2] if lang == "ru" else item[1]


def cat_name(key, lang="uz"):
    return _label(CATEGORIES, key, lang)


def job_type_name(key, lang="uz"):
    return _label(JOB_TYPES, key, lang)


def exp_name(key, lang="uz"):
    return _label(EXP_LEVELS, key, lang)


def exp_years(key) -> int:
    item = _find(EXP_LEVELS, key)
    return item[3] if item else 0


def edu_name(key, lang="uz"):
    return _label(EDU_LEVELS, key, lang)


def lang_name(key, lang="uz"):
    return _label(LANGUAGES, key, lang)


def color_for(seed: int) -> str:
    return COLORS[seed % len(COLORS)]
