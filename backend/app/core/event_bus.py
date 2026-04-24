class EventBus:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type, callback):
        if not hasattr(self, "subscribers"):
            self.subscribers = {}

        if event_type not in self.subscribers:
            self.subscribers[event_type] = []

        self.subscribers[event_type].append(callback)

    def publish(self, event_type, data):
        if not hasattr(self, "subscribers"):
            self.subscribers = {}

        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                callback(data)