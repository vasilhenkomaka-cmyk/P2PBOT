"""
P2P Щоденник — Telegram Mini App + Bot
Запуск на Railway
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from database import init_db, add_deal, get_deals, get_deals_today, get_stats, delete_deal

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")  # наприклад https://your-app.up.railway.app
# ===========================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()
bot: Bot = None
dp: Dispatcher = None


# ---------- Pydantic models ----------
class DealCreate(BaseModel):
    deal_type: str = Field(..., pattern="^(buy|sell)$")
    rate: float = Field(..., gt=0, lt=1000)
    amount_usdt: float = Field(..., gt=0, lt=1_000_000)
    fee_percent: float = Field(0, ge=0, le=10)
    note: str = Field("", max_length=200)
    user_id: int


class DealDelete(BaseModel):
    deal_id: int
    user_id: int


# ---------- Lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot, dp
    await init_db()

    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не встановлено!")
    else:
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_router(router)

        # Запускаємо polling у фоні
        asyncio.create_task(dp.start_polling(bot))
        logger.info("Бот запущено (polling)")

    yield

    if bot:
        await bot.session.close()


app = FastAPI(title="P2P Journal Mini App", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статика
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------- API ----------
@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse("static/index.html")


@app.get("/api/stats")
async def api_stats(user_id: int, today: bool = False):
    stats = await get_stats(user_id, only_today=today)
    return stats


@app.get("/api/deals")
async def api_deals(user_id: int, limit: int = 30):
    deals = await get_deals(user_id, limit=limit)
    return {"deals": deals}


@app.get("/api/deals/today")
async def api_deals_today(user_id: int):
    deals = await get_deals_today(user_id)
    return {"deals": deals}


@app.post("/api/deals")
async def api_create_deal(data: DealCreate):
    deal_id = await add_deal(
        user_id=data.user_id,
        deal_type=data.deal_type,
        rate=data.rate,
        amount=data.amount_usdt,
        fee=data.fee_percent,
        note=data.note
    )
    return {"ok": True, "id": deal_id}


@app.post("/api/deals/delete")
async def api_delete_deal(data: DealDelete):
    ok = await delete_deal(data.user_id, data.deal_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Deal not found")
    return {"ok": True}


# ---------- Bot handlers ----------
@router.message(CommandStart())
async def cmd_start(message: Message):
    webapp_url = WEBAPP_URL or "https://example.com"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📱 Відкрити додаток",
            web_app=WebAppInfo(url=webapp_url)
        )],
        [InlineKeyboardButton(text="📊 Швидка статистика", callback_data="quick_stats")],
    ])

    text = (
        "👋 <b>P2P Щоденник</b>\n\n"
        "Натисни кнопку нижче, щоб відкрити додаток прямо в Telegram.\n"
        "Там можна додавати угоди, дивитися прибуток і баланс."
    )
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "quick_stats")
async def quick_stats(callback):
    stats = await get_stats(callback.from_user.id, only_today=True)
    text = (
        f"📅 <b>Сьогодні</b>\n\n"
        f"Угод: <b>{stats['total_deals']}</b>\n"
        f"Прибуток: <b>{stats['profit']:,.2f} ₴</b>\n"
        f"Баланс: <b>{stats['balance_usdt']:,.2f} USDT</b>"
    )
    await callback.message.answer(text)
    await callback.answer()


# Для локального запуску
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
