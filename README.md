# Telegram Premium Movie Bot (Lite Structure)

Bu loyiha siz yuborgan katta texnik topshiriq asosida qayta yig‘ildi, lekin **papka soni kamaytirildi**. Asosiy imkoniyatlar saqlandi:

- aiogram 3.x
- SQLite + SQLAlchemy async
- Alembic
- webhook + polling
- admin panel
- premium tariflar
- manual screenshot to‘lov
- **ixtiyoriy summa bilan to‘lov (1000 so‘mdan 1 000 000 so‘mgacha)**
- Click / Payme webhook skeleton
- referral
- required channels
- movie code search
- broadcast
- audit log
- **admin paneldan kesh tozalash**
- Uzbek default UI

## Papka tuzilmasi

```text
app/
  core/        # config, db, models, repositories, services, ui, middlewares
  modules/     # handlers/routerlar
  providers/   # click/payme/ai providerlari
  locales/     # uz/ru/en matnlar
alembic/
```

## Lokal ishga tushirish

```bash
python -m venv .venv
. .venv/Scripts/activate   # Windows
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python -m app.main
```

## GitHub ga qo‘yish

```bash
git init
git add .
git commit -m "initial bot"
git branch -M main
git remote add origin https://github.com/USERNAME/REPO.git
git push -u origin main
```

## Railway / Render

### Railway
- New Project
- Deploy from GitHub Repo
- Variables ga `.env` dagi qiymatlarni kiriting
- Start command kerak emas, `python -m app.main` ishlaydi

### Render
- New Web Service
- Build Command: `pip install -r requirements.txt`
- Start Command: `python -m app.main`
- Agar webhook ishlatsangiz `USE_WEBHOOK=true` qiling

## Muhim

- `BOT_TOKEN` va `SUPERADMINS` ni to‘ldiring
- webhook ishlatsangiz `BASE_URL` real domen bo‘lishi kerak
- Click/Payme real merchant field mapping yakuniy production callback formatiga qarab moslanadi

## Admin buyruqlar

- `/start`
- `/admin`
- `/movie CODE`

## Premium sotib olish

Foydalanuvchi ikki xil yo‘l bilan to‘lay oladi:
1. Tayyor tariflar: `1 oy`, `3 oy`, `1 yil`
2. `✍️ Boshqa summa kiritish` tugmasi orqali ixtiyoriy summa

Default oraliq:
- minimum: `1000`
- maksimum: `1000000`

Bu qiymatlar DB setting sifatida ham seed qilinadi:
- `custom_payment_min`
- `custom_payment_max`

## Kino qo‘shish formati

Admin panel ichida:
```text
Nomi | KOD123 | Kategoriya | https://t.me/post_link | Tavsif
```

## Kesh tozalash

Admin panel ichida:
- `🧹 Kesh tozalash`

Bu tugma:
- `data/tmp`
- `data/cache`
- `tmp`
- `cache`

ichidagi vaqtinchalik fayllarni tozalaydi.

## Qisqa eslatma

Bu versiya papka sonini kamaytirish uchun qayta tuzilgan. Ichki modullar birlashtirilgan, lekin kerakli funksiyalar saqlangan.
