# Execution Engine README

## Overview
هذا الموديول يوفر محرك تنفيذ أوامر قابل للـ **Paper Trading** والربط لاحقاً مع Binance. البنية مقسمة إلى:
- **OMS**: Order Management System
- **Execution Router**: يقرر استراتيجية التنفيذ
- **Adapters**: PaperAdapter و BinanceAdapter (skeleton)
- **MarketDataProvider**: موفر بيانات سوق وهمي للاختبارات

## المتطلبات
- Python 3.9+
- مكتبات (أضفها إلى `requirements.txt` أو venv):
  - `pydantic`
  - `aiohttp`
  - `pytest`
  - `pytest-asyncio`

## ملفات رئيسية ومساراتها
- **نماذج البيانات**: `backend/app/execution/models.py`
- **محاكاة الانزلاق والـ latency**: `backend/app/execution/slippage.py`
- **OMS**: `backend/app/execution/oms.py`
- **Execution Router**: `backend/app/execution/router.py`
- **Paper Adapter**: `backend/app/execution/adapters/paper_adapter.py`
- **Binance Adapter (skeleton)**: `backend/app/execution/adapters/binance_adapter.py`
- **Mock Market Data**: `backend/app/execution/market_data/mock_market_data.py`
- **اختبارات**: `backend/app/execution/tests/*.py`
- **ملف إعدادات مثال**: `backend/app/execution/config.example.yaml`
- **سجل تدقيق**: `backend/app/execution/audit/audit_log.jsonl`
- **مخطط SQLite**: `backend/app/execution/persistence/sqlite_schema.sql`

## إعداد وتشغيل في وضع Paper Trading
1. انسخ `config.example.yaml` إلى `config.yaml` وعدّل القيم حسب الحاجة (paper_mode: true).
2. شغّل بيئة افتراضية وثبّت المتطلبات.
3. مثال تشغيل بسيط (داخل مشروعك):
   - استدعاء OMS وRouter وPaperAdapter في نقطة الدخول (script أو FastAPI background task).
   - مثال سريع في REPL:
     ```python
     from backend.app.execution.market_data.mock_market_data import MockMarketDataProvider
     from backend.app.execution.adapters.paper_adapter import PaperAdapter
     from backend.app.execution.router import ExecutionRouter
     from backend.app.execution.oms import OMS

     md = MockMarketDataProvider(initial_data={"BTCUSDT":{"mid_price":60000,"avg_depth":5}})
     adapter = PaperAdapter(market_data_provider=md)
     router = ExecutionRouter(adapter)
     oms = OMS(router)

     import asyncio
     asyncio.create_task(oms.run())
     # ثم استخدم oms.create_order(...) لإرسال أوامر للاختبار
     ```
4. تحقق من `backend/app/execution/audit/audit_log.jsonl` أو سجلات التطبيق لمتابعة الأحداث.

## تشغيل الاختبارات
- شغّل:
  ```bash
  pytest backend/app/execution/tests -q
