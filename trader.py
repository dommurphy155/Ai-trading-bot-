"""
Main Trading Logic and Strategy Implementation
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np

from config import Config

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
        self.last_analysis_time = {}
        self.consecutive_losses = 0
        self.daily_trades = 0
        self.start_time = None
        
    async def start(self):
        """Start the trading system"""
        self.is_running = True
        self.is_paused = False
        self.start_time = datetime.utcnow()
        self.logger.info("Trading system started")
    
    async def pause(self):
        """Pause trading (stop new trades but keep monitoring)"""
        self.is_paused = True
        self.logger.info("Trading system paused")
    
    async def stop(self):
        """Stop the trading system"""
        self.is_running = False
        self.is_paused = False
        self.logger.info("Trading system stopped")
    
    async def emergency_stop(self):
        """Emergency stop with position closure"""
        self.logger.critical("EMERGENCY STOP INITIATED")
        
        try:
            # Stop trading
            await self.stop()
            
            # Close all positions if configured
            if Config.CLOSE_POSITIONS_ON_STOP:
                await self.close_all_positions()
                
        except Exception as e:
            self.logger.error(f"Error during emergency stop: {e}")
    
    async def start_trading_loop(self):
        """Main trading loop"""
        self.logger.info("Starting main trading loop")
        
        while self.is_running:
            try:
                # Check if trading is paused
                if self.is_paused:
                    await asyncio.sleep(Config.SCAN_INTERVAL)
                    continue
                
                # Check daily reset
                await self._check_daily_reset()
                
                # Check failsafe conditions
                if not await self._check_failsafe_conditions():
                    self.logger.warning("Failsafe conditions triggered, pausing trading")
                    self.is_paused = True
                    await asyncio.sleep(60)  # Wait before retrying
                    continue
                
                # Scan markets and evaluate trades
                await self.evaluate_and_execute()
                
                # Wait before next scan
                await asyncio.sleep(Config.SCAN_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(Config.SCAN_INTERVAL)
    
    async def evaluate_and_execute(self):
        """Evaluate markets and execute trades"""
        try:
            # Get current account status
            account_info = await self.fxopen_handler.get_account_info()
            balance = float(account_info.get('Balance', 0))
            equity = float(account_info.get('Equity', 0))
            
            # Check if we can trade
            if not await self._can_trade(account_info):
                return
            
            # Scan each currency pair
            for symbol in Config.CURRENCIES:
                try:
                    await self._evaluate_symbol(symbol, balance)
                except Exception as e:
                    self.logger.error(f"Error evaluating {symbol}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error in evaluate_and_execute: {e}")
    
    async def _evaluate_symbol(self, symbol: str, balance: float):
        """Evaluate a specific symbol for trading opportunities"""
        try:
            # Check if enough time has passed since last analysis
            now = datetime.utcnow()
            if symbol in self.last_analysis_time:
                time_diff = (now - self.last_analysis_time[symbol]).total_seconds()
                if time_diff < Config.SCAN_INTERVAL:
                    return
            
            # Get market data
            market_data = await self._get_comprehensive_market_data(symbol)
            
            # Perform AI analysis
            analysis = await self.ai_analyzer.analyze_market_data(market_data)
            
            # Update last analysis time
            self.last_analysis_time[symbol] = now
            
            # Check if signal is actionable
            if await self._is_signal_actionable(analysis, symbol):
                await self._execute_trade(analysis, symbol, balance)
                
        except Exception as e:
            self.logger.error(f"Error evaluating symbol {symbol}: {e}")
    
    async def _get_comprehensive_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive market data for analysis"""
        try:
            # Get current market data
            current_data = await self.fxopen_handler.get_market_data(symbol)
            
            # Get historical data for different timeframes
            timeframe_analysis = {}
            for tf in Config.TIMEFRAMES:
                try:
                    hist_data = await self.fxopen_handler.get_historical_data(symbol, tf, 100)
                    if hist_data:
                        timeframe_analysis[tf] = self._calculate_technical_indicators(hist_data)
                except Exception as e:
                    self.logger.warning(f"Could not get {tf} data for {symbol}: {e}")
            
            # Calculate technical indicators for current data
            indicators = self._calculate_current_indicators(current_data)
            
            # Prepare comprehensive market data
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
                'news_impact': 'None'  # Would integrate with news API in production
            }
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error getting comprehensive market data for {symbol}: {e}")
            return {'symbol': symbol, 'current_price': 0, 'error': str(e)}
    
    def _calculate_technical_indicators(self, hist_data: List[Dict]) -> Dict[str, Any]:
        """Calculate technical indicators from historical data"""
        try:
            if len(hist_data) < 20:
                return {}
            
            # Extract price data
            closes = [float(d.get('Close', 0)) for d in hist_data[-50:]]
            highs = [float(d.get('High', 0)) for d in hist_data[-50:]]
            lows = [float(d.get('Low', 0)) for d in hist_data[-50:]]
            
            if not closes or not highs or not lows:
                return {}
            
            indicators = {}
            
            # Simple Moving Averages
            if len(closes) >= 20:
                indicators['SMA_20'] = np.mean(closes[-20:])
            if len(closes) >= 50:
                indicators['SMA_50'] = np.mean(closes[-50:])
            
            # Exponential Moving Average
            if len(closes) >= 20:
                indicators['EMA_20'] = self._calculate_ema(closes, 20)
            
            # RSI
            if len(closes) >= 14:
                indicators['RSI'] = self._calculate_rsi(closes, 14)
            
            # MACD
            if len(closes) >= 26:
                macd_data = self._calculate_macd(closes)
                indicators.update(macd_data)
            
            # Bollinger Bands
            if len(closes) >= 20:
                bb_data = self._calculate_bollinger_bands(closes, 20, 2)
                indicators.update(bb_data)
            
            # Support and Resistance
            support_resistance = self._calculate_support_resistance(highs, lows)
            indicators.update(support_resistance)
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error calculating technical indicators: {e}")
            return {}
    
    def _calculate_current_indicators(self, current_data: Dict) -> Dict[str, Any]:
        """Calculate indicators for current price data"""
        return {
            'spread_pips': current_data.get('spread', 0),
            'bid_ask_ratio': current_data.get('bid', 0) / max(current_data.get('ask', 1), 0.0001)
        }
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(self, prices: List[float]) -> Dict[str, float]:
        """Calculate MACD indicator"""
        try:
            ema_12 = self._calculate_ema(prices, 12)
            ema_26 = self._calculate_ema(prices, 26)
            macd_line = ema_12 - ema_26
            
            # Signal line (EMA of MACD line) - simplified
            signal_line = macd_line * 0.8  # Simplified calculation
            
            return {
                'MACD': macd_line,
                'MACD_Signal': signal_line,
                'MACD_Histogram': macd_line - signal_line
            }
        except:
            return {'MACD': 0, 'MACD_Signal': 0, 'MACD_Histogram': 0}
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int, std_dev: float) -> Dict[str, float]:
        """Calculate Bollinger Bands"""
        try:
            sma = np.mean(prices[-period:])
            std = np.std(prices[-period:])
            
            return {
                'BB_Upper': sma + (std * std_dev),
                'BB_Middle': sma,
                'BB_Lower': sma - (std * std_dev)
            }
        except:
            return {'BB_Upper': 0, 'BB_Middle': 0, 'BB_Lower': 0}
    
    def _calculate_support_resistance(self, highs: List[float], lows: List[float]) -> Dict[str, float]:
        """Calculate support and resistance levels"""
        try:
            recent_highs = highs[-20:]
            recent_lows = lows[-20:]
            
            resistance = max(recent_highs)
            support = min(recent_lows)
            
            return {
                'Resistance': resistance,
                'Support': support
            }
        except:
            return {'Resistance': 0, 'Support': 0}
    
    def _get_trading_session(self) -> str:
        """Determine current trading session"""
        utc_hour = datetime.utcnow().hour
        
        if 0 <= utc_hour < 7:
            return "Asian"
        elif 7 <= utc_hour < 15:
            return "European"
        elif 15 <= utc_hour < 22:
            return "American"
        else:
            return "Asian"
    
    def _calculate_volatility(self, timeframe_analysis: Dict) -> str:
        """Calculate market volatility"""
        try:
            # Simple volatility calculation based on RSI
            rsi_values = []
            for tf_data in timeframe_analysis.values():
                if 'RSI' in tf_data:
                    rsi_values.append(tf_data['RSI'])
            
            if rsi_values:
                avg_rsi = np.mean(rsi_values)
                if avg_rsi > 70 or avg_rsi < 30:
                    return "High"
                elif avg_rsi > 60 or avg_rsi < 40:
                    return "Medium"
                else:
                    return "Low"
            
            return "Normal"
        except:
            return "Normal"
    
    async def _is_signal_actionable(self, analysis: Dict[str, Any], symbol: str) -> bool:
        """Check if the AI signal is actionable"""
        try:
            # Check signal validity
            signal = analysis.get('signal', 'HOLD')
            confidence = analysis.get('confidence', 0)
            
            if signal == 'HOLD':
                return False
            
            # Check confidence threshold
            if confidence < 0.7:  # Require at least 70% confidence
                self.logger.debug(f"Low confidence signal for {symbol}: {confidence:.2f}")
                return False
            
            # Check spread
            spread = analysis.get('spread', 0)
            if spread > Config.MAX_SPREAD_PIPS:
                self.logger.debug(f"Spread too high for {symbol}: {spread} pips")
                return False
            
            # Check risk-reward ratio
            rr_ratio = analysis.get('risk_reward_ratio', 0)
            if rr_ratio < 1.5:  # Require at least 1:1.5 risk-reward
                self.logger.debug(f"Poor risk-reward ratio for {symbol}: {rr_ratio:.2f}")
                return False
            
            # Check maximum open positions
            current_positions = await self.fxopen_handler.get_positions()
            if len(current_positions) >= Config.MAX_OPEN_POSITIONS:
                self.logger.debug("Maximum open positions reached")
                return False
            
            # Check if we already have a position in this symbol
            for pos in current_positions:
                if pos.get('Symbol') == symbol:
                    self.logger.debug(f"Already have position in {symbol}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking signal actionability: {e}")
            return False
    
    async def _execute_trade(self, analysis: Dict[str, Any], symbol: str, balance: float):
        """Execute a trade based on AI analysis"""
        try:
            signal = analysis.get('signal')
            confidence = analysis.get('confidence', 0)
            entry_price = analysis.get('entry_price', 0)
            stop_loss = analysis.get('stop_loss', 0)
            take_profit = analysis.get('take_profit', 0)
            
            # Calculate position size
            risk_amount = balance * (Config.MAX_RISK_PERCENT / 100)
            stop_loss_pips = abs(entry_price - stop_loss) * 10000  # Convert to pips
            
            position_size = await self.fxopen_handler.calculate_position_size(
                symbol, risk_amount, int(stop_loss_pips)
            )
            
            # Prepare order parameters
            order_params = {
                'symbol': symbol,
                'side': signal.lower(),
                'volume': position_size,
                'order_type': 'market',
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'comment': f"AI_{confidence:.2f}_{datetime.utcnow().strftime('%H%M%S')}"
            }
            
            # Execute the trade
            result = await self.fxopen_handler.place_order(order_params)
            
            if result:
                # Record the trade
                trade_data = {
                    'symbol': symbol,
                    'side': signal,
                    'volume': position_size,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'confidence': confidence,
                    'reason': f"AI Analysis: {', '.join(analysis.get('reasons', []))}",
                    'timestamp': datetime.utcnow().isoformat(),
                    'analysis': analysis
                }
                
                await self.earnings_tracker.record_trade(trade_data)
                
                # Take screenshot if enabled
                if Config.SCREENSHOT_ENABLED:
                    try:
                        screenshot_data = await self.screenshot.capture_trade_screenshot(trade_data)
                        if screenshot_data:
                            trade_data['screenshot'] = screenshot_data
                    except Exception as e:
                        self.logger.warning(f"Failed to capture screenshot: {e}")
                
                # Send notification via Telegram
                from telegram_bot import TelegramBot
                telegram_bot = TelegramBot()
                await telegram_bot.send_trade_notification(trade_data)
                
                # Reset consecutive losses on successful trade
                self.consecutive_losses = 0
                self.daily_trades += 1
                
                self.logger.info(f"Trade executed: {symbol} {signal} {position_size} lots")
                
        except Exception as e:
            self.logger.error(f"Error executing trade for {symbol}: {e}")
            
            # Increment consecutive losses on trade execution failure
            self.consecutive_losses += 1
    
    async def close_all_positions(self):
        """Close all open positions"""
        try:
            results = await self.fxopen_handler.close_all_positions()
            self.logger.info(f"Closed {len(results)} positions")
            return results
        except Exception as e:
            self.logger.error(f"Error closing all positions: {e}")
            raise
    
    async def _can_trade(self, account_info: Dict) -> bool:
        """Check if trading is allowed based on current conditions"""
        try:
            # Check account balance
            balance = float(account_info.get('Balance', 0))
            equity = float(account_info.get('Equity', 0))
            
            if balance <= 0 or equity <= 0:
                self.logger.warning("Insufficient account balance or equity")
                return False
            
            # Check margin level
            margin_level = float(account_info.get('MarginLevel', 0))
            if margin_level > 0 and margin_level < 200:  # Less than 200% margin level
                self.logger.warning(f"Low margin level: {margin_level:.2f}%")
                return False
            
            # Check daily trades limit
            if self.daily_trades >= 10:  # Max 10 trades per day
                self.logger.info("Daily trade limit reached")
                return False
            
            # Check consecutive losses
            if self.consecutive_losses >= Config.MAX_CONSECUTIVE_LOSSES:
                self.logger.warning(f"Too many consecutive losses: {self.consecutive_losses}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking trading conditions: {e}")
            return False
    
    async def _check_failsafe_conditions(self) -> bool:
        """Check failsafe conditions"""
        try:
            if not Config.ENABLE_FAILSAFE:
                return True
            
            return await self.failsafe.check_trading_conditions(
                trader=self,
                fxopen_handler=self.fxopen_handler,
                earnings_tracker=self.earnings_tracker
            )
            
        except Exception as e:
            self.logger.error(f"Error checking failsafe conditions: {e}")
            return False
    
    async def _check_daily_reset(self):
        """Check if we need to reset daily counters"""
        try:
            if self.start_time:
                current_date = datetime.utcnow().date()
                start_date = self.start_time.date()
                
                if current_date > start_date:
                    # Reset daily counters
                    self.daily_trades = 0
                    self.consecutive_losses = 0
                    self.start_time = datetime.utcnow()
                    self.logger.info("Daily counters reset")
                    
        except Exception as e:
            self.logger.error(f"Error checking daily reset: {e}")
