import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self, strict=False):
        self.subscribers = defaultdict(list)
        self.strict = strict  # إذا True = يمنع events بدون subscribers

    def subscribe(self, event_type, callback):
        self.subscribers[event_type].append(callback)
        logger.info(f"[EventBus] Subscribed -> {event_type} | {callback.__name__}")

    def publish(self, event_type, data):
        subs = self.subscribers.get(event_type, [])

        logger.info(f"[EventBus] Event -> {event_type} | Subscribers: {len(subs)}")

        if not subs:
            if self.strict:
                logger.error(f"[EventBus] No subscribers for REQUIRED event: {event_type}")
            else:
                logger.info(f"[EventBus] No subscribers (ignored): {event_type}")
            return

        for callback in subs:
            try:
                callback(data)

            except Exception as e:
                logger.error(
                    f"[EventBus] Callback error | event={event_type} | "
                    f"handler={callback.__name__} | error={str(e)}"
                )

# Singleton
event_bus = EventBus(strict=False)