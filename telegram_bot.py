"""
Telegram Bot for Trading Bot Monitoring and Control
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import io
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

try:
    from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    # Fallback if telegram is not available
    TELEGRAM_AVAILABLE = False
    print("Warning: Telegram library not available. Bot will run in simulation mode.")
    
    # Create dummy classes for type hints when telegram is not available
    class Update:
        pass
    
    class ContextTypes:
        DEFAULT_TYPE = object

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
        self.telegram_available = TELEGRAM_AVAILABLE
        
    async def initialize(self):
        """Initialize the Telegram bot"""
        self.application = Application.builder().token(self.bot_token).build()
        self.bot = self.application.bot
        
        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("balance", self.balance_command))
        self.application.add_handler(CommandHandler("positions", self.positions_command))
        self.application.add_handler(CommandHandler("performance", self.performance_command))
        self.application.add_handler(CommandHandler("stop", self.stop_command))
        self.application.add_handler(CommandHandler("start_trading", self.start_trading_command))
        self.application.add_handler(CommandHandler("stop_trading", self.stop_trading_command))
        self.application.add_handler(CommandHandler("close_all", self.close_all_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Add callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Add message handler for other messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def test_connection(self) -> bool:
        """Test Telegram bot connection"""
        if not self.telegram_available:
            self.logger.warning("Telegram not available - running in simulation mode")
            return True
            
        try:
            if not self.bot:
                self.bot = Bot(token=self.bot_token)
            
            me = await self.bot.get_me()
            self.logger.info(f"Telegram bot connected: @{me.username}")
            return True
        except Exception as e:
            self.logger.error(f"Telegram connection test failed: {e}")
            raise
    
    async def start_polling(self):
        """Start the Telegram bot polling"""
        if not self.telegram_available:
            self.logger.info("Telegram polling disabled - running in simulation mode")
            # Keep the method running but don't do actual polling
            while True:
                await asyncio.sleep(10)
            return
            
        try:
            if not self.application:
                await self.initialize()
            
            self.logger.info("Starting Telegram bot polling...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            # Keep the bot running
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Telegram bot polling error: {e}")
            raise
    
    async def stop(self):
        """Stop the Telegram bot"""
        try:
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                
            self.logger.info("Telegram bot stopped")
        except Exception as e:
            self.logger.error(f"Error stopping Telegram bot: {e}")
    
    async def send_message(self, text: str, parse_mode: str = None, reply_markup=None) -> bool:
        """Send message to the configured chat"""
        if not self.telegram_available:
            self.logger.info(f"Telegram message (simulation): {text[:100]}...")
            return True
            
        try:
            if not self.bot:
                self.bot = Bot(token=self.bot_token)
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    async def send_photo(self, photo_data: bytes, caption: str = None) -> bool:
        """Send photo to the configured chat"""
        try:
            if not self.bot:
                self.bot = Bot(token=self.bot_token)
            
            await self.bot.send_photo(
                chat_id=self.chat_id,
                photo=io.BytesIO(photo_data),
                caption=caption
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to send Telegram photo: {e}")
            return False
    
    async def send_startup_notification(self):
        """Send bot startup notification"""
        message = """
🤖 *AI Trading Bot Started*

✅ Bot is now running and monitoring markets
📊 All systems initialized successfully
🔄 Automatic trading is enabled

Use /help to see available commands.
        """
        await self.send_message(message, parse_mode="Markdown")
    
    async def send_shutdown_notification(self):
        """Send bot shutdown notification"""
        message = """
🛑 *AI Trading Bot Stopped*

❌ Bot has been shut down
📊 All monitoring stopped
⚠️ Manual intervention may be required

Bot will remain offline until manually restarted.
        """
        await self.send_message(message, parse_mode="Markdown")
    
    async def send_trade_notification(self, trade_data: Dict[str, Any]):
        """Send trade execution notification"""
        emoji = "🟢" if trade_data.get('side', '').lower() == 'buy' else "🔴"
        
        message = f"""
{emoji} *Trade Executed*

