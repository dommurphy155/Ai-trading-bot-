# mt_handler.py

from fxopen_api import FXOpenAPI
import os

class MTHandler:
    def __init__(self):
        self.api = FXOpenAPI(
            token_id=os.getenv("FXOPEN_TOKEN_ID"),
            token_key=os.getenv("FXOPEN_TOKEN_KEY"),
            token_secret=os.getenv("FXOPEN_TOKEN_SECRET"),
            server=os.getenv("FXOPEN_SERVER")
        )

    def get_account_info(self):
        try:
            return self.api.get_account_info()
        except Exception as e:
            return {"error": str(e)}

    def get_open_positions(self):
        try:
            return self.api.get_open_positions()
        except Exception as e:
            return {"error": str(e)}

    def place_order(self, symbol, volume, order_type, price=None, stop_loss=None, take_profit=None):
        try:
            return self.api.place_order(symbol, volume, order_type, price, stop_loss, take_profit)
        except Exception as e:
            return {"error": str(e)}
