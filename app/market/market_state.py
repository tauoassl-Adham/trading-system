import logging

logger = logging.getLogger(__name__)

class MarketState:
    def __init__(self, event_bus, atr_multiplier=1.5):
        self.event_bus = event_bus
        self.atr_multiplier = atr_multiplier
        
        self.swings = [] 
        self.atr = 0.0
        self.trend = "NEUTRAL"
        
        # الاشتراك في الأحداث
        self.event_bus.subscribe("candle_closed", self.on_candle_closed)
        self.event_bus.subscribe("tick", self.on_tick) # إضافة الاشتراك في التك
    
    def on_tick(self, data):
        """دالة للاختبار والتحقق من وصول البيانات"""
        # نشر رسالة نجاح أن التك وصل للمحرك
        self.event_bus.publish("tick_processed", {
            "status": "received", 
            "price": data.get("price")
        })
        logger.info(f"MarketState received tick: {data.get('price')}")

    def on_candle_closed(self, data):
        """معالجة إغلاق الشمعة وتحديث حالة السوق"""
        candle = data["candle"]
        symbol = data["symbol"]
        close = candle["close"]
        high = candle["high"]
        low = candle["low"]
        
        logger.info(f"MarketState processing {symbol} | Close: {close}")
        
        # 1. تحديث الهيكل (Swings)
        self.detect_swings(close, high, low, close)
        
        # 2. التحقق من تغير الهيكل (CHoCH)
        self.check_for_choch(close)

    def update_atr(self, high, low, close):
        tr = max(high - low, abs(high - close), abs(low - close))
        if self.atr == 0:
            self.atr = tr
        else:
            self.atr = (self.atr * 13 + tr) / 14 
        return self.atr

    def detect_swings(self, current_price, high, low, close):
        threshold = self.update_atr(high, low, close) * self.atr_multiplier
        if not self.swings:
            self.swings.append({'price': high, 'type': 'high'})
            self.swings.append({'price': low, 'type': 'low'})
            logger.info("Initial Swings set.")

    def check_for_choch(self, current_candle_close):
        if not self.swings:
            return False
            
        last_swing = self.swings[-1] 
        
        if last_swing['type'] == 'high' and current_candle_close > last_swing['price']:
            self.trend = "BULLISH"
            logger.info(f"CHoCH Detected: Bullish Shift at {current_candle_close}")
            return True
        elif last_swing['type'] == 'low' and current_candle_close < last_swing['price']:
            self.trend = "BEARISH"
            logger.info(f"CHoCH Detected: Bearish Shift at {current_candle_close}")
            return True
        
        return False