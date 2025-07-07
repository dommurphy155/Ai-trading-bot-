import os
import MetaTrader5 as mt5

class Trader:
    def __init__(self, mt5_handler, ai_analyzer, earnings_tracker, screenshot, telegram_bot):
        self.mt5 = mt5_handler
        self.ai = ai_analyzer
        self.earn = earnings_tracker
        self.ss = screenshot
        self.bot = telegram_bot
        self.risk = float(os.getenv("RISK_LEVEL", 5.5)) / 100

    async def evaluate_and_execute(self):
        symbol = "EURUSD"
        ask, bid = self.mt5.get_price(symbol)
        price = (ask + bid) / 2
        signal, conf = await self.ai.analyze(symbol, price)
        if signal in ("BUY","SELL") and conf > 0.7:
            balance = 100000  # replace with real balance call if needed
            volume = max(0.01, round(balance * self.risk / price, 2))
            order_type = mt5.ORDER_TYPE_BUY if signal=="BUY" else mt5.ORDER_TYPE_SELL
            sl = price * (0.995 if signal=="BUY" else 1.005)
            tp = price * (1.005 if signal=="BUY" else 0.995)
            result = self.mt5.place_order(symbol, volume, order_type, price, sl, tp)
            self.earn.log(symbol, volume, 0.0)
            path = self.ss.grab_chart(symbol)
            await self.bot.send_trade_confirmation(path, result)
