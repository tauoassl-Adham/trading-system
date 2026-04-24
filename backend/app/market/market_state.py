print("LOADED:", __name__)
print("MARKET STATE FILE LOADED")


class MarketState:
    def __init__(self, event_bus):
        self.last_price = None
        self.event_bus = event_bus

        self.event_bus.subscribe("tick", self.on_tick)

    def on_tick(self, data):
        self.last_price = data["price"]
        print("MARKET STATE UPDATED:", self.last_price)