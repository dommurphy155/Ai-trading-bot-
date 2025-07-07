import os
import time
import hmac
import json
import hashlib
import logging
import requests
import schedule
from datetime import datetime
from telegram import Bot

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# ENV variables
API_KEY = os.getenv("OPENAI_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TT_LOGIN = os.getenv("FXOPEN_LOGIN")
TT_KEY = os.getenv("FXOPEN_KEY")
TT_SECRET = os.getenv("FXOPEN_SECRET")

BASE_URL = "https://restapi.fxopen.com:8443"

bot = Bot(token=TG_TOKEN)

def hmac_auth(endpoint, payload=None):
    nonce = str(int(time.time() * 1000))
    body = json.dumps(payload) if payload else ""
    message = nonce + endpoint + body
    signature = hmac.new(
        TT_SECRET.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    headers = {
        "X-Auth-Apikey": TT_KEY,
        "X-Auth-Nonce": nonce,
        "X-Auth-Signature": signature,
        "Content-Type": "application/json",
    }
    return headers

def get_account_info():
    endpoint = f"/accounts/{TT_LOGIN}"
    url = BASE_URL + endpoint
    headers = hmac_auth(endpoint)
    r = requests.get(url, headers=headers)
    return r.json()

def get_prices():
    endpoint = f"/tickdata"
    url = BASE_URL + endpoint
    headers = hmac_auth(endpoint)
    r = requests.get(url, headers=headers)
    return r.json()

def send_update():
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
    bot.send_message(chat_id=TG_CHAT_ID, text=msg)
    logging.info("Update sent.")

def main_loop():
    schedule.every(1).seconds.do(send_update)
    while True:
        schedule.run_pending()
        time.sleep(0.5)
=======
import asyncio
from dotenv import load_dotenv
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
    Remove MT5 references, switch to FXOpen integration, fix imports

if __name__ == "__main__":
    logging.info("FXOpen AI Bot running.")
    main_loop()
