# Trading Intelligence System (TIS)

نظام تداول ذكي يعتمد على بيانات السوق الحية من Binance.

## الميزات

- بث بيانات الأسعار الحية من Binance WebSocket
- بناء شموع متعددة الإطارات الزمنية (1m, 5m, 15m, 1h, 4h, 1d)
- تحليل هيكل السوق واكتشاف الأنماط
- استراتيجيات تداول قابلة للتوسع
- إدارة المخاطر والمراكز (قيد التطوير)
- واجهة API باستخدام FastAPI

## التثبيت

1. قم بتثبيت Python 3.8 أو أحدث
2. قم بإنشاء بيئة افتراضية:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # على Windows
   ```
3. قم بتثبيت الاعتمادات:
   ```bash
   pip install -r backend/requirements.txt
   ```

## التشغيل

لتشغيل الخادم:
```bash
uvicorn app.main:app --reload
```

سيتم تشغيل الخادم على http://localhost:8000

## الاختبارات

لتشغيل الاختبارات:
```bash
python -m unittest backend/tests/
```

## API Endpoints

- `GET /` - حالة الخادم
- `GET /snapshot` - لقطة حالة السوق (السعر، الاتجاهات)
- `GET /signals` - الإشارات النشطة من الاستراتيجيات
- `GET /risk` - حالة إدارة المخاطر
- `GET /positions` - المراكز النشطة (Paper Trading)
- `GET /trades` - سجل التداول (Paper Trading)

## البنية

- `backend/app/` - كود التطبيق الرئيسي
- `backend/app/core/` - نواة النظام (EventBus)
- `backend/app/data/` - معالجة البيانات والاتصال بـ WebSocket
- `backend/app/market/` - تحليل السوق
- `backend/app/strategy/` - الاستراتيجيات
- `backend/app/risk/` - إدارة المخاطر (قيد التطوير)
- `backend/app/portfolio/` - إدارة المراكز (قيد التطوير)
- `backend/app/execution/` - تنفيذ التداول (قيد التطوير)
- `frontend/` - واجهة المستخدم (قيد التطوير)
- `data/` - بيانات التخزين
- `logs/` - ملفات السجلات