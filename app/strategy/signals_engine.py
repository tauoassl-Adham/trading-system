"""
╔══════════════════════════════════════════════════════════════════╗
║         SCYLLA SIGNALS ENGINE — محرك الإشارات المؤسسي           ║
║         يربط SMC Engine + AI Engine + Alerts Manager            ║
╚══════════════════════════════════════════════════════════════════╝

المهام:
  - استقبال تحليل SMC من smc_engine
  - تصفية الإشارات بناءً على الجودة والشروط
  - إرسال إشعارات للتيليغرام والداشبورد
  - تتبع الإشارات النشطة ومراقبتها
  - تفعيل/إيقاف أنواع الإشارات
"""

import logging
import asyncio
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
#  SIGNAL DATA CLASS
# ══════════════════════════════════════════════
@dataclass
class Signal:
    id:          str
    symbol:      str
    bias:        str           # BUY | SELL | NO_TRADE
    poi_price:   float
    sl:          float
    tp1:         float
    tp2:         float
    tp3:         float
    confidence:  float
    reason:      str
    trend_1d:    str
    trend_4h:    str
    trend_1h:    str
    aligned:     bool
    bos:         bool
    choch:       bool
    choch_type:  str
    timestamp:   datetime = field(default_factory=datetime.utcnow)
    status:      str = "ACTIVE"   # ACTIVE | HIT_TP1 | HIT_TP2 | HIT_TP3 | HIT_SL | EXPIRED
    ai_analysis: dict = field(default_factory=dict)