📈 *Symbol:* {trade_data.get('symbol', 'N/A')}
💹 *Side:* {trade_data.get('side', 'N/A').upper()}
📊 *Volume:* {trade_data.get('volume', 'N/A')}
💰 *Entry Price:* {trade_data.get('entry_price', 'N/A')}
🛡️ *Stop Loss:* {trade_data.get('stop_loss', 'N/A')}
🎯 *Take Profit:* {trade_data.get('take_profit', 'N/A')}
🤖 *AI Confidence:* {trade_data.get('confidence', 0) * 100:.1f}%

*Reason:* {trade_data.get('reason', 'AI Analysis')}
        """
        await self.send_message(message, parse_mode="Markdown")
    
    async def send_status_update(self, status_data: Dict[str, Any]):
        """Send periodic status update"""
        message = f"""
📊 *Trading Bot Status Update*

💰 *Balance:* ${status_data.get('account_balance', 0):,.2f}
📈 *Equity:* ${status_data.get('account_equity', 0):,.2f}
📉 *Used Margin:* ${status_data.get('used_margin', 0):,.2f}
💸 *Free Margin:* ${status_data.get('free_margin', 0):,.2f}

📈 *Daily P&L:* ${status_data.get('daily_pnl', 0):,.2f}
📊 *Total P&L:* ${status_data.get('total_pnl', 0):,.2f}
🎯 *Win Rate:* {status_data.get('win_rate', 0) * 100:.1f}%

🔄 *Open Positions:* {status_data.get('open_positions', 0)}
⚡ *Status:* {status_data.get('bot_status', 'Unknown').upper()}

🕐 *Updated:* {datetime.utcnow().strftime('%H:%M:%S UTC')}
        """
        await self.send_message(message, parse_mode="Markdown")
    
    async def send_error_notification(self, error_message: str):
        """Send error notification"""
        message = f"""
❌ *Trading Bot Error*

🚨 *Error:* {error_message}
🕐 *Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

Please check the bot logs for more details.
        """
        await self.send_message(message, parse_mode="Markdown")
    
    async def send_health_alert(self, health_data: Dict[str, Any]):
        """Send system health alert"""
        status_emoji = "🚨" if health_data.get('critical') else "⚠️"
        
        message = f"""
{status_emoji} *System Health Alert*

🔍 *Status:* {'CRITICAL' if health_data.get('critical') else 'WARNING'}
📊 *Issues:* {len(health_data.get('issues', []))}

*Problems Detected:*
"""
        
        for issue in health_data.get('issues', []):
            message += f"• {issue}\n"
        
        message += f"\n🕐 *Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        await self.send_message(message, parse_mode="Markdown")
    
    # Command handlers
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        keyboard = [
            [InlineKeyboardButton("📊 Status", callback_data="status")],
            [InlineKeyboardButton("💰 Balance", callback_data="balance"),
             InlineKeyboardButton("📈 Positions", callback_data="positions")],
            [InlineKeyboardButton("📊 Performance", callback_data="performance")],
            [InlineKeyboardButton("🆘 Help", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = """
🤖 *Welcome to AI Trading Bot*

Your intelligent forex trading assistant is ready!

Use the buttons below or type commands directly:
        """
        
        await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            if self.fxopen_handler and self.earnings_tracker:
                account_info = await self.fxopen_handler.get_account_info()
                earnings = await self.earnings_tracker.get_current_performance()
                
                message = f"""
📊 *Trading Bot Status*

💰 *Balance:* ${account_info.get('Balance', 0):,.2f}
📈 *Equity:* ${account_info.get('Equity', 0):,.2f}
📉 *Margin:* ${account_info.get('UsedMargin', 0):,.2f}

📈 *Daily P&L:* ${earnings.get('daily_pnl', 0):,.2f}
🎯 *Win Rate:* {earnings.get('win_rate', 0) * 100:.1f}%

