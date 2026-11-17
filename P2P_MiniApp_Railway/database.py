import aiosqlite
from datetime import datetime, date
from typing import Optional
import os

DB_PATH = os.getenv("DB_PATH", "p2p_journal.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                deal_type TEXT NOT NULL,
                rate REAL NOT NULL,
                amount_usdt REAL NOT NULL,
                fee_percent REAL DEFAULT 0,
                note TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_date ON deals(user_id, created_at)
        """)
        await db.commit()


async def add_deal(user_id: int, deal_type: str, rate: float, amount: float,
                   fee: float = 0.0, note: str = "") -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO deals (user_id, deal_type, rate, amount_usdt, fee_percent, note, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, deal_type, rate, amount, fee, note, datetime.now().isoformat())
        )
        await db.commit()
        return cursor.lastrowid


async def get_deals(user_id: int, limit: int = 30) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM deals WHERE user_id = ? ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_deals_today(user_id: int) -> list:
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM deals 
               WHERE user_id = ? AND date(created_at) = ?
               ORDER BY created_at DESC""",
            (user_id, today)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_stats(user_id: int, only_today: bool = False) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if only_today:
            where = "user_id = ? AND date(created_at) = date('now')"
            params = (user_id,)
        else:
            where = "user_id = ?"
            params = (user_id,)

        cur = await db.execute(
            f"""SELECT 
                    COUNT(*) as cnt,
                    COALESCE(SUM(amount_usdt), 0) as total_usdt,
                    COALESCE(SUM(amount_usdt * rate * (1 + fee_percent/100.0)), 0) as total_uah
                FROM deals WHERE {where} AND deal_type = 'buy'""",
            params
        )
        buys = dict(await cur.fetchone())

        cur = await db.execute(
            f"""SELECT 
                    COUNT(*) as cnt,
                    COALESCE(SUM(amount_usdt), 0) as total_usdt,
                    COALESCE(SUM(amount_usdt * rate * (1 - fee_percent/100.0)), 0) as total_uah
                FROM deals WHERE {where} AND deal_type = 'sell'""",
            params
        )
        sells = dict(await cur.fetchone())

        buy_usdt = buys["total_usdt"] or 0
        sell_usdt = sells["total_usdt"] or 0
        spent = buys["total_uah"] or 0
        received = sells["total_uah"] or 0

        return {
            "total_deals": (buys["cnt"] or 0) + (sells["cnt"] or 0),
            "buys_count": buys["cnt"] or 0,
            "sells_count": sells["cnt"] or 0,
            "buy_usdt": buy_usdt,
            "sell_usdt": sell_usdt,
            "balance_usdt": buy_usdt - sell_usdt,
            "spent_uah": spent,
            "received_uah": received,
            "profit": received - spent,
            "avg_buy": (spent / buy_usdt) if buy_usdt > 0 else 0,
            "avg_sell": (received / sell_usdt) if sell_usdt > 0 else 0,
        }


async def delete_deal(user_id: int, deal_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM deals WHERE id = ? AND user_id = ?",
            (deal_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0
