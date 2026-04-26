import logging

logger = logging.getLogger(__name__)

class StrategyEngine:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.CORE_WEIGHT, self.CONFIRMER_WEIGHT = 0.60, 0.40
        self.MIN_CONFIDENCE = 0.80
        self.market_bias = "NEUTRAL" # الاتجاه العام
        
        self.last_confirmers = {}
        
        # الاشتراك في إغلاق الشموع بدلاً من التيكات
        self.event_bus.subscribe("candle_closed_1d", self.update_bias)
        self.event_bus.subscribe("candle_closed_15m", self.process_signal)
        self.event_bus.subscribe("analytics_update", self.receive_confirmers)
        
        logger.info("StrategyEngine (Swing Edition) Ready.")

    def update_bias(self, data):
        candle = data.get("candle")
        self.market_bias = "BUY" if candle["close"] > candle["open"] else "SELL"
        logger.info(f"📈 Macro Bias Updated: {self.market_bias}")

    def receive_confirmers(self, data):
        self.last_confirmers.update(data.get("confirmers", {}))

    def process_signal(self, data):
        core_data = data.get("core", {})
        # شرط التوافق: لا صفقة إذا كانت عكس الاتجاه
        if core_data.get("bias") != self.market_bias:
            logger.info(f"⚠️ Signal filtered: Counter-trend ({core_data.get('bias')}) vs Bias ({self.market_bias})")
            return

        # الحساب والتحقق
        score = 0.9 # مبسط هنا، ضع منطق الحساب المرجح الخاص بك
        if score >= self.MIN_CONFIDENCE:
            action = core_data.get("bias")
            entry = core_data.get("entry_price")
            ob = core_data.get("order_block", {})
            
            if not ob or "low" not in ob: return

            stop_loss = ob.get("low") if action == "BUY" else ob.get("high")
            tp = entry + (abs(entry - stop_loss) * 2.5) if action == "BUY" else entry - (abs(entry - stop_loss) * 2.5)

            self.event_bus.publish("trade_signal", {
                "symbol": "BTCUSDT", "action": action, "entry": entry, "sl": stop_loss, "tp": tp
            })
            logger.info(f"🔥 Swing Trade Executed: {action} at {entry}")