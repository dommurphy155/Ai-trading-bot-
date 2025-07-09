import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
import numpy as np

from config import Config
from telegram_bot import TelegramBot

class Trader:
    def __init__(self, ai_analyzer, fxopen_handler, earnings_tracker, screenshot, failsafe):
        self.ai_analyzer = ai_analyzer
        self.fxopen_handler = fxopen_handler
        self.earnings_tracker = earnings_tracker
        self.screenshot = screenshot
        self.failsafe = failsafe
        self.logger = logging.getLogger(__name__)
        
        self.is_running = False
        self.is_paused = False
        self.last_analysis_time: Dict[str, datetime] = {}
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.daily_trades = 0
        self.start_time = None
        self.trade_lock = asyncio.Lock()
        
        self.telegram_bot = TelegramBot()
        
        # Per-symbol cooldown after loss (in seconds)
        self.symbol_cooldowns: Dict[str, datetime] = {}
    
    async def start(self):
        self.is_running = True
        self.is_paused = False
        self.start_time = datetime.utcnow()
        self.logger.info("Trading system started")
    
    async def pause(self):
        self.is_paused = True
        self.logger.info("Trading system paused")
    
    async def stop(self):
        self.is_running = False
        self.is_paused = False
        self.logger.info("Trading system stopped")
    
    async def emergency_stop(self):
        self.logger.critical("EMERGENCY STOP INITIATED")
        try:
            await self.stop()
            if Config.CLOSE_POSITIONS_ON_STOP:
                await self.close_all_positions()
        except Exception as e:
            self.logger.error(f"Error during emergency stop: {e}")
    
    async def start_trading_loop(self):
        self.logger.info("Starting main trading loop")
        while self.is_running:
            try:
                if self.is_paused:
                    await asyncio.sleep(Config.SCAN_INTERVAL)
                    continue
                
                await self._check_daily_reset()
                
                if not await self._check_failsafe_conditions():
                    self.logger.warning("Failsafe triggered - pausing trading")
                    self.is_paused = True
                    await asyncio.sleep(60)
                    continue
                
                await self.evaluate_and_execute()
                await asyncio.sleep(Config.SCAN_INTERVAL)
            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(Config.SCAN_INTERVAL)
    
    async def evaluate_and_execute(self):
        async with self.trade_lock:
            try:
                account_info = await self._retry_api_call(self.fxopen_handler.get_account_info)
                balance = float(account_info.get('Balance', 0))
                equity = float(account_info.get('Equity', 0))
                
                if not await self._can_trade(account_info):
                    return
                
                for symbol in Config.CURRENCIES:
                    # Check cooldown after loss for symbol
                    cooldown_end = self.symbol_cooldowns.get(symbol)
                    if cooldown_end and datetime.utcnow() < cooldown_end:
                        self.logger.debug(f"{symbol} in cooldown after loss until {cooldown_end}")
                        continue
                    
                    try:
                        await self._evaluate_symbol(symbol, balance)
                    except Exception as e:
                        self.logger.error(f"Error evaluating {symbol}: {e}")
            except Exception as e:
                self.logger.error(f"Error in evaluate_and_execute: {e}")
    
    async def _evaluate_symbol(self, symbol: str, balance: float):
        now = datetime.utcnow()
        if symbol in self.last_analysis_time:
            elapsed = (now - self.last_analysis_time[symbol]).total_seconds()
            if elapsed < Config.SCAN_INTERVAL:
                return
        
        market_data = await self._get_comprehensive_market_data(symbol)
        analysis = await self.ai_analyzer.analyze_market_data(market_data)
        self.last_analysis_time[symbol] = now
        
        if await self._is_signal_actionable(analysis, symbol):
            await self._execute_trade(analysis, symbol, balance)
    
    async def _get_comprehensive_market_data(self, symbol: str) -> Dict[str, Any]:
        try:
            current_data = await self._retry_api_call(lambda: self.fxopen_handler.get_market_data(symbol))
            timeframe_analysis = {}
            for tf in Config.TIMEFRAMES:
                try:
                    hist_data = await self._retry_api_call(lambda: self.fxopen_handler.get_historical_data(symbol, tf, 100))
                    if hist_data:
                        timeframe_analysis[tf] = self._calculate_technical_indicators(hist_data)
                except Exception as e:
                    self.logger.warning(f"Failed getting {tf} data for {symbol}: {e}")
            
            indicators = self._calculate_current_indicators(current_data)
            
            market_data = {
                'symbol': symbol,
                'current_price': current_data.get('current_price', 0),
                'bid': current_data.get('bid', 0),
                'ask': current_data.get('ask', 0),
                'spread': current_data.get('spread', 0),
                'timestamp': current_data.get('timestamp'),
                'indicators': indicators,
                'timeframe_analysis': timeframe_analysis,
                'session': self._get_trading_session(),
                'volatility': self._calculate_volatility(timeframe_analysis),
                'news_impact': 'None'  # stub for future news integration
            }
            return market_data
        except Exception as e:
            self.logger.error(f"Error getting market data for {symbol}: {e}")
            return {'symbol': symbol, 'current_price': 0, 'error': str(e)}
    
    def _calculate_technical_indicators(self, hist_data: List[Dict]) -> Dict[str, Any]:
        if len(hist_data) < 20:
            return {}
        
        closes = np.array([float(d.get('Close', 0)) for d in hist_data[-50:]])
        highs = np.array([float(d.get('High', 0)) for d in hist_data[-50:]])
        lows = np.array([float(d.get('Low', 0)) for d in hist_data[-50:]])
        
        if len(closes) < 20 or len(highs) < 20 or len(lows) < 20:
            return {}
        
        indicators = {}
        indicators['SMA_20'] = np.mean(closes[-20:])
        indicators['SMA_50'] = np.mean(closes[-50:]) if len(closes) >= 50 else np.nan
        indicators['EMA_20'] = self._calculate_ema(closes, 20)
        indicators['RSI'] = self._calculate_rsi(closes, 14)
        
        macd_data = self._calculate_macd(closes)
        indicators.update(macd_data)
        
        bb_data = self._calculate_bollinger_bands(closes, 20, 2)
        indicators.update(bb_data)
        
        support_resistance = self._calculate_support_resistance(highs, lows)
        indicators.update(support_resistance)
        
        # Add ATR for volatility
        indicators['ATR_14'] = self._calculate_atr(hist_data, 14)
        
        return indicators
    
    def _calculate_current_indicators(self, current_data: Dict) -> Dict[str, Any]:
        bid = current_data.get('bid', 0)
        ask = current_data.get('ask', 0)
        spread = current_data.get('spread', 0)
        
        bid_ask_ratio = bid / ask if ask > 0 else 0
        
        return {
            'spread_pips': spread,
            'bid_ask_ratio': bid_ask_ratio
        }
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        multiplier = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        return ema
    
    def _calculate_rsi(self, prices: np.ndarray, period: int) -> float:
        if len(prices) < period + 1:
            return 50.0
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: np.ndarray) -> Dict[str, float]:
        try:
            ema_12 = self._calculate_ema(prices, 12)
            ema_26 = self._calculate_ema(prices, 26