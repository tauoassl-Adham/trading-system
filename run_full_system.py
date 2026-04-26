import sys
import os
import time

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.event_bus import event_bus
from app.market.market_state import MarketState
from app.analytics.analytics_engine import AnalyticsEngine
from app.strategy.strategy_engine import StrategyEngine
from app.risk.risk_manager import RiskManager
from app.execution.paper_trader import PaperTrader

# 1. تشغيل جميع المحركات
market = MarketState(event_bus)
analytics = AnalyticsEngine(event_bus)
strategy = StrategyEngine(event_bus)
risk = RiskManager(event_bus)
execution = PaperTrader(event_bus)

print("✅ --- ALL ENGINES ARE LIVE ---")

# 2. محاكاة فرصة SMC مكتملة مع اهتزاز تسلا
def simulate_perfect_setup():
    # إرسال بيانات الهيكل (Core 70%)
    event_bus.publish("market_structure_update", {
        "core": {
            "symbol": "BTCUSDT",
            "smc_valid": True,
            "liquidity_sweep": True,
            "bias": "BUY",
            "entry_price": 50000,
            "order_block": {"high": 50000, "low": 49000} # الوقف سيكون 49000
        }
    })
    
    # إرسال تكة سعرية لتحفيز تسلا (Confirmers 30%)
    # الرقم 50004 جذره الرقمي هو 9 (5+0+0+0+4=9) - اهتزاز تسلا
    event_bus.publish("tick", {"price": 50004})

    # محاكاة حركة السعر لضرب الهدف (60000)
    time.sleep(1)
    print("... Moving price to target ...")
    event_bus.publish("tick", {"price": 52000}) # الهدف هو Entry + (Diff*2) = 52000

if __name__ == "__main__":
    simulate_perfect_setup()