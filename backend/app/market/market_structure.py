class MarketStructure:
    def __init__(self, event_bus):
        self.event_bus = event_bus

        self.highs = []
        self.lows = []

        self.trend = "UNKNOWN"

        self.last_high = None
        self.last_low = None

        self.event_bus.subscribe("tick", self.on_tick)

    def on_tick(self, data):
        price = data["price"]

        self._update_structure(price)

    def _update_structure(self, price):
        # أول نسخة بسيطة جدًا (نطوّرها لاحقًا)

        if self.last_high is None or price > self.last_high:
            self.last_high = price
            self.highs.append(price)

        if self.last_low is None or price < self.last_low:
            self.last_low = price
            self.lows.append(price)

        self._detect_trend()

    def _detect_trend(self):
        if len(self.highs) < 3 or len(self.lows) < 3:
            return

        # بسيط كبداية
        if self.highs[-1] > self.highs[-2] and self.lows[-1] > self.lows[-2]:
            self.trend = "UPTREND"

        elif self.highs[-1] < self.highs[-2] and self.lows[-1] < self.lows[-2]:
            self.trend = "DOWNTREND"

        else:
            self.trend = "RANGE"

        print("STRUCTURE:", self.trend)