class MarketSnapshot:
    def __init__(self, data_store):
        self.ds = data_store

    def get_price(self, symbol="BTCUSDT"):
        return self.ds.last_prices.get(symbol)

    def get_last_candle(self, symbol, tf):
        candles = self.ds.final_candles.get(symbol, {}).get(tf, [])
        return candles[-1] if candles else None

    def get_trend(self, symbol, tf):
        candles = self.ds.final_candles.get(symbol, {}).get(tf, [])
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

    def get_snapshot(self, symbol="BTCUSDT"):
        return {
            "symbol": symbol,
            "price": self.get_price(symbol),
            "trend_15m": self.get_trend(symbol, "15m"),
            "trend_1h": self.get_trend(symbol, "1h"),
            "trend_4h": self.get_trend(symbol, "4h"),
            "trend_1d": self.get_trend(symbol, "1d"),
            "indicators": {
                "rsi_15m": self.ds.calculate_rsi(symbol, "15m"),
                "rsi_1h": self.ds.calculate_rsi(symbol, "1h"),
                "sma_20_1h": self.ds.calculate_sma(symbol, "1h", 20)
            },
            "last_15m": self.get_last_candle(symbol, "15m"),
            "last_1h": self.get_last_candle(symbol, "1h"),
        }