🔄 *Bot Status:* {'ACTIVE' if self.trader and self.trader.is_running else 'STOPPED'}
                """
            else:
                message = "⚠️ Trading components not fully initialized"
                
        except Exception as e:
            message = f"❌ Error getting status: {str(e)}"
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command"""
        try:
            if self.fxopen_handler:
                account_info = await self.fxopen_handler.get_account_info()
                
                message = f"""
💰 *Account Balance Details*

💵 *Balance:* ${account_info.get('Balance', 0):,.2f}
📈 *Equity:* ${account_info.get('Equity', 0):,.2f}
📉 *Used Margin:* ${account_info.get('UsedMargin', 0):,.2f}
💸 *Free Margin:* ${account_info.get('FreeMargin', 0):,.2f}
📊 *Margin Level:* {account_info.get('MarginLevel', 0):,.2f}%

🏦 *Account:* {account_info.get('Login', 'N/A')}
💱 *Currency:* {account_info.get('Currency', 'N/A')}
⚖️ *Leverage:* 1:{account_info.get('Leverage', 'N/A')}
                """
            else:
                message = "⚠️ FXOpen handler not initialized"
                
        except Exception as e:
            message = f"❌ Error getting balance: {str(e)}"
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def positions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command"""
        try:
            if self.fxopen_handler:
                positions = await self.fxopen_handler.get_positions()
                
                if positions:
                    message = "📈 *Open Positions*\n\n"
                    
                    for i, pos in enumerate(positions[:10]):  # Limit to 10 positions
                        side_emoji = "🟢" if pos.get('Side', '').lower() == 'buy' else "🔴"
                        
                        message += f"""
{side_emoji} *Position {i+1}*
📊 *Symbol:* {pos.get('Symbol', 'N/A')}
💹 *Side:* {pos.get('Side', 'N/A')}
📈 *Volume:* {pos.get('Volume', 'N/A')}
💰 *Entry:* {pos.get('OpenPrice', 'N/A')}
📊 *Current:* {pos.get('CurrentPrice', 'N/A')}
💸 *P&L:* ${pos.get('Profit', 0):,.2f}

