import sqlite3
from datetime import datetime

class TradeLogger:
    def __init__(self, db_name="trading_journal.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_table()

    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            action TEXT,
            entry_price REAL,
            exit_price REAL,
            pnl REAL,
            reason TEXT,
            timestamp DATETIME,
            market_state TEXT
        )
        """
        self.conn.execute(query)
        self.conn.commit()

    def log_trade(self, trade_data):
        query = """
        INSERT INTO trades (symbol, action, entry_price, exit_price, pnl, reason, timestamp, market_state)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(query, (
            trade_data['symbol'], trade_data['action'], trade_data['entry_price'],
            trade_data.get('exit_price'), trade_data.get('pnl'), trade_data.get('reason'),
            datetime.now(), str(trade_data.get('market_state', 'N/A'))
        ))
        self.conn.commit()