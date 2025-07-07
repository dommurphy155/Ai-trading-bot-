import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

class TelegramBot:
    def __init__(self, trader, earnings_tracker):
        self.trader = trader
        self.earn = earnings_tracker
        self.app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("maketrade", self.cmd_maketrade))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("dailyearnings", self.cmd_daily))
        self.app.add_handler(CommandHandler("weeklyearnings", self.cmd_weekly))
        self.app.add_handler(CommandHandler("portfolio", self.cmd_portfolio))
        self.app.add_handler(CommandHandler("resetbot", self.cmd_reset))

    async def cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        text = "🚀 Bot running. Use /status to see open trades."
        await ctx.bot.send_message(chat_id=os.getenv("TELEGRAM_CHAT_ID"), text=text)

    async def cmd_maketrade(self, update, ctx):
        await self.trader.evaluate_and_execute()
        await ctx.bot.send_message(chat_id=os.getenv("TELEGRAM_CHAT_ID"), text="Trade executed.")

    async def cmd_status(self, update, ctx):
        positions = self.trader.mt5.get_positions() or []
        await ctx.bot.send_message(chat_id=os.getenv("TELEGRAM_CHAT_ID"),
                                   text=f"Open positions: {len(positions)}")

    async def cmd_daily(self, update, ctx):
        pnl = self.earn.get_period(1)
        await ctx.bot.send_message(chat_id=os.getenv("TELEGRAM_CHAT_ID"),
                                   text=f"Today's P&L: {pnl:.2f} USD")

    async def cmd_weekly(self, update, ctx):
        pnl = self.earn.get_period(7)
        await ctx.bot.send_message(chat_id=os.getenv("TELEGRAM_CHAT_ID"),
                                   text=f"Last 7 days P&L: {pnl:.2f} USD")

    async def cmd_portfolio(self, update, ctx):
        balance = 100000  # replace with real balance fetch
        await ctx.bot.send_message(chat_id=os.getenv("TELEGRAM_CHAT_ID"),
                                   text=f"Balance: {balance:.2f} USD")

    async def cmd_reset(self, update, ctx):
        await ctx.bot.send_message(chat_id=os.getenv("TELEGRAM_CHAT_ID"), text="Restarting bot…")
        os.execv(__file__, [""])

    async def send_trade_confirmation(self, img_path, result):
        await self.app.bot.send_photo(chat_id=os.getenv("TELEGRAM_CHAT_ID"),
                                      photo=open(img_path, "rb"),
                                      caption=f"Order result: {result}")

    async def start_polling(self):
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        await self.app.updater.idle()
