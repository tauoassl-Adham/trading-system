import logging
from app.strategy.base_strategy import BaseStrategy, Signal

logger = logging.getLogger(__name__)


class TrendFollowingStrategy(BaseStrategy):
    """استراتيجية تتبع الاتجاه البسيطة"""

    def __init__(self, event_bus, data_store):
        super().__init__(event_bus, data_store, "TrendFollowing")
        self.lookback = 5  # عدد الشموع للتحقق من الاتجاه

    def generate_signal(self, symbol, candle):
        """توليد إشارة بناءً على اتجاه الشموع الأخيرة"""
        candles = self.data_store.get_candles(symbol, "1m", limit=self.lookback + 1)

        if len(candles) < self.lookback + 1:
            return None

        # التحقق من اتجاه صاعد
        bullish = all(c["close"] > c["open"] for c in candles[-self.lookback:])
        if bullish and candle["close"] > candle["open"]:
            return Signal("BUY", candle["close"], stop_loss=candle["low"] * 0.995, take_profit=candle["close"] * 1.01)

        # التحقق من اتجاه هابط
        bearish = all(c["close"] < c["open"] for c in candles[-self.lookback:])
        if bearish and candle["close"] < candle["open"]:
            return Signal("SELL", candle["close"], stop_loss=candle["high"] * 1.005, take_profit=candle["close"] * 0.99)

        return None
