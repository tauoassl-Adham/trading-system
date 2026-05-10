import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio, logging, httpx, json, uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.core.event_bus import event_bus
from app.core.ws_manager import ws_manager
from app.data.websocket_client import stream
from app.market.candle_engine import CandleEngine
from app.market.market_state import MarketState
from app.strategy.strategy_engine import StrategyEngine
from app.strategy.smc_engine import SMCEngine
from app.strategy.ai_engine import get_ai_engine
from app.strategy.signals_engine import SignalsEngine
from app.strategy.news_engine import get_news_engine
from app.alerts.alerts_manager import get_alerts_manager, AlertType
from app.risk.risk_manager import RiskManager
from app.execution.paper_executor import PaperExecutor

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BINANCE_REST   = "https://api.binance.com"
SMC_SYMBOLS    = ["BTCUSDT","ETHUSDT","BNBUSDT"]
SMC_TIMEFRAMES = ["1d","4h","1h"]
SMC_LIMITS     = {"1d":100,"4h":150,"1h":200}
TF_MAP = {"1m":"1m","3m":"3m","5m":"5m","15m":"15m","30m":"30m",
          "1h":"1h","2h":"2h","4h":"4h","6h":"6h","8h":"8h",
          "12h":"12h","1d":"1d","3d":"3d","1w":"1w","1M":"1M"}

async def fetch_binance_candles(symbol, interval, limit=120):
    tf = TF_MAP.get(interval,"5m")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{BINANCE_REST}/api/v3/klines",
            params={"symbol":symbol.upper(),"interval":tf,"limit":limit})
        resp.raise_for_status()
        raw = resp.json()
    candles = [{"t":int(k[0])//1000,"o":float(k[1]),"h":float(k[2]),
                "l":float(k[3]),"c":float(k[4]),"v":float(k[5])} for k in raw]
    return candles[:-1] if candles else candles

async def fetch_binance_ticker(symbol):
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{BINANCE_REST}/api/v3/ticker/24hr",
            params={"symbol":symbol.upper()})
        resp.raise_for_status()
        d = resp.json()
    return {"symbol":d["symbol"],"price":float(d["lastPrice"]),
            "open":float(d["openPrice"]),"high":float(d["highPrice"]),
            "low":float(d["lowPrice"]),"volume":float(d["volume"]),
            "change":float(d["priceChange"]),"change_pct":float(d["priceChangePercent"])}

def broadcast_event(data):
    try:
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast(data), loop)
    except Exception as e:
        logger.error(f"Broadcast error: {e}")

async def initialize_smc_engine(smc):
    logger.info("🔄 Initializing SMC Engine...")
    for symbol in SMC_SYMBOLS:
        for tf in SMC_TIMEFRAMES:
            try:
                raw = await fetch_binance_candles(symbol, tf, SMC_LIMITS.get(tf,150)+1)
                smc.load_historical_candles(symbol, tf, raw)
                logger.info(f"  ✅ {symbol} {tf}: {len(raw)} candles")
                await asyncio.sleep(0.2)
            except Exception as e:
                logger.warning(f"  ⚠️ {symbol} {tf}: {e}")
    logger.info("✅ SMC Engine ready")

# ── تهيئة المحركات ──
candle_engine   = CandleEngine(event_bus)
market_state    = MarketState(event_bus)
strategy_engine = StrategyEngine(event_bus)
smc_engine      = SMCEngine(event_bus)
risk_manager    = RiskManager(event_bus, risk_per_trade=0.01, balance=10000)
paper_executor  = PaperExecutor(event_bus)
ai_engine       = get_ai_engine(event_bus)
alerts_manager  = get_alerts_manager(event_bus, ws_manager)
signals_engine  = SignalsEngine(event_bus, alerts_manager, ai_engine)
news_engine     = get_news_engine(event_bus, ai_engine)

# ── نشر أخبار للداشبورد ──
def broadcast_news(data):
    broadcast_event({"type": "news_update", **data})

# ── الاشتراكات ──
for ev in ["trade_signal","execute_order","candle_closed_15m","smc_analysis",
           "choch_detected","bos_detected","signal_closed","signal_updated","alert_sent"]:
    event_bus.subscribe(ev, broadcast_event)
event_bus.subscribe("news_update", broadcast_news)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_smc_engine(smc_engine)
    asyncio.create_task(stream(event_bus))
    asyncio.create_task(news_engine.run_loop(interval_minutes=5))
    logger.info("🚀 Scylla LIVE — AI + SMC + Signals + Alerts + News")
    yield

app = FastAPI(lifespan=lifespan)

# ══ REST Endpoints ══

@app.get("/api/status")
async def get_status():
    return {"system":"Online","ai":"Gemini 1.5 Flash",
            "smc_symbols":SMC_SYMBOLS,"alerts":alerts_manager.get_config()}

@app.get("/api/candles/{symbol}/{interval}")
async def get_candles(symbol, interval, limit:int=120):
    try:
        return {"symbol":symbol,"interval":interval,
                "candles":await fetch_binance_candles(symbol,interval,limit)}
    except Exception as e:
        return JSONResponse(status_code=502,content={"error":str(e)})

@app.get("/api/ticker/24h/{symbol}")
async def get_ticker(symbol):
    try:
        return await fetch_binance_ticker(symbol)
    except Exception as e:
        return JSONResponse(status_code=502,content={"error":str(e)})

@app.get("/api/price/{symbol}")
async def get_price(symbol):
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{BINANCE_REST}/api/v3/ticker/price",
                params={"symbol":symbol.upper()})
            d = resp.json()
        return {"symbol":d["symbol"],"price":float(d["price"])}
    except Exception as e:
        return JSONResponse(status_code=502,content={"error":str(e)})

@app.get("/api/smc/{symbol}")
async def get_smc(symbol):
    a = smc_engine.get_last_analysis(symbol.upper())
    if not a:
        return JSONResponse(status_code=404,content={"message":f"No analysis for {symbol}"})
    return {"symbol":a.symbol,"bias":a.bias,"trend_1d":a.trend_1d,"trend_4h":a.trend_4h,
            "trend_1h":a.trend_1h,"aligned":a.aligned,"poi_price":a.poi_price,
            "sl":a.sl,"tp1":a.tp1,"tp2":a.tp2,"tp3":a.tp3,
            "confidence":a.confidence,"reason":a.reason}

@app.get("/api/smc/{symbol}/analyze")
async def analyze_smc(symbol):
    try:
        a = smc_engine.run_analysis(symbol.upper())
        if not a:
            return {"status":"insufficient_data","symbol":symbol}
        return {"status":"ok","symbol":a.symbol,"bias":a.bias,
                "trend_1d":a.trend_1d,"trend_4h":a.trend_4h,"trend_1h":a.trend_1h,
                "aligned":a.aligned,"poi_price":a.poi_price,"sl":a.sl,
                "tp1":a.tp1,"tp2":a.tp2,"tp3":a.tp3,
                "confidence":a.confidence,"reason":a.reason}
    except Exception as e:
        return JSONResponse(status_code=500,content={"error":str(e)})

# ── News Endpoints ────────────────────────────
@app.get("/api/news")
async def get_news(limit: int = 20):
    return {"news": news_engine.get_latest(limit),
            "last_fetch": news_engine.last_fetch}

@app.get("/api/news/important")
async def get_important_news():
    return {"news": news_engine.get_important()}

@app.post("/api/news/refresh")
async def refresh_news():
    asyncio.create_task(_refresh_news())
    return {"status": "refreshing"}

async def _refresh_news():
    crypto  = await news_engine.fetch_news("crypto")
    general = await news_engine.fetch_news("general")
    all_n   = crypto + general
    all_n.sort(key=lambda x: x.get('datetime',0), reverse=True)
    translated = await news_engine.translate_news(all_n[:15])
    news_engine.cache = translated
    await ws_manager.broadcast({"type":"news_update","items":translated,"count":len(translated)})

# ── Signals Endpoints ─────────────────────────
@app.get("/api/signals/active")
async def active_signals():
    return {"signals":signals_engine.get_active_signals()}

@app.get("/api/signals/history")
async def signals_history(limit:int=50):
    return {"signals":signals_engine.get_history(limit)}

@app.post("/api/signals/toggle/{signal_type}")
async def toggle_signal(signal_type, enabled:bool=True):
    signals_engine.toggle_signal_type(signal_type, enabled)
    return {"status":"ok","signal_type":signal_type,"enabled":enabled}

@app.post("/api/signals/filters")
async def update_filters(min_confidence:float=None,require_aligned:bool=None,min_rr:float=None):
    signals_engine.update_filters(min_confidence,require_aligned,min_rr)
    return {"status":"ok"}

# ── Alerts Endpoints ──────────────────────────
@app.get("/api/alerts/history")
async def alerts_history(limit:int=50):
    return {"alerts":alerts_manager.get_history(limit)}

@app.get("/api/alerts/config")
async def alerts_config():
    return alerts_manager.get_config()

@app.post("/api/alerts/toggle/{alert_type}")
async def toggle_alert(alert_type, enabled:bool=True):
    try:
        alerts_manager.toggle(AlertType(alert_type), enabled)
        return {"status":"ok","alert_type":alert_type,"enabled":enabled}
    except ValueError:
        return JSONResponse(status_code=400,content={"error":f"Unknown: {alert_type}"})

# ── AI Endpoints ──────────────────────────────
@app.post("/api/ai/chat")
async def ai_chat(body:dict):
    msg = body.get("message","")
    if not msg:
        return JSONResponse(status_code=400,content={"error":"message required"})
    return {"response": await ai_engine.chat(msg)}

@app.post("/api/ai/analyze-market")
async def ai_market(body:dict):
    return await ai_engine.analyze_market(body)

@app.post("/api/ai/analyze-news")
async def ai_news(body:dict):
    return await ai_engine.analyze_news(body.get("news",[]))

@app.post("/api/ai/psychology")
async def ai_psych(body:dict):
    return await ai_engine.analyze_psychology(body)

@app.get("/api/portfolio")
async def get_portfolio():
    return {"balance":10000,"equity":10000,"open_positions":[],
            "closed_trades":[],"daily_pnl":0,"total_pnl":0,
            "win_rate":0,"max_drawdown":0}

# ══ WebSocket ══
@app.websocket("/ws/dashboard")
async def ws_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    logger.info("✅ Dashboard connected")

    # إرسال الأخبار الحالية فور الاتصال
    if news_engine.cache:
        await websocket.send_text(json.dumps({
            "type":  "news_update",
            "items": news_engine.cache[:10],
            "count": len(news_engine.cache),
        }))

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg    = json.loads(raw)
                action = msg.get("action","")

                if action == "get_candles":
                    candles = await fetch_binance_candles(
                        msg.get("symbol","BTCUSDT"),
                        msg.get("interval","5m"),
                        int(msg.get("limit",120)))
                    await websocket.send_text(json.dumps({
                        "type":"candles","symbol":msg.get("symbol"),
                        "interval":msg.get("interval"),"candles":candles}))

                elif action == "paper_trade":
                    event_bus.publish("paper_trade_request",{
                        "symbol":msg.get("symbol","BTCUSDT"),
                        "side":msg.get("side","BUY"),
                        "qty":float(msg.get("qty",0)),
                        "price":float(msg.get("price",0))})

                elif action == "get_smc":
                    sym = msg.get("symbol","BTCUSDT").upper()
                    a   = smc_engine.get_last_analysis(sym)
                    if a:
                        await websocket.send_text(json.dumps({
                            "type":"smc_analysis","symbol":a.symbol,"bias":a.bias,
                            "trend_1d":a.trend_1d,"trend_4h":a.trend_4h,"trend_1h":a.trend_1h,
                            "aligned":a.aligned,"poi_price":a.poi_price,"sl":a.sl,
                            "tp1":a.tp1,"tp2":a.tp2,"tp3":a.tp3,
                            "confidence":a.confidence,"reason":a.reason}))

                elif action == "get_news":
                    await websocket.send_text(json.dumps({
                        "type":  "news_update",
                        "items": news_engine.get_latest(20),
                        "count": len(news_engine.cache)}))

                elif action == "ai_chat":
                    response = await ai_engine.chat(msg.get("message",""))
                    await websocket.send_text(json.dumps({
                        "type":"ai_response","response":response}))

                elif action == "toggle_alert":
                    try:
                        at = AlertType(msg.get("alert_type"))
                        alerts_manager.toggle(at, msg.get("enabled",True))
                        await websocket.send_text(json.dumps({
                            "type":"alert_toggled",
                            "alert_type":msg.get("alert_type"),
                            "enabled":msg.get("enabled",True)}))
                    except ValueError:
                        pass

                elif action == "toggle_signal":
                    signals_engine.toggle_signal_type(
                        msg.get("signal_type",""), msg.get("enabled",True))

                elif action == "ping":
                    await websocket.send_text(json.dumps({"type":"pong"}))

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("❌ Dashboard disconnected")
    except Exception as e:
        ws_manager.disconnect(websocket)
        logger.error(f"WS error: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)