# ══════════════════════════════════════════════
#  SIGNALS ENGINE
# ══════════════════════════════════════════════
class SignalsEngine:
    """
    المحرك المركزي للإشارات.
    يستقبل من SMC ويرسل للـ Alerts + Dashboard
    """

    # إعدادات الفلترة
    MIN_CONFIDENCE   = 0.55    # الحد الأدنى للثقة
    REQUIRE_ALIGNED  = True    # يشترط توافق الـ timeframes
    MIN_RR           = 1.5     # الحد الأدنى لنسبة Risk/Reward

    def __init__(self, event_bus, alerts_manager=None, ai_engine=None):
        self.event_bus      = event_bus
        self.alerts         = alerts_manager
        self.ai             = ai_engine
        self.active_signals = {}   # symbol → Signal
        self.history        = []
        self.enabled        = True

        # إعدادات أنواع الإشارات — قابلة للتغيير من الداشبورد
        self.signal_settings = {
            "entry":   True,
            "exit":    True,
            "choch":   True,
            "bos":     True,
            "warning": True,
        }

        # الاشتراك في أحداث SMC
        self.event_bus.subscribe("smc_analysis", self._on_smc_analysis)
        self.event_bus.subscribe("tick",         self._on_tick)

        logger.info("✅ SignalsEngine initialized — watching SMC events")

    # ══════════════════════════════════════════
    #  استقبال تحليل SMC
    # ══════════════════════════════════════════
    def _on_smc_analysis(self, data: dict):
        """يُستدعى من SMC Engine عند كل تحليل"""
        asyncio.create_task(self._process_smc(data))

    async def _process_smc(self, data: dict):
        if not self.enabled:
            return

        symbol = data.get("symbol", "BTCUSDT")
        bias   = data.get("bias", "NO_TRADE")

        # ── تنبيهات CHoCH و BOS (بغض النظر عن الـ bias) ──
        if data.get("choch") and self.signal_settings["choch"]:
            await self._fire_choch(symbol, data)

        if data.get("bos") and self.signal_settings["bos"]:
            await self._fire_bos(symbol, data)

        # ── إشارة دخول ──
        if bias in ("BUY", "SELL") and self.signal_settings["entry"]:
            await self._process_entry_signal(symbol, data)

    # ══════════════════════════════════════════
    #  معالجة إشارة الدخول
    # ══════════════════════════════════════════
    async def _process_entry_signal(self, symbol: str, data: dict):
        """فلترة وإرسال إشارة الدخول"""

        # فلتر 1: الثقة
        conf = data.get("confidence", 0)
        if conf < self.MIN_CONFIDENCE:
            logger.debug(f"[{symbol}] Signal rejected — low confidence: {conf:.0%}")
            return

        # فلتر 2: التوافق
        if self.REQUIRE_ALIGNED and not data.get("aligned", False):
            logger.debug(f"[{symbol}] Signal rejected — timeframes not aligned")
            return

        # فلتر 3: Risk/Reward
        entry = data.get("poi_price", 0)
        sl    = data.get("sl", 0)
        tp1   = data.get("tp1", 0)
        if entry and sl and tp1:
            rr = abs(tp1-entry) / abs(sl-entry) if sl != entry else 0
            if rr < self.MIN_RR:
                logger.debug(f"[{symbol}] Signal rejected — low RR: {rr:.2f}")
                return

        # ── تحليل AI اختياري ──
        ai_data = {}
        if self.ai:
            try:
                ai_data = await self.ai.analyze_market({
                    "symbol":   symbol,
                    "price":    entry,
                    "trend_1d": data.get("trend_1d"),
                    "trend_4h": data.get("trend_4h"),
                    "trend_1h": data.get("trend_1h"),
                    "bos":      data.get("bos"),
                    "choch":    data.get("choch"),
                    "ob_high":  data.get("ob",{}).get("high",0) if data.get("ob") else 0,
                    "ob_low":   data.get("ob",{}).get("low",0) if data.get("ob") else 0,
                })
                # إذا AI رفض الإشارة مع ثقة عالية — نتجاهل
                if ai_data.get("verdict") == "NO_TRADE" and ai_data.get("confidence",0) > 0.8:
                    logger.info(f"[{symbol}] Signal rejected by AI")
                    return
            except Exception as e:
                logger.warning(f"AI analysis skipped: {e}")

        # ── بناء الإشارة ──
        import uuid
        signal = Signal(
            id         = str(uuid.uuid4())[:8],
            symbol     = symbol,
            bias       = data.get("bias"),
            poi_price  = entry,
            sl         = sl,
            tp1        = tp1,
            tp2        = data.get("tp2", 0),
            tp3        = data.get("tp3", 0),
            confidence = conf,
            reason     = data.get("reason", ""),
            trend_1d   = data.get("trend_1d", "NEUTRAL"),
            trend_4h   = data.get("trend_4h", "NEUTRAL"),
            trend_1h   = data.get("trend_1h", "NEUTRAL"),
            aligned    = data.get("aligned", False),
            bos        = data.get("bos", False),
            choch      = data.get("choch", False),
            choch_type = data.get("choch_type", ""),
            ai_analysis= ai_data,
        )

        # حفظ الإشارة
        self.active_signals[symbol] = signal
        self.history.append(signal)

        # نشر للـ EventBus
        self.event_bus.publish("trade_signal", self._signal_to_dict(signal))

        # إرسال التنبيه
        if self.alerts:
            await self.alerts.signal_entry(symbol, self._signal_to_dict(signal))

        logger.info(
            f"✅ SIGNAL [{signal.bias}] {symbol} @ {signal.poi_price:.2f} "
            f"| SL:{signal.sl:.2f} | TP1:{signal.tp1:.2f} "
            f"| Conf:{signal.confidence:.0%}"
        )

    # ══════════════════════════════════════════
    #  CHoCH Alert
    # ══════════════════════════════════════════
    async def _fire_choch(self, symbol: str, data: dict):
        choch_data = {
            "choch_type": data.get("choch_type", ""),
            "price":      data.get("poi_price", 0),
            "timeframe":  "1H",
            "trend_1d":   data.get("trend_1d"),
            "trend_4h":   data.get("trend_4h"),
        }
        self.event_bus.publish("choch_detected", {
            "symbol": symbol, **choch_data
        })
        if self.alerts:
            await self.alerts.signal_choch(symbol, choch_data)
        logger.info(f"⚡ CHoCH detected: {symbol} — {choch_data['choch_type']}")

    # ══════════════════════════════════════════
    #  BOS Alert
    # ══════════════════════════════════════════
    async def _fire_bos(self, symbol: str, data: dict):
        bos_data = {
            "direction":  data.get("bias", ""),
            "price":      data.get("poi_price", 0),
            "timeframe":  "1H",
        }
        self.event_bus.publish("bos_detected", {
            "symbol": symbol, **bos_data
        })
        if self.alerts:
            await self.alerts.signal_bos(symbol, bos_data)
        logger.info(f"📐 BOS detected: {symbol}")

    # ══════════════════════════════════════════
    #  مراقبة الإشارات النشطة (SL/TP Auto)
    # ══════════════════════════════════════════
    def _on_tick(self, data: dict):
        """يراقب الأسعار لإغلاق الإشارات عند SL/TP"""
        symbol = data.get("symbol")
        price  = data.get("price", 0)
        signal = self.active_signals.get(symbol)
        if not signal or signal.status != "ACTIVE":
            return
        asyncio.create_task(self._check_signal_levels(signal, price))

    async def _check_signal_levels(self, signal: Signal, price: float):
        if signal.bias == "BUY":
            if price <= signal.sl:
                await self._close_signal(signal, "HIT_SL", price)
            elif signal.tp3 and price >= signal.tp3:
                await self._close_signal(signal, "HIT_TP3", price)
            elif signal.tp2 and price >= signal.tp2:
                await self._update_signal(signal, "HIT_TP2", price)
            elif price >= signal.tp1:
                await self._update_signal(signal, "HIT_TP1", price)
        elif signal.bias == "SELL":
            if price >= signal.sl:
                await self._close_signal(signal, "HIT_SL", price)
            elif signal.tp3 and price <= signal.tp3:
                await self._close_signal(signal, "HIT_TP3", price)
            elif signal.tp2 and price <= signal.tp2:
                await self._update_signal(signal, "HIT_TP2", price)
            elif price <= signal.tp1:
                await self._update_signal(signal, "HIT_TP1", price)

    async def _close_signal(self, signal: Signal, status: str, price: float):
        signal.status = status
        self.active_signals.pop(signal.symbol, None)

        pnl_pct = 0
        if signal.poi_price:
            if signal.bias == "BUY":
                pnl_pct = (price - signal.poi_price) / signal.poi_price * 100
            else:
                pnl_pct = (signal.poi_price - price) / signal.poi_price * 100

        emoji  = "✅" if "TP" in status else "❌"
        msg    = f"{emoji} {status} — {signal.symbol} | PnL: {pnl_pct:+.2f}%"

        self.event_bus.publish("signal_closed", {
            "signal_id": signal.id,
            "symbol":    signal.symbol,
            "status":    status,
            "price":     price,
            "pnl_pct":   pnl_pct,
        })
        if self.alerts:
            await self.alerts.signal_exit(signal.symbol, {
                "status":   status,
                "price":    price,
                "pnl_pct":  pnl_pct,
                "reason":   msg,
            })
        logger.info(f"🔴 Signal closed: {msg}")

    async def _update_signal(self, signal: Signal, status: str, price: float):
        """تحديث حالة الإشارة عند TP1/TP2 بدون إغلاق"""
        if signal.status == status:
            return
        signal.status = status
        self.event_bus.publish("signal_updated", {
            "signal_id": signal.id,
            "symbol":    signal.symbol,
            "status":    status,
            "price":     price,
        })
        logger.info(f"📊 Signal updated: {signal.symbol} → {status} @ {price:.2f}")

    # ══════════════════════════════════════════
    #  API للداشبورد
    # ══════════════════════════════════════════
    def get_active_signals(self) -> list:
        return [self._signal_to_dict(s) for s in self.active_signals.values()]

    def get_history(self, limit=50) -> list:
        return [self._signal_to_dict(s) for s in self.history[-limit:]]

    def toggle_signal_type(self, signal_type: str, enabled: bool):
        if signal_type in self.signal_settings:
            self.signal_settings[signal_type] = enabled
            logger.info(f"Signal type '{signal_type}': {'ON' if enabled else 'OFF'}")

    def update_filters(self, min_confidence: float = None,
                       require_aligned: bool = None,
                       min_rr: float = None):
        if min_confidence is not None:
            self.MIN_CONFIDENCE = min_confidence
        if require_aligned is not None:
            self.REQUIRE_ALIGNED = require_aligned
        if min_rr is not None:
            self.MIN_RR = min_rr
        logger.info(
            f"Filters updated — Conf:{self.MIN_CONFIDENCE:.0%} "
            f"| Aligned:{self.REQUIRE_ALIGNED} | RR:{self.MIN_RR}"
        )

    def _signal_to_dict(self, s: Signal) -> dict:
        return {
            "id":         s.id,
            "symbol":     s.symbol,
            "bias":       s.bias,
            "poi_price":  s.poi_price,
            "sl":         s.sl,
            "tp1":        s.tp1,
            "tp2":        s.tp2,
            "tp3":        s.tp3,
            "confidence": s.confidence,
            "reason":     s.reason,
            "trend_1d":   s.trend_1d,
            "trend_4h":   s.trend_4h,
            "trend_1h":   s.trend_1h,
            "aligned":    s.aligned,
            "bos":        s.bos,
            "choch":      s.choch,
            "status":     s.status,
            "timestamp":  s.timestamp.isoformat(),
        }