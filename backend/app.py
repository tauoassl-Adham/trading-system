import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import logging
import httpx
import json
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# ── المحركات الأساسية ──
from app.core.event_bus import event_bus
from app.core.ws_manager import ws_manager
from app.data.websocket_client import stream
from app.market.candle_engine import CandleEngine
from app.market.market_state import MarketState
from app.strategy.strategy_engine import StrategyEngine
from app.strategy.smc_engine import SMCEngine          # ✅ إضافة 1
from app.risk.risk_manager import RiskManager
from app.execution.paper_executor import PaperExecutor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
#  Binance REST
# ══════════════════════════════════════════════
BINANCE_REST = "https://api.binance.com"

TF_MAP = {
    "1m":"1m","3m":"3m","5m":"5m","15m":"15m","30m":"30m",
    "1h":"1h","2h":"2h","4h":"4h","6h":"6h","8h":"8h",
    "12h":"12h","1d":"1d","3d":"3d","1w":"1w","1M":"1M"
}

SMC_SYMBOLS    = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
SMC_TIMEFRAMES = ["1d", "4h", "1h"]
SMC_LIMITS     = {"1d": 100, "4h": 150, "1h": 200}

async def fetch_binance_candles(symbol: str, interval: str, limit: int = 120):
    tf  = TF_MAP.get(interval, "5m")
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
    if candles:
        candles = candles[:-1]   # احذف الشمعة المفتوحة
    return candles

async def fetch_binance_ticker(symbol: str):
    url    = f"{BINANCE_REST}/api/v3/ticker/24hr"
    params = {"symbol": symbol.upper()}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        d = resp.json()
    return {
        "symbol":     d["symbol"],
        "price":      float(d["lastPrice"]),
        "open":       float(d["openPrice"]),
        "high":       float(d["highPrice"]),
        "low":        float(d["lowPrice"]),
        "volume":     float(d["volume"]),
        "change":     float(d["priceChange"]),
        "change_pct": float(d["priceChangePercent"]),
    }

# ══════════════════════════════════════════════
#  Broadcast Helper
# ══════════════════════════════════════════════
def broadcast_event(data):
    try:
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast(data), loop)
    except Exception as e:
        logger.error(f"Broadcast error: {e}")

# ══════════════════════════════════════════════
#  ✅ إضافة 2 — تهيئة SMC بالشموع التاريخية
# ══════════════════════════════════════════════
async def initialize_smc_engine(smc: SMCEngine):
    """
    يحمّل الشموع التاريخية من Binance لكل أصل وكل timeframe
    قبل أن يبدأ الـ live stream — عشان المحرك يكون جاهز فوراً
    """
    logger.info("🔄 Initializing SMC Engine with historical data...")
    for symbol in SMC_SYMBOLS:
        for tf in SMC_TIMEFRAMES:
            try:
                limit = SMC_LIMITS.get(tf, 150)
                raw   = await fetch_binance_candles(symbol, tf, limit + 1)
                smc.load_historical_candles(symbol, tf, raw)
                logger.info(f"  ✅ {symbol} {tf}: {len(raw)} candles loaded")
                await asyncio.sleep(0.2)   # نتجنب rate limit
            except Exception as e:
                logger.warning(f"  ⚠️  {symbol} {tf} failed: {e}")
    logger.info("✅ SMC Engine ready")

# ══════════════════════════════════════════════
#  تهيئة المحركات  (قبل lifespan)
# ══════════════════════════════════════════════
candle_engine   = CandleEngine(event_bus)
market_state    = MarketState(event_bus)
strategy_engine = StrategyEngine(event_bus)
smc_engine      = SMCEngine(event_bus)             # ✅ إضافة 3
risk_manager    = RiskManager(event_bus, risk_per_trade=0.01, balance=10000)
paper_executor  = PaperExecutor(event_bus)

# ── الاشتراكات ──
event_bus.subscribe("trade_signal",      broadcast_event)
event_bus.subscribe("execute_order",     broadcast_event)
event_bus.subscribe("candle_closed_15m", broadcast_event)
event_bus.subscribe("smc_analysis",      broadcast_event)   # ✅ بث إشارات SMC للداشبورد

# ══════════════════════════════════════════════
#  Lifespan
# ══════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_smc_engine(smc_engine)   # أولاً: البيانات التاريخية
    asyncio.create_task(stream(event_bus))     # ثانياً: الـ live stream
    logger.info("🚀 Scylla System LIVE — SMC Engine Active")
    yield

app = FastAPI(lifespan=lifespan)

# ══════════════════════════════════════════════
#  REST Endpoints
# ══════════════════════════════════════════════

@app.get("/api/status")
async def get_status():
    return {
        "system": "Online",
        "mode": "SMC Swing Trading",
        "smc_symbols": SMC_SYMBOLS,
        "active_timeframes": ["1h", "4h", "1d"],
    }

@app.get("/api/candles/{symbol}/{interval}")
async def get_candles(symbol: str, interval: str, limit: int = 120):
    try:
        candles = await fetch_binance_candles(symbol, interval, limit)
        return {"symbol": symbol, "interval": interval, "candles": candles}
    except Exception as e:
        return JSONResponse(status_code=502,
                            content={"error": "Failed to fetch candles", "detail": str(e)})

@app.get("/api/ticker/24h/{symbol}")
async def get_ticker_24h(symbol: str):
    try:
        return await fetch_binance_ticker(symbol)
    except Exception as e:
        return JSONResponse(status_code=502,
                            content={"error": "Failed to fetch ticker", "detail": str(e)})

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

@app.get("/api/portfolio")
async def get_portfolio():
    return {"balance": 10000, "equity": 10000, "open_positions": [], "closed_trades": []}

# ✅ آخر تحليل SMC لأصل معين
@app.get("/api/smc/{symbol}")
async def get_smc_analysis(symbol: str):
    analysis = smc_engine.get_last_analysis(symbol.upper())
    if not analysis:
        return JSONResponse(status_code=404,
                            content={"message": f"No SMC analysis yet for {symbol}"})
    return {
        "symbol":     analysis.symbol,
        "bias":       analysis.bias,
        "trend_1d":   analysis.trend_1d,
        "trend_4h":   analysis.trend_4h,
        "trend_1h":   analysis.trend_1h,
        "aligned":    analysis.aligned,
        "poi_price":  analysis.poi_price,
        "poi_valid":  analysis.poi_valid,
        "sl":         analysis.sl,
        "tp1":        analysis.tp1,
        "tp2":        analysis.tp2,
        "tp3":        analysis.tp3,
        "confidence": analysis.confidence,
        "reason":     analysis.reason,
    }

# ✅ تشغيل تحليل SMC يدوي فوري
@app.get("/api/smc/{symbol}/analyze")
async def trigger_smc_analysis(symbol: str):
    try:
        analysis = smc_engine.run_analysis(symbol.upper())
        if not analysis:
            return {"status": "insufficient_data", "symbol": symbol}
        return {
            "status":     "ok",
            "symbol":     analysis.symbol,
            "bias":       analysis.bias,
            "reason":     analysis.reason,
            "confidence": analysis.confidence,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/test-signal")
async def test_signal():
    data = {"action": "TEST_BUY", "symbol": "BTCUSDT", "entry": 95000, "status": "MANUAL_TEST"}
    await ws_manager.broadcast(data)
    return {"status": "ok", "data": data}

# ══════════════════════════════════════════════
#  WebSocket
# ══════════════════════════════════════════════
@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    logger.info("✅ Dashboard connected")
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg    = json.loads(raw)
                action = msg.get("action", "")

                if action == "get_candles":
                    symbol   = msg.get("symbol", "BTCUSDT")
                    interval = msg.get("interval", "5m")
                    limit    = int(msg.get("limit", 120))
                    try:
                        candles = await fetch_binance_candles(symbol, interval, limit)
                        await websocket.send_text(json.dumps({
                            "type": "candles", "symbol": symbol,
                            "interval": interval, "candles": candles
                        }))
                    except Exception as e:
                        await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))

                elif action == "paper_trade":
                    event_bus.publish("paper_trade_request", {
                        "symbol": msg.get("symbol", "BTCUSDT"),
                        "side":   msg.get("side", "BUY"),
                        "qty":    float(msg.get("qty", 0)),
                        "price":  float(msg.get("price", 0)),
                    })

                # ✅ طلب تحليل SMC من الداشبورد
                elif action == "get_smc":
                    symbol   = msg.get("symbol", "BTCUSDT").upper()
                    analysis = smc_engine.get_last_analysis(symbol)
                    if analysis:
                        await websocket.send_text(json.dumps({
                            "type":       "smc_analysis",
                            "symbol":     analysis.symbol,
                            "bias":       analysis.bias,
                            "trend_1d":   analysis.trend_1d,
                            "trend_4h":   analysis.trend_4h,
                            "trend_1h":   analysis.trend_1h,
                            "aligned":    analysis.aligned,
                            "poi_price":  analysis.poi_price,
                            "sl":         analysis.sl,
                            "tp1":        analysis.tp1,
                            "tp2":        analysis.tp2,
                            "tp3":        analysis.tp3,
                            "confidence": analysis.confidence,
                            "reason":     analysis.reason,
                        }))
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "smc_analysis", "symbol": symbol,
                            "bias": "LOADING", "reason": "Analysis in progress..."
                        }))

                elif action == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("❌ Dashboard disconnected")
    except Exception as e:
        ws_manager.disconnect(websocket)
        logger.error(f"WebSocket error: {e}")

# ══════════════════════════════════════════════
#  Run
# ══════════════════════════════════════════════
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)