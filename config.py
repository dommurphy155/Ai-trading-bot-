# config.py

import os

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    FXOPEN_LOGIN = os.getenv("FXOPEN_LOGIN")
    FXOPEN_PASSWORD = os.getenv("FXOPEN_PASSWORD")
    FXOPEN_SERVER = os.getenv("FXOPEN_SERVER")

    FXOPEN_API_TOKEN_ID = os.getenv("FXOPEN_API_TOKEN_ID")
    FXOPEN_API_TOKEN_KEY = os.getenv("FXOPEN_API_TOKEN_KEY")
    FXOPEN_API_TOKEN_SECRET = os.getenv("FXOPEN_API_TOKEN_SECRET")

    LEVERAGE = 33  # or load from env if variable

    # Add any other constants or config params here
