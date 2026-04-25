from fastapi import FastAPI
import asyncio
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.event_bus import EventBus
from app.data.data_store import MarketDataStore
from app.market.market_snapshot import MarketSnapshot
from app.data.websocket_client import stream
from app.market.market_structure import MarketStructure
from app.strategy.trend_following import TrendFollowingStrategy
from app.risk.risk_manager import RiskManager
from app.execution.paper_trader import PaperTrader
from app.portfolio.portfolio_manager import PortfolioManager
from app.analytics.analytics_engine import AnalyticsEngine

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

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

# � Portfolio management layer
portfolio_manager = PortfolioManager()

# 📊 Analytics layer
analytics_engine = AnalyticsEngine(portfolio_manager, risk_manager)

# 📈 Execution layer (Paper Trading)
paper_trader = PaperTrader(event_bus, risk_manager, portfolio_manager)
# ربط PortfolioManager مع تحديث الأسعار
def on_tick_update(data):
    """تحديث أسعار PortfolioManager عند تلقي tick"""
    symbol = data.get("symbol", "BTCUSDT")
    price = data.get("price")
    if price:
        portfolio_manager.update_prices({symbol: price})

event_bus.subscribe("tick", on_tick_update)

@app.on_event("startup")
async def startup():
    asyncio.create_task(stream(event_bus))


@app.get("/")
def root():
    return {"message": "System is running"}


@app.get("/dashboard")
def dashboard():
    return FileResponse("../frontend/dashboard.html", media_type="text/html")


@app.get("/snapshot")
def get_snapshot():
    return snapshot.get_snapshot()


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


@app.get("/analytics")
def get_analytics():
    return analytics_engine.generate_performance_report()


@app.get("/analytics/suggestions")
def get_suggestions():
    return {"suggestions": analytics_engine.get_strategy_suggestions()}