"""
Configuration management for AI Trading Bot
"""

import os
from typing import Dict, Any

class Config:
    # API Keys and Tokens
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
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
    MAX_RISK_PERCENT = float(os.getenv("MAX_RISK_PERCENT", "2.0"))
    MAX_DAILY_LOSS_PERCENT = float(os.getenv("MAX_DAILY_LOSS_PERCENT", "5.0"))
    MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "5"))
    DEFAULT_LEVERAGE = int(os.getenv("DEFAULT_LEVERAGE", "33"))
    
    # AI Analysis Configuration
    AI_MODEL = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
    AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.3"))
    AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "1000"))
    
    # Market Scanning Configuration
    SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "30"))  # seconds
    CURRENCIES = os.getenv("CURRENCIES", "EURUSD,GBPUSD,USDJPY,AUDUSD,USDCAD,USDCHF,NZDUSD").split(",")
    TIMEFRAMES = os.getenv("TIMEFRAMES", "M5,M15,H1,H4").split(",")
    
    # Monitoring Configuration
    STATUS_UPDATE_INTERVAL = int(os.getenv("STATUS_UPDATE_INTERVAL", "300"))  # seconds
    HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))  # seconds
    SCREENSHOT_ENABLED = os.getenv("SCREENSHOT_ENABLED", "true").lower() == "true"
    
    # Risk Management
    STOP_LOSS_PIPS = int(os.getenv("STOP_LOSS_PIPS", "20"))
    TAKE_PROFIT_PIPS = int(os.getenv("TAKE_PROFIT_PIPS", "40"))
    MAX_SPREAD_PIPS = int(os.getenv("MAX_SPREAD_PIPS", "3"))
    
    # Failsafe Configuration
    ENABLE_FAILSAFE = os.getenv("ENABLE_FAILSAFE", "true").lower() == "true"
    CLOSE_POSITIONS_ON_STOP = os.getenv("CLOSE_POSITIONS_ON_STOP", "false").lower() == "true"
    MAX_CONSECUTIVE_LOSSES = int(os.getenv("MAX_CONSECUTIVE_LOSSES", "3"))
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/trading_bot.log")
    MAX_LOG_SIZE_MB = int(os.getenv("MAX_LOG_SIZE_MB", "100"))
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration parameters"""
        required_vars = [
            'OPENAI_API_KEY',
            'TELEGRAM_BOT_TOKEN',
            'TELEGRAM_CHAT_ID',
            'FXOPEN_LOGIN',
            'FXOPEN_API_KEY',
            'FXOPEN_API_SECRET'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"Missing required environment variables: {', '.join(missing_vars)}")
            return False
        
        return True
    
    @classmethod
    def get_trading_params(cls) -> Dict[str, Any]:
        """Get trading parameters as dictionary"""
        return {
            'max_risk_percent': cls.MAX_RISK_PERCENT,
            'max_daily_loss_percent': cls.MAX_DAILY_LOSS_PERCENT,
            'max_open_positions': cls.MAX_OPEN_POSITIONS,
            'default_leverage': cls.DEFAULT_LEVERAGE,
            'stop_loss_pips': cls.STOP_LOSS_PIPS,
            'take_profit_pips': cls.TAKE_PROFIT_PIPS,
            'max_spread_pips': cls.MAX_SPREAD_PIPS,
            'currencies': cls.CURRENCIES,
            'timeframes': cls.TIMEFRAMES
        }
    
    @classmethod
    def get_ai_params(cls) -> Dict[str, Any]:
        """Get AI analysis parameters as dictionary"""
        return {
            'model': cls.AI_MODEL,
            'temperature': cls.AI_TEMPERATURE,
            'max_tokens': cls.AI_MAX_TOKENS
        }
