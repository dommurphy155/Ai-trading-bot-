"""
Screenshot Capture Module for Trade Documentation
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime


class Screenshot:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.screenshot_dir = "screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)

    async def capture_trade_screenshot(self, trade_data: Dict[str, Any]) -> Optional[str]:
        """
        Capture screenshot for trade documentation

        Args:
            trade_data: Trade info dict

        Returns:
            Filename or None on failure
        """
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            symbol = trade_data.get('symbol', 'UNKNOWN')
            side = trade_data.get('side', 'UNKNOWN')
            filename = f"trade_{symbol}_{side}_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)

            success = await self._create_trade_image(trade_data, filepath)
            if success:
                self.logger.info(f"Screenshot captured: {filename}")
                return filename
            else:
                self.logger.warning("Failed to capture screenshot")
                return None
        except Exception as e:
            self.logger.error(f"Error capturing trade screenshot: {e}")
            return None

    async def _create_trade_image(self, trade_data: Dict[str, Any], filepath: str) -> bool:
        """
        Create a visual trade snapshot.
        Current placeholder: saves trade info text file alongside fake .png name.
        """
        try:
            trade_info = (
                f"TRADE SCREENSHOT\n"
                f"================\n"
                f"Timestamp: {trade_data.get('timestamp', 'Unknown')}\n"
                f"Symbol: {trade_data.get('symbol', 'Unknown')}\n"
                f"Side: {trade_data.get('side', 'Unknown')}\n"
                f"Volume: {trade_data.get('volume', 'Unknown')}\n"
                f"Entry Price: {trade_data.get('entry_price', 'Unknown')}\n"
                f"Stop Loss: {trade_data.get('stop_loss', 'Unknown')}\n"
                f"Take Profit: {trade_data.get('take_profit', 'Unknown')}\n"
                f"AI Confidence: {trade_data.get('confidence', 0)*100:.1f}%\n"
                f"Reason: {trade_data.get('reason', 'Unknown')}\n"
                f"================\n"
            )
            text_path = filepath.replace('.png', '.txt')
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(trade_info)
            return True
        except Exception as e:
            self.logger.error(f"Error creating trade image: {e}")
            return False

    async def capture_account_screenshot(self) -> Optional[str]:
        """Capture account status placeholder screenshot"""
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"account_status_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)

            info = (
                f"ACCOUNT STATUS SCREENSHOT\n"
                f"========================\n"
                f"Timestamp: {datetime.utcnow().isoformat()}\n"
                f"Note: Placeholder - replace with real screenshot logic\n"
                f"========================\n"
            )
            text_path = filepath.replace('.png', '.txt')
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(info)

            self.logger.info(f"Account screenshot captured: {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"Error capturing account screenshot: {e}")
            return None

    async def capture_chart_screenshot(self, symbol: str, timeframe: str) -> Optional[str]:
        """Capture chart screenshot placeholder"""
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"chart_{symbol}_{timeframe}_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)

            info = (
                f"CHART SCREENSHOT\n"
                f"===============\n"
                f"Symbol: {symbol}\n"
                f"Timeframe: {timeframe}\n"
                f"Timestamp: {datetime.utcnow().isoformat()}\n"
                f"Note: Placeholder - replace with real chart capture\n"
                f"===============\n"
            )
            text_path = filepath.replace('.png', '.txt')
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(info)

            self.logger.info(f"Chart screenshot captured: {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"Error capturing chart screenshot: {e}")
            return None

    async def cleanup_old_screenshots(self, days_to_keep: int = 7):
        """Delete screenshots older than days_to_keep"""
        try:
            cutoff = time.time() - days_to_keep * 86400
            deleted = 0
            for fname in os.listdir(self.screenshot_dir):
                path = os.path.join(self.screenshot_dir, fname)
                if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                    try:
                        os.remove(path)
                        deleted += 1
                    except OSError as e:
                        self.logger.warning(f"Failed to delete {path}: {e}")
            self.logger.info(f"Deleted {deleted} old screenshots")
        except Exception as e:
            self.logger.error(f"Error cleaning up old screenshots: {e}")

    async def get_screenshot_path(self, filename: str) -> str:
        return os.path.join(self.screenshot_dir, filename)

    async def screenshot_exists(self, filename: str) -> bool:
        return os.path.exists(os.path.join(self.screenshot_dir, filename))

    async def get_screenshot_data(self, filename: str) -> Optional[bytes]:
        try:
            path = os.path.join(self.screenshot_dir, filename)
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    return f.read()
            else:
                self.logger.warning(f"Screenshot file not found: {filename}")
                return None
        except Exception as e:
            self.logger.error(f"Error reading screenshot data: {e}")
            return None

    async def get_screenshot_list(self) -> List[dict]:
        try:
            files = []
            for fname in os.listdir(self.screenshot_dir):
                path = os.path.join(self.screenshot_dir, fname)
                if os.path.isfile(path):
                    stat = os.stat(path)
                    files.append({
                        'filename': fname,
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
            files.sort(key=lambda x: x['created'], reverse=True)
            return files
        except Exception as e:
            self.logger.error(f"Error getting screenshot list: {e}")
            return []