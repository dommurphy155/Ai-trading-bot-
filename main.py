# main.py
import os
import asyncio
from dotenv import load_dotenv
from mt5_handler import MT5Handler
from ai_analyzer import AIAnalyzer
from earnings_tracker import EarningsTracker
from screenshot import Screenshot
from trader import Trader
from telegram_bot import TelegramBot

async def market_scanner(trader):
    while True:
        try:
            await trader.evaluate_and_execute()
        except Exception as e:
            print(f"[Scanner Error] {e}")
        await asyncio.sleep(1)

async def main():
    load_dotenv()
    # Initialize modules
    mt5 = MT5Handler()
    ai = AIAnalyzer()
    earnings = EarningsTracker()
    ss = Screenshot()
    # Telegram bot setup (earnings first so it's available)
    bot = TelegramBot(None, earnings)
    trader = Trader(mt5, ai, earnings, ss, bot)
    bot.trader = trader

    # Start market scanning task
    asyncio.create_task(market_scanner(trader))
    # Start Telegram command polling
    await bot.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
