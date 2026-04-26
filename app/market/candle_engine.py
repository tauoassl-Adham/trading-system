import logging

logger = logging.getLogger(__name__)

class CandleEngine:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        # تعريف الإطارات الزمنية بالثواني
        self.timeframes = {
            "5m": 300, "15m": 900, "1h": 3600, 
            "4h": 14400, "1d": 86400, "1w": 604800
        }
        self.candles = {tf: None for tf in self.timeframes}
        self.event_bus.subscribe("tick", self.on_tick)
        logger.info("CandleEngine initialized for MTF analysis.")

    def on_tick(self, data):
        price = data["price"]
        timestamp = data["timestamp"]
        symbol = data["symbol"]

        for tf_name, seconds in self.timeframes.items():
            start_time = timestamp - (timestamp % seconds)
            
            if self.candles[tf_name] is None or self.candles[tf_name]["start_time"] != start_time:
                if self.candles[tf_name] is not None:
                    self.event_bus.publish(f"candle_closed_{tf_name}", {
                        "symbol": symbol, "timeframe": tf_name, "candle": self.candles[tf_name]
                    })
                self.candles[tf_name] = {
                    "open": price, "high": price, "low": price, "close": price,
                    "start_time": start_time
                }
            else:
                c = self.candles[tf_name]
                c["high"] = max(c["high"], price)
                c["low"] = min(c["low"], price)
                c["close"] = price