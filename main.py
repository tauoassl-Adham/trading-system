import asyncio
import logging
import uvicorn
from fastapi import FastAPI, WebSocket
from contextlib import asynccontextmanager

# استيراد المحركات (تأكد أن مجلد app بجانب هذا الملف)
from app.core.event_bus import event_bus
from app.core.ws_manager import ws_manager
from app.data.websocket_client import stream
from app.market.candle_engine import CandleEngine
from app.market.market_state import MarketState
from app.strategy.strategy_engine import StrategyEngine
from app.risk.risk_manager import RiskManager
from app.execution.paper_executor import PaperExecutor
from app.core.event_bus import EventBus
from app.strategy.strategy_engine import StrategyEngine
from app.market.simulate_market import MarketSimulator

# إعداد السجلات - تصحيح __name__
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# تأكد أن دالة البث تستخدم الـ event loop الصحيح
def broadcast_event(data):
    try:
        # تأكد من أننا نستخدم نفس الـ loop الذي يعمل عليه السيرفر
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast(data), loop)
        logger.info(f"Broadcasted: {data}") # أضفنا هذه للتأكد في التيرمنال
    except Exception as e:
        logger.error(f"Error broadcasting event: {e}")

# تعريف Lifecycle للنظام
@asynccontextmanager
async def lifespan(app: FastAPI):
    # تشغيل تدفق البيانات في الخلفية
    asyncio.create_task(stream(event_bus))
    logger.info("🚀 Scylla System: Engines Synchronized and Live Feed Active")
    yield
    # هنا يمكنك إغلاق الاتصالات إذا لزم الأمر عند الإغلاق

app = FastAPI(lifespan=lifespan)

# --- الروابط (Endpoints) ---

@app.get("/status")
async def get_status():
    return {
        "system": "Online",
        "mode": "Swing Trading - MTF",
        "active_timeframes": ["5m", "15m", "1h", "4h", "1d", "1w"]
    }

# الرابط الذي كان يعطيك 404 (أضفته لك هنا)
@app.get("/test-signal")
async def test_signal():
    test_data = {
        "action": "TEST_BUY", 
        "symbol": "GOLD", 
        "entry": 2289.76, 
        "status": "MANUAL_TEST"
    }
    await ws_manager.broadcast(test_data)
    return {"status": "Success", "message": "Signal broadcasted to dashboard!", "data": test_data}

# --- تهيئة المحركات ---
candle_engine = CandleEngine(event_bus)
market_state = MarketState(event_bus)
strategy_engine = StrategyEngine(event_bus)
risk_manager = RiskManager(event_bus, risk_per_trade=0.01, balance=10000)
paper_executor = PaperExecutor(event_bus)

# ربط الأحداث الحيوية بالبث المباشر
event_bus.subscribe("trade_signal", broadcast_event)
event_bus.subscribe("execute_order", broadcast_event)
event_bus.subscribe("candle_closed_15m", broadcast_event)

# WebSocket connection
@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    logger.info("✅ Dashboard Client Connected")
    try:
        while True:
            # الحفاظ على الاتصال مفتوحاً
            await websocket.receive_text()
    except Exception:
        ws_manager.disconnect(websocket)
        logger.info("❌ Dashboard Client Disconnected")

# تشغيل السيرفر - تصحيح __main__
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)