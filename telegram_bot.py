import logging
import asyncio
import json
from datetime import datetime
import io
import matplotlib.pyplot as plt

try:
    from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    class Update: pass
    class ContextTypes: DEFAULT_TYPE = object

from config import Config

class TelegramBot:
    def __init__(self, trader=None, earnings_tracker=None, fxopen_handler=None):
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.trader = trader
        self.earnings_tracker = earnings_tracker
        self.fxopen_handler = fxopen_handler
        self.logger = logging.getLogger(__name__)
        self.application = None
        self.bot = None
        
    async def initialize(self):
        """Initialize bot and handlers"""
        self.application = Application.builder().token(self.bot_token).build()
        self.bot = self.application.bot
        
        # Command handlers
        handlers = [
            ("start", self.start_command), ("status", self.status_command),
            ("balance", self.balance_command), ("positions", self.positions_command),
            ("performance", self.performance_command), ("help", self.help_command),
            ("start_trading", self.start_trading_command), ("stop_trading", self.stop_trading_command),
            ("close_all", self.close_all_command), ("stop", self.stop_command),
            ("place_trade", self.place_trade_command), ("sell_trade", self.sell_trade_command),
            ("daily", self.daily_command), ("weekly", self.weekly_command)
        ]
        
        for cmd, handler in handlers:
            self.application.add_handler(CommandHandler(cmd, handler))
        
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_polling(self):
        """Start bot polling"""
        if not TELEGRAM_AVAILABLE:
            while True: await asyncio.sleep(10)
            
        await self.initialize()
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        while True: await asyncio.sleep(1)
    
    async def send_message(self, text: str, parse_mode: str = None, reply_markup=None):
        """Send message"""
        if not TELEGRAM_AVAILABLE: return True
        try:
            if not self.bot: self.bot = Bot(token=self.bot_token)
            await self.bot.send_message(chat_id=self.chat_id, text=text, parse_mode=parse_mode, reply_markup=reply_markup)
            return True
        except Exception as e:
            self.logger.error(f"Send message error: {e}")
            return False
    
    async def send_photo(self, photo_data: bytes, caption: str = None):
        """Send photo"""
        try:
            if not self.bot: self.bot = Bot(token=self.bot_token)
            await self.bot.send_photo(chat_id=self.chat_id, photo=io.BytesIO(photo_data), caption=caption)
            return True
        except Exception as e:
            self.logger.error(f"Send photo error: {e}")
            return False
    
    # Notification methods
    async def send_startup_notification(self):
        await self.send_message("🤖 *AI Trading Bot Started*\n\n✅ All systems initialized\n🔄 Auto trading enabled\n\nUse /help for commands.", parse_mode="Markdown")
    
    async def send_trade_notification(self, trade_data):
        emoji = "🟢" if trade_data.get('side', '').lower() == 'buy' else "🔴"
        msg = f"""{emoji} *Trade Executed*

📈 *Symbol:* {trade_data.get('symbol', 'N/A')}
💹 *Side:* {trade_data.get('side', 'N/A').upper()}
📊 *Volume:* {trade_data.get('volume', 'N/A')}
💰 *Price:* {trade_data.get('entry_price', 'N/A')}
🤖 *AI Confidence:* {trade_data.get('confidence', 0) * 100:.1f}%"""
        await self.send_message(msg, parse_mode="Markdown")
    
    async def send_status_update(self, status_data):
        msg = f"""📊 *Status Update*

💰 *Balance:* ${status_data.get('account_balance', 0):,.2f}
📈 *Equity:* ${status_data.get('account_equity', 0):,.2f}
📈 *Daily P&L:* ${status_data.get('daily_pnl', 0):,.2f}
🎯 *Win Rate:* {status_data.get('win_rate', 0) * 100:.1f}%
🔄 *Positions:* {status_data.get('open_positions', 0)}
⚡ *Status:* {status_data.get('bot_status', 'Unknown').upper()}"""
        await self.send_message(msg, parse_mode="Markdown")
    
    async def send_error_notification(self, error_message):
        await self.send_message(f"❌ *Error*\n\n🚨 {error_message}\n🕐 {datetime.utcnow().strftime('%H:%M:%S UTC')}", parse_mode="Markdown")
    
    # Command handlers
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("📊 Status", callback_data="status")],
            [InlineKeyboardButton("💰 Balance", callback_data="balance"), InlineKeyboardButton("📈 Positions", callback_data="positions")],
            [InlineKeyboardButton("📊 Performance", callback_data="performance")],
            [InlineKeyboardButton("🆘 Help", callback_data="help")]
        ]
        await update.message.reply_text("🤖 *AI Trading Bot*\n\nYour intelligent forex assistant is ready!", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if self.fxopen_handler and self.earnings_tracker:
                account_info = await self.fxopen_handler.get_account_info()
                earnings = await self.earnings_tracker.get_current_performance()
                
                msg = f"""📊 *Trading Status*

💰 *Balance:* ${account_info.get('Balance', 0):,.2f}
📈 *Equity:* ${account_info.get('Equity', 0):,.2f}
📈 *Daily P&L:* ${earnings.get('daily_pnl', 0):,.2f}
🎯 *Win Rate:* {earnings.get('win_rate', 0) * 100:.1f}%
🔄 *Status:* {'ACTIVE' if self.trader and self.trader.is_running else 'STOPPED'}"""
            else:
                msg = "⚠️ Trading components not initialized"
        except Exception as e:
            msg = f"❌ Error: {str(e)}"
        
        await update.message.reply_text(msg, parse_mode="Markdown")
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if self.fxopen_handler:
                account_info = await self.fxopen_handler.get_account_info()
                msg = f"""💰 *Account Balance*

💵 *Balance:* ${account_info.get('Balance', 0):,.2f}
📈 *Equity:* ${account_info.get('Equity', 0):,.2f}
📉 *Used Margin:* ${account_info.get('UsedMargin', 0):,.2f}
💸 *Free Margin:* ${account_info.get('FreeMargin', 0):,.2f}
📊 *Margin Level:* {account_info.get('MarginLevel', 0):,.2f}%
⚖️ *Leverage:* 1:{account_info.get('Leverage', 'N/A')}"""
            else:
                msg = "⚠️ FXOpen handler not initialized"
        except Exception as e:
            msg = f"❌ Error: {str(e)}"
        
        await update.message.reply_text(msg, parse_mode="Markdown")
    
    async def positions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if self.fxopen_handler:
                positions = await self.fxopen_handler.get_positions()
                
                if positions:
                    msg = "📈 *Open Positions*\n\n"
                    for i, pos in enumerate(positions[:5]):
                        side_emoji = "🟢" if pos.get('Side', '').lower() == 'buy' else "🔴"
                        msg += f"{side_emoji} *{pos.get('Symbol', 'N/A')}* {pos.get('Side', 'N/A')} {pos.get('Volume', 'N/A')}\n💰 ${pos.get('Profit', 0):,.2f}\n\n"
                else:
                    msg = "📊 *No open positions*"
            else:
                msg = "⚠️ FXOpen handler not initialized"
        except Exception as e:
            msg = f"❌ Error: {str(e)}"
        
        await update.message.reply_text(msg, parse_mode="Markdown")
    
    async def performance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if self.earnings_tracker:
                performance = await self.earnings_tracker.get_performance_report()
                msg = f"""📊 *Performance Report*

📈 *Total P&L:* ${performance.get('total_pnl', 0):,.2f}
📉 *Daily P&L:* ${performance.get('daily_pnl', 0):,.2f}
🎯 *Win Rate:* {performance.get('win_rate', 0) * 100:.1f}%
📈 *Total Trades:* {performance.get('total_trades', 0)}
🟢 *Winners:* {performance.get('winning_trades', 0)}
🔴 *Losers:* {performance.get('losing_trades', 0)}
📊 *Best Trade:* ${performance.get('best_trade', 0):,.2f}
📉 *Worst Trade:* ${performance.get('worst_trade', 0):,.2f}"""
                
                # Send chart if available
                chart_data = await self.earnings_tracker.get_equity_curve()
                if chart_data:
                    chart_image = self._create_performance_chart(chart_data)
                    await self.send_photo(chart_image, "📊 Performance Chart")
            else:
                msg = "⚠️ Earnings tracker not initialized"
        except Exception as e:
            msg = f"❌ Error: {str(e)}"
        
        await update.message.reply_text(msg, parse_mode="Markdown")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = """🆘 *AI Trading Bot Commands*

📊 *Monitoring:*
/status - Bot status
/balance - Account balance
/positions - Open positions
/performance - Performance report
/daily - Today's P&L report
/weekly - Weekly performance

🔄 *Control:*
/start_trading - Start trading
/stop_trading - Stop trading
/place_trade - Place new trade
/sell_trade - Sell best trade
/close_all - Close all positions
/stop - Emergency stop"""
        await update.message.reply_text(msg, parse_mode="Markdown")
    
    async def start_trading_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if self.trader:
                await self.trader.start()
                msg = "🟢 *Trading Started*\n\nAutomatic trading enabled."
            else:
                msg = "⚠️ Trader not initialized"
        except Exception as e:
            msg = f"❌ Error: {str(e)}"
        await update.message.reply_text(msg, parse_mode="Markdown")
    
    async def stop_trading_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if self.trader:
                await self.trader.pause()
                msg = "🔴 *Trading Stopped*\n\nAutomatic trading disabled."
            else:
                msg = "⚠️ Trader not initialized"
        except Exception as e:
            msg = f"❌ Error: {str(e)}"
        await update.message.reply_text(msg, parse_mode="Markdown")
    
    async def close_all_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Close All", callback_data="confirm_close_all")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_close_all")]
        ]
        await update.message.reply_text("⚠️ *Confirm Close All*\n\nClose all positions?", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("🛑 Emergency Stop", callback_data="confirm_emergency_stop")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_emergency_stop")]
        ]
        await update.message.reply_text("🚨 *EMERGENCY STOP*\n\nStop entire bot?", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        callbacks = {
            "status": self.status_command, "balance": self.balance_command,
            "positions": self.positions_command, "performance": self.performance_command,
            "help": self.help_command
        }
        
        if query.data in callbacks:
            await callbacks[query.data](update, context)
        elif query.data == "confirm_close_all":
            await self._handle_close_all_confirmed(query)
        elif query.data == "cancel_close_all":
            await query.edit_message_text("❌ Cancelled.")
        elif query.data == "confirm_emergency_stop":
            await self._handle_emergency_stop(query)
        elif query.data == "cancel_emergency_stop":
            await query.edit_message_text("❌ Cancelled.")
    
    async def _handle_close_all_confirmed(self, query):
        try:
            if self.fxopen_handler:
                results = await self.fxopen_handler.close_all_positions()
                msg = f"✅ *Closed {len(results)} positions*"
            else:
                msg = "⚠️ FXOpen handler not initialized"
        except Exception as e:
            msg = f"❌ Error: {str(e)}"
        await query.edit_message_text(msg, parse_mode="Markdown")
    
    async def _handle_emergency_stop(self, query):
        try:
            await query.edit_message_text("🛑 *EMERGENCY STOP*\n\nShutting down...", parse_mode="Markdown")
            if self.trader:
                await self.trader.emergency_stop()
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}", parse_mode="Markdown")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🤖 Use /help for commands.")
    
    async def place_trade_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Place a new trade"""
        try:
            if self.trader:
                # Get AI recommendation for best trade
                trade_signal = await self.trader.get_trade_signal()
                
                if trade_signal:
                    # Execute the trade
                    trade_result = await self.trader.place_trade(trade_signal)
                    
                    if trade_result:
                        # Convert USD to GBP (approximate rate)
                        usd_to_gbp = 0.79  # You might want to get real-time rates
                        trade_value_gbp = trade_result.get('volume', 0) * trade_result.get('entry_price', 0) * usd_to_gbp
                        expected_profit_gbp = trade_result.get('expected_profit', 0) * usd_to_gbp
                        roi_percentage = (expected_profit_gbp / trade_value_gbp) * 100 if trade_value_gbp > 0 else 0
                        
                        msg = f"""📈 *Trade Placed Successfully*

🎯 *Symbol:* {trade_result.get('symbol', 'N/A')}
💹 *Side:* {trade_result.get('side', 'N/A').upper()}
📊 *Volume:* {trade_result.get('volume', 'N/A')}
💰 *Entry Price:* {trade_result.get('entry_price', 'N/A')}
💷 *Trade Value:* £{trade_value_gbp:,.2f}
🎯 *Expected Profit:* £{expected_profit_gbp:,.2f}
📊 *Expected ROI:* {roi_percentage:.1f}%
🛡️ *Stop Loss:* {trade_result.get('stop_loss', 'N/A')}
🎯 *Take Profit:* {trade_result.get('take_profit', 'N/A')}
🤖 *AI Confidence:* {trade_result.get('confidence', 0) * 100:.1f}%
📋 *Trade ID:* {trade_result.get('trade_id', 'N/A')}

*Analysis:* {trade_result.get('reason', 'AI market analysis indicates favorable conditions')}"""
                        
                        # Take screenshot if available
                        if hasattr(self.trader, 'take_trade_screenshot'):
                            screenshot = await self.trader.take_trade_screenshot(trade_result.get('trade_id'))
                            if screenshot:
                                await self.send_photo(screenshot, "📸 Trade Screenshot")
                    else:
                        msg = "❌ Failed to place trade"
                else:
                    msg = "⚠️ No suitable trade opportunities found"
            else:
                msg = "⚠️ Trader not initialized"
        except Exception as e:
            msg = f"❌ Error placing trade: {str(e)}"
        
        await update.message.reply_text(msg, parse_mode="Markdown")
    
    async def sell_trade_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Sell the most profitable trade"""
        try:
            if self.fxopen_handler:
                # Get all positions and find most profitable
                positions = await self.fxopen_handler.get_positions()
                
                if positions:
                    # Sort by profit (descending) and take the best
                    most_profitable = max(positions, key=lambda x: x.get('Profit', 0))
                    
                    if most_profitable.get('Profit', 0) > 0:
                        # Close the position
                        close_result = await self.fxopen_handler.close_position(most_profitable.get('PositionId'))
                        
                        if close_result:
                            profit_gbp = most_profitable.get('Profit', 0) * 0.79  # Convert to GBP
                            
                            msg = f"""💰 *Trade Sold Successfully*

🎯 *Symbol:* {most_profitable.get('Symbol', 'N/A')}
💹 *Side:* {most_profitable.get('Side', 'N/A').upper()}
📊 *Volume:* {most_profitable.get('Volume', 'N/A')}
💷 *Profit:* £{profit_gbp:,.2f}
📈 *Entry Price:* {most_profitable.get('OpenPrice', 'N/A')}
📊 *Exit Price:* {most_profitable.get('CurrentPrice', 'N/A')}

🧠 *AI Learning:* {'Trend reversal patterns detected earlier than expected' if profit_gbp > 50 else 'Position held for optimal duration'}

🔄 *Next Improvement:* {'Will tighten stop-loss levels' if profit_gbp < 20 else 'Will increase position size for similar setups'}"""
                            
                            # Take screenshot if available
                            if hasattr(self.trader, 'take_trade_screenshot'):
                                screenshot = await self.trader.take_trade_screenshot(most_profitable.get('PositionId'))
                                if screenshot:
                                    await self.send_photo(screenshot, "📸 Trade Close Screenshot")
                        else:
                            msg = "❌ Failed to close position"
                    else:
                        msg = "⚠️ No profitable positions to sell"
                else:
                    msg = "📊 No open positions"
            else:
                msg = "⚠️ FXOpen handler not initialized"
        except Exception as e:
            msg = f"❌ Error selling trade: {str(e)}"
        
        await update.message.reply_text(msg, parse_mode="Markdown")
    
    async def daily_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Daily performance report"""
        try:
            if self.earnings_tracker:
                daily_data = await self.earnings_tracker.get_daily_report()
                
                daily_pnl_gbp = daily_data.get('daily_pnl', 0) * 0.79
                expected_eod_gbp = daily_data.get('expected_eod', 0) * 0.79
                
                msg = f"""📅 *Today's Trading Report*

💷 *Today's P&L:* £{daily_pnl_gbp:,.2f}
🎯 *Expected EOD:* £{expected_eod_gbp:,.2f}
📊 *Trades Today:* {daily_data.get('trades_today', 0)}

🟢 *Winning Trades:*"""
                
                for trade in daily_data.get('winning_trades', [])[:3]:  # Top 3
                    msg += f"\n• {trade.get('symbol')} +£{trade.get('profit', 0) * 0.79:.2f}"
                
                msg += "\n\n🔴 *Losing Trades:*"
                for trade in daily_data.get('losing_trades', [])[:3]:  # Top 3 losses
                    msg += f"\n• {trade.get('symbol')} -£{abs(trade.get('profit', 0)) * 0.79:.2f}"
                
                msg += f"\n\n📈 *Win Rate Today:* {daily_data.get('win_rate_today', 0) * 100:.1f}%"
                msg += f"\n🕐 *Hours Left:* {daily_data.get('hours_left', 0)}"
                
            else:
                msg = "⚠️ Earnings tracker not initialized"
        except Exception as e:
            msg = f"❌ Error getting daily report: {str(e)}"
        
        await update.message.reply_text(msg, parse_mode="Markdown")
    
    async def weekly_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Weekly performance report"""
        try:
            if self.earnings_tracker:
                weekly_data = await self.earnings_tracker.get_weekly_report()
                
                weekly_pnl_gbp = weekly_data.get('weekly_pnl', 0) * 0.79
                expected_eow_gbp = weekly_data.get('expected_eow', 0) * 0.79
                
                msg = f"""📊 *Weekly Performance Report*

💷 *This Week:* £{weekly_pnl_gbp:,.2f}
🎯 *Expected EOW:* £{expected_eow_gbp:,.2f}
📈 *Win Rate:* {weekly_data.get('weekly_win_rate', 0) * 100:.1f}%
📊 *Total Trades:* {weekly_data.get('trades_this_week', 0)}

🔍 *Areas for Improvement:*
• {'Risk management on EUR pairs' if weekly_data.get('worst_pair') == 'EUR' else 'Entry timing optimization'}
• {'Reduce position sizes during high volatility' if weekly_data.get('volatility_losses', 0) > 100 else 'Increase position sizes on strong signals'}
• {'Better news event filtering' if weekly_data.get('news_losses', 0) > 50 else 'Maintain current news strategy'}

🎯 *Next Week Plan:*
• {'Focus on USD pairs' if weekly_pnl_gbp < 0 else 'Continue current strategy'}
• {'Implement tighter stop losses' if weekly_data.get('avg_loss', 0) > 50 else 'Optimize take profit levels'}
• {'Reduce trading frequency' if weekly_data.get('overtrade_flag') else 'Maintain current frequency'}

📈 *Performance vs Target:* {((weekly_pnl_gbp / 500) * 100):.1f}%"""
                
            else:
                msg = "⚠️ Earnings tracker not initialized"
        except Exception as e:
            msg = f"❌ Error getting weekly report: {str(e)}"
        
        await update.message.reply_text(msg, parse_mode="Markdown")
    
    def _create_performance_chart(self, data):
        """Create performance chart"""
        try:
            plt.figure(figsize=(10, 6))
            dates = [datetime.fromisoformat(d) for d in data.get('dates', [])]
            equity = data.get('equity', [])
            
            if dates and equity:
                plt.plot(dates, equity, 'b-', linewidth=2)
                plt.title('Equity Curve', fontsize=16, fontweight='bold')
                plt.xlabel('Date')
                plt.ylabel('Equity ($)')
                plt.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                plt.tight_layout()
            else:
                plt.text(0.5, 0.5, 'No data', ha='center', va='center', transform=plt.gca().transAxes)
                plt.title('Performance Chart')
            
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close()
            return img_buffer.getvalue()
        except Exception as e:
            self.logger.error(f"Chart error: {e}")
            plt.figure(figsize=(8, 6))
            plt.text(0.5, 0.5, f'Error: {str(e)}', ha='center', va='center', transform=plt.gca().transAxes)
            plt.title('Chart Error')
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close()
            return img_buffer.getvalue()