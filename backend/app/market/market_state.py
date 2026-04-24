import logging

logger = logging.getLogger(__name__)

logger.info("LOADED: %s", __name__)
logger.info("MARKET STATE FILE LOADED")


class MarketState:
    def __init__(self, event_bus):
        self.last_price = None
        self.event_bus = event_bus

        self.event_bus.subscribe("tick", self.on_tick)

    def on_tick(self, data):
        self.last_price = data["price"]
        logger.info("MARKET STATE UPDATED: %s", self.last_price)