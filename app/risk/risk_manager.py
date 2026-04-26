import logging

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, event_bus, risk_per_trade=0.01, balance=10000):
        self.event_bus = event_bus
        self.risk_per_trade = risk_per_trade # 1% مخاطرة
        self.balance = balance # رأس مال المحاكاة
        
        # الاشتراك في إشارات التداول المؤكدة
        self.event_bus.subscribe("trade_signal", self.execute_risk_check)
        logger.info(f"RiskManager initialized. Capital: {self.balance} | Risk per trade: {self.risk_per_trade*100}%")

    def execute_risk_check(self, signal):
        """حساب حجم الصفقة بناءً على المسافة للـ Stop Loss"""
        entry = signal["entry"]
        sl = signal["sl"]
        
        # حساب المسافة للمخاطرة
        risk_distance = abs(entry - sl)
        if risk_distance == 0:
            logger.error("❌ Risk Check Failed: Stop Loss equals Entry.")
            return

        # تحديد حجم الصفقة بناءً على مخاطرة الـ 1%
        # Formula: (Balance * Risk_Percent) / Risk_Distance
        position_size = (self.balance * self.risk_per_trade) / risk_distance
        
        logger.info(f"🛡️ Risk Check Passed. Size: {position_size:.4f} units | SL: {sl}")
        
        # إرسال الأمر النهائي للمنفذ (PaperExecutor)
        self.event_bus.publish("execute_order", {
            **signal,
            "size": position_size
        })