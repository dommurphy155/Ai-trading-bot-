# -*- coding: utf-8 -*-
"""
AI Trading Bot - Main Entry Point
Integrates OpenAI analysis, FXOpen trading, and Telegram monitoring
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from dotenv import load_dotenv

from config import Config
from ai_analyzer import AIAnalyzer
from fxopen_handler import FXOpenHandler
from telegram_bot import TelegramBot
from trader import Trader
from earnings_tracker import EarningsTracker
from screenshot import Screenshot
from failsafe import FailsafeManager
from logger import setup_logging


class TradingBotApp:
    def __init__(self) -> None:
        self.running: bool = False
        self.ai_analyzer: AIAnalyzer | None = None
        self.fxopen_handler: FXOpenHandler | None = None
        self.telegram_bot: TelegramBot | None = None
        self.trader: Trader | None = None
        self.earnings_tracker: EarningsTracker | None = None
        self.screenshot: Screenshot | None = None
        self.failsafe: FailsafeManager | None = None
        self.logger = logging.getLogger(__name__)

    async def initialize(self) -> None:
        """Initialize all bot components"""
        try:
            load_dotenv()

            setup_logging()
            self.logger.info("Starting AI Trading Bot initialization...")

            if not Config.validate():
                raise ValueError("Invalid configuration. Check your environment variables.")

            self.ai_analyzer = AIAnalyzer()
            self.fxopen_handler = FXOpenHandler()
            self.earnings_tracker = EarningsTracker()
            self.screenshot = Screenshot()
            self.failsafe = FailsafeManager()

            self.trader = Trader(
                ai_analyzer=self.ai_analyzer,
                fxopen_handler=self.fxopen_handler,
                earnings_tracker=self.earnings_tracker,
                screenshot=self.screenshot,
                failsafe=self.failsafe,
            )

            self.telegram_bot = TelegramBot(
                trader=self.trader,
                earnings_tracker=self.earnings_tracker,
                fxopen_handler=self.fxopen_handler,
            )

            await self._test_connections()
            self.logger.info("Bot initialization completed successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize bot: {e}")
            raise

    async def _test_connections(self) -> None:
        self.logger.info("Testing external service connections...")

        try:
            await self.ai_analyzer.test_connection()
            self.logger.info("✓ OpenAI connection successful")
        except Exception as e:
            self.logger.error(f"✗ OpenAI connection failed: {e}")
            raise

        try:
            await self.fxopen_handler.test_connection()
            self.logger.info("✓ FXOpen connection successful")
        except Exception as e:
            self.logger.error(f"✗ FXOpen connection failed: {e}")
            raise

        try:
            await self.telegram_bot.test_connection()
            self.logger.info("✓ Telegram connection successful")
        except Exception as e:
            self.logger.error(f"✗ Telegram connection failed: {e}")
            raise

    async def start(self) -> None:
        self.running = True
        self.logger.info("Starting AI Trading Bot...")

        try:
            await self.telegram_bot.send_startup_notification()

            tasks = [
                asyncio.create_task(self.trader.start_trading_loop()),
                asyncio.create_task(self.telegram_bot.start_polling()),
                asyncio.create_task(self._periodic_status_update()),
                asyncio.create_task(self._monitor_system_health()),
            ]

            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            self.logger.error(f"Bot execution error: {e}")
            if self.telegram_bot:
                await self.telegram_bot.send_error_notification(str(e))
            raise

    async def _periodic_status_update(self) -> None:
        while self.running:
            try:
                await asyncio.sleep(Config.STATUS_UPDATE_INTERVAL)
                if self.running:
                    status = await self._get_system_status()
                    await self.telegram_bot.send_status_update(status)
            except Exception as e:
                self.logger.error(f"Error in periodic status update: {e}")

    async def _monitor_system_health(self) -> None:
        while self.running:
            try:
                await asyncio.sleep(Config.HEALTH_CHECK_INTERVAL)
                if self.running:
                    health_status = await self.failsafe.check_system_health(
                        trader=self.trader,
                        fxopen_handler=self.fxopen_handler,
                        earnings_tracker=self.earnings_tracker,
                    )

                    if not health_status["healthy"]:
                        await self.telegram_bot.send_health_alert(health_status)
                        if health_status["critical"]:
                            self.logger.critical("Critical system health issue detected, stopping bot")
                            await self.stop()
            except Exception as e:
                self.logger.error(f"Error in system health monitoring: {e}")

    async def _get_system_status(self) -> dict:
        try:
            account_info = await self.fxopen_handler.get_account_info()
            earnings = await self.earnings_tracker.get_current_performance()

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "account_balance": account_info.get("balance", 0),
                "account_equity": account_info.get("equity", 0),
                "used_margin": account_info.get("used_margin", 0),
                "free_margin": account_info.get("free_margin", 0),
                "daily_pnl": earnings.get("daily_pnl", 0),
                "total_pnl": earnings.get("total_pnl", 0),
                "win_rate": earnings.get("win_rate", 0),
                "open_positions": len(account_info.get("positions", [])),
                "bot_status": "running" if self.running else "stopped",
            }
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}

    async def stop(self) -> None:
        self.logger.info("Stopping AI Trading Bot...")
        self.running = False

        try:
            if Config.CLOSE_POSITIONS_ON_STOP:
                await self.trader.close_all_positions()

            if self.telegram_bot:
                await self.telegram_bot.send_shutdown_notification()

            if self.trader:
                await self.trader.stop()

            if self.telegram_bot:
                await self.telegram_bot.stop()

            self.logger.info("Bot stopped successfully")

        except Exception as e:
            self.logger.error(f"Error during bot shutdown: {e}")

    def setup_signal_handlers(self) -> None:
        def signal_handler(signum, frame) -> None:
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.stop())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main() -> None:
    bot_app = TradingBotApp()

    try:
        bot_app.setup_signal_handlers()
        await bot_app.initialize()
        await bot_app.start()

    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        await bot_app.stop()


if __name__ == "__main__":
    asyncio.run(main())