"""
                else:
                    message = "📊 *No open positions*"
            else:
                message = "⚠️ FXOpen handler not initialized"
                
        except Exception as e:
            message = f"❌ Error getting positions: {str(e)}"
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def performance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /performance command"""
        try:
            if self.earnings_tracker:
                performance = await self.earnings_tracker.get_performance_report()
                
                message = f"""
📊 *Performance Report*

📈 *Total P&L:* ${performance.get('total_pnl', 0):,.2f}
📉 *Daily P&L:* ${performance.get('daily_pnl', 0):,.2f}
📊 *Weekly P&L:* ${performance.get('weekly_pnl', 0):,.2f}

🎯 *Win Rate:* {performance.get('win_rate', 0) * 100:.1f}%
📈 *Total Trades:* {performance.get('total_trades', 0)}
🟢 *Winning Trades:* {performance.get('winning_trades', 0)}
🔴 *Losing Trades:* {performance.get('losing_trades', 0)}

📊 *Best Trade:* ${performance.get('best_trade', 0):,.2f}
📉 *Worst Trade:* ${performance.get('worst_trade', 0):,.2f}
📈 *Average Trade:* ${performance.get('avg_trade', 0):,.2f}

🏆 *Profit Factor:* {performance.get('profit_factor', 0):.2f}
📊 *Sharpe Ratio:* {performance.get('sharpe_ratio', 0):.2f}
                """
                
                # Generate and send performance chart
                chart_data = await self.earnings_tracker.get_equity_curve()
                if chart_data:
                    chart_image = self._create_performance_chart(chart_data)
                    await self.send_photo(chart_image, "📊 Performance Chart")
                    
            else:
                message = "⚠️ Earnings tracker not initialized"
                
        except Exception as e:
            message = f"❌ Error getting performance: {str(e)}"
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        message = """
🆘 *AI Trading Bot Commands*

📊 *Monitoring:*
/status - Current bot status
/balance - Account balance details
/positions - Open positions
/performance - Performance report

🔄 *Control:*
/start_trading - Start automatic trading
/stop_trading - Stop automatic trading
/close_all - Close all positions

ℹ️ *Information:*
/help - Show this help message

⚠️ *Emergency:*
/stop - Emergency stop (stops entire bot)

The bot sends automatic updates every few minutes with account status and trade notifications.
        """
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def start_trading_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start_trading command"""
        try:
            if self.trader:
                await self.trader.start()
                message = "🟢 *Trading Started*\n\nAutomatic trading is now enabled."
            else:
                message = "⚠️ Trader not initialized"
        except Exception as e:
            message = f"❌ Error starting trading: {str(e)}"
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def stop_trading_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop_trading command"""
        try:
            if self.trader:
                await self.trader.pause()
                message = "🔴 *Trading Stopped*\n\nAutomatic trading is now disabled."
            else:
                message = "⚠️ Trader not initialized"
        except Exception as e:
            message = f"❌ Error stopping trading: {str(e)}"
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def close_all_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /close_all command"""
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Close All", callback_data="confirm_close_all")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_close_all")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "⚠️ *Confirm Close All Positions*\n\nAre you sure you want to close all open positions?"
        await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command (emergency stop)"""
        keyboard = [
            [InlineKeyboardButton("🛑 Yes, Emergency Stop", callback_data="confirm_emergency_stop")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_emergency_stop")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "🚨 *EMERGENCY STOP CONFIRMATION*\n\nThis will stop the entire bot. Are you sure?"
        await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "status":
            await self.status_command(update, context)
        elif data == "balance":
            await self.balance_command(update, context)
        elif data == "positions":
            await self.positions_command(update, context)
        elif data == "performance":
            await self.performance_command(update, context)
        elif data == "help":
            await self.help_command(update, context)
        elif data == "confirm_close_all":
            await self._handle_close_all_confirmed(query)
        elif data == "cancel_close_all":
            await query.edit_message_text("❌ Close all positions cancelled.")
        elif data == "confirm_emergency_stop":
            await self._handle_emergency_stop(query)
        elif data == "cancel_emergency_stop":
            await query.edit_message_text("❌ Emergency stop cancelled.")
    
    async def _handle_close_all_confirmed(self, query):
        """Handle confirmed close all positions"""
        try:
            if self.fxopen_handler:
                results = await self.fxopen_handler.close_all_positions()
                message = f"✅ *Positions Closed*\n\nClosed {len(results)} positions successfully."
            else:
                message = "⚠️ FXOpen handler not initialized"
        except Exception as e:
            message = f"❌ Error closing positions: {str(e)}"
        
        await query.edit_message_text(message, parse_mode="Markdown")
    
    async def _handle_emergency_stop(self, query):
        """Handle emergency stop"""
        try:
            message = "🛑 *EMERGENCY STOP INITIATED*\n\nBot is shutting down..."
            await query.edit_message_text(message, parse_mode="Markdown")
            
            # Trigger bot shutdown
            if self.trader:
                await self.trader.emergency_stop()
                
        except Exception as e:
            message = f"❌ Error during emergency stop: {str(e)}"
            await query.edit_message_text(message, parse_mode="Markdown")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle non-command messages"""
        message = "🤖 I'm an AI trading bot. Use /help to see available commands."
        await update.message.reply_text(message)
    
    def _create_performance_chart(self, data: Dict[str, Any]) -> bytes:
        """Create performance chart image"""
        try:
            plt.figure(figsize=(10, 6))
            
            # Extract data
            dates = [datetime.fromisoformat(d) for d in data.get('dates', [])]
            equity = data.get('equity', [])
            
            if dates and equity:
                plt.plot(dates, equity, color='blue', linewidth=2)
                plt.title('Account Equity Curve', fontsize=16, fontweight='bold')
                plt.xlabel('Date')
                plt.ylabel('Equity ($)')
                plt.grid(True, alpha=0.3)
                
                # Format x-axis
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
                plt.xticks(rotation=45)
                
                plt.tight_layout()
                
                # Save to bytes
                img_buffer = io.BytesIO()
                plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
                img_buffer.seek(0)
                
                plt.close()
                return img_buffer.getvalue()
            else:
                # Create empty chart
                plt.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=plt.gca().transAxes)
                plt.title('Performance Chart')
                
                img_buffer = io.BytesIO()
                plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
                img_buffer.seek(0)
                
                plt.close()
                return img_buffer.getvalue()
                
        except Exception as e:
            self.logger.error(f"Error creating performance chart: {e}")
            
            # Create error chart
            plt.figure(figsize=(8, 6))
            plt.text(0.5, 0.5, f'Chart Error:\n{str(e)}', ha='center', va='center', transform=plt.gca().transAxes)
            plt.title('Performance Chart - Error')
            
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            
            plt.close()
            return img_buffer.getvalue()
