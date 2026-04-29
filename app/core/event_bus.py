import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self):
        self.subscribers = defaultdict(list)

    def subscribe(self, event_type, callback):
        self.subscribers[event_type].append(callback)
        logger.info(f"Subscribed to {event_type}: {callback.__name__}")

    def unsubscribe(self, event_type, callback): # الدالة التي أضفناها
        if event_type in self.subscribers:
            if callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)

    def publish(self, event_type, data):
        # ... (باقي الكود كما هو)
        for callback in self.subscribers[event_type]:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in {callback.__name__} for {event_type}: {e}")

# هذا السطر هو مفتاح الحل:
event_bus = EventBus()