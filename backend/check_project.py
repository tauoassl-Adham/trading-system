import os
import importlib

def check_project():
    print("--- 🔍 Scylla System Diagnostics ---")
    
    # 1. قائمة الملفات المتوقعة
    required_files = [
        "app/main.py",
        "app/core/event_bus.py",
        "app/data/websocket_client.py",
        "app/market/candle_engine.py",
        "app/market/market_state.py",
        "app/strategy/strategy_engine.py"
    ]
    
    # 2. فحص وجود الملفات
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ Found: {file_path}")
        else:
            print(f"❌ Missing: {file_path}")

    # 3. فحص إمكانية استيراد الكلاسات (Imports Test)
    print("\n--- 📦 Imports Check ---")
    modules = ["app.main", "app.core.event_bus", "app.market.market_state"]
    for mod in modules:
        try:
            importlib.import_module(mod)
            print(f"✅ Can import: {mod}")
        except Exception as e:
            print(f"❌ Failed to import {mod}: {e}")

if __name__ == "__main__":
    check_project()