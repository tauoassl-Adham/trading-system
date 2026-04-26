import logging
logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type, callback):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
        logger.info(f"New subscriber for event: {event_type}")

    def publish(self, event_type, data):
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                callback(data)

# هذا السطر هو الأهم: هو الذي يوحد النسخة التي يستوردها الجميع
event_bus = EventBus()