import os
import time
import hmac
import json
import hashlib
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot

# Your bot modules (adjust imports if you changed file names)
from ai_analyzer import AIAnalyzer
from earnings_tracker import EarningsTracker
from screenshot import Screenshot
from trader import Trader  # This Trader should be rewritten for FXOpen already
from telegram_bot import TelegramBot

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Load env variables
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FXOPEN_LOGIN = os.getenv("FXOPEN_LOGIN")
FXOPEN_KEY = os.getenv("FXOPEN_KEY")
FXOPEN_SECRET = os.getenv("FXOPEN_SECRET")

BASE_URL = "https://restapi.fxopen.com:8443"

# Telegram Bot instance for direct sends outside TelegramBot class
bot = Bot(token=TG_TOKEN)

def hmac_auth(endpoint, payload=None):
    nonce = str(int(time.time() * 1000))
    body = json.dumps(payload) if payload else ""
    message = nonce + endpoint + body
    signature = hmac.new(
        FXOPEN_SECRET.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    headers = {
        "X-Auth-Apikey": FXOPEN_KEY,
        "X-Auth-Nonce": nonce,
        "X-Auth-Signature": signature,
        "Content-Type": "application/json",
    }
    return headers

def get_account_info():
    endpoint = f"/accounts/{FXOPEN_LOGIN}"
    url = BASE_URL + endpoint
    headers = hmac_auth(endpoint)
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()
    else:
        logging.error(f"FXOpen account info fetch failed: {r.status_code} {r.text}")
        return {}

async def send_update():
    account = get_account_info()
    balance = account.get("Balance", "N/A")
    equity = account.get("Equity", "N/A")
    margin = account.get("UsedMargin", "N/A")

    msg = (
        f"💹 FXOpen Bot Report:\n"
        f"Balance: ${balance}\n"
        f"Equity: ${equity}\n"
        f"Used Margin: ${margin}\n"
        f"Time: {datetime.utcnow().strftime('%H:%M:%S UTC')}"
    )
    try:
        await bot.send_message(chat_id=TG_CHAT_ID, text=msg)
        logging.info("Update sent.")
    except Exception as e:
        logging.error(f"Failed to send Telegram update: {e}")

async def periodic_update(interval_sec=60):
    while True:
        await send_update()
        await asyncio.sleep(interval_sec)

async def market_scanner(trader):
    while True:
        try:
            await trader.evaluate_and_execute()
        except Exception as e:
            logging.error(f"[Scanner Error] {e}")
        await asyncio.sleep(1)

async def main():
    # Initialize AI, earnings, screenshot handlers
    ai = AIAnalyzer()
    earnings = EarningsTracker()
    ss = Screenshot()

    # Telegram bot setup (pass earnings for reporting)
    tg_bot = TelegramBot(None, earnings)

    # Trader with FXOpen integration (Trader class must be FXOpen ready)
    trader = Trader(ai, earnings, ss, tg_bot)
    tg_bot.trader = trader

    # Start periodic FXOpen balance update every 60 seconds
    asyncio.create_task(periodic_update(60))

    # Start market scanning task
    asyncio.create_task(market_scanner(trader))

    # Start Telegram bot polling
    await tg_bot.start_polling()

if __name__ == "__main__":
    logging.info("Starting FXOpen AI Trading Bot")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
