import os
import MetaTrader5 as mt5

class MT5Handler:
    def __init__(self):
        self.login = int(os.getenv("MT5_LOGIN"))
        self.password = os.getenv("MT5_PASSWORD")
        self.server = os.getenv("MT5_SERVER")
        if not mt5.initialize(login=self.login, password=self.password, server=self.server):
            raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")

    def get_price(self, symbol="EURUSD"):
        tick = mt5.symbol_info_tick(symbol)
        return tick.ask, tick.bid

    def place_order(self, symbol, volume, order_type, price, sl, tp):
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 234000,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        return mt5.order_send(request)

    def get_positions(self):
        return mt5.positions_get()
