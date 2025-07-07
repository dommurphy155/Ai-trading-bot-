import os
import time
from datetime import datetime
import MetaTrader5 as mt5
from matplotlib import pyplot as plt

class Screenshot:
    def __init__(self, out_dir="screenshots"):
        os.makedirs(out_dir, exist_ok=True)
        self.out_dir = out_dir

    def grab_chart(self, symbol="EURUSD"):
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 60)
        times = [datetime.fromtimestamp(r[0]) for r in rates]
        closes = [r[4] for r in rates]
        plt.figure()
        plt.plot(times, closes)
        path = os.path.join(self.out_dir, f"{symbol}_{int(time.time())}.png")
        plt.savefig(path, bbox_inches="tight")
        plt.close()
        return path
