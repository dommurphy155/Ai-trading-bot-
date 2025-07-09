import logging
from datetime import datetime

class FailsafeManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def check_system_health(self, trader, fxopen_handler, earnings_tracker):
        """
        Perform basic health diagnostics and return health status.
        Expects:
          - fxopen_handler.get_account_info() -> dict with keys: equity, used_margin
          - earnings_tracker.get_current_performance() -> dict with keys: win_rate, daily_pnl
        """
        try:
            self.logger.info("🔍 Running system health check...")

            account_info = await fxopen_handler.get_account_info()
            performance = await earnings_tracker.get_current_performance()

            equity = float(account_info.get("equity", 0))
            margin = float(account_info.get("used_margin", 0))
            win_rate = float(performance.get("win_rate", 0))
            pnl = float(performance.get("daily_pnl", 0))

            critical = False
            reasons = []

            if equity < 10:
                critical = True
                reasons.append("🟥 Account equity critically low")

            if win_rate < 20:
                reasons.append("⚠️ Low win rate detected")

            if pnl < -50:
                reasons.append("⚠️ Daily PnL in dangerous territory")

            if not reasons:
                reasons.append("✅ All checks passed")

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "healthy": not critical,
                "critical": critical,
                "reasons": reasons,
                "equity": equity,
                "margin": margin,
                "win_rate": win_rate,
                "daily_pnl": pnl,
            }

        except Exception as e:
            self.logger.error(f"Failsafe system health check failed: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "healthy": False,
                "critical": True,
                "reasons": [f"Failsafe error: {str(e)}"],
                "equity": 0,
                "margin": 0,
                "win_rate": 0,
                "daily_pnl": 0,
            }