# AyolQadam Bot

**AyolQadami** platformasining Telegram boti (aiogram 3). Bot mustaqil ishlaydi. Xohlasangiz, uni web ilova (`ayolkaryera-web`) bilan bog'lash mumkin.

## Imkoniyatlar

### 👩 Ish izlovchi
- **🔎 Ish qidirish**: barchasi, «✨ Menga mos» (rezyumedagi soha va shahar bo'yicha), soha, shahar yoki so'z bo'yicha.
- Vakansiyalar bittadan ko'rsatiladi. Tagida **📞 Bog'lanish**, **✅ Ariza yuborish**, **📄 PDF**, **📝 DOC**, **☆ Saqlash** va **⬅️ 3/25 ➡️** tugmalari bor.
- **📄 Rezyume ustasi** 13 qadamdan iborat va rasm qo'shish mumkin. Oxirida bot **professional PDF va Word** rezyume tayyorlab beradi.
- Qayta to'ldirishda «⏭ O'tkazib yuborish» bosilsa, eski qiymat saqlanib qoladi.
- **📨 Arizalarim**: har bir arizaning holati (yuborildi, ko'rildi, suhbatga taklif, rad etildi).
- Bildirishnomalar: yangi mos vakansiya, suhbatga taklif, rad javobi, moderatsiya natijasi.

### 🏢 Ish beruvchi
- **👩‍💼 Nomzodlar**: nomzodning asosiy ma'lumotlari ko'rsatiladi. Tagida **📄 Resume PDF**, **📝 Resume DOC**, **📞 Bog'lanish**, **✉️ Taklif yuborish** va **⬅️ ➡️** tugmalari bor.
- **➕ Vakansiya joylash** (10 qadam). Vakansiya botda, kanalda va saytda chiqadi, mos nomzodlarga esa bildirishnoma boradi.
- **📋 Vakansiyalarim** bo'limida:
  - kelgan arizalarni ko'rish va ularga «🎉 Suhbatga taklif» yoki «❌ Rad etish» bilan javob berish;
  - vakansiyani yopish, qayta ochish yoki o'chirish.

### 🛠 Admin panel (`/admin` yoki «🛠 Admin panel» tugmasi)
| Bo'lim | Nima qiladi |
|---|---|
| 📢 **E'lon joylash** | Istalgan xabarni yuborasiz yoki boshqa kanaldan **forward** qilasiz (matn, rasm, video, fayl). E'lon kanalga bot nomidan, **«Ishlamoqchiman»** va **«E'lon berish»** tugmalari bilan chiqadi. U bot va saytdagi ro'yxatga ham qo'shiladi. Har bir post uchun tugma havolasini alohida berish mumkin. |
| ✉️ **Xabar yuborish** | Xabar hammaga, faqat ish izlovchilarga yoki faqat ish beruvchilarga yuboriladi. Ikki rejim bor: oddiy (nusxa, tugma qo'shish mumkin) va **forward**. Tarqatish fonda ketadi va oxirida hisobot keladi. |
| 📊 **Statistika** | Foydalanuvchilar (bugun, 7 va 30 kun), faollik, rollar, tillar, botni bloklaganlar. Vakansiya, rezyume, ariza va takliflar soni. Top sohalar va shaharlar. **CSV eksport**. |
| 🕓 **Moderatsiya** | Foydalanuvchi joylagan vakansiya va rezyumelarni tasdiqlash yoki rad etish. Yangisi kelganda adminlarga darhol xabar boradi. |
| 📡 **E'lon kanallari** | E'lonlar joylanadigan kanallar. Kanal postni forward qilish yoki @username yuborish orqali qo'shiladi. |
| 🔒 **Majburiy obuna** | Yoqilganda foydalanuvchi til tanlagach kanal(lar)ga obuna bo'lmaguncha botdan foydalana olmaydi. Bitta tugma bilan yoqiladi yoki o'chiriladi. |
| 🔘 **Kanal tugmalari** | «Ishlamoqchiman» va «E'lon berish» tugmalarining matni va havolasi. Havola qiymatlari: `bot`, `https://...`, `@username`, `+998...` (bosilganda raqam ko'rsatiladi) yoki `-` (tugmasiz). |
| 🌐 **Web sinxron** | Web bilan ma'lumot almashishni yoqadi yoki o'chiradi. Ulanishni tekshirish va hamma ma'lumotni qayta yuborish ham shu yerda. |
| ⚙️ **Sozlamalar** | Moderatsiya, vakansiyalarni kanalga avtomatik joylash, rezyumelarni kanalga joylash, mos nomzodlarga bildirishnoma. |
| 👤 **Foydalanuvchilar** | ID yoki @username orqali qidirish, ban qilish yoki bandan chiqarish, shaxsiy xabar yozish. |
| 👮 **Adminlar** | Qo'shimcha adminlarni qo'shish va o'chirish (buni faqat `.env` dagi bosh admin qila oladi). |
| ✉️ **Yordam** | Foydalanuvchi «✉️ Yordam» orqali yozgan xabar adminlarga «💬 Javob berish» tugmasi bilan keladi. |

Admin vakansiya yoki rezyume kartochkasida **🛠 Yopish**, **🗑 O'chirish** va **🙈 Yashirish** tugmalarini ham ko'radi.

Boshqa imkoniyatlar:
- 🇺🇿 O'zbek va 🇷🇺 rus tillari.
- Vakansiya 30 kundan keyin avtomatik yopiladi va egasiga xabar boradi.
- Botni bloklagan foydalanuvchilar avtomatik belgilanadi va tarqatishda o'tkazib yuboriladi.

## O'rnatish (lokal)

```bash
cd ayolqadam-bot
python -m venv .venv
.venv\Scripts\activate            # Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # Linux: cp .env.example .env  -> BOT_TOKEN va ADMIN_IDS ni kiriting
python run.py
```
Windows'da `start.bat` ni ikki marta bossangiz ham ishga tushadi.

### Kanallarni sozlash
1. Botni kanalga **admin** qiling. «Post joylash» va «Foydalanuvchi qo'shish» huquqlari kerak.
2. Botda `/admin` → **📡 E'lon kanallari** → «➕ Kanal qo'shish». Kanaldan bitta postni forward qiling.
3. Majburiy obuna uchun: **🔒 Majburiy obuna** → kanal qo'shing → «🟢 Yoqish».

## Serverga joylash

**systemd** (Ubuntu):
```bash
sudo mkdir -p /opt/ayolqadam-bot && sudo cp -r . /opt/ayolqadam-bot && cd /opt/ayolqadam-bot
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env
sudo chown -R www-data:www-data /opt/ayolqadam-bot
sudo cp deploy/ayolqadam-bot.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now ayolqadam-bot
journalctl -u ayolqadam-bot -f
```

**Docker:**
```bash
cp .env.example .env    # to'ldiring
docker compose up -d --build
```

Ma'lumotlar `data/` papkasida turadi: `bot.db` (SQLite) va `bot.log`. Zaxira nusxa olish uchun shu papkani saqlang.
Bot boshqa servis talab qilmaydi (PostgreSQL, Redis kerak emas). Web ilova o'chiq bo'lsa ham bot to'liq ishlaydi.

## Web ilova bilan bog'lash

Bog'lanish ikki tomonlama va admin paneldagi **🌐 Web sinxron** kaliti bilan boshqariladi.

1. **Sayt botdan o'qiydi.** `.env` da `API_ENABLED=1` qiling. Bot `http://server:8080/api` da REST API ochadi. Web ilovaning `.env.local` faylida `VITE_BOT_API_URL=https://api.sizning-domen.uz` qiling. Shundan keyin:
   - bot vakansiyalari saytda ko'rinadi;
   - saytda joylangan vakansiya botga keladi, moderatsiyadan o'tadi va kanalga chiqadi.
2. **Bot backend'ga yozadi.** Keyinchalik web backend qilinsa, `WEB_API_URL` va `WEB_API_KEY` ni kiriting. Bot yangi vakansiya va rezyumelarni `POST {WEB_API_URL}/vacancies` va `/resumes` ga yuboradi.

Kalit o'chirilganda API `503` qaytaradi va bot hech narsa yubormaydi. Tarmoq xatolari botning ishlashiga ta'sir qilmaydi.

Production'da API'ni nginx orqali HTTPS bilan oching va `API_CORS` ga sayt domenini yozing.

### REST API
| Metod | Yo'l | Kalit | Tavsif |
|---|---|---|---|
| GET | `/api/health` | — | Holat (doim ochiq) |
| GET | `/api/vacancies?category=&city=&q=&limit=&offset=` | — | Faol vakansiyalar (sayt formatida) |
| GET | `/api/vacancies/{id}` | — | Bitta vakansiya (`tg12` yoki `12`) |
| POST | `/api/vacancies` | ixtiyoriy | Saytdan vakansiya. Kalitsiz yuborilsa doim moderatsiyaga tushadi; IP bo'yicha soatiga 20 ta so'rov chegarasi bor. |
| DELETE | `/api/vacancies/{ext_id}` | ✅ | Vakansiyani yopish |
| GET | `/api/resumes` | ✅ | Faol rezyumelar (shaxsiy ma'lumot) |
| POST | `/api/resumes` | ixtiyoriy | Saytdan rezyume (`candidates.js` formati) |
| GET | `/api/stats` | ✅ | Statistika |

Kalit `X-Api-Key: <WEB_API_KEY>` sarlavhasida yuboriladi. Ma'lumot shakli web'dagi `src/data/mock.js` (vakansiya) va `src/data/candidates.js` (nomzod) bilan bir xil.

## Tuzilma
```
app/
  config.py        .env sozlamalari
  db.py            SQLite qatlami (users, resumes, vacancies, applications, invites, favorites, channels, settings, admins)
  texts.py         uz/ru matnlar
  constants.py     sohalar, shaharlar, formatlar (web bilan bir xil id'lar)
  middlewares.py   foydalanuvchi, ban, majburiy obuna
  handlers/
    start.py       /start, til, obuna, rol, deep-link'lar, kanal telefon tugmasi
    menu.py        asosiy menyu tugmalari
    browse.py      e'lon/nomzodlarni ko'rish (⬅️ ➡️), ariza, taklif, fayllar
    resume.py      rezyume ustasi
    vacancy.py     vakansiya ustasi
    cabinet.py     rezyumem, vakansiyalarim, arizalarim, sozlamalar, yordam
    admin.py       admin panel
  services/
    docs.py        PDF (reportlab) va Word (python-docx) dizayni
    flow.py        moderatsiya → kanal → web → bildirishnomalar
    websync.py     web formatiga o'girish va push
    notify.py      xavfsiz yuborish (blok, limit)
  api/server.py    REST API (aiohttp)
assets/fonts       DejaVu shriftlari (PDF'da o'zbek/rus harflari uchun)
```
