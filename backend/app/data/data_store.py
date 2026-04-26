from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


class MarketDataStore:
    def __init__(self, event_bus, max_history=1000):
        self.event_bus = event_bus
        self.max_history = max_history

        # دعم عدة عملات
        self.last_prices = {}  # {symbol: price}
        self.ticks = defaultdict(lambda: deque(maxlen=max_history))

        # هيكلية الشموع: {symbol: {tf: deque}}
        self.final_candles = defaultdict(lambda: {
            "1m": deque(maxlen=self.max_history),
            "5m": deque(maxlen=self.max_history),
            "15m": deque(maxlen=self.max_history),
            "1h": deque(maxlen=self.max_history),
            "4h": deque(maxlen=self.max_history),
            "1d": deque(maxlen=self.max_history)
        })

        # الشموع الحالية قيد التكوين: {symbol: {tf: {bucket: candle}}}
        self.current = defaultdict(lambda: defaultdict(dict))

        self.event_bus.subscribe("tick", self.on_tick)

    def on_tick(self, data):
        symbol = data["symbol"]
        price = data["price"]
        ts = data["timestamp"] / 1000

        self.last_prices[symbol] = price
        self.ticks[symbol].append(data)

        self._update_candle(symbol, "1m", ts, price, 60)
        self._update_candle(symbol, "5m", ts, price, 300)
        self._update_candle(symbol, "15m", ts, price, 900)
        self._update_candle(symbol, "1h", ts, price, 3600)
        self._update_candle(symbol, "4h", ts, price, 14400)
        self._update_candle(symbol, "1d", ts, price, 86400)

    def _update_candle(self, symbol, tf, ts, price, interval):
        bucket = int(ts // interval) * interval

        if bucket not in self.current[symbol][tf]:
            # إغلاق الشمعة السابقة إذا وجدت
            if self.current[symbol][tf]:
                prev_bucket = max(self.current[symbol][tf].keys())
                closed_candle = self.current[symbol][tf][prev_bucket]
                self.event_bus.publish(f"candle_closed_{tf}", {
                    "symbol": symbol,
                    "candle": closed_candle
                })
                # حذفها لتوفير الذاكرة
                del self.current[symbol][tf][prev_bucket]

            # بدء شمعة جديدة
            candle = {
                "symbol": symbol,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "start": bucket
            }
            self.current[symbol][tf][bucket] = candle
            self.final_candles[symbol][tf].append(candle)
        else:
            candle = self.current[symbol][tf][bucket]
            candle["high"] = max(candle["high"], price)
            candle["low"] = min(candle["low"], price)
            candle["close"] = price

    def get_candles(self, symbol, tf, limit=None):
        """الحصول على الشموع المكتملة + الشمعة الحالية لرمز معين"""
        if symbol not in self.final_candles:
            return []
            
        history = list(self.final_candles[symbol].get(tf, []))
        if symbol in self.current and tf in self.current[symbol] and self.current[symbol][tf]:
            current_bucket = max(self.current[symbol][tf].keys())
            history.append(self.current[symbol][tf][current_bucket])
        return history[-limit:] if limit else history

    def calculate_rsi(self, symbol, tf, period=14):
        """حساب مؤشر القوة النسبية (RSI) يدوياً بكفاءة عالية"""
        candles = self.get_candles(symbol, tf, limit=period + 1)
        if len(candles) < period + 1:
            return 50.0  # قيمة محايدة عند نقص البيانات

        deltas = []
        for i in range(1, len(candles)):
            deltas.append(candles[i]["close"] - candles[i-1]["close"])

        gains = [d if d > 0 else 0 for d in deltas]
        losses = [abs(d) if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def calculate_sma(self, symbol, tf, period=20):
        """حساب المتوسط المتحرك البسيط (SMA)"""
        candles = self.get_candles(symbol, tf, limit=period)
        if len(candles) < period:
            return candles[-1]["close"] if candles else 0
        
        return sum(c["close"] for c in candles) / period
