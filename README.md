# Telegram Kino Bot (Majburiy Obuna Tizimi bilan)

Ushbu bot foydalanuvchilarga kino kodlari orqali kinolarni taqdim etadi. Botdan foydalanish uchun foydalanuvchilar admin tomonidan belgilangan kanallarga obuna bo'lishlari shart.

## Imkoniyatlar:
- **Majburiy obuna:** Foydalanuvchi kanallarga obuna bo'lmaguncha kino ololmaydi.
- **Kino kodlari:** Har bir kinoga alohida kod biriktiriladi.
- **Admin Panel:** Kanallarni va kinolarni boshqarish (qo'shish/o'chirish).
- **Sodda va toza kod:** `aiogram` kutubxonasida yozilgan.

## O'rnatish:

1. Kutubxonalarni o'rnating:
   ```bash
   pip install -r requirements.txt
   ```

2. `src/config.py` faylini tahrirlang:
   - `BOT_TOKEN`: BotFather dan olingan token.
   - `ADMIN_IDS`: Adminlarning Telegram ID raqamlari.

3. Botni ishga tushiring:
   ```bash
   python -m src.main
   ```

## Admin Panelga kirish:
Telegramda botga `/admin` buyrug'ini yuboring.

## Muhim eslatma:
Bot kanallarda admin huquqiga ega bo'lishi kerak (obunani tekshira olishi uchun).
