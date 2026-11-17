# P2P Щоденник — Telegram Mini App

Повноцінний Mini App + бот для обліку P2P-угод.

## Що вміє

- Красивий інтерфейс прямо всередині Telegram
- Додавання угод (купівля / продаж)
- Статистика за сьогодні і загальна
- Баланс USDT, середні курси, спред
- Історія угод

## Деплой на Railway (покроково)

### 1. Підготуй код

1. Створи репозиторій на GitHub
2. Завантаж усі файли з цієї папки в репозиторій

Або просто завантаж папку як ZIP і розпакуй.

### 2. Railway

1. Зайди на [railway.app](https://railway.app) і зареєструйся (через GitHub)
2. Натисни **New Project** → **Deploy from GitHub repo** (або Empty Project + Upload)
3. Вибери свій репозиторій

### 3. Змінні оточення

У Railway → твій сервіс → **Variables** додай:

```
BOT_TOKEN = твій_токен_від_BotFather
WEBAPP_URL = https://твій-домен.up.railway.app
```

`WEBAPP_URL` — це посилання, яке Railway дасть після деплою (можна спочатку поставити заглушку, потім оновити).

### 4. Start Command

У Settings → Deploy переконайся, що Start Command:

```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### 5. Після деплою

1. Скопіюй публічний URL (типу `https://p2p-journal-production.up.railway.app`)
2. Встав його в змінну `WEBAPP_URL`
3. Перезапусти сервіс

### 6. Готово

Напиши боту `/start` → з’явиться кнопка **«Відкрити додаток»**.

---

## Локальний запуск (для тесту)

```bash
pip install -r requirements.txt
export BOT_TOKEN=твій_токен
export WEBAPP_URL=http://localhost:8000
python main.py
```

Для Mini App локально потрібен HTTPS-тунель (наприклад ngrok).

## Структура

```
├── main.py          # FastAPI + aiogram бот
├── database.py      # SQLite
├── requirements.txt
├── static/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── README.md
```
