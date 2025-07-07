import sqlite3
from datetime import datetime, timedelta

class EarningsTracker:
    def __init__(self, db_path="earnings.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS earnings(
                ts TEXT,
                symbol TEXT,
                volume REAL,
                pnl REAL
            )
        """)
        self.conn.commit()

    def log(self, symbol, volume, pnl):
        self.conn.execute(
            "INSERT INTO earnings(ts, symbol, volume, pnl) VALUES(?,?,?,?)",
            (datetime.utcnow().isoformat(), symbol, volume, pnl)
        )
        self.conn.commit()

    def get_period(self, days=1):
        since = datetime.utcnow() - timedelta(days=days)
        c = self.conn.execute(
            "SELECT SUM(pnl) FROM earnings WHERE ts>=?",
            (since.isoformat(),)
        )
        return c.fetchone()[0] or 0.0
