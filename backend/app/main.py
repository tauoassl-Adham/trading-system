print("LOADED:", __name__)
from fastapi import FastAPI
import asyncio

from app.core.event_bus import EventBus
from app.market.market_state import MarketState
from app.data.websocket_client import stream

app = FastAPI()

event_bus = EventBus()
market_state = MarketState(event_bus)


@app.on_event("startup")
async def startup():
    asyncio.create_task(stream(event_bus))


@app.get("/")
def root():
    return {"message": "System is running"}