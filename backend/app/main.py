from fastapi import FastAPI
import asyncio

from app.core.event_bus import EventBus
from app.data.data_store import MarketDataStore
from app.market.market_snapshot import MarketSnapshot
from app.data.websocket_client import stream
from app.market.market_structure import MarketStructure
from app.strategy.trend_following import TrendFollowingStrategy
from app.risk.risk_manager import RiskManager
from app.execution.paper_trader import PaperTrader

app = FastAPI()

# 🔥 النظام المركزي
event_bus = EventBus()
market_structure = MarketStructure(event_bus)

# 🧠 Data Store (هذا هو القلب الآن)
data_store = MarketDataStore(event_bus)

# 📸 Snapshot layer
snapshot = MarketSnapshot(data_store)

# 🧠 Strategy layer
trend_strategy = TrendFollowingStrategy(event_bus, data_store)

# ⚠️ Risk management layer
risk_manager = RiskManager(event_bus)

# 📈 Execution layer (Paper Trading)
paper_trader = PaperTrader(event_bus, risk_manager)


@app.on_event("startup")
async def startup():
    asyncio.create_task(stream(event_bus))


@app.get("/")
def root():
    return {"message": "System is running"}


@app.get("/signals")
def get_signals():
    return {
        "trend_following": trend_strategy.get_active_signal("BTCUSDT")
    }


@app.get("/risk")
def get_risk_status():
    return risk_manager.get_risk_status()


@app.get("/positions")
def get_positions():
    return paper_trader.get_positions()


@app.get("/trades")
def get_trades(limit: int = 10):
    return paper_trader.get_trade_history(limit)