import logging

logger = logging.getLogger(__name__)

class PaperExecutor:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.event_bus.subscribe("execute_order", self.execute_trade)
        logger.info("PaperExecutor initialized. Ready for simulation.")

    def execute_trade(self, order_data):
        """محاكاة التنفيذ بدون اتصال بالمنصة"""
        symbol = order_data.get("symbol")
        action = order_data.get("action")
        size = order_data.get("position_size")
        entry = order_data.get("entry")
        
        logger.info(f"📄 PAPER TRADING: Executed {action} {size} of {symbol} at {entry}")
        
        # إرسال تأكيد وهمي للنظام
        self.event_bus.publish("trade_confirmed", {
            "status": "filled",
            "order_id": "PAPER_12345",
            "data": order_data
        })