import sys
import os
# أضف مجلد trading-system للـ path عشان يشوف مجلد app/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import logging
import httpx
import json
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# استيراد المحركات
from app.core.event_bus import event_bus
from app.core.ws_manager import ws_manager
from app.data.websocket_client import stream
from app.market.candle_engine import CandleEngine
from app.market.market_state import MarketState
from app.strategy.strategy_engine import StrategyEngine
from app.risk.risk_manager import RiskManager
from app.execution.paper_executor import PaperExecutor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  Binance REST — جلب الشموع التاريخية
# ─────────────────────────────────────────────
BINANCE_REST = "https://api.binance.com"

# تحويل timeframe من صيغة الداشبورد إلى صيغة Binance
TF_MAP = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "2h": "2h", "4h": "4h", "6h": "6h", "8h": "8h",
    "12h": "12h", "1d": "1d", "3d": "3d", "1w": "1w", "1M": "1M"
}

async def fetch_binance_candles(symbol: str, interval: str, limit: int = 120):
    tf = TF_MAP.get(interval, "5m")
    url = f"{BINANCE_REST}/api/v3/klines"
    params = {"symbol": symbol.upper(), "interval": tf, "limit": limit}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        raw = resp.json()

    candles = []
    for k in raw:
        candles.append({
            "t": int(k[0]) // 1000,
            "o": float(k[1]),
            "h": float(k[2]),
            "l": float(k[3]),
            "c": float(k[4]),
            "v": float(k[5]),
        })
    
    # ✅ احذف آخر شمعة — هي مفتوحة حالياً، الـ kline stream يتولاها
    if candles:
        candles = candles[:-1]
    
    return candles

async def fetch_binance_ticker(symbol: str):
    """يجلب بيانات الـ 24h ticker من Binance"""
    url = f"{BINANCE_REST}/api/v3/ticker/24hr"
    params = {"symbol": symbol.upper()}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        d = resp.json()
    return {
        "symbol": d["symbol"],
        "price": float(d["lastPrice"]),
        "open": float(d["openPrice"]),
        "high": float(d["highPrice"]),
        "low": float(d["lowPrice"]),
        "volume": float(d["volume"]),
        "change": float(d["priceChange"]),
        "change_pct": float(d["priceChangePercent"]),
    }

# ─────────────────────────────────────────────
#  Broadcast Helper
# ─────────────────────────────────────────────
def broadcast_event(data):
    try:
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast(data), loop)
        logger.info(f"Broadcasted: {data}")
    except Exception as e:
        logger.error(f"Error broadcasting event: {e}")

# ─────────────────────────────────────────────
#  Lifespan
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(stream(event_bus))
    logger.info("🚀 Scylla System: Live Feed Active")
    yield

app = FastAPI(lifespan=lifespan)

# ─────────────────────────────────────────────
#  تهيئة المحركات
# ─────────────────────────────────────────────
candle_engine   = CandleEngine(event_bus)
market_state    = MarketState(event_bus)
strategy_engine = StrategyEngine(event_bus)
risk_manager    = RiskManager(event_bus, risk_per_trade=0.01, balance=10000)
paper_executor  = PaperExecutor(event_bus)

event_bus.subscribe("trade_signal",     broadcast_event)
event_bus.subscribe("execute_order",    broadcast_event)
event_bus.subscribe("candle_closed_15m",broadcast_event)

# ─────────────────────────────────────────────
#  REST Endpoints
# ─────────────────────────────────────────────

@app.get("/api/status")
async def get_status():
    return {
        "system": "Online",
        "mode": "Swing Trading - MTF",
        "active_timeframes": ["1m","5m","15m","1h","4h","1d"]
    }

# ✅ الـ endpoint المفقود — الداشبورد يطلبه بـ loadCandles()
@app.get("/api/candles/{symbol}/{interval}")
async def get_candles(symbol: str, interval: str, limit: int = 120):
    """
    يرجع الشموع التاريخية من Binance بصيغة جاهزة للداشبورد
    مثال: GET /api/candles/BTCUSDT/5m?limit=120
    """
    try:
        candles = await fetch_binance_candles(symbol, interval, limit)
        logger.info(f"✅ Candles fetched: {symbol} {interval} → {len(candles)} candles")
        return {"symbol": symbol, "interval": interval, "candles": candles}
    except Exception as e:
        logger.error(f"❌ Candles fetch failed: {e}")
        return JSONResponse(
            status_code=502,
            content={"error": "Failed to fetch candles", "detail": str(e)}
        )

# ✅ الـ endpoint المفقود — لجلب بيانات الـ 24h
@app.get("/api/ticker/24h/{symbol}")
async def get_ticker_24h(symbol: str):
    """
    يرجع بيانات الـ 24h لحساب التغيير اليومي في الداشبورد
    """
    try:
        data = await fetch_binance_ticker(symbol)
        return data
    except Exception as e:
        logger.error(f"❌ Ticker fetch failed: {e}")
        return JSONResponse(
            status_code=502,
            content={"error": "Failed to fetch ticker", "detail": str(e)}
        )

@app.get("/api/price/{symbol}")
async def get_price(symbol: str):
    try:
        url = f"{BINANCE_REST}/api/v3/ticker/price"
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url, params={"symbol": symbol.upper()})
            d = resp.json()
        return {"symbol": d["symbol"], "price": float(d["price"])}
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": str(e)})

@app.get("/api/test-signal")
async def test_signal():
    data = {"action": "TEST_BUY", "symbol": "BTCUSDT", "entry": 95000, "status": "MANUAL_TEST"}
    await ws_manager.broadcast(data)
    return {"status": "ok", "data": data}

@app.get("/api/portfolio")
async def get_portfolio():
    # placeholder — سيُربط بـ PaperExecutor لاحقاً
    return {
        "balance": 10000,
        "equity": 10000,
        "open_positions": [],
        "closed_trades": []
    }

# ─────────────────────────────────────────────
#  WebSocket — مع معالجة get_candles
# ─────────────────────────────────────────────
@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    logger.info("✅ Dashboard Client Connected")
    try:
        while True:
            raw = await websocket.receive_text()

            # ─── معالجة الرسائل القادمة من الداشبورد ───
            try:
                msg = json.loads(raw)
                action = msg.get("action", "")

                # ✅ الداشبورد يطلب الشموع عبر WebSocket (requestCandles)
                if action == "get_candles":
                    symbol   = msg.get("symbol", "BTCUSDT")
                    interval = msg.get("interval", "5m")
                    limit    = int(msg.get("limit", 120))
                    try:
                        candles = await fetch_binance_candles(symbol, interval, limit)
                        await websocket.send_text(json.dumps({
                            "type": "candles",
                            "symbol": symbol,
                            "interval": interval,
                            "candles": candles
                        }))
                        logger.info(f"📊 WS Candles sent: {symbol} {interval} → {len(candles)}")
                    except Exception as e:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": f"Failed to fetch candles: {e}"
                        }))

                # Paper Trade
                elif action == "paper_trade":
                    symbol = msg.get("symbol", "BTCUSDT")
                    side   = msg.get("side", "BUY")
                    qty    = float(msg.get("qty", 0))
                    price  = float(msg.get("price", 0))
                    event_bus.publish("paper_trade_request", {
                        "symbol": symbol, "side": side, "qty": qty, "price": price
                    })
                    logger.info(f"📝 Paper Trade: {side} {qty} {symbol} @ {price}")

                # Ping
                elif action == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

            except json.JSONDecodeError:
                pass  # رسائل نصية غير JSON — نتجاهلها

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("❌ Dashboard Client Disconnected")
    except Exception as e:
        ws_manager.disconnect(websocket)
        logger.error(f"WebSocket error: {e}")

# ─────────────────────────────────────────────
#  Run
# ─────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)