from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


class MarketDataStore:
    def __init__(self, event_bus, max_history=1000):
        self.event_bus = event_bus
        self.max_history = max_history

        self.last_price = None
        self.ticks = deque(maxlen=max_history)

        self.final_candles = {
            "1m": deque(maxlen=self.max_history),
            "5m": deque(maxlen=self.max_history),
            "15m": deque(maxlen=self.max_history),
            "1h": deque(maxlen=self.max_history),
            "4h": deque(maxlen=self.max_history),
            "1d": deque(maxlen=self.max_history)
        }

        self.current = defaultdict(dict)

        self.event_bus.subscribe("tick", self.on_tick)

    def on_tick(self, data):
        price = data["price"]
        ts = data["timestamp"] / 1000

        self.last_price = price
        self.ticks.append(data)

        self._update_candle("1m", ts, price, 60)
        self._update_candle("5m", ts, price, 300)
        self._update_candle("15m", ts, price, 900)
        self._update_candle("1h", ts, price, 3600)
        self._update_candle("4h", ts, price, 14400)
        self._update_candle("1d", ts, price, 86400)

    def _update_candle(self, tf, ts, price, interval):
        bucket = int(ts // interval) * interval

        if bucket not in self.current[tf]:
            # إغلاق الشمعة السابقة إذا وجدت
            if self.current[tf]:
                prev_bucket = max(self.current[tf].keys())
                closed_candle = self.current[tf][prev_bucket]
                self.event_bus.publish(f"candle_closed_{tf}", closed_candle)

            # بدء شمعة جديدة
            candle = {
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "start": bucket
            }
            self.current[tf][bucket] = candle
            self.final_candles[tf].append(candle)
        else:
            candle = self.current[tf][bucket]
            candle["high"] = max(candle["high"], price)
            candle["low"] = min(candle["low"], price)
            candle["close"] = price

    def get_candles(self, tf, limit=None):
        """الحصول على الشموع المكتملة + الشمعة الحالية"""
        history = list(self.final_candles.get(tf, []))
        if tf in self.current and self.current[tf]:
            current_bucket = max(self.current[tf].keys())
            history.append(self.current[tf][current_bucket])
        return history[-limit:] if limit else history