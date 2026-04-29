import time
import random
import logging
from datetime import datetime

import random

def generate_confirmers(bus):
    bus.publish("analytics_update", {
        "confirmers": {
            "macro": random.uniform(0.6, 1.0),
            "momentum": random.uniform(0.5, 1.0)
        }
    })

logger = logging.getLogger(__name__)

class MarketSimulator:
    def __init__(self, event_bus, symbol="BTCUSDT", timeframe=60):
        self.event_bus = event_bus
        self.symbol = symbol
        self.timeframe = timeframe  # بالثواني (60 = 1m)
        self.price = 30000.0
        self.volatility = 0.003
        self.running = False

    def generate_candle(self):
        open_price = self.price

        high = open_price
        low = open_price

        # نحاكي حركة داخل الشمعة
        for _ in range(10):  # عدد الحركات داخل الشمعة
            change = random.uniform(-self.volatility, self.volatility)
            self.price *= (1 + change)

            high = max(high, self.price)
            low = min(low, self.price)

        close = self.price

        candle = {
            "symbol": self.symbol,
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": round(random.uniform(10, 100), 2),
            "timestamp": datetime.utcnow().isoformat(),
            "timeframe": self.timeframe
        }

        return candle

    def start(self):
        self.running = True
        logger.info("Candle simulation started")

        while self.running:
            candle = self.generate_candle()

            # إرسال الشمعة للنظام
            self.event_bus.publish("MARKET_CANDLE", candle)

            logger.debug(f"New candle: {candle}")

            time.sleep(self.timeframe)

    def stop(self):
        self.running = False
        logger.info("Simulation stopped")