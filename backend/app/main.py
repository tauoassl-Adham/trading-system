from fastapi import FastAPI
import asyncio

from app.core.event_bus import EventBus
from app.data.data_store import MarketDataStore
from app.market.market_snapshot import MarketSnapshot
from app.data.websocket_client import stream

app = FastAPI()

# 🔥 النظام المركزي
event_bus = EventBus()

# 🧠 Data Store (هذا هو القلب الآن)
data_store = MarketDataStore(event_bus)

# 📸 Snapshot layer
snapshot = MarketSnapshot(data_store)


@app.on_event("startup")
async def startup():
    asyncio.create_task(stream(event_bus))


@app.get("/")
def root():
    return {"message": "System is running"}