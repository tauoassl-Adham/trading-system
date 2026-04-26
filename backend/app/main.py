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

# 📂 Portfolio management layer
portfolio_manager = PortfolioManager()

# 📊 Analytics layer
analytics_engine = AnalyticsEngine(portfolio_manager, risk_manager)

# 📈 Execution layer (Paper Trading)
paper_trader = PaperTrader(event_bus, risk_manager, portfolio_manager)

# ربط PortfolioManager مع تحديث الأسعار
def on_tick_update(data):
    """تحديث أسعار PortfolioManager عند تلقي tick"""
    symbol = data.get("symbol")
    price = data.get("price")
    if symbol and price:
        portfolio_manager.update_prices({symbol: price})

event_bus.subscribe("tick", on_tick_update)

@app.on_event("startup")
async def startup():
    # استهداف عدة عملات كما في الرؤية
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]
    asyncio.create_task(stream(event_bus, symbols=symbols))


@app.get("/")
def root():
    return {"message": "System is running"}


@app.get("/dashboard")
def dashboard():
    return FileResponse("../frontend/dashboard.html", media_type="text/html")


@app.get("/snapshot/{symbol}")
def get_snapshot(symbol: str = "BTCUSDT"):
    return snapshot.get_snapshot(symbol)


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


@app.post("/manual-trade")
def manual_trade(trade: dict):
    """
    إدخال صفقة يدوية للمراقبة
    trade = {
        "symbol": "BTCUSDT",
        "direction": "BUY" or "SELL",
        "quantity": 0.001,
        "entry_price": 77500.0,
        "stop_loss": 77000.0,
        "take_profit": 78000.0
    }
    """
    try:
        # التحقق من المخاطر
        risk_check = risk_manager.validate_manual_trade(trade)
        if not risk_check["approved"]:
            return {"error": risk_check["reason"]}

        # إدخال الصفقة
        side = "long" if trade["direction"] == "BUY" else "short"
        portfolio_manager.update_position(
            trade["symbol"],
            side,
            trade["quantity"] if trade["direction"] == "BUY" else -trade["quantity"],
            trade["entry_price"]
        )

        return {"success": True, "message": "تم إدخال الصفقة بنجاح"}

    except Exception as e:
        return {"error": str(e)}


@app.delete("/position/{symbol}")
def close_position_manual(symbol: str, exit_price: float):
    """إغلاق مركز يدوياً"""
    try:
        # البحث عن المركز
        positions = portfolio_manager.get_positions()
        position = next((p for p in positions if p["symbol"] == symbol), None)

        if not position:
            return {"error": "المركز غير موجود"}

        # إغلاق المركز
        side = "long" if position["side"] == "long" else "short"
        quantity = -position["quantity"] if side == "long" else position["quantity"]

        portfolio_manager.update_position(symbol, side, quantity, exit_price)

        return {"success": True, "message": f"تم إغلاق مركز {symbol}"}

    except Exception as e:
        return {"error": str(e)}


@app.get("/symbols")
def get_available_symbols():
    """الحصول على قائمة العملات المتاحة"""
    # قائمة العملات الرئيسية في Binance
    symbols = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT",
        "DOTUSDT", "DOGEUSDT", "AVAXUSDT", "LTCUSDT", "TRXUSDT"
    ]
    return {"symbols": symbols}


@app.get("/timeframes")
def get_available_timeframes():
    """الحصول على الـ timeframes المتاحة"""
    timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
    return {"timeframes": timeframes}