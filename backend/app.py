"""
╔══════════════════════════════════════════════════════════════╗
║           SCYLLA TRADING PLATFORM — Backend v2.0            ║
║         FastAPI + WebSocket + Binance Historical API        ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import logging
import httpx
import json
from pathlib import Path
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# ── المحركات الداخلية ──────────────────────────────────────────
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.event_bus import event_bus
from app.core.ws_manager import ws_manager
from app.data.websocket_client import stream
from app.market.candle_engine import CandleEngine
from app.market.market_state import MarketState
from app.strategy.strategy_engine import StrategyEngine
from app.risk.risk_manager import RiskManager
from app.execution.paper_executor import PaperExecutor

# ── الإعدادات ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-20s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("scylla.backend")

BASE_DIR   = Path(__file__).resolve().parent.parent
FRONTEND   = BASE_DIR / "frontend"
BINANCE_API = "https://api.binance.com/api/v3"

# ── تهيئة المحركات ─────────────────────────────────────────────
candle_engine   = CandleEngine(event_bus)
market_state    = MarketState(event_bus)
strategy_engine = StrategyEngine(event_bus)
risk_manager    = RiskManager(event_bus, risk_per_trade=0.01, balance=10_000)
paper_executor  = PaperExecutor(event_bus)

# ══════════════════════════════════════════════════════════════
#  دالة البث للداشبورد عبر WebSocket
# ══════════════════════════════════════════════════════════════
async def _broadcast(data: dict):
    """إرسال أي حدث داخلي للداشبورد مباشرة"""
    if ws_manager.active_connections:
        await ws_manager.broadcast(data)

def sync_broadcast(data: dict):
    """wrapper متزامن يُستخدم مع event_bus.subscribe"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_broadcast(data))
    except Exception as e:
        logger.error(f"Broadcast error: {e}")

# ── ربط الأحداث الحيوية بالداشبورد ───────────────────────────
event_bus.subscribe("trade_signal",      sync_broadcast)
event_bus.subscribe("execute_order",     sync_broadcast)
event_bus.subscribe("trade_confirmed",   sync_broadcast)
event_bus.subscribe("candle_closed_5m",  sync_broadcast)
event_bus.subscribe("candle_closed_15m", sync_broadcast)
event_bus.subscribe("candle_closed_1h",  sync_broadcast)

# ══════════════════════════════════════════════════════════════
#  جلب الشموع التاريخية من Binance
# ══════════════════════════════════════════════════════════════
INTERVAL_MAP = {
    "5m": "5m", "15m": "15m", "1h": "1h",
    "4h": "4h", "1d": "1d",  "1w": "1w"
}

async def fetch_historical_candles(symbol: str, interval: str, limit: int = 100) -> list:
    """
    يجلب آخر `limit` شمعة من Binance REST API
    ويعيدها بصيغة: [{t, o, h, l, c, v}, ...]
    """
    url = f"{BINANCE_API}/klines"
    params = {
        "symbol":   symbol.upper(),
        "interval": INTERVAL_MAP.get(interval, "5m"),
        "limit":    limit
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            raw = resp.json()
            candles = [
                {
                    "t": int(k[0]) // 1000,   # open_time بالثواني
                    "o": float(k[1]),
                    "h": float(k[2]),
                    "l": float(k[3]),
                    "c": float(k[4]),
                    "v": float(k[5])
                }
                for k in raw
            ]
            logger.info(f"Fetched {len(candles)} candles | {symbol} {interval}")
            return candles
    except Exception as e:
        logger.error(f"Historical fetch error: {e}")
        return []

# ══════════════════════════════════════════════════════════════
#  Lifespan — يبدأ وينتهي مع السيرفر
# ══════════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("━" * 60)
    logger.info("  SCYLLA PLATFORM — Starting Up")
    logger.info("━" * 60)

    # تشغيل WebSocket Stream في الخلفية
    asyncio.create_task(stream(event_bus))
    logger.info("✅ Binance WebSocket stream started")

    yield  # السيرفر يعمل هنا

    logger.info("🔴 Scylla Platform shutting down...")

# ══════════════════════════════════════════════════════════════
#  تعريف التطبيق
# ══════════════════════════════════════════════════════════════
app = FastAPI(
    title="Scylla Trading Platform",
    version="2.0.0",
    lifespan=lifespan
)

# السماح بالطلبات من الداشبورد
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# تقديم ملفات الـ Frontend (CSS, JS)
if FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")

# ══════════════════════════════════════════════════════════════
#  الروابط (Endpoints)
# ══════════════════════════════════════════════════════════════

@app.get("/")
async def serve_dashboard():
    """يفتح الداشبورد مباشرة في المتصفح"""
    dashboard = FRONTEND / "dashboard.html"
    if dashboard.exists():
        return FileResponse(str(dashboard))
    return {"error": "dashboard.html not found", "path": str(dashboard)}


@app.get("/api/status")
async def get_status():
    """حالة النظام"""
    return {
        "system": "Online",
        "version": "2.0.0",
        "mode": "Paper Trading",
        "engines": {
            "candle_engine":   "active",
            "market_state":    "active",
            "strategy_engine": "active",
            "risk_manager":    "active",
            "paper_executor":  "active"
        },
        "active_timeframes": list(candle_engine.timeframes.keys()),
        "ws_clients": len(ws_manager.active_connections)
    }


@app.get("/api/candles/{symbol}/{interval}")
async def get_candles(symbol: str, interval: str, limit: int = 100):
    """
    يجلب الشموع التاريخية من Binance
    مثال: GET /api/candles/BTCUSDT/5m?limit=100
    """
    candles = await fetch_historical_candles(symbol, interval, limit)
    return {
        "symbol":   symbol.upper(),
        "interval": interval,
        "count":    len(candles),
        "candles":  candles
    }


@app.get("/api/price/{symbol}")
async def get_price(symbol: str):
    """السعر اللحظي من Binance"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{BINANCE_API}/ticker/price", params={"symbol": symbol.upper()})
            resp.raise_for_status()
            data = resp.json()
            return {"symbol": data["symbol"], "price": float(data["price"])}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/ticker/24h/{symbol}")
async def get_24h_ticker(symbol: str):
    """بيانات 24 ساعة (سعر الفتح، أعلى، أدنى، التغيير)"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{BINANCE_API}/ticker/24hr", params={"symbol": symbol.upper()})
            resp.raise_for_status()
            d = resp.json()
            return {
                "symbol":        d["symbol"],
                "open":          float(d["openPrice"]),
                "high":          float(d["highPrice"]),
                "low":           float(d["lowPrice"]),
                "close":         float(d["lastPrice"]),
                "change_pct":    float(d["priceChangePercent"]),
                "volume":        float(d["volume"]),
                "quote_volume":  float(d["quoteVolume"])
            }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/signal/test")
async def test_signal():
    """إرسال إشارة اختبار للداشبورد"""
    test = {
        "type":   "trade_signal",
        "action": "TEST_BUY",
        "symbol": "BTCUSDT",
        "entry":  candle_engine.candles.get("5m", {}).get("close", 0) if candle_engine.candles.get("5m") else 0,
        "sl":     0,
        "tp":     0,
        "status": "TEST"
    }
    await _broadcast(test)
    return {"status": "Signal sent", "data": test}


@app.get("/api/portfolio")
async def get_portfolio():
    """حالة المحفظة الوهمية"""
    return {
        "balance":      risk_manager.balance,
        "risk_per_trade": risk_manager.risk_per_trade,
        "open_positions": [],
        "pnl":          0.0
    }


# ══════════════════════════════════════════════════════════════
#  WebSocket — الاتصال المباشر مع الداشبورد
# ══════════════════════════════════════════════════════════════
@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    client = websocket.client
    logger.info(f"✅ Dashboard connected: {client}")

    # إرسال رسالة ترحيب فورية
    await websocket.send_json({
        "type":    "connected",
        "message": "Scylla Platform v2.0 — Live",
        "engines": "all_active"
    })

    try:
        while True:
            # استقبال طلبات من الداشبورد
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                await handle_dashboard_message(msg, websocket)
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info(f"❌ Dashboard disconnected: {client}")
    except Exception as e:
        ws_manager.disconnect(websocket)
        logger.error(f"WS error: {e}")


async def handle_dashboard_message(msg: dict, websocket: WebSocket):
    """
    معالجة الطلبات القادمة من الداشبورد عبر WebSocket
    """
    action = msg.get("action")

    if action == "get_candles":
        # الداشبورد يطلب شموع تاريخية
        symbol   = msg.get("symbol", "BTCUSDT")
        interval = msg.get("interval", "5m")
        limit    = msg.get("limit", 100)
        candles  = await fetch_historical_candles(symbol, interval, limit)
        await websocket.send_json({
            "type":     "candles",
            "symbol":   symbol,
            "interval": interval,
            "candles":  candles
        })

    elif action == "paper_trade":
        # الداشبورد يرسل أمر تداول وهمي
        symbol = msg.get("symbol", "BTCUSDT")
        side   = msg.get("side", "BUY")
        qty    = float(msg.get("qty", 0))
        price  = float(msg.get("price", 0))

        if price > 0 and qty > 0:
            event_bus.publish("trade_signal", {
                "symbol": symbol,
                "action": side,
                "entry":  price,
                "sl":     price * (0.99 if side == "BUY" else 1.01),
                "tp":     price * (1.02 if side == "BUY" else 0.98),
            })
            await websocket.send_json({
                "type":    "paper_trade_ack",
                "status":  "queued",
                "symbol":  symbol,
                "side":    side,
                "price":   price,
                "qty":     qty
            })

    elif action == "ping":
        await websocket.send_json({"type": "pong"})


# ══════════════════════════════════════════════════════════════
#  نقطة التشغيل
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )