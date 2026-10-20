"""Ikki tilli matnlar (uz / ru). Admin panel matnlari faqat o'zbekcha — ular handlers/admin.py ichida."""
from __future__ import annotations

LANGS = ("uz", "ru")

T: dict[str, dict[str, str]] = {
    # ---------- start ----------
    "choose_lang": {"uz": "🇺🇿 Tilni tanlang\n🇷🇺 Выберите язык", "ru": "🇺🇿 Tilni tanlang\n🇷🇺 Выберите язык"},
    "sub_required": {
        "uz": "📢 Botdan foydalanish uchun quyidagi kanal(lar)ga obuna bo'ling, so'ng <b>«✅ Tekshirish»</b> tugmasini bosing.",
        "ru": "📢 Чтобы пользоваться ботом, подпишитесь на канал(ы) ниже и нажмите <b>«✅ Проверить»</b>.",
    },
    "sub_check": {"uz": "✅ Tekshirish", "ru": "✅ Проверить"},
    "sub_fail": {"uz": "❌ Hali barcha kanallarga obuna bo'lmadingiz.", "ru": "❌ Вы ещё не подписались на все каналы."},
    "choose_role": {
        "uz": "Siz kimsiz? 👇\n\n👩 <b>Ish izlovchi</b> — vakansiyalarni ko'rish, rezyume yaratish (PDF/Word), ariza yuborish.\n\n"
              "🏢 <b>Ish beruvchi</b> — vakansiya joylash, nomzodlar bazasi, rezyumelarni yuklab olish.",
        "ru": "Кто вы? 👇\n\n👩 <b>Соискатель</b> — просмотр вакансий, резюме (PDF/Word), отклики.\n\n"
              "🏢 <b>Работодатель</b> — размещение вакансий, база кандидатов, скачивание резюме.",
    },
    "role_seeker": {"uz": "👩 Ish izlovchi", "ru": "👩 Соискатель"},
    "role_employer": {"uz": "🏢 Ish beruvchi", "ru": "🏢 Работодатель"},
    "welcome": {
        "uz": "Assalomu alaykum, <b>{name}</b>! 👋\n\n<b>AyolQadami</b> — ayollar uchun ish va karyera platformasi.\nQuyidagi menyudan kerakli bo'limni tanlang 👇",
        "ru": "Здравствуйте, <b>{name}</b>! 👋\n\n<b>AyolQadami</b> — платформа работы и карьеры для женщин.\nВыберите нужный раздел в меню 👇",
    },
    "banned": {"uz": "⛔️ Siz botdan foydalanishdan cheklangansiz.", "ru": "⛔️ Вам ограничен доступ к боту."},

    # ---------- menyu ----------
    "m_jobs": {"uz": "🔎 Ish qidirish", "ru": "🔎 Поиск работы"},
    "m_resume": {"uz": "📄 Mening rezyumem", "ru": "📄 Моё резюме"},
    "m_apps": {"uz": "📨 Arizalarim", "ru": "📨 Мои отклики"},
    "m_saved": {"uz": "⭐ Saqlanganlar", "ru": "⭐ Избранное"},
    "m_candidates": {"uz": "👩‍💼 Nomzodlar", "ru": "👩‍💼 Кандидаты"},
    "m_post_vac": {"uz": "➕ Vakansiya joylash", "ru": "➕ Разместить вакансию"},
    "m_my_vacs": {"uz": "📋 Vakansiyalarim", "ru": "📋 Мои вакансии"},
    "m_web": {"uz": "🌐 Sayt", "ru": "🌐 Сайт"},
    "m_settings": {"uz": "⚙️ Sozlamalar", "ru": "⚙️ Настройки"},
    "m_help": {"uz": "✉️ Yordam", "ru": "✉️ Помощь"},
    "m_admin": {"uz": "🛠 Admin panel", "ru": "🛠 Админ панель"},

    "back": {"uz": "⬅️ Orqaga", "ru": "⬅️ Назад"},
    "cancel": {"uz": "❌ Bekor qilish", "ru": "❌ Отмена"},
    "skip": {"uz": "⏭ O'tkazib yuborish", "ru": "⏭ Пропустить"},
    "done": {"uz": "✅ Tayyor", "ru": "✅ Готово"},
    "yes": {"uz": "✅ Ha", "ru": "✅ Да"},
    "no": {"uz": "❌ Yo'q", "ru": "❌ Нет"},
    "cancelled": {"uz": "Bekor qilindi.", "ru": "Отменено."},
    "main_menu": {"uz": "🏠 Bosh menyu", "ru": "🏠 Главное меню"},
    "bad_input": {"uz": "⚠️ Noto'g'ri qiymat, qaytadan kiriting.", "ru": "⚠️ Неверное значение, введите ещё раз."},
    "too_long": {"uz": "⚠️ Juda uzun matn ({n} belgigacha).", "ru": "⚠️ Слишком длинный текст (до {n} символов)."},
    "send_phone": {"uz": "📱 Raqamni yuborish", "ru": "📱 Отправить номер"},
    "any": {"uz": "🌍 Hammasi", "ru": "🌍 Все"},
    "loading": {"uz": "⏳ Tayyorlanmoqda...", "ru": "⏳ Готовим..."},
    "not_found": {"uz": "Topilmadi yoki o'chirilgan.", "ru": "Не найдено или удалено."},
    "negotiable": {"uz": "Kelishiladi", "ru": "Договорная"},
    "sum": {"uz": "so'm", "ru": "сум"},
    "from": {"uz": "dan", "ru": "от"},

    # ---------- qidiruv ----------
    "jobs_filter": {"uz": "🔎 <b>Ish qidirish</b>\n\nFaol vakansiyalar: <b>{n}</b>\nQanday qidiramiz?", "ru": "🔎 <b>Поиск работы</b>\n\nАктивных вакансий: <b>{n}</b>\nКак ищем?"},
    "cands_filter": {"uz": "👩‍💼 <b>Nomzodlar bazasi</b>\n\nFaol rezyumelar: <b>{n}</b>\nQanday qidiramiz?", "ru": "👩‍💼 <b>База кандидатов</b>\n\nАктивных резюме: <b>{n}</b>\nКак ищем?"},
    "f_all": {"uz": "📋 Barchasi", "ru": "📋 Все"},
    "f_match": {"uz": "✨ Menga mos", "ru": "✨ Подходящие мне"},
    "f_cat": {"uz": "🗂 Soha bo'yicha", "ru": "🗂 По сфере"},
    "f_city": {"uz": "📍 Shahar bo'yicha", "ru": "📍 По городу"},
    "f_q": {"uz": "🔤 So'z bo'yicha", "ru": "🔤 По слову"},
    "ask_q": {"uz": "🔤 Qidiruv so'zini yozing (masalan: <i>buxgalter</i>, <i>enaga</i>, <i>React</i>):", "ru": "🔤 Введите слово для поиска (например: <i>бухгалтер</i>, <i>няня</i>, <i>React</i>):"},
    "choose_cat": {"uz": "🗂 Sohani tanlang:", "ru": "🗂 Выберите сферу:"},
    "choose_city": {"uz": "📍 Shaharni tanlang:", "ru": "📍 Выберите город:"},
    "no_results": {"uz": "😔 Hozircha mos natija topilmadi. Boshqa filtr bilan urinib ko'ring.", "ru": "😔 Пока ничего не найдено. Попробуйте другой фильтр."},
    "need_match_resume": {"uz": "«✨ Menga mos» uchun avval rezyume yarating — soha va shahringiz bo'yicha tanlab beramiz.", "ru": "Для «✨ Подходящие мне» сначала создайте резюме — подберём по сфере и городу."},

    # ---------- karta tugmalari ----------
    "b_contact": {"uz": "📞 Bog'lanish", "ru": "📞 Связаться"},
    "b_apply": {"uz": "✅ Ariza yuborish", "ru": "✅ Откликнуться"},
    "b_save": {"uz": "☆ Saqlash", "ru": "☆ В избранное"},
    "b_saved": {"uz": "⭐ Saqlangan", "ru": "⭐ В избранном"},
    "b_vac_pdf": {"uz": "📄 PDF", "ru": "📄 PDF"},
    "b_vac_doc": {"uz": "📝 DOC", "ru": "📝 DOC"},
    "b_res_pdf": {"uz": "📄 Resume PDF", "ru": "📄 Резюме PDF"},
    "b_res_doc": {"uz": "📝 Resume DOC", "ru": "📝 Резюме DOC"},
    "b_invite": {"uz": "✉️ Taklif yuborish", "ru": "✉️ Пригласить"},
    "b_filter": {"uz": "🔎 Filtr", "ru": "🔎 Фильтр"},
    "b_channel": {"uz": "📢 Kanalda ko'rish", "ru": "📢 Смотреть в канале"},

    # ---------- vakansiya kartasi ----------
    "v_salary": {"uz": "💰 Maosh", "ru": "💰 Зарплата"},
    "v_city": {"uz": "📍 Shahar", "ru": "📍 Город"},
    "v_type": {"uz": "🕒 Format", "ru": "🕒 Формат"},
    "v_exp": {"uz": "🎓 Tajriba", "ru": "🎓 Опыт"},
    "v_cat": {"uz": "🗂 Soha", "ru": "🗂 Сфера"},
    "v_req": {"uz": "📌 Talablar", "ru": "📌 Требования"},
    "v_cond": {"uz": "🎁 Sharoitlar", "ru": "🎁 Условия"},
    "v_views": {"uz": "👁 {n} · 📅 {date}", "ru": "👁 {n} · 📅 {date}"},
    "contact_info": {"uz": "📞 <b>Bog'lanish</b>\n\n{lines}", "ru": "📞 <b>Контакты</b>\n\n{lines}"},
    "no_contact": {"uz": "Aloqa ma'lumoti ko'rsatilmagan. «✅ Ariza yuborish» orqali murojaat qiling.", "ru": "Контакты не указаны. Используйте «✅ Откликнуться»."},
    "phone_alert": {"uz": "📞 Bog'lanish uchun: {phone}", "ru": "📞 Для связи: {phone}"},

    # ---------- rezyume kartasi ----------
    "r_age": {"uz": "🎂 Yoshi", "ru": "🎂 Возраст"},
    "r_age_val": {"uz": "{n} yosh", "ru": "{n} лет"},
    "lbl_skills": {"uz": "🛠 Ko'nikmalar", "ru": "🛠 Навыки"},
    "lbl_langs": {"uz": "🗣 Tillar", "ru": "🗣 Языки"},
    "r_edu_l": {"uz": "🎓 Ma'lumoti", "ru": "🎓 Образование"},
    "r_salary_l": {"uz": "💰 Kutilgan maosh", "ru": "💰 Ожидаемая зарплата"},
    "r_types_l": {"uz": "🕒 Format", "ru": "🕒 Формат"},
    "r_about_l": {"uz": "💬 O'zi haqida", "ru": "💬 О себе"},
    "r_exp_l": {"uz": "💼 Tajriba", "ru": "💼 Опыт"},

    # ---------- ariza ----------
    "need_resume": {"uz": "📄 Ariza yuborish uchun avval rezyume yarating — 3 daqiqa vaqt oladi.", "ru": "📄 Чтобы откликнуться, сначала создайте резюме — это займёт 3 минуты."},
    "resume_inactive": {"uz": "⏳ Rezyumengiz hali faol emas (moderatsiyada yoki yashirilgan). Faol bo'lgach ariza yubora olasiz.", "ru": "⏳ Ваше резюме ещё не активно (на модерации или скрыто)."},
    "applied": {"uz": "✅ Arizangiz yuborildi! Ish beruvchi javob berganda bildirishnoma olasiz.", "ru": "✅ Отклик отправлен! Вы получите уведомление, когда работодатель ответит."},
    "already_applied": {"uz": "Siz bu vakansiyaga allaqachon ariza yuborgansiz.", "ru": "Вы уже откликнулись на эту вакансию."},
    "own_vacancy": {"uz": "Bu sizning vakansiyangiz.", "ru": "Это ваша вакансия."},
    "b_create_resume": {"uz": "➕ Rezyume yaratish", "ru": "➕ Создать резюме"},

    # ---------- rezyume ustasi ----------
    "r_intro": {
        "uz": "📄 <b>Rezyume yaratish</b>\n\n13 ta qisqa savol — taxminan 3 daqiqa. Oxirida <b>professional PDF va Word</b> rezyume tayyor bo'ladi.\n\nIstalgan payt <b>«❌ Bekor qilish»</b> ni bosishingiz mumkin.",
        "ru": "📄 <b>Создание резюме</b>\n\n13 коротких вопросов — около 3 минут. В конце получите <b>профессиональное резюме в PDF и Word</b>.\n\nВ любой момент можно нажать <b>«❌ Отмена»</b>.",
    },
    "r_name": {"uz": "1/13. ✍️ Ism-familiyangiz (masalan: <i>Malika Rahimova</i>):", "ru": "1/13. ✍️ Ваше имя и фамилия (например: <i>Малика Рахимова</i>):"},
    "r_birth": {"uz": "2/13. 🎂 Tug'ilgan yilingiz (masalan: <i>1995</i>):", "ru": "2/13. 🎂 Год рождения (например: <i>1995</i>):"},
    "r_phone": {"uz": "3/13. 📱 Telefon raqamingiz — tugmani bosing yoki yozing (<i>+998 90 123 45 67</i>):", "ru": "3/13. 📱 Ваш номер — нажмите кнопку или введите (<i>+998 90 123 45 67</i>):"},
    "r_city": {"uz": "4/13. 📍 Qaysi shahardasiz?", "ru": "4/13. 📍 В каком вы городе?"},
    "r_cat": {"uz": "5/13. 🗂 Qaysi sohada ishlamoqchisiz?", "ru": "5/13. 🗂 В какой сфере хотите работать?"},
    "r_headline": {"uz": "6/13. 💼 Lavozim / mutaxassisligingiz (masalan: <i>Buxgalter</i>, <i>Enaga</i>, <i>Frontend dasturchi</i>):", "ru": "6/13. 💼 Должность / специальность (например: <i>Бухгалтер</i>, <i>Няня</i>):"},
    "r_exp_level": {"uz": "7/13. ⏳ Ish tajribangiz:", "ru": "7/13. ⏳ Ваш опыт работы:"},
    "r_exp": {
        "uz": "8/13. 🏢 Qayerda ishlagansiz? Har bir joyni yangi qatordan yozing:\n\n<i>2020–2024 — «Agro Invest», bosh buxgalter\n2018–2020 — «Savdo Group», buxgalter</i>",
        "ru": "8/13. 🏢 Где вы работали? Каждое место с новой строки:\n\n<i>2020–2024 — «Agro Invest», главный бухгалтер\n2018–2020 — «Savdo Group», бухгалтер</i>",
    },
    "r_edu_level": {"uz": "9/13. 🎓 Ma'lumotingiz:", "ru": "9/13. 🎓 Ваше образование:"},
    "r_edu": {"uz": "🏫 O'quv yurti, yo'nalish va yil (masalan: <i>TDIU, Buxgalteriya hisobi, 2012</i>):", "ru": "🏫 Учебное заведение, направление и год (например: <i>ТГЭУ, Бухучёт, 2012</i>):"},
    "r_skills": {"uz": "10/13. 🛠 Ko'nikmalaringizni vergul bilan yozing (masalan: <i>1C, Excel, Soliq hisoboti</i>):", "ru": "10/13. 🛠 Навыки через запятую (например: <i>1C, Excel, Налоговая отчётность</i>):"},
    "r_langs": {"uz": "11/13. 🗣 Qaysi tillarni bilasiz? Tanlang va <b>«✅ Tayyor»</b> ni bosing:", "ru": "11/13. 🗣 Какие языки знаете? Отметьте и нажмите <b>«✅ Готово»</b>:"},
    "r_types": {"uz": "12/13. 🕒 Qaysi ish formati mos? (bir nechtasini tanlash mumkin)", "ru": "12/13. 🕒 Какой формат работы подходит? (можно несколько)"},
    "r_salary": {"uz": "13/13. 💰 Kutilayotgan maosh, so'mda (masalan: <i>5000000</i>):", "ru": "13/13. 💰 Ожидаемая зарплата в сумах (например: <i>5000000</i>):"},
    "r_about": {"uz": "💬 O'zingiz haqingizda 2–4 gap yozing: kuchli tomonlaringiz, maqsadingiz.", "ru": "💬 Напишите о себе 2–4 предложения: сильные стороны, цели."},
    "r_photo": {"uz": "📸 Rezyume uchun rasmingizni yuboring (ixtiyoriy) — u PDF va Word faylda chiqadi.", "ru": "📸 Отправьте фото для резюме (необязательно) — оно появится в PDF и Word."},
    "r_preview": {"uz": "👆 Rezyumengiz shunday ko'rinadi. Hammasi to'g'rimi?", "ru": "👆 Так выглядит ваше резюме. Всё верно?"},
    "r_save": {"uz": "💾 Saqlash va e'lon qilish", "ru": "💾 Сохранить и опубликовать"},
    "r_restart": {"uz": "🔄 Qaytadan to'ldirish", "ru": "🔄 Заполнить заново"},
    "r_saved_pending": {"uz": "✅ Rezyume saqlandi va moderatsiyaga yuborildi. Tasdiqlangach ish beruvchilar ko'radi.", "ru": "✅ Резюме сохранено и отправлено на модерацию. После проверки его увидят работодатели."},
    "r_saved_active": {"uz": "✅ Rezyume saqlandi va e'lon qilindi! Endi ish beruvchilar sizni topa oladi.", "ru": "✅ Резюме сохранено и опубликовано! Теперь работодатели смогут вас найти."},
    "r_files_ready": {"uz": "📎 Rezyumengiz fayllari:", "ru": "📎 Файлы вашего резюме:"},
    "bad_year": {"uz": "⚠️ Yilni 4 xonali son bilan yozing (1950–2010).", "ru": "⚠️ Введите год 4 цифрами (1950–2010)."},
    "bad_phone": {"uz": "⚠️ Telefon raqami noto'g'ri. Masalan: <i>+998 90 123 45 67</i>", "ru": "⚠️ Неверный номер. Например: <i>+998 90 123 45 67</i>"},
    "bad_number": {"uz": "⚠️ Faqat raqam yozing, masalan: <i>5000000</i>", "ru": "⚠️ Введите только число, например: <i>5000000</i>"},
    "pick_one": {"uz": "Kamida bittasini tanlang.", "ru": "Выберите хотя бы один вариант."},

    "my_resume": {"uz": "📄 <b>Mening rezyumem</b>\n\nHolati: {status}\n👁 Ko'rishlar: <b>{views}</b>", "ru": "📄 <b>Моё резюме</b>\n\nСтатус: {status}\n👁 Просмотры: <b>{views}</b>"},
    "no_resume": {"uz": "📄 Sizda hali rezyume yo'q.\n\nRezyume yarating — ish beruvchilar sizni topadi, bot esa uni <b>PDF va Word</b> formatida chiroyli qilib tayyorlab beradi.", "ru": "📄 У вас ещё нет резюме.\n\nСоздайте его — работодатели найдут вас, а бот подготовит красивое резюме в <b>PDF и Word</b>."},
    "b_edit": {"uz": "✏️ Qayta to'ldirish", "ru": "✏️ Заполнить заново"},
    "b_hide": {"uz": "🙈 Yashirish", "ru": "🙈 Скрыть"},
    "b_show": {"uz": "👁 Faollashtirish", "ru": "👁 Активировать"},
    "b_delete": {"uz": "🗑 O'chirish", "ru": "🗑 Удалить"},
    "b_view": {"uz": "👀 Ko'rish", "ru": "👀 Просмотр"},
    "confirm_delete": {"uz": "Rostdan ham o'chirilsinmi? Bu amalni qaytarib bo'lmaydi.", "ru": "Точно удалить? Это действие нельзя отменить."},
    "deleted": {"uz": "🗑 O'chirildi.", "ru": "🗑 Удалено."},

    "st_pending": {"uz": "⏳ Moderatsiyada", "ru": "⏳ На модерации"},
    "st_active": {"uz": "✅ Faol", "ru": "✅ Активно"},
    "st_rejected": {"uz": "❌ Rad etilgan", "ru": "❌ Отклонено"},
    "st_hidden": {"uz": "🙈 Yashirilgan", "ru": "🙈 Скрыто"},
    "st_closed": {"uz": "🔒 Yopilgan", "ru": "🔒 Закрыто"},

    # ---------- vakansiya ustasi ----------
    "v_intro": {
        "uz": "➕ <b>Vakansiya joylash</b>\n\n10 ta savolga javob bering. E'lon <b>botda, saytda va kanalimizda</b> chiqadi, mos nomzodlarga esa bildirishnoma boradi.",
        "ru": "➕ <b>Размещение вакансии</b>\n\nОтветьте на 10 вопросов. Вакансия появится <b>в боте, на сайте и в канале</b>, а подходящим кандидатам придёт уведомление.",
    },
    "v_title": {"uz": "1/10. 💼 Lavozim nomi (masalan: <i>Bosh buxgalter</i>):", "ru": "1/10. 💼 Название должности (например: <i>Главный бухгалтер</i>):"},
    "v_company": {"uz": "2/10. 🏢 Kompaniya / tashkilot nomi:", "ru": "2/10. 🏢 Название компании:"},
    "vq_cat": {"uz": "3/10. 🗂 Soha:", "ru": "3/10. 🗂 Сфера:"},
    "vq_city": {"uz": "4/10. 📍 Shahar:", "ru": "4/10. 📍 Город:"},
    "vq_type": {"uz": "5/10. 🕒 Ish formati:", "ru": "5/10. 🕒 Формат работы:"},
    "v_salary_q": {"uz": "6/10. 💰 Maosh, so'mda. Masalan: <i>5000000</i> yoki <i>5000000-8000000</i>", "ru": "6/10. 💰 Зарплата в сумах. Например: <i>5000000</i> или <i>5000000-8000000</i>"},
    "v_exp_q": {"uz": "7/10. 🎓 Talab qilinadigan tajriba:", "ru": "7/10. 🎓 Требуемый опыт:"},
    "v_desc": {"uz": "8/10. 📝 Ish haqida batafsil: vazifalar, ish vaqti, manzil:", "ru": "8/10. 📝 Подробно о работе: обязанности, график, адрес:"},
    "v_req_q": {"uz": "9/10. 📌 Talablar (har birini yangi qatordan):", "ru": "9/10. 📌 Требования (каждое с новой строки):"},
    "v_cond_q": {"uz": "10/10. 🎁 Sharoitlar va qulayliklar (har birini yangi qatordan):", "ru": "10/10. 🎁 Условия и преимущества (каждое с новой строки):"},
    "v_phone": {"uz": "📞 Aloqa uchun telefon raqami:", "ru": "📞 Телефон для связи:"},
    "v_tg": {"uz": "✈️ Telegram aloqa (masalan: <i>@hr_manager</i>):", "ru": "✈️ Telegram для связи (например: <i>@hr_manager</i>):"},
    "use_my_tg": {"uz": "✈️ @{u} dan foydalanish", "ru": "✈️ Использовать @{u}"},
    "b_negotiable": {"uz": "🤝 Kelishiladi", "ru": "🤝 Договорная"},
    "v_preview": {"uz": "👆 Vakansiyangiz shunday ko'rinadi. E'lon qilamizmi?", "ru": "👆 Так выглядит ваша вакансия. Публикуем?"},
    "v_publish": {"uz": "📢 E'lon qilish", "ru": "📢 Опубликовать"},
    "v_saved_pending": {"uz": "✅ Vakansiya moderatsiyaga yuborildi. Tasdiqlangach botda, saytda va kanalda chiqadi.", "ru": "✅ Вакансия отправлена на модерацию. После проверки появится в боте, на сайте и в канале."},
    "v_saved_active": {"uz": "✅ Vakansiya e'lon qilindi!", "ru": "✅ Вакансия опубликована!"},

    "my_vacs": {"uz": "📋 <b>Mening vakansiyalarim</b> ({n})\n\nBatafsil ko'rish uchun tanlang 👇", "ru": "📋 <b>Мои вакансии</b> ({n})\n\nВыберите для просмотра 👇"},
    "no_vacs": {"uz": "📋 Sizda hali vakansiya yo'q.", "ru": "📋 У вас ещё нет вакансий."},
    "b_apps": {"uz": "👥 Arizalar ({n})", "ru": "👥 Отклики ({n})"},
    "b_close": {"uz": "🔒 Yopish", "ru": "🔒 Закрыть"},
    "b_reopen": {"uz": "🔓 Qayta ochish", "ru": "🔓 Открыть снова"},
    "no_apps": {"uz": "Hali ariza kelmagan.", "ru": "Откликов пока нет."},
    "apps_list": {"uz": "👥 <b>«{title}»</b> — arizalar ({n}):", "ru": "👥 <b>«{title}»</b> — отклики ({n}):"},
    "b_accept": {"uz": "🎉 Suhbatga taklif", "ru": "🎉 Пригласить на собеседование"},
    "b_reject": {"uz": "❌ Rad etish", "ru": "❌ Отказать"},
    "app_done": {"uz": "Javob nomzodga yuborildi ✅", "ru": "Ответ отправлен кандидату ✅"},

    # ---------- arizalarim ----------
    "my_apps": {"uz": "📨 <b>Arizalarim</b>\n\n{lines}", "ru": "📨 <b>Мои отклики</b>\n\n{lines}"},
    "no_my_apps": {"uz": "📨 Siz hali ariza yubormagansiz. «🔎 Ish qidirish» bo'limidan boshlang!", "ru": "📨 Вы ещё не откликались. Начните с «🔎 Поиск работы»!"},
    "app_new": {"uz": "⏳ Yuborildi", "ru": "⏳ Отправлен"},
    "app_viewed": {"uz": "👀 Ko'rildi", "ru": "👀 Просмотрен"},
    "app_invited": {"uz": "🎉 Suhbatga taklif", "ru": "🎉 Приглашение"},
    "app_rejected": {"uz": "❌ Rad etildi", "ru": "❌ Отказ"},

    # ---------- saqlanganlar ----------
    "saved_none": {"uz": "⭐ Hali hech narsa saqlanmagan. Kartochkadagi «☆ Saqlash» tugmasini bosing.", "ru": "⭐ В избранном пока пусто. Нажмите «☆ В избранное» на карточке."},
    "fav_added": {"uz": "⭐ Saqlandi", "ru": "⭐ Добавлено в избранное"},
    "fav_removed": {"uz": "Saqlanganlardan olib tashlandi", "ru": "Удалено из избранного"},

    # ---------- takliflar ----------
    "invite_pick": {"uz": "✉️ Qaysi vakansiya bo'yicha taklif yuboramiz?", "ru": "✉️ По какой вакансии отправить приглашение?"},
    "invite_general": {"uz": "💬 Umumiy taklif (vakansiyasiz)", "ru": "💬 Общее приглашение"},
    "invite_sent": {"uz": "✅ Taklif nomzodga yuborildi!", "ru": "✅ Приглашение отправлено кандидату!"},
    "invite_dup": {"uz": "Bu nomzodga allaqachon taklif yuborgansiz.", "ru": "Вы уже приглашали этого кандидата."},

    # ---------- bildirishnomalar ----------
    "n_new_app": {"uz": "📨 <b>Yangi ariza!</b>\n\nVakansiya: <b>{title}</b>\nNomzod: <b>{name}</b> — {headline}", "ru": "📨 <b>Новый отклик!</b>\n\nВакансия: <b>{title}</b>\nКандидат: <b>{name}</b> — {headline}"},
    "n_invited": {"uz": "🎉 <b>Tabriklaymiz!</b>\n\n«{title}» vakansiyasi bo'yicha ish beruvchi sizni <b>suhbatga taklif qilmoqda</b>.\n\n{contact}", "ru": "🎉 <b>Поздравляем!</b>\n\nПо вакансии «{title}» работодатель <b>приглашает вас на собеседование</b>.\n\n{contact}"},
    "n_rejected": {"uz": "«{title}» vakansiyasi bo'yicha arizangiz rad etildi. Tushkunlikka tushmang — sizga mos ish albatta topiladi! 💪", "ru": "По вакансии «{title}» вам отказали. Не расстраивайтесь — подходящая работа обязательно найдётся! 💪"},
    "n_invite": {"uz": "✉️ <b>Sizga ish taklifi!</b>\n\n<b>{employer}</b> rezyumengiz bilan qiziqdi.\n{vac}\n{contact}", "ru": "✉️ <b>Вам предложение о работе!</b>\n\n<b>{employer}</b> заинтересовался вашим резюме.\n{vac}\n{contact}"},
    "n_vac_ok": {"uz": "✅ «{title}» vakansiyangiz tasdiqlandi va e'lon qilindi!", "ru": "✅ Ваша вакансия «{title}» одобрена и опубликована!"},
    "n_vac_no": {"uz": "❌ «{title}» vakansiyangiz rad etildi. Ma'lumotlarni tekshirib, qayta joylashtiring.", "ru": "❌ Ваша вакансия «{title}» отклонена. Проверьте данные и разместите снова."},
    "n_res_ok": {"uz": "✅ Rezyumengiz tasdiqlandi! Endi ish beruvchilar sizni ko'ra oladi.", "ru": "✅ Ваше резюме одобрено! Теперь работодатели видят вас."},
    "n_res_no": {"uz": "❌ Rezyumengiz rad etildi. Ma'lumotlarni to'g'rilab, qayta to'ldiring.", "ru": "❌ Ваше резюме отклонено. Исправьте данные и заполните снова."},
    "n_match": {"uz": "🔔 <b>Sizga mos yangi vakansiya!</b>", "ru": "🔔 <b>Новая подходящая вакансия!</b>"},
    "n_expired": {"uz": "⏰ «{title}» vakansiyangiz muddati tugadi va yopildi. «📋 Vakansiyalarim» bo'limidan qayta ochishingiz mumkin.", "ru": "⏰ Срок вакансии «{title}» истёк. Открыть снова можно в «📋 Мои вакансии»."},

    # ---------- sozlamalar ----------
    "settings": {"uz": "⚙️ <b>Sozlamalar</b>\n\n🌐 Til: <b>O'zbekcha</b>\n👤 Rol: <b>{role}</b>\n🔔 Bildirishnomalar: <b>{notif}</b>", "ru": "⚙️ <b>Настройки</b>\n\n🌐 Язык: <b>Русский</b>\n👤 Роль: <b>{role}</b>\n🔔 Уведомления: <b>{notif}</b>"},
    "s_lang": {"uz": "🌐 Tilni o'zgartirish", "ru": "🌐 Сменить язык"},
    "s_role": {"uz": "🔄 Rolni almashtirish", "ru": "🔄 Сменить роль"},
    "s_notif": {"uz": "🔔 Bildirishnomalar", "ru": "🔔 Уведомления"},
    "on": {"uz": "yoqilgan ✅", "ru": "включены ✅"},
    "off": {"uz": "o'chirilgan ❌", "ru": "выключены ❌"},
    "role_changed": {"uz": "✅ Rol o'zgartirildi.", "ru": "✅ Роль изменена."},
    "lang_changed": {"uz": "✅ Til o'zgartirildi.", "ru": "✅ Язык изменён."},

    # ---------- yordam ----------
    "help": {
        "uz": "✉️ <b>Yordam</b>\n\nSavol, taklif yoki shikoyatingizni bitta xabarda yozing — adminlar tez orada javob berishadi.",
        "ru": "✉️ <b>Помощь</b>\n\nНапишите вопрос, предложение или жалобу одним сообщением — администраторы скоро ответят.",
    },
    "sup_sent": {"uz": "✅ Xabaringiz adminlarga yuborildi. Javobni shu yerda olasiz.", "ru": "✅ Сообщение отправлено администраторам. Ответ придёт сюда."},
    "sup_answer": {"uz": "💬 <b>Admin javobi:</b>\n\n{text}", "ru": "💬 <b>Ответ администратора:</b>\n\n{text}"},

    # ---------- sayt ----------
    "web_text": {"uz": "🌐 <b>AyolQadami</b> web ilovasi — vakansiyalar xaritasi, QadamAI, kurslar va to'liq rezyume ustasi.", "ru": "🌐 Веб-приложение <b>AyolQadami</b> — карта вакансий, QadamAI, курсы и полный конструктор резюме."},
    "web_open": {"uz": "🌐 Saytni ochish", "ru": "🌐 Открыть сайт"},
    "web_none": {"uz": "🌐 Sayt manzili hali sozlanmagan.", "ru": "🌐 Адрес сайта ещё не настроен."},
}


def t(key: str, lang: str | None = "uz", **kw) -> str:
    item = T.get(key)
    if item is None:
        return key
    text = item.get(lang or "uz") or item["uz"]
    return text.format(**kw) if kw else text


def variants(key: str) -> set[str]:
    """Reply tugma matnining barcha tillardagi ko'rinishi — F.text.in_(...) filtri uchun."""
    return set(T[key].values())
