"""
╔══════════════════════════════════════════════════════════════════╗
║         SCYLLA SMC ENGINE — Smart Money Concepts Core           ║
║         Phase 2: Top-Down Structure Analysis (1D→4H→1H)         ║
╚══════════════════════════════════════════════════════════════════╝

المكونات:
  - SwingDetector       : يكتشف Swing Highs/Lows الحقيقية
  - StructureAnalyzer   : يكتشف BOS و CHoCH لكل timeframe
  - OrderBlockFinder    : يحدد OBs الصالحة (Fresh + Displacement)
  - FVGDetector         : يكتشف Fair Value Gaps
  - LiquidityMapper     : يرسم مناطق السيولة (Equal H/L)
  - SMCEngine           : المحرك الرئيسي — يجمع كل المكونات
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
#  DATA STRUCTURES
# ══════════════════════════════════════════════

@dataclass
class Candle:
    t: int        # timestamp (unix seconds)
    o: float      # open
    h: float      # high
    l: float      # low
    c: float      # close
    v: float = 0  # volume


@dataclass
class SwingPoint:
    price: float
    index: int
    candle_t: int
    type: str          # "high" | "low"
    swept: bool = False


@dataclass
class OrderBlock:
    type: str          # "bullish" | "bearish"
    high: float
    low: float
    origin_t: int      # timestamp الشمعة الأصلية
    timeframe: str
    mitigated: bool = False
    displacement: float = 0.0   # حجم الـ displacement بعد الـ OB
    fvg_aligned: bool = False    # هل يوجد FVG يتوافق معه


@dataclass
class FVG:
    type: str          # "bullish" | "bearish"
    top: float
    bottom: float
    origin_t: int
    timeframe: str
    filled: bool = False


@dataclass
class LiquidityZone:
    type: str          # "equal_highs" | "equal_lows" | "trendline_highs" | "trendline_lows"
    price: float
    timeframe: str
    swept: bool = False


@dataclass
class SMCAnalysis:
    """
    النتيجة الكاملة لتحليل أصل واحد —
    يُرسَل للـ StrategyEngine كحدث smc_analysis
    """
    symbol: str
    timestamp: int

    # الهيكل
    trend_1d: str = "NEUTRAL"    # BULLISH | BEARISH | NEUTRAL
    trend_4h: str = "NEUTRAL"
    trend_1h: str = "NEUTRAL"
    aligned: bool = False         # هل الـ 3 timeframes متوافقة

    # البنية
    bos_detected: bool = False
    choch_detected: bool = False
    choch_type: str = ""          # "bullish" | "bearish"

    # مناطق الاهتمام
    active_ob: Optional[OrderBlock] = None
    active_fvg: Optional[FVG] = None
    liquidity_zones: list = field(default_factory=list)

    # الإشارة النهائية
    poi_price: float = 0.0        # نقطة الدخول المقترحة
    poi_valid: bool = False        # هل الـ POI صالح (مش في liquidity pool)
    bias: str = "NO_TRADE"        # BUY | SELL | NO_TRADE

    # مستويات Risk Management
    sl: float = 0.0
    tp1: float = 0.0
    tp2: float = 0.0
    tp3: float = 0.0

    # تفاصيل للـ Alert
    reason: str = ""
    confidence: float = 0.0


# ══════════════════════════════════════════════
#  SWING DETECTOR
# ══════════════════════════════════════════════

class SwingDetector:
    """
    يكتشف Swing Highs و Swing Lows الحقيقية
    بناءً على نافذة من الشموع (lookback)
    """

    def __init__(self, lookback: int = 3):
        self.lookback = lookback  # عدد الشموع يمين ويسار للتأكيد

    def detect(self, candles: list[Candle]) -> list[SwingPoint]:
        swings = []
        n = len(candles)
        lb = self.lookback

        for i in range(lb, n - lb):
            c = candles[i]

            # Swing High: أعلى من كل الشموع يمين ويسار
            is_sh = all(c.h >= candles[i - j].h for j in range(1, lb + 1)) and \
                    all(c.h >= candles[i + j].h for j in range(1, lb + 1))

            # Swing Low: أدنى من كل الشموع يمين ويسار
            is_sl = all(c.l <= candles[i - j].l for j in range(1, lb + 1)) and \
                    all(c.l <= candles[i + j].l for j in range(1, lb + 1))

            if is_sh:
                swings.append(SwingPoint(
                    price=c.h, index=i, candle_t=c.t, type="high"
                ))
            if is_sl:
                swings.append(SwingPoint(
                    price=c.l, index=i, candle_t=c.t, type="low"
                ))

        return sorted(swings, key=lambda s: s.index)


# ══════════════════════════════════════════════
#  STRUCTURE ANALYZER — BOS & CHoCH
# ══════════════════════════════════════════════

class StructureAnalyzer:
    """
    يحلل الهيكل ويكتشف:
      - BOS  (Break of Structure) : كسر في اتجاه الترند الحالي
      - CHoCH (Change of Character): كسر عكس الترند = تغيير محتمل
    """

    def analyze(self, candles: list[Candle], swings: list[SwingPoint]) -> dict:
        result = {
            "trend": "NEUTRAL",
            "bos": False,
            "choch": False,
            "choch_type": "",
            "last_bos_price": 0.0,
        }

        if len(swings) < 4:
            return result

        # آخر 4 swing points لتحديد الترند
        recent = swings[-4:]
        highs = [s for s in recent if s.type == "high"]
        lows  = [s for s in recent if s.type == "low"]

        if len(highs) >= 2 and len(lows) >= 2:
            hh = highs[-1].price > highs[-2].price   # Higher High
            hl = lows[-1].price  > lows[-2].price    # Higher Low
            lh = highs[-1].price < highs[-2].price   # Lower High
            ll = lows[-1].price  < lows[-2].price    # Lower Low

            if hh and hl:
                result["trend"] = "BULLISH"
            elif lh and ll:
                result["trend"] = "BEARISH"

        # آخر سعر إغلاق
        last_close = candles[-1].c if candles else 0

        # BOS / CHoCH بناءً على آخر Swing High/Low
        last_high = next((s for s in reversed(swings) if s.type == "high"), None)
        last_low  = next((s for s in reversed(swings) if s.type == "low"),  None)

        if result["trend"] == "BULLISH" and last_low:
            # في ترند صاعد: كسر آخر Low = CHoCH (تحذير هبوط)
            if last_close < last_low.price:
                result["choch"] = True
                result["choch_type"] = "bearish"
                result["trend"] = "BEARISH"
                logger.info(f"CHoCH BEARISH detected @ {last_close:.2f}")

        elif result["trend"] == "BEARISH" and last_high:
            # في ترند هابط: كسر آخر High = CHoCH (تحذير صعود)
            if last_close > last_high.price:
                result["choch"] = True
                result["choch_type"] = "bullish"
                result["trend"] = "BULLISH"
                logger.info(f"CHoCH BULLISH detected @ {last_close:.2f}")

        # BOS: كسر في اتجاه الترند
        if result["trend"] == "BULLISH" and last_high:
            if last_close > last_high.price and not result["choch"]:
                result["bos"] = True
                result["last_bos_price"] = last_high.price

        elif result["trend"] == "BEARISH" and last_low:
            if last_close < last_low.price and not result["choch"]:
                result["bos"] = True
                result["last_bos_price"] = last_low.price

        return result


# ══════════════════════════════════════════════
#  ORDER BLOCK FINDER
# ══════════════════════════════════════════════

class OrderBlockFinder:
    """
    يحدد Order Blocks الصالحة:
      - Bullish OB: آخر شمعة حمراء قبل BOS صاعد قوي
      - Bearish OB: آخر شمعة خضراء قبل BOS هابط قوي
      - يتحقق من: Fresh (غير محطم) + Displacement
    """

    def __init__(self, displacement_pct: float = 0.003):
        # الحد الأدنى للـ displacement (0.3% من السعر)
        self.displacement_pct = displacement_pct

    def find(self, candles: list[Candle], trend: str, timeframe: str) -> Optional[OrderBlock]:
        if len(candles) < 5:
            return None

        n = len(candles)

        if trend == "BULLISH":
            # ابحث عن آخر شمعة هبوطية (bearish) قبل حركة صعودية قوية
            for i in range(n - 2, max(n - 30, 1), -1):
                c = candles[i]
                if c.c >= c.o:
                    continue  # شمعة صاعدة — تجاوز

                # الشمعة التالية: displacement صاعد قوي
                next_c = candles[i + 1]
                displacement = (next_c.h - next_c.l)
                threshold = c.l * self.displacement_pct

                if displacement < threshold:
                    continue

                # تحقق إن الـ OB Fresh (السعر الحالي ما كسره)
                current_price = candles[-1].c
                if current_price < c.l:
                    continue  # محطم

                ob = OrderBlock(
                    type="bullish",
                    high=c.h,
                    low=c.l,
                    origin_t=c.t,
                    timeframe=timeframe,
                    displacement=displacement
                )
                logger.info(f"Bullish OB found @ {ob.low:.2f}-{ob.high:.2f} [{timeframe}]")
                return ob

        elif trend == "BEARISH":
            # ابحث عن آخر شمعة صاعدة (bullish) قبل حركة هبوطية قوية
            for i in range(n - 2, max(n - 30, 1), -1):
                c = candles[i]
                if c.c <= c.o:
                    continue  # شمعة هبوطية — تجاوز

                next_c = candles[i + 1]
                displacement = (next_c.h - next_c.l)
                threshold = c.h * self.displacement_pct

                if displacement < threshold:
                    continue

                current_price = candles[-1].c
                if current_price > c.h:
                    continue  # محطم

                ob = OrderBlock(
                    type="bearish",
                    high=c.h,
                    low=c.l,
                    origin_t=c.t,
                    timeframe=timeframe,
                    displacement=displacement
                )
                logger.info(f"Bearish OB found @ {ob.low:.2f}-{ob.high:.2f} [{timeframe}]")
                return ob

        return None


# ══════════════════════════════════════════════
#  FVG DETECTOR
# ══════════════════════════════════════════════

class FVGDetector:
    """
    يكتشف Fair Value Gaps:
      - Bullish FVG: فجوة بين High[i-1] و Low[i+1] في حركة صاعدة
      - Bearish FVG: فجوة بين Low[i-1] و High[i+1] في حركة هبوطية
    """

    def find_latest(self, candles: list[Candle], timeframe: str) -> list[FVG]:
        fvgs = []
        n = len(candles)

        for i in range(1, n - 1):
            prev = candles[i - 1]
            curr = candles[i]
            next_c = candles[i + 1]

            # Bullish FVG: فجوة صاعدة
            if next_c.l > prev.h:
                fvg = FVG(
                    type="bullish",
                    top=next_c.l,
                    bottom=prev.h,
                    origin_t=curr.t,
                    timeframe=timeframe
                )
                # تحقق إنها ما اتملأت
                for j in range(i + 2, n):
                    if candles[j].l <= fvg.bottom:
                        fvg.filled = True
                        break
                if not fvg.filled:
                    fvgs.append(fvg)

            # Bearish FVG: فجوة هبوطية
            elif next_c.h < prev.l:
                fvg = FVG(
                    type="bearish",
                    top=prev.l,
                    bottom=next_c.h,
                    origin_t=curr.t,
                    timeframe=timeframe
                )
                for j in range(i + 2, n):
                    if candles[j].h >= fvg.top:
                        fvg.filled = True
                        break
                if not fvg.filled:
                    fvgs.append(fvg)

        return fvgs


# ══════════════════════════════════════════════
#  LIQUIDITY MAPPER
# ══════════════════════════════════════════════

class LiquidityMapper:
    """
    يرسم مناطق السيولة:
      - Equal Highs / Equal Lows (تجمع Stop Losses)
      - يحدد إذا كانت محطوفة (swept) أم لا
    """

    def __init__(self, tolerance_pct: float = 0.001):
        self.tolerance = tolerance_pct  # 0.1% تساوي في السعر

    def find_equal_levels(self, candles: list[Candle], timeframe: str) -> list[LiquidityZone]:
        zones = []
        n = len(candles)

        highs = [(i, c.h) for i, c in enumerate(candles)]
        lows  = [(i, c.l) for i, c in enumerate(candles)]

        # Equal Highs
        for i in range(len(highs) - 1):
            for j in range(i + 2, min(i + 15, len(highs))):
                price_i = highs[i][1]
                price_j = highs[j][1]
                if abs(price_i - price_j) / price_i < self.tolerance:
                    avg_price = (price_i + price_j) / 2
                    # تحقق إنها ما اتاخذت
                    swept = any(candles[k].h > avg_price * (1 + self.tolerance)
                                for k in range(j + 1, n))
                    zones.append(LiquidityZone(
                        type="equal_highs",
                        price=avg_price,
                        timeframe=timeframe,
                        swept=swept
                    ))
                    break

        # Equal Lows
        for i in range(len(lows) - 1):
            for j in range(i + 2, min(i + 15, len(lows))):
                price_i = lows[i][1]
                price_j = lows[j][1]
                if abs(price_i - price_j) / price_i < self.tolerance:
                    avg_price = (price_i + price_j) / 2
                    swept = any(candles[k].l < avg_price * (1 - self.tolerance)
                                for k in range(j + 1, n))
                    zones.append(LiquidityZone(
                        type="equal_lows",
                        price=avg_price,
                        timeframe=timeframe,
                        swept=swept
                    ))
                    break

        return zones


# ══════════════════════════════════════════════
#  RISK CALCULATOR
# ══════════════════════════════════════════════

class SMCRiskCalculator:
    """
    يحسب SL و TP1/2/3 بناءً على SMC rules:
      - SL: تحت/فوق OB الحقيقي (مش داخل liquidity pool)
      - TP1: أول مقاومة/دعم هيكلية
      - TP2: أكبر POI
      - TP3: هدف الـ macro
    """

    def calculate(self, bias: str, entry: float, ob: OrderBlock,
                  swings: list[SwingPoint], current_price: float) -> dict:

        if not ob:
            return {}

        if bias == "BUY":
            sl = ob.low * 0.9995       # أسفل الـ OB بقليل

            # TP1: أول Swing High فوق السعر الحالي
            above_highs = sorted(
                [s.price for s in swings if s.type == "high" and s.price > entry],
                key=lambda x: x
            )
            tp1 = above_highs[0] if above_highs else entry * 1.02
            tp2 = above_highs[1] if len(above_highs) > 1 else entry * 1.04
            tp3 = entry + (entry - sl) * 3   # RR 1:3

        else:  # SELL
            sl = ob.high * 1.0005

            below_lows = sorted(
                [s.price for s in swings if s.type == "low" and s.price < entry],
                key=lambda x: x, reverse=True
            )
            tp1 = below_lows[0] if below_lows else entry * 0.98
            tp2 = below_lows[1] if len(below_lows) > 1 else entry * 0.96
            tp3 = entry - (sl - entry) * 3

        rr = abs(tp1 - entry) / abs(sl - entry) if sl != entry else 0

        return {
            "sl": round(sl, 2),
            "tp1": round(tp1, 2),
            "tp2": round(tp2, 2),
            "tp3": round(tp3, 2),
            "rr": round(rr, 2)
        }


# ══════════════════════════════════════════════
#  SMC ENGINE — المحرك الرئيسي
# ══════════════════════════════════════════════

class SMCEngine:
    """
    المحرك الرئيسي للاستراتيجية.

    يستقبل الشموع المغلقة من الـ CandleEngine،
    يحلل الهيكل Top-Down (1D → 4H → 1H)،
    ويصدر حدث smc_analysis عند اكتمال التحليل.

    الاتصال بالنظام:
      event_bus.subscribe("candle_closed_1d")  → update_htf(1D)
      event_bus.subscribe("candle_closed_4h")  → update_htf(4H)
      event_bus.subscribe("candle_closed_1h")  → run_analysis() ← نقطة الإطلاق
    """

    # عدد الشموع المحفوظة لكل timeframe
    CANDLE_LIMIT = {
        "1d": 100,
        "4h": 150,
        "1h": 200,
        "15m": 300,
    }

    SUPPORTED_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

    def __init__(self, event_bus):
        self.event_bus = event_bus

        # مخزن الشموع: symbol → tf → deque[Candle]
        self.candles: dict[str, dict[str, deque]] = {
            sym: {
                tf: deque(maxlen=self.CANDLE_LIMIT.get(tf, 200))
                for tf in ["1d", "4h", "1h", "15m"]
            }
            for sym in self.SUPPORTED_SYMBOLS
        }

        # المكونات
        self.swing_detector   = SwingDetector(lookback=3)
        self.structure        = StructureAnalyzer()
        self.ob_finder        = OrderBlockFinder(displacement_pct=0.003)
        self.fvg_detector     = FVGDetector()
        self.liq_mapper       = LiquidityMapper(tolerance_pct=0.001)
        self.risk_calc        = SMCRiskCalculator()

        # آخر تحليل لكل أصل
        self.last_analysis: dict[str, SMCAnalysis] = {}

        # الاشتراك في الأحداث
        self.event_bus.subscribe("candle_closed_1d",  self._on_1d)
        self.event_bus.subscribe("candle_closed_4h",  self._on_4h)
        self.event_bus.subscribe("candle_closed_1h",  self._on_1h)
        self.event_bus.subscribe("candle_closed_15m", self._on_15m)

        logger.info("✅ SMCEngine initialized — watching: " + ", ".join(self.SUPPORTED_SYMBOLS))

    # ── candle ingestion ──────────────────────────────
    def _ingest(self, data: dict, tf: str):
        sym = data.get("symbol", "BTCUSDT")
        if sym not in self.candles:
            return
        raw = data.get("candle", {})
        if not raw:
            return
        c = Candle(
            t=int(raw.get("start_time", 0)),
            o=float(raw.get("open",  0)),
            h=float(raw.get("high",  0)),
            l=float(raw.get("low",   0)),
            c=float(raw.get("close", 0)),
            v=float(raw.get("volume", 0)),
        )
        self.candles[sym][tf].append(c)

    def _on_1d(self,  data): self._ingest(data, "1d")
    def _on_4h(self,  data): self._ingest(data, "4h")
    def _on_15m(self, data): self._ingest(data, "15m")

    def _on_1h(self, data):
        self._ingest(data, "1h")
        sym = data.get("symbol", "BTCUSDT")
        self.run_analysis(sym)   # ← يشتغل التحليل على كل إغلاق 1H

    # ── التحليل الرئيسي ──────────────────────────────
    def run_analysis(self, symbol: str) -> Optional[SMCAnalysis]:
        """
        يشغّل التحليل الكامل Top-Down للأصل المحدد.
        يصدر حدث smc_analysis إذا وُجدت إشارة.
        """
        c1d  = list(self.candles[symbol]["1d"])
        c4h  = list(self.candles[symbol]["4h"])
        c1h  = list(self.candles[symbol]["1h"])

        # نحتاج على الأقل 10 شموع في كل timeframe
        if len(c1d) < 10 or len(c4h) < 10 or len(c1h) < 10:
            logger.debug(f"[{symbol}] Not enough candles yet.")
            return None

        current_price = c1h[-1].c
        current_t     = c1h[-1].t

        analysis = SMCAnalysis(symbol=symbol, timestamp=current_t)

        # ── Phase 2: Top-Down Structure ──────────────

        # 1D
        swings_1d  = self.swing_detector.detect(c1d)
        struct_1d  = self.structure.analyze(c1d, swings_1d)
        analysis.trend_1d = struct_1d["trend"]

        # 4H
        swings_4h  = self.swing_detector.detect(c4h)
        struct_4h  = self.structure.analyze(c4h, swings_4h)
        analysis.trend_4h = struct_4h["trend"]

        # 1H
        swings_1h  = self.swing_detector.detect(c1h)
        struct_1h  = self.structure.analyze(c1h, swings_1h)
        analysis.trend_1h = struct_1h["trend"]

        # تحقق من التوافق
        trends = [analysis.trend_1d, analysis.trend_4h, analysis.trend_1h]
        analysis.aligned = len(set(trends)) == 1 and "NEUTRAL" not in trends

        if not analysis.aligned:
            analysis.bias   = "NO_TRADE"
            analysis.reason = (
                f"Structure misaligned: 1D={analysis.trend_1d} "
                f"4H={analysis.trend_4h} 1H={analysis.trend_1h}"
            )
            logger.info(f"[{symbol}] NO_TRADE — {analysis.reason}")
            self._publish(analysis)
            return analysis

        # الاتجاه المتوافق
        consensus_trend = analysis.trend_1d
        analysis.bos_detected   = struct_1h["bos"]
        analysis.choch_detected = struct_1h["choch"]
        analysis.choch_type     = struct_1h["choch_type"]

        # ── Phase 3: Order Block + FVG ───────────────

        # نبحث عن OB في الـ 4H (أقوى مستوى)
        ob = self.ob_finder.find(c4h, consensus_trend, "4h")

        # إذا ما لقينا في 4H، نجرب 1H
        if not ob:
            ob = self.ob_finder.find(c1h, consensus_trend, "1h")

        analysis.active_ob = ob

        # FVGs
        fvgs_1h = self.fvg_detector.find_latest(c1h, "1h")
        fvgs_4h = self.fvg_detector.find_latest(c4h, "4h")
        all_fvgs = fvgs_1h + fvgs_4h

        # أقرب FVG يتوافق مع الاتجاه
        if consensus_trend == "BULLISH":
            relevant_fvgs = [f for f in all_fvgs
                             if f.type == "bullish" and f.bottom < current_price]
            if relevant_fvgs:
                analysis.active_fvg = max(relevant_fvgs, key=lambda f: f.bottom)
        else:
            relevant_fvgs = [f for f in all_fvgs
                             if f.type == "bearish" and f.top > current_price]
            if relevant_fvgs:
                analysis.active_fvg = min(relevant_fvgs, key=lambda f: f.top)

        # تحديد التوافق بين OB و FVG
        if ob and analysis.active_fvg:
            fvg = analysis.active_fvg
            if consensus_trend == "BULLISH":
                ob.fvg_aligned = ob.low <= fvg.top and ob.high >= fvg.bottom
            else:
                ob.fvg_aligned = ob.high >= fvg.bottom and ob.low <= fvg.top

        # ── Liquidity Zones ──────────────────────────
        liq_1d = self.liq_mapper.find_equal_levels(c1d, "1d")
        liq_4h = self.liq_mapper.find_equal_levels(c4h, "4h")
        analysis.liquidity_zones = liq_1d + liq_4h

        # ── Phase 3: Validate POI ────────────────────
        if not ob:
            analysis.bias   = "NO_TRADE"
            analysis.reason = "No valid Order Block found"
            self._publish(analysis)
            return analysis

        # تحقق: هل الـ OB داخل Liquidity Pool غير محطوف؟
        poi_in_liquidity = False
        for lz in analysis.liquidity_zones:
            if not lz.swept:
                dist_pct = abs(lz.price - ob.low) / ob.low
                if dist_pct < 0.005:   # أقرب من 0.5%
                    poi_in_liquidity = True
                    break

        if poi_in_liquidity:
            analysis.poi_valid = False
            analysis.bias      = "NO_TRADE"
            analysis.reason    = "POI inside unswept liquidity pool — HIGH RISK"
            logger.warning(f"[{symbol}] {analysis.reason}")
            self._publish(analysis)
            return analysis

        analysis.poi_valid = True
        analysis.poi_price = (ob.high + ob.low) / 2

        # ── Phase 4: Risk Management ─────────────────
        analysis.bias = "BUY" if consensus_trend == "BULLISH" else "SELL"

        risk = self.risk_calc.calculate(
            bias=analysis.bias,
            entry=analysis.poi_price,
            ob=ob,
            swings=swings_1d + swings_4h,
            current_price=current_price
        )

        analysis.sl  = risk.get("sl",  0)
        analysis.tp1 = risk.get("tp1", 0)
        analysis.tp2 = risk.get("tp2", 0)
        analysis.tp3 = risk.get("tp3", 0)

        # Confidence Score
        score = 0.4  # base
        if analysis.aligned:          score += 0.2
        if analysis.bos_detected:     score += 0.1
        if analysis.choch_detected:   score += 0.1
        if ob and ob.fvg_aligned:     score += 0.1
        if ob and ob.displacement > 0: score += 0.1

        analysis.confidence = round(min(score, 1.0), 2)

        analysis.reason = (
            f"✅ {analysis.bias} Setup | "
            f"Trend aligned {analysis.trend_1d}/{analysis.trend_4h}/{analysis.trend_1h} | "
            f"OB {'+ FVG' if ob.fvg_aligned else ''} @ {analysis.poi_price:.2f} | "
            f"Conf: {analysis.confidence:.0%}"
        )

        logger.info(f"[{symbol}] SMC SIGNAL → {analysis.bias} @ {analysis.poi_price:.2f} | {analysis.reason}")

        self._publish(analysis)
        self.last_analysis[symbol] = analysis
        return analysis

    # ── نشر الحدث ────────────────────────────────────
    def _publish(self, analysis: SMCAnalysis):
        self.event_bus.publish("smc_analysis", {
            "symbol":      analysis.symbol,
            "timestamp":   analysis.timestamp,
            "bias":        analysis.bias,
            "trend_1d":    analysis.trend_1d,
            "trend_4h":    analysis.trend_4h,
            "trend_1h":    analysis.trend_1h,
            "aligned":     analysis.aligned,
            "bos":         analysis.bos_detected,
            "choch":       analysis.choch_detected,
            "choch_type":  analysis.choch_type,
            "poi_price":   analysis.poi_price,
            "poi_valid":   analysis.poi_valid,
            "ob": {
                "type":         analysis.active_ob.type,
                "high":         analysis.active_ob.high,
                "low":          analysis.active_ob.low,
                "fvg_aligned":  analysis.active_ob.fvg_aligned,
                "displacement": analysis.active_ob.displacement,
            } if analysis.active_ob else None,
            "fvg": {
                "type":   analysis.active_fvg.type,
                "top":    analysis.active_fvg.top,
                "bottom": analysis.active_fvg.bottom,
            } if analysis.active_fvg else None,
            "sl":          analysis.sl,
            "tp1":         analysis.tp1,
            "tp2":         analysis.tp2,
            "tp3":         analysis.tp3,
            "confidence":  analysis.confidence,
            "reason":      analysis.reason,
        })

    # ── واجهة يدوية للاختبار ─────────────────────────
    def get_last_analysis(self, symbol: str) -> Optional[SMCAnalysis]:
        return self.last_analysis.get(symbol)

    def load_historical_candles(self, symbol: str, tf: str, candles_data: list[dict]):
        """
        يحمّل شموع تاريخية مسبقاً (من REST API)
        يُستدعى عند بدء تشغيل النظام لتهيئة المحرك
        """
        if symbol not in self.candles or tf not in self.candles[symbol]:
            return
        for raw in candles_data:
            c = Candle(
                t=int(raw.get("t", 0)),
                o=float(raw.get("o", 0)),
                h=float(raw.get("h", 0)),
                l=float(raw.get("l", 0)),
                c=float(raw.get("c", 0)),
                v=float(raw.get("v", 0)),
            )
            self.candles[symbol][tf].append(c)
        logger.info(f"✅ Loaded {len(candles_data)} historical candles → {symbol} {tf}")