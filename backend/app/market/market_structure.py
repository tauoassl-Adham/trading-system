class MarketStructure:
    def __init__(self, event_bus):
        self.event_bus = event_bus

        # swings حقيقية
        self.highs = []
        self.lows = []

        self.last_high = None
        self.last_low = None

        # فلترة الحركة
        self.threshold = 10  # لاحقًا نخليه dynamic

        # الاستقرار
        self.trend_history = []
        self.confirmed_trend = "UNKNOWN"

        self.last_printed_trend = None

        self.event_bus.subscribe("tick", self.on_tick)

    def on_tick(self, data):
        symbol = data["symbol"]
        price = data["price"]
        # حالياً ندعم رمز واحد في هيكل السوق للتبسيط، أو يمكن توسيعه لاحقاً
        if symbol == "BTCUSDT":
            self._update_structure(price)

    def _update_structure(self, price):
        # أول تيك
        if self.last_high is None:
            self.last_high = price
            self.last_low = price
            return

        updated = False

        # Higher High
        if price > self.last_high + self.threshold:
            self.last_high = price
            self.highs.append(price)
            updated = True

        # Lower Low
        if price < self.last_low - self.threshold:
            self.last_low = price
            self.lows.append(price)
            updated = True

        # فقط إذا صار swing حقيقي
        if updated:
            logger.info(f"NEW SWING: {price}")
            self._detect_trend()

    def _detect_trend(self):
        if len(self.highs) < 2 or len(self.lows) < 2:
            return

        # الاتجاه الخام
        if self.highs[-1] > self.highs[-2] and self.lows[-1] > self.lows[-2]:
            current_trend = "UPTREND"

        elif self.highs[-1] < self.highs[-2] and self.lows[-1] < self.lows[-2]:
            current_trend = "DOWNTREND"

        else:
            current_trend = "RANGE"

        # نافذة الاستقرار
        self.trend_history.append(current_trend)

        if len(self.trend_history) > 5:
            self.trend_history.pop(0)

        # تأكيد الترند
        if len(self.trend_history) == 5:
            most_common = max(set(self.trend_history), key=self.trend_history.count)

            if self.trend_history.count(most_common) >= 4:
                if most_common != self.confirmed_trend:
                    self.confirmed_trend = most_common
                    print("STABLE STRUCTURE:", self.confirmed_trend)