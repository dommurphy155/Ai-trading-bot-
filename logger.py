"""
Centralized Logging Configuration
"""

import logging
import logging.handlers
import os
import glob
import time
import traceback
from datetime import datetime
from typing import Optional

from config import Config


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""

    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
        "RESET": "\033[0m",
    }

    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        formatted = super().format(record)
        record.levelname = levelname  # reset to original for other handlers
        return formatted


def setup_logging():
    log_dir = os.path.dirname(Config.LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO))
    root_logger.handlers.clear()

    file_handler = logging.handlers.RotatingFileHandler(
        filename=Config.LOG_FILE,
        maxBytes=Config.MAX_LOG_SIZE_MB * 1024 * 1024,
        backupCount=Config.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_formatter = ColoredFormatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO))

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    configure_module_loggers()

    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized")
    logger.info(f"Log level: {Config.LOG_LEVEL}")
    logger.info(f"Log file: {Config.LOG_FILE}")


def configure_module_loggers():
    # Silence noisy libs
    for noisy_lib in ("telegram", "httpx", "aiohttp", "asyncio", "matplotlib"):
        logging.getLogger(noisy_lib).setLevel(logging.WARNING)

    # Your main modules
    for mod in ("ai_analyzer", "fxopen_handler", "telegram_bot", "trader", "earnings_tracker", "failsafe"):
        logging.getLogger(mod).setLevel(logging.INFO)


class TradingLogger:
    """Dedicated logger for trades"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.trade_log_file = f"logs/trades_{datetime.now():%Y%m%d}.log"
        self._setup_trade_handler()

    def _setup_trade_handler(self):
        try:
            trade_handler = logging.FileHandler(self.trade_log_file, encoding="utf-8")
            formatter = logging.Formatter("%(asctime)s | TRADE | %(message)s", "%Y-%m-%d %H:%M:%S")
            trade_handler.setFormatter(formatter)
            trade_handler.setLevel(logging.INFO)

            # Filter: only messages with 'trade_action' attribute
            trade_handler.addFilter(lambda record: hasattr(record, "trade_action"))
            self.logger.addHandler(trade_handler)
        except Exception as e:
            self.logger.error(f"Failed to setup trade handler: {e}")

    def log_trade_entry(self, trade_data: dict):
        msg = (
            f"ENTRY | {trade_data.get('symbol','N/A')} | {trade_data.get('side','N/A')} | "
            f"{trade_data.get('volume','N/A')} | Entry: {trade_data.get('entry_price','N/A')} | "
            f"SL: {trade_data.get('stop_loss','N/A')} | TP: {trade_data.get('take_profit','N/A')} | "
            f"Confidence: {trade_data.get('confidence',0)*100:.1f}%"
        )
        record = self.logger.makeRecord(self.logger.name, logging.INFO, "", 0, msg, None, None)
        record.trade_action = True
        self.logger.handle(record)

    def log_trade_exit(self, trade_data: dict):
        msg = (
            f"EXIT | {trade_data.get('symbol','N/A')} | {trade_data.get('side','N/A')} | "
            f"{trade_data.get('volume','N/A')} | Exit: {trade_data.get('close_price','N/A')} | "
            f"P&L: ${trade_data.get('pnl',0):.2f} | Duration: {trade_data.get('duration_hours',0):.1f}h"
        )
        record = self.logger.makeRecord(self.logger.name, logging.INFO, "", 0, msg, None, None)
        record.trade_action = True
        self.logger.handle(record)

    def log_trade_modification(self, trade_data: dict):
        msg = (
            f"MODIFY | {trade_data.get('symbol','N/A')} | New SL: {trade_data.get('new_stop_loss','N/A')} | "
            f"New TP: {trade_data.get('new_take_profit','N/A')}"
        )
        record = self.logger.makeRecord(self.logger.name, logging.INFO, "", 0, msg, None, None)
        record.trade_action = True
        self.logger.handle(record)


class PerformanceLogger:
    """Logger for performance metrics"""

    def __init__(self):
        self.logger = logging.getLogger("performance")
        self.performance_log_file = f"logs/performance_{datetime.now():%Y%m%d}.log"
        self._setup_performance_handler()

    def _setup_performance_handler(self):
        try:
            perf_handler = logging.FileHandler(self.performance_log_file, encoding="utf-8")
            formatter = logging.Formatter("%(asctime)s | PERFORMANCE | %(message)s", "%Y-%m-%d %H:%M:%S")
            perf_handler.setFormatter(formatter)
            perf_handler.setLevel(logging.INFO)
            self.logger.addHandler(perf_handler)
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to setup performance handler: {e}")

    def log_daily_summary(self, summary: dict):
        msg = (
            f"DAILY_SUMMARY | Trades: {summary.get('total_trades',0)} | Wins: {summary.get('winning_trades',0)} | "
            f"Losses: {summary.get('losing_trades',0)} | Win Rate: {summary.get('win_rate',0)*100:.1f}% | "
            f"P&L: ${summary.get('daily_pnl',0):.2f} | Balance: ${summary.get('balance',0):.2f}"
        )
        self.logger.info(msg)

    def log_weekly_summary(self, summary: dict):
        msg = (
            f"WEEKLY_SUMMARY | Trades: {summary.get('total_trades',0)} | Win Rate: {summary.get('win_rate',0)*100:.1f}% | "
            f"P&L: ${summary.get('weekly_pnl',0):.2f} | Best Trade: ${summary.get('best_trade',0):.2f} | "
            f"Worst Trade: ${summary.get('worst_trade',0):.2f}"
        )
        self.logger.info(msg)


def get_trade_logger(name: str) -> TradingLogger:
    return TradingLogger(name)


def get_performance_logger() -> PerformanceLogger:
    return PerformanceLogger()


def cleanup_old_logs(days_to_keep: int = 30):
    try:
        log_pattern = "logs/*.log*"
        cutoff = time.time() - days_to_keep * 86400
        deleted = 0
        for log_file in glob.glob(log_pattern):
            try:
                if os.path.getmtime(log_file) < cutoff:
                    os.remove(log_file)
                    deleted += 1
            except OSError:
                pass
        if deleted > 0:
            logging.getLogger(__name__).info(f"Cleaned up {deleted} old log files")
    except Exception as e:
        logging.getLogger(__name__).error(f"Error cleaning up old logs: {e}")


def log_exception(logger: logging.Logger, exception: Exception, context: str = ""):
    logger.error(f"Exception in {context}: {exception}")
    logger.debug(f"Full traceback:\n{traceback.format_exc()}")


class LogExecutionTime:
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
        duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        if exc_type:
            self.logger.error(f"{self.operation_name} failed after {duration:.3f}s: {exc_val}")
        else:
            self.logger.log(self.level, f"{self.operation_name} completed in {duration:.3f}s")