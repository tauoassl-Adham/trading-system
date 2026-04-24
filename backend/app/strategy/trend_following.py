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
        candles = self.data_store.get_candles("1m", limit=self.lookback + 1)

        if len(candles) < self.lookback + 1:
            return None

        # التحقق من اتجاه صاعد
        bullish = all(c["close"] > c["open"] for c in candles[-self.lookback:])
        if bullish and candle["close"] > candle["open"]:
            return Signal("BUY", candle["close"], stop_loss=candle["low"] * 0.98)

        # التحقق من اتجاه هابط
        bearish = all(c["close"] < c["open"] for c in candles[-self.lookback:])
        if bearish and candle["close"] < candle["open"]:
            return Signal("SELL", candle["close"], stop_loss=candle["high"] * 1.02)

        return None