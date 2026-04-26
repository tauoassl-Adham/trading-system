import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """فئة أساسية لجميع الاستراتيجيات"""

    def __init__(self, event_bus, data_store, name="BaseStrategy"):
        self.event_bus = event_bus
        self.data_store = data_store
        self.name = name
        self.active_signals = {}  # symbol -> signal

        # الاشتراك في الأحداث المطلوبة
        self.event_bus.subscribe("candle_closed_1m", self.on_candle_closed)

    @abstractmethod
    def generate_signal(self, symbol, candle):
        """توليد إشارة بناءً على الشمعة"""
        pass

    def on_candle_closed(self, candle):
        """معالجة إغلاق الشمعة"""
        symbol = "BTCUSDT"  # افتراضياً، يمكن توسيع لمتعدد الأصول
        signal = self.generate_signal(symbol, candle)

        if signal:
            self.active_signals[symbol] = signal
            self.event_bus.publish("strategy_signal", {
                "strategy": self.name,
                "symbol": symbol,
                "signal": signal,
                "candle": candle
            })
            logger.info(f"Strategy {self.name}: {signal} for {symbol}")

    def get_active_signal(self, symbol):
        """الحصول على الإشارة النشطة للأصل"""
        return self.active_signals.get(symbol)


class Signal:
    """فئة تمثل إشارة التداول"""

    def __init__(self, direction, entry_price, stop_loss=None, take_profit=None):
        self.direction = direction  # "BUY" or "SELL"
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.timestamp = None  # سيتم تعيينه عند الإنشاء

    def __str__(self):
        return f"{self.direction} @ {self.entry_price}"