from aiogram.fsm.state import State, StatesGroup


class ResumeForm(StatesGroup):
    name = State()
    birth = State()
    phone = State()
    city = State()
    cat = State()
    headline = State()
    exp_level = State()
    exp = State()
    edu_level = State()
    edu = State()
    skills = State()
    langs = State()
    types = State()
    salary = State()
    about = State()
    photo = State()
    confirm = State()


class VacancyForm(StatesGroup):
    title = State()
    company = State()
    cat = State()
    city = State()
    jtype = State()
    salary = State()
    exp = State()
    desc = State()
    req = State()
    cond = State()
    phone = State()
    tg = State()
    confirm = State()


class Browse(StatesGroup):
    query = State()


class Support(StatesGroup):
    message = State()


class AdminPost(StatesGroup):
    message = State()
    cat = State()
    city = State()
    apply = State()
    apply_input = State()
    post = State()
    post_input = State()
    confirm = State()


class AdForm(StatesGroup):
    """«E'lon berish»: shablon maydonlari birma-bir, so'ng ko'rib chiqish."""
    fill = State()
    confirm = State()


class AdminBroadcast(StatesGroup):
    message = State()
    button = State()
    confirm = State()


class AdminInput(StatesGroup):
    """Bitta qiymat so'raladigan admin amallari (kanal qo'shish, tugma matni, foydalanuvchi qidirish ...)."""
    value = State()
