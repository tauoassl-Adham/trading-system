import logging
from app.core.event_bus import event_bus

logger = logging.getLogger(__name__)

class AnalyticsEngine:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        # الاشتراك في التكات السعرية لرصد الاهتزاز اللحظي
        self.event_bus.subscribe("tick", self.analyze_tesla_vibration)

    def calculate_digital_root(self, number):
        """حساب الجذر الرقمي لأي سعر (مثلاً: 2205 -> 2+2+0+5 = 9)"""
        n = int(float(number) * 100) # تحويل السعر لعدد صحيح (بدون فاصلة)
        if n == 0: return 0
        return 1 + ((n - 1) % 9)

    def analyze_tesla_vibration(self, data):
        price = data.get("price")
        if not price: return

        root = self.calculate_digital_root(price)
        
        # التحقق مما إذا كان السعر يتوافق مع أرقام تسلا
        is_tesla_match = root in [3, 6, 9]
        
        if is_tesla_match:
            # إرسال إشارة تأكيد للطبقة الثانية
            self.event_bus.publish("analytics_update", {
                "confirmers": {
                    "tesla_match": True,
                    "vibration_root": root
                }
            })
            # logger.info(f"✨ Tesla Vibration Detected! Root: {root} at Price: {price}")