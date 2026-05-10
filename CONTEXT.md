# SCYLLA TRADING PLATFORM — Master Context
**Version:** 4.0 | **Stack:** Python FastAPI + HTML/JS | **Data:** Binance + Finnhub + GNews

---

## 🏗️ المعمارية العامة

```
Binance WebSocket (Live Prices + Klines)
         ↓
    EventBus (pub/sub singleton)
    ├── CandleEngine      → candle_closed_{tf}
    ├── MarketState       → swing detection
    ├── SMCEngine         → smc_analysis (1H trigger)
    ├── SignalsEngine     → trade_signal + alerts
    ├── StrategyEngine    → bias + confirmers
    ├── RiskManager       → position sizing
    └── PaperExecutor     → paper trades

GNews API (Arabic) + Finnhub (EN Institutional)
         ↓
    NewsEngine → news_update → WebSocket → Dashboard

AI Engine (Gemini 2.0 Flash)
    ├── analyze_market()     → SMC signals
    ├── analyze_psychology() → trader state
    ├── chat()               → dashboard chat
    └── explain_signal()     → Telegram messages

AlertsManager → Telegram Bot + WebSocket Toast + Sound
```

---

## 📁 هيكل الملفات الكامل

```
D:\trading-system\
├── .env                          ← SECRETS (لا يُرفع)
│   ├── GEMINI_API_KEY
│   ├── TELEGRAM_BOT_TOKEN
│   ├── TELEGRAM_CHAT_ID
│   ├── FINNHUB_API_KEY
│   └── GNEWS_API_KEY
│
├── app/
│   ├── core/
│   │   ├── event_bus.py          ← Singleton pub/sub
│   │   ├── ws_manager.py         ← WebSocket connections
│   │   └── database.py           ← SQLite trade logger
│   │
│   ├── data/
│   │   ├── websocket_client.py   ← Binance WS stream
│   │   └── data_store.py         ← Candles + RSI + SMA
│   │
│   ├── market/
│   │   ├── candle_engine.py      ← Multi-TF candles (5m→1w)
│   │   ├── market_state.py       ← ATR + Swings + CHoCH
│   │   ├── market_structure.py   ← HH/HL/LH/LL detection
│   │   └── market_snapshot.py    ← Price + trend snapshot
│   │
│   ├── strategy/
│   │   ├── smc_engine.py         ← SMC full engine (Phase 1-4)
│   │   ├── signals_engine.py     ← Signal filtering + lifecycle
│   │   ├── ai_engine.py          ← Gemini 2.0 Flash wrapper
│   │   ├── news_engine.py        ← GNews AR + Finnhub + RSS
│   │   ├── strategy_engine.py    ← Score + bias engine
│   │   ├── base_strategy.py      ← Abstract base
│   │   └── trend_following.py    ← Simple trend strategy
│   │
│   ├── risk/
│   │   └── risk_manager.py       ← Position sizing (1% risk)
│   │
│   ├── execution/
│   │   ├── paper_executor.py     ← Simulated execution
│   │   ├── paper_trader.py       ← SL/TP monitoring
│   │   └── base_executor.py      ← Abstract base
│   │
│   ├── portfolio/
│   │   └── portfolio_manager.py  ← DCA + multi-portfolio
│   │
│   ├── alerts/
│   │   └── alerts_manager.py     ← Telegram + Toast + Sound
│   │
│   └── analytics/
│       ├── analytics_engine.py   ← Tesla vibration (legacy)
│       └── behavioral_engine.py  ← Win rate + performance
│
├── backend/
│   └── app.py                    ← FastAPI main (port 8000)
│
└── frontend/
    ├── dashboard.html             ← Main UI
    ├── css/
    │   └── styles.css
    └── js/
        ├── config.js              ← State + constants
        ├── chart.js               ← TradingView LW Charts v4
        ├── market.js              ← Binance WS + news fetch
        ├── ui.js                  ← OrderBook + Feed + Trade
        ├── strategy.js            ← SMC page render
        ├── alerts.js              ← Toast + Sound + Ticker
        └── app.js                 ← Init + Nav + Theme
```

---

## 🔌 API Endpoints الرئيسية

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | System health |
| GET | `/api/candles/{symbol}/{interval}` | Historical candles |
| GET | `/api/ticker/24h/{symbol}` | 24h stats |
| GET | `/api/smc/{symbol}/analyze` | SMC analysis |
| GET | `/api/signals/active` | Active signals |
| GET | `/api/signals/history` | Signal history |
| POST | `/api/signals/toggle/{type}` | Enable/disable signal |
| GET | `/api/alerts/config` | Alerts settings |
| POST | `/api/alerts/toggle/{type}` | Enable/disable alert |
| GET | `/api/news` | Latest news (AR) |
| GET | `/api/news/important` | Important news only |
| POST | `/api/ai/chat` | AI chat |
| POST | `/api/ai/analyze-market` | Market analysis |
| WS | `/ws/dashboard` | Real-time feed |

---

## 📡 WebSocket Events (Backend → Frontend)

| Event Type | Description |
|------------|-------------|
| `news_update` | أخبار جديدة عربية |
| `smc_analysis` | تحليل SMC جديد |
| `trade_signal` | إشارة تداول |
| `choch_detected` | تغيير هيكل |
| `bos_detected` | كسر هيكل |
| `signal_closed` | إشارة مغلقة (SL/TP) |
| `alert` | تنبيه للداشبورد |
| `candles` | بيانات شموع |
| `ai_response` | رد الذكاء الاصطناعي |

---

## ⚙️ الإعدادات الحالية

| Setting | Value |
|---------|-------|
| Paper Capital | $10,000 |
| Risk per trade | 1% |
| SMC Symbols | BTCUSDT, ETHUSDT, BNBUSDT |
| SMC Trigger | Every 1H close |
| News Interval | 15 min (96 req/day) |
| AI Model | gemini-2.0-flash |
| AI Daily Quota | 1500 req/day |
| Telegram Target | @AdhamAbuoHamuod |

---

## 🚦 حالة المشروع

### ✅ مكتمل
- TradingView Lightweight Charts v4 (شموع + Volume + MA20/50/100/200 + RSI)
- SMC Engine (SwingDetector + StructureAnalyzer + OB + FVG + Liquidity)
- Signals Engine (فلترة + lifecycle + SL/TP auto-close)
- Alerts System (Telegram + Toast + Sound + تخصيص كامل)
- News Ticker (GNews AR + Finnhub EN institutional)
- AI Engine (Gemini 2.0 Flash + Smart Quota)
- Multi-language (AR/EN) + Dark/Light theme
- 12/24h clock toggle
- Order Book (simulated)
- Paper Trading panel

### 🔄 قيد التطوير
- Trading Engine (Market/Limit/Stop Orders + SL/TP Auto)
- Drawing Tools (canvas overlay)
- Portfolio Manager (multi-portfolio)
- Psychology Tracker
- Backtesting Engine
- Macro/News Analysis Page
- On-Chain Data

---

## 🛠️ تشغيل المشروع

```bash
cd D:\trading-system
venv\Scripts\activate
pip install fastapi uvicorn websockets httpx google-genai python-dotenv
python backend\app.py
# → http://127.0.0.1:8000
```

---

## 📝 قواعد التطوير

1. كل ملف جديد يُضاف لـ CONTEXT.md فوراً
2. الـ `.env` لا يُرفع أبداً على GitHub
3. كل تعديل = ذكر المسار الكامل أولاً
4. الملفات الكبيرة تُرسل بـ `bash_tool` لا `create_file`
5. رقم السطر مطلوب في كل تعديل