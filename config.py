"""
Configuration for FXOpen AI Trading Bot using Hugging Face
"""

import os
from typing import Dict, Any

class Config:
    # Hugging Face API
    HF_TOKEN = os.getenv("HF_TOKEN", "")
    HF_MODEL = os.getenv("HF_MODEL", "mistralai/Mixtral-8x7B-Instruct-v0.1")

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    # FXOpen API
    FXOPEN_LOGIN = os.getenv("FXOPEN_LOGIN", "")
    FXOPEN_API_KEY = os.getenv("FXOPEN_API_KEY", "")
    FXOPEN_API_SECRET = os.getenv("FXOPEN_API_SECRET", "")
    FXOPEN_SERVER = os.getenv("FXOPEN_SERVER", "ttdemomarginal.fxopen.net")
    FXOPEN_BASE_URL = os.getenv("FXOPEN_BASE_URL", "https://restapi.fxopen.com:8443")

    # AI Config
    AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.3"))
    AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "1024"))

    # Trading Settings
    MAX_RISK_PERCENT = float(os.getenv("MAX_RISK_PERCENT", "2.0"))
    MAX_DAILY_LOSS_PERCENT = float(os.getenv("MAX_DAILY_LOSS_PERCENT", "5.0"))
    MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "5"))
    DEFAULT_LEVERAGE = int(os.getenv("DEFAULT_LEVERAGE", "33"))

    STOP_LOSS_PIPS = int(os.getenv("STOP_LOSS_PIPS", "20"))
    TAKE_PROFIT_PIPS = int(float(STOP_LOSS_PIPS) * 2.0)
    MAX_SPREAD_PIPS = int(os.getenv("MAX_SPREAD_PIPS", "3"))

    CURRENCIES = os.getenv("CURRENCIES", "EURUSD,GBPUSD,USDJPY").split(",")
    TIMEFRAMES = os.getenv("TIMEFRAMES", "M5,M15,H1").split(",")

    @classmethod
    def validate(cls) -> bool:
        required = ["HF_TOKEN", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "FXOPEN_LOGIN", "FXOPEN_API_KEY", "FXOPEN_API_SECRET"]
        missing = [v for v in required if not getattr(cls, v)]
        if missing:
            print(f"❌ Missing config vars: {', '.join(missing)}")
            return False
        return True