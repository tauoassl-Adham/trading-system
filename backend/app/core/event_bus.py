import logging

logger = logging.getLogger(__name__)

class EventBus:
    """ناقل الأحداث المركزي - يضمن تواصل الوحدات بشكل غير متزامن وفعال"""
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type: str, callback):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to event: {event_type}")

    def publish(self, event_type: str, data: any):
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error executing callback for event {event_type}: {str(e)}")
