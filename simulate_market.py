import sys
import os
import time

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.event_bus import event_bus
from app.market.market_state import MarketState

# 1. تهيئة المحرك يدوياً داخل المحاكي
market_state = MarketState(event_bus)

def on_tick_processed(data):
    print(f"✅ Feedback received from engine: {data}")

def simulate():
    print("--- 🚀 Starting Full System Simulation ---")
    
    # 2. الاشتراك في الرد
    event_bus.subscribe("tick_processed", on_tick_processed)
    
    # 3. إرسال البيانات
    for i in range(5):
        price = 2200 + i * 5
        print(f"📤 Sending tick: {price}")
        
        event_bus.publish("tick", {"price": price})
        
        time.sleep(1)
        
    print("--- ✅ Simulation Finished ---")

if __name__ == "__main__":
    simulate()