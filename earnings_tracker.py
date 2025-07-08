"""
Earnings and Performance Tracking Module
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import os
import numpy as np

class EarningsTracker:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.trades_file = "data/trades.json"
        self.performance_file = "data/performance.json"
        self.trades = []
        self.daily_performance = {}
        
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Load existing data
        asyncio.create_task(self._load_data())
    
    async def _load_data(self):
        """Load existing trades and performance data"""
        try:
            # Load trades
            if os.path.exists(self.trades_file):
                with open(self.trades_file, 'r') as f:
                    self.trades = json.load(f)
                self.logger.info(f"Loaded {len(self.trades)} historical trades")
            
            # Load performance data
            if os.path.exists(self.performance_file):
                with open(self.performance_file, 'r') as f:
                    self.daily_performance = json.load(f)
                self.logger.info("Loaded historical performance data")
                
        except Exception as e:
            self.logger.error(f"Error loading historical data: {e}")
            self.trades = []
            self.daily_performance = {}
    
    async def _save_data(self):
        """Save trades and performance data"""
        try:
            # Save trades
            with open(self.trades_file, 'w') as f:
                json.dump(self.trades, f, indent=2)
            
            # Save performance data
            with open(self.performance_file, 'w') as f:
                json.dump(self.daily_performance, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving data: {e}")
    
    async def record_trade(self, trade_data: Dict[str, Any]):
        """Record a new trade"""
        try:
            # Add trade ID and timestamp if not present
            if 'trade_id' not in trade_data:
                trade_data['trade_id'] = f"trade_{len(self.trades) + 1}_{int(datetime.utcnow().timestamp())}"
            
            if 'timestamp' not in trade_data:
                trade_data['timestamp'] = datetime.utcnow().isoformat()
            
            # Add initial status
            trade_data['status'] = 'open'
            trade_data['open_time'] = trade_data['timestamp']
            trade_data['pnl'] = 0.0
            
            # Store the trade
            self.trades.append(trade_data)
            
            # Save data
            await self._save_data()
            
            self.logger.info(f"Trade recorded: {trade_data['symbol']} {trade_data['side']} {trade_data['volume']}")
            
        except Exception as e:
            self.logger.error(f"Error recording trade: {e}")
    
    async def update_trade_pnl(self, trade_id: str, current_pnl: float, current_price: float = None):
        """Update trade P&L"""
        try:
            for trade in self.trades:
                if trade.get('trade_id') == trade_id:
                    trade['pnl'] = current_pnl
                    if current_price:
                        trade['current_price'] = current_price
                    trade['last_update'] = datetime.utcnow().isoformat()
                    break
            
            # Save updated data
            await self._save_data()
            
        except Exception as e:
            self.logger.error(f"Error updating trade P&L: {e}")
    
    async def close_trade(self, trade_id: str, close_price: float, close_time: str = None, final_pnl: float = None):
        """Mark a trade as closed"""
        try:
            for trade in self.trades:
                if trade.get('trade_id') == trade_id:
                    trade['status'] = 'closed'
                    trade['close_price'] = close_price
                    trade['close_time'] = close_time or datetime.utcnow().isoformat()
                    
                    if final_pnl is not None:
                        trade['pnl'] = final_pnl
                    
                    # Calculate trade duration
                    if 'open_time' in trade:
                        try:
                            open_dt = datetime.fromisoformat(trade['open_time'].replace('Z', '+00:00'))
                            close_dt = datetime.fromisoformat(trade['close_time'].replace('Z', '+00:00'))
                            duration = (close_dt - open_dt).total_seconds() / 3600  # hours
                            trade['duration_hours'] = duration
                        except:
                            pass
                    
                    break
            
            # Update daily performance
            await self._update_daily_performance()
            
            # Save data
            await self._save_data()
            
            self.logger.info(f"Trade closed: {trade_id} with P&L: {final_pnl}")
            
        except Exception as e:
            self.logger.error(f"Error closing trade: {e}")
    
    async def _update_daily_performance(self):
        """Update daily performance metrics"""
        try:
            today = datetime.utcnow().date().isoformat()
            
            # Calculate daily performance
            daily_trades = [t for t in self.trades if t.get('open_time', '').startswith(today)]
            closed_trades = [t for t in daily_trades if t.get('status') == 'closed']
            
            daily_pnl = sum(t.get('pnl', 0) for t in closed_trades)
            winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
            losing_trades = [t for t in closed_trades if t.get('pnl', 0) < 0]
            
            self.daily_performance[today] = {
                'date': today,
                'total_trades': len(daily_trades),
                'closed_trades': len(closed_trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'daily_pnl': daily_pnl,
                'win_rate': len(winning_trades) / max(len(closed_trades), 1),
                'best_trade': max([t.get('pnl', 0) for t in closed_trades], default=0),
                'worst_trade': min([t.get('pnl', 0) for t in closed_trades], default=0),
                'avg_trade': daily_pnl / max(len(closed_trades), 1)
            }
            
        except Exception as e:
            self.logger.error(f"Error updating daily performance: {e}")
    
    async def get_current_performance(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        try:
            closed_trades = [t for t in self.trades if t.get('status') == 'closed']
            open_trades = [t for t in self.trades if t.get('status') == 'open']
            
            if not closed_trades:
                return {
                    'total_pnl': 0.0,
                    'daily_pnl': 0.0,
                    'weekly_pnl': 0.0,
                    'win_rate': 0.0,
                    'total_trades': 0,
                    'open_positions': len(open_trades)
                }
            
            # Calculate total P&L
            total_pnl = sum(t.get('pnl', 0) for t in closed_trades)
            
            # Calculate daily P&L
            today = datetime.utcnow().date()
            daily_trades = [t for t in closed_trades 
                           if datetime.fromisoformat(t.get('close_time', '')).date() == today]
            daily_pnl = sum(t.get('pnl', 0) for t in daily_trades)
            
            # Calculate weekly P&L
            week_ago = today - timedelta(days=7)
            weekly_trades = [t for t in closed_trades 
                            if datetime.fromisoformat(t.get('close_time', '')).date() >= week_ago]
            weekly_pnl = sum(t.get('pnl', 0) for t in weekly_trades)
            
            # Calculate win rate
            winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
            win_rate = len(winning_trades) / len(closed_trades)
            
            return {
                'total_pnl': total_pnl,
                'daily_pnl': daily_pnl,
                'weekly_pnl': weekly_pnl,
                'win_rate': win_rate,
                'total_trades': len(closed_trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(closed_trades) - len(winning_trades),
                'open_positions': len(open_trades),
                'avg_trade': total_pnl / len(closed_trades) if closed_trades else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting current performance: {e}")
            return {'error': str(e)}
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        try:
            current_perf = await self.get_current_performance()
            closed_trades = [t for t in self.trades if t.get('status') == 'closed']
            
            if not closed_trades:
                return current_perf
            
            # Calculate additional metrics
            pnl_values = [t.get('pnl', 0) for t in closed_trades]
            
            # Best and worst trades
            best_trade = max(pnl_values)
            worst_trade = min(pnl_values)
            
            # Profit factor (gross profit / gross loss)
            winning_pnl = [p for p in pnl_values if p > 0]
            losing_pnl = [abs(p) for p in pnl_values if p < 0]
            
            gross_profit = sum(winning_pnl)
            gross_loss = sum(losing_pnl)
            profit_factor = gross_profit / max(gross_loss, 0.01)
            
            # Calculate Sharpe ratio (simplified)
            if len(pnl_values) > 1:
                returns_std = np.std(pnl_values)
                sharpe_ratio = np.mean(pnl_values) / max(returns_std, 0.01)
            else:
                sharpe_ratio = 0.0
            
            # Maximum drawdown
            max_drawdown = await self._calculate_max_drawdown()
            
            # Update current performance with additional metrics
            current_perf.update({
                'best_trade': best_trade,
                'worst_trade': worst_trade,
                'profit_factor': profit_factor,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'gross_profit': gross_profit,
                'gross_loss': gross_loss
            })
            
            return current_perf
            
        except Exception as e:
            self.logger.error(f"Error generating performance report: {e}")
            return {'error': str(e)}
    
    async def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown"""
        try:
            closed_trades = [t for t in self.trades if t.get('status') == 'closed']
            if not closed_trades:
                return 0.0
            
            # Sort trades by close time
            sorted_trades = sorted(closed_trades, key=lambda x: x.get('close_time', ''))
            
            # Calculate running balance
            balance = 0
            max_balance = 0
            max_drawdown = 0
            
            for trade in sorted_trades:
                balance += trade.get('pnl', 0)
                max_balance = max(max_balance, balance)
                drawdown = max_balance - balance
                max_drawdown = max(max_drawdown, drawdown)
            
            return max_drawdown
            
        except Exception as e:
            self.logger.error(f"Error calculating max drawdown: {e}")
            return 0.0
    
    async def get_equity_curve(self) -> Dict[str, Any]:
        """Get equity curve data for charting"""
        try:
            closed_trades = [t for t in self.trades if t.get('status') == 'closed']
            if not closed_trades:
                return {'dates': [], 'equity': [], 'trades': []}
            
            # Sort trades by close time
            sorted_trades = sorted(closed_trades, key=lambda x: x.get('close_time', ''))
            
            dates = []
            equity = []
            balance = 1000  # Starting balance assumption
            
            for trade in sorted_trades:
                close_time = trade.get('close_time', '')
                if close_time:
                    balance += trade.get('pnl', 0)
                    dates.append(close_time)
                    equity.append(balance)
            
            return {
                'dates': dates,
                'equity': equity,
                'trades': len(sorted_trades)
            }
            
        except Exception as e:
            self.logger.error(f"Error generating equity curve: {e}")
            return {'dates': [], 'equity': [], 'error': str(e)}
    
    async def get_symbol_performance(self, symbol: str) -> Dict[str, Any]:
        """Get performance metrics for a specific symbol"""
        try:
            symbol_trades = [t for t in self.trades if t.get('symbol') == symbol and t.get('status') == 'closed']
            
            if not symbol_trades:
                return {
                    'symbol': symbol,
                    'total_trades': 0,
                    'total_pnl': 0.0,
                    'win_rate': 0.0
                }
            
            total_pnl = sum(t.get('pnl', 0) for t in symbol_trades)
            winning_trades = [t for t in symbol_trades if t.get('pnl', 0) > 0]
            win_rate = len(winning_trades) / len(symbol_trades)
            
            return {
                'symbol': symbol,
                'total_trades': len(symbol_trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(symbol_trades) - len(winning_trades),
                'total_pnl': total_pnl,
                'win_rate': win_rate,
                'avg_trade': total_pnl / len(symbol_trades),
                'best_trade': max([t.get('pnl', 0) for t in symbol_trades]),
                'worst_trade': min([t.get('pnl', 0) for t in symbol_trades])
            }
            
        except Exception as e:
            self.logger.error(f"Error getting symbol performance for {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}
    
    async def get_monthly_performance(self) -> Dict[str, Any]:
        """Get monthly performance breakdown"""
        try:
            closed_trades = [t for t in self.trades if t.get('status') == 'closed']
            monthly_data = {}
            
            for trade in closed_trades:
                close_time = trade.get('close_time', '')
                if close_time:
                    try:
                        date = datetime.fromisoformat(close_time.replace('Z', '+00:00'))
                        month_key = date.strftime('%Y-%m')
                        
                        if month_key not in monthly_data:
                            monthly_data[month_key] = {
                                'month': month_key,
                                'trades': 0,
                                'pnl': 0.0,
                                'winning_trades': 0,
                                'losing_trades': 0
                            }
                        
                        monthly_data[month_key]['trades'] += 1
                        monthly_data[month_key]['pnl'] += trade.get('pnl', 0)
                        
                        if trade.get('pnl', 0) > 0:
                            monthly_data[month_key]['winning_trades'] += 1
                        else:
                            monthly_data[month_key]['losing_trades'] += 1
                            
                    except:
                        continue
            
            # Calculate win rates
            for month_data in monthly_data.values():
                total_trades = month_data['trades']
                if total_trades > 0:
                    month_data['win_rate'] = month_data['winning_trades'] / total_trades
                else:
                    month_data['win_rate'] = 0.0
            
            return {
                'monthly_breakdown': list(monthly_data.values()),
                'total_months': len(monthly_data)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting monthly performance: {e}")
            return {'error': str(e)}
    
    async def export_trades_csv(self, filename: str = None) -> str:
        """Export trades to CSV format"""
        try:
            import csv
            
            if not filename:
                filename = f"trades_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            
            filepath = f"data/{filename}"
            
            with open(filepath, 'w', newline='') as csvfile:
                if not self.trades:
                    return filepath
                
                fieldnames = self.trades[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for trade in self.trades:
                    writer.writerow(trade)
            
            self.logger.info(f"Trades exported to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error exporting trades to CSV: {e}")
            raise
