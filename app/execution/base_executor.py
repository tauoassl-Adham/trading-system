class BaseExecutor:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.event_bus.subscribe("execute_order", self.execute_trade)

    def execute_trade(self, order_data):
        raise NotImplementedError("يجب تعريف دالة التنفيذ في المحرك الفرعي")