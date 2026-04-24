from collections import defaultdict, deque


class MarketDataStore:
    def __init__(self, event_bus):
        self.event_bus = event_bus

        self.last_price = None
        self.ticks = deque(maxlen=1000)

        self.final_candles = {
            "1m": [],
            "5m": [],
            "15m": [],
            "1h": [],
            "4h": [],
            "1d": []
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