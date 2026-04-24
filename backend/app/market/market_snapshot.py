class MarketSnapshot:
    def __init__(self, data_store):
        self.ds = data_store

    def get_price(self):
        return self.ds.last_price

    def get_last_candle(self, tf):
        candles = self.ds.final_candles.get(tf, [])
        return candles[-1] if candles else None

    def get_trend(self, tf):
        candles = self.ds.final_candles.get(tf, [])
        if len(candles) < 2:
            return "neutral"

        last = candles[-1]
        prev = candles[-2]

        if last["close"] > prev["close"]:
            return "bullish"
        elif last["close"] < prev["close"]:
            return "bearish"
        else:
            return "neutral"

    def get_snapshot(self):
        return {
            "price": self.get_price(),
            "trend_15m": self.get_trend("15m"),
            "trend_1h": self.get_trend("1h"),
            "trend_4h": self.get_trend("4h"),
            "trend_1d": self.get_trend("1d"),
            "last_15m": self.get_last_candle("15m"),
            "last_1h": self.get_last_candle("1h"),
        }