import os
from typing import Dict, Any

class Config:
    # API Keys and Tokens
    # OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # no longer used, remove if you want
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    
    # FXOpen Configuration
    FXOPEN_LOGIN = os.getenv("FXOPEN_LOGIN", "")
    FXOPEN_PASSWORD = os.getenv("FXOPEN_PASSWORD", "")
    FXOPEN_SERVER = os.getenv("FXOPEN_SERVER", "")
    FXOPEN_API_KEY = os.getenv("FXOPEN_API_KEY", "")
    FXOPEN_API_SECRET = os.getenv("FXOPEN_API_SECRET", "")
    FXOPEN_BASE_URL = os.getenv("FXOPEN_BASE_URL", "https://restapi.fxopen.com:8443")
    
    # Trading Configuration
    MAX_RISK_PERCENT = float(os.getenv("MAX_RISK_PERCENT", "2.0"))  # % of account balance risked per trade
    MAX_DAILY_LOSS_PERCENT = float(os.getenv("MAX_DAILY_LOSS_PERCENT", "5.0"))
    MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "5"))
    DEFAULT_LEVERAGE = int(os.getenv("DEFAULT_LEVERAGE", "33"))
    
    # Profit and Risk Ratios (Dynamic)
    PROFIT_TARGET_MULTIPLIER = float(os.getenv("PROFIT_TARGET_MULTIPLIER", "2.0"))
    ADAPTIVE_RISK_SCALING = os.getenv("ADAPTIVE_RISK_SCALING", "true").lower() == "true"
    RISK_SCALING_FACTOR = float(os.getenv("RISK_SCALING_FACTOR", "0.1"))
    
    # Cooldown and Streak Management
    MAX_CONSECUTIVE_LOSSES = int(os.getenv("MAX_CONSECUTIVE_LOSSES", "3"))
    COOLDOWN_PERIOD_MINUTES = int(os.getenv("COOLDOWN_PERIOD_MINUTES", "30"))
    
    # AI Analysis Configuration - switched to Hugging Face
    HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")  # your HF token here
    HF_MODEL_NAME = os.getenv("HF_MODEL_NAME", "gpt2")  # default to gpt2 or your chosen model
    AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.3"))
    AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "1000"))
    
    # Market Scanning Configuration
    SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "30"))
    CURRENCIES = os.getenv("CURRENCIES", "EURUSD,GBPUSD,USDJPY,AUDUSD,USDCAD,USDCHF,NZDUSD").split(",")
    TIMEFRAMES = os.getenv("TIMEFRAMES", "M5,M15,H1,H4").split(",")
    
    # Monitoring Configuration
    STATUS_UPDATE_INTERVAL = int(os.getenv("STATUS_UPDATE_INTERVAL", "300"))
    HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))
    SCREENSHOT_ENABLED = os.getenv("SCREENSHOT_ENABLED", "true").lower() == "true"
    
    # Risk Management
    STOP_LOSS_PIPS = int(os.getenv("STOP_LOSS_PIPS", "20"))
    TAKE_PROFIT_PIPS = int(float(os.getenv("STOP_LOSS_PIPS", "20")) * PROFIT_TARGET_MULTIPLIER)
    MAX_SPREAD_PIPS = int(os.getenv("MAX_SPREAD_PIPS", "3"))
    
    # Failsafe Configuration
    ENABLE_FAILSAFE = os.getenv("ENABLE_FAILSAFE", "true").lower() == "true"
    CLOSE_POSITIONS_ON_STOP = os.getenv("CLOSE_POSITIONS_ON_STOP", "false").lower() == "true"
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/trading_bot.log")
    MAX_LOG_SIZE_MB = int(os.getenv("MAX_LOG_SIZE_MB", "100"))
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    
    @classmethod
    def validate(cls) -> bool:
        required_vars = [
            'HF_API_TOKEN',
            'TELEGRAM_BOT_TOKEN',
            'TELEGRAM_CHAT_ID',
            'FXOPEN_LOGIN',
            'FXOPEN_API_KEY',
            'FXOPEN_API_SECRET'
        ]
        
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        if missing_vars:
            print(f"Missing required environment variables: {', '.join(missing_vars)}")
            return False
        return True
    
    @classmethod
    def get_trading_params(cls) -> Dict[str, Any]:
        return {
            'max_risk_percent': cls.MAX_RISK_PERCENT,
            'max_daily_loss_percent': cls.MAX_DAILY_LOSS_PERCENT,
            'max_open_positions': cls.MAX_OPEN_POSITIONS,
            'default_leverage': cls.DEFAULT_LEVERAGE,
            'stop_loss_pips': cls.STOP_LOSS_PIPS,
            'take_profit_pips': cls.TAKE_PROFIT_PIPS,
            'max_spread_pips': cls.MAX_SPREAD_PIPS,
            'currencies': cls.CURRENCIES,
            'timeframes': cls.TIMEFRAMES,
            'profit_target_multiplier': cls.PROFIT_TARGET_MULTIPLIER,
            'adaptive_risk_scaling': cls.ADAPTIVE_RISK_SCALING,
            'risk_scaling_factor': cls.RISK_SCALING_FACTOR,
            'max_consecutive_losses': cls.MAX_CONSECUTIVE_LOSSES,
            'cooldown_period_minutes': cls.COOLDOWN_PERIOD_MINUTES,
        }
    
    @classmethod
    def get_ai_params(cls) -> Dict[str, Any]:
        return {
            'model': cls.HF_MODEL_NAME,
            'temperature': cls.AI_TEMPERATURE,
            'max_tokens': cls.AI_MAX_TOKENS
        }