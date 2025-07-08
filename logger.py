"""
Centralized Logging Configuration
"""

import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional

from config import Config

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Add color to levelname
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        # Format the message
        formatted = super().format(record)
        
        # Reset levelname to original
        record.levelname = levelname
        
        return formatted

def setup_logging():
    """Setup centralized logging configuration"""
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(Config.LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=Config.LOG_FILE,
        maxBytes=Config.MAX_LOG_SIZE_MB * 1024 * 1024,  # Convert MB to bytes
        backupCount=Config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    
    file_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)  # File gets all messages
    
    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO))
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    configure_module_loggers()
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized")
    logger.info(f"Log level: {Config.LOG_LEVEL}")
    logger.info(f"Log file: {Config.LOG_FILE}")

def configure_module_loggers():
    """Configure logging for specific modules"""
    
    # Reduce verbosity of external libraries
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    
    # Set appropriate levels for our modules
    logging.getLogger('ai_analyzer').setLevel(logging.INFO)
    logging.getLogger('fxopen_handler').setLevel(logging.INFO)
    logging.getLogger('telegram_bot').setLevel(logging.INFO)
    logging.getLogger('trader').setLevel(logging.INFO)
    logging.getLogger('earnings_tracker').setLevel(logging.INFO)
    logging.getLogger('failsafe').setLevel(logging.INFO)

class TradingLogger:
    """Specialized logger for trading operations"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.trade_log_file = f"logs/trades_{datetime.now().strftime('%Y%m%d')}.log"
        
        # Create trade-specific file handler
        self._setup_trade_handler()
    
    def _setup_trade_handler(self):
        """Setup trade-specific log handler"""
        try:
            trade_handler = logging.FileHandler(self.trade_log_file, encoding='utf-8')
            trade_formatter = logging.Formatter(
                fmt='%(asctime)s | TRADE | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            trade_handler.setFormatter(trade_formatter)
            trade_handler.setLevel(logging.INFO)
            
            # Add filter to only log trade-related messages
            trade_handler.addFilter(lambda record: hasattr(record, 'trade_action'))
            
            self.logger.addHandler(trade_handler)
            
        except Exception as e:
            self.logger.error(f"Failed to setup trade handler: {e}")
    
    def log_trade_entry(self, trade_data: dict):
        """Log trade entry"""
        message = (
            f"ENTRY | {trade_data.get('symbol', 'N/A')} | "
            f"{trade_data.get('side', 'N/A')} | "
            f"{trade_data.get('volume', 'N/A')} | "
            f"Entry: {trade_data.get('entry_price', 'N/A')} | "
            f"SL: {trade_data.get('stop_loss', 'N/A')} | "
            f"TP: {trade_data.get('take_profit', 'N/A')} | "
            f"Confidence: {trade_data.get('confidence', 0) * 100:.1f}%"
        )
        
        # Add trade_action attribute for filtering
        record = self.logger.makeRecord(
            name=self.logger.name,
            level=logging.INFO,
            fn='',
            lno=0,
            msg=message,
            args=(),
            exc_info=None
        )
        record.trade_action = True
        self.logger.handle(record)
    
    def log_trade_exit(self, trade_data: dict):
        """Log trade exit"""
        message = (
            f"EXIT | {trade_data.get('symbol', 'N/A')} | "
            f"{trade_data.get('side', 'N/A')} | "
            f"{trade_data.get('volume', 'N/A')} | "
            f"Exit: {trade_data.get('close_price', 'N/A')} | "
            f"P&L: ${trade_data.get('pnl', 0):.2f} | "
            f"Duration: {trade_data.get('duration_hours', 0):.1f}h"
        )
        
        record = self.logger.makeRecord(
            name=self.logger.name,
            level=logging.INFO,
            fn='',
            lno=0,
            msg=message,
            args=(),
            exc_info=None
        )
        record.trade_action = True
        self.logger.handle(record)
    
    def log_trade_modification(self, trade_data: dict):
        """Log trade modification"""
        message = (
            f"MODIFY | {trade_data.get('symbol', 'N/A')} | "
            f"New SL: {trade_data.get('new_stop_loss', 'N/A')} | "
            f"New TP: {trade_data.get('new_take_profit', 'N/A')}"
        )
        
        record = self.logger.makeRecord(
            name=self.logger.name,
            level=logging.INFO,
            fn='',
            lno=0,
            msg=message,
            args=(),
            exc_info=None
        )
        record.trade_action = True
        self.logger.handle(record)

class PerformanceLogger:
    """Logger for performance and analytics"""
    
    def __init__(self):
        self.logger = logging.getLogger('performance')
        self.performance_log_file = f"logs/performance_{datetime.now().strftime('%Y%m%d')}.log"
        self._setup_performance_handler()
    
    def _setup_performance_handler(self):
        """Setup performance-specific log handler"""
        try:
            perf_handler = logging.FileHandler(self.performance_log_file, encoding='utf-8')
            perf_formatter = logging.Formatter(
                fmt='%(asctime)s | PERFORMANCE | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            perf_handler.setFormatter(perf_formatter)
            perf_handler.setLevel(logging.INFO)
            
            self.logger.addHandler(perf_handler)
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to setup performance handler: {e}")
    
    def log_daily_summary(self, summary_data: dict):
        """Log daily performance summary"""
        message = (
            f"DAILY_SUMMARY | "
            f"Trades: {summary_data.get('total_trades', 0)} | "
            f"Wins: {summary_data.get('winning_trades', 0)} | "
            f"Losses: {summary_data.get('losing_trades', 0)} | "
            f"Win Rate: {summary_data.get('win_rate', 0) * 100:.1f}% | "
            f"P&L: ${summary_data.get('daily_pnl', 0):.2f} | "
            f"Balance: ${summary_data.get('balance', 0):.2f}"
        )
        self.logger.info(message)
    
    def log_weekly_summary(self, summary_data: dict):
        """Log weekly performance summary"""
        message = (
            f"WEEKLY_SUMMARY | "
            f"Trades: {summary_data.get('total_trades', 0)} | "
            f"Win Rate: {summary_data.get('win_rate', 0) * 100:.1f}% | "
            f"P&L: ${summary_data.get('weekly_pnl', 0):.2f} | "
            f"Best Trade: ${summary_data.get('best_trade', 0):.2f} | "
            f"Worst Trade: ${summary_data.get('worst_trade', 0):.2f}"
        )
        self.logger.info(message)

def get_trade_logger(name: str) -> TradingLogger:
    """Get a trading logger instance"""
    return TradingLogger(name)

def get_performance_logger() -> PerformanceLogger:
    """Get a performance logger instance"""
    return PerformanceLogger()

def cleanup_old_logs(days_to_keep: int = 30):
    """Clean up old log files"""
    try:
        import glob
        import time
        
        log_pattern = "logs/*.log*"
        current_time = time.time()
        cutoff_time = current_time - (days_to_keep * 24 * 60 * 60)
        
        deleted_count = 0
        
        for log_file in glob.glob(log_pattern):
            try:
                file_time = os.path.getmtime(log_file)
                if file_time < cutoff_time:
                    os.remove(log_file)
                    deleted_count += 1
            except OSError:
                continue
        
        if deleted_count > 0:
            logger = logging.getLogger(__name__)
            logger.info(f"Cleaned up {deleted_count} old log files")
            
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error cleaning up old logs: {e}")

def log_exception(logger: logging.Logger, exception: Exception, context: str = ""):
    """Log exception with full traceback"""
    import traceback
    
    error_msg = f"Exception in {context}: {str(exception)}"
    logger.error(error_msg)
    logger.debug(f"Full traceback:\n{traceback.format_exc()}")

# Context manager for logging function execution time
class LogExecutionTime:
    """Context manager to log function execution time"""
    
    def __init__(self, logger: logging.Logger, operation_name: str, level: int = logging.DEBUG):
        self.logger = logger
        self.operation_name = operation_name
        self.level = level
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.log(self.level, f"Starting {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            if exc_type:
                self.logger.error(f"{self.operation_name} failed after {duration:.3f}s: {exc_val}")
            else:
                self.logger.log(self.level, f"{self.operation_name} completed in {duration:.3f}s")
