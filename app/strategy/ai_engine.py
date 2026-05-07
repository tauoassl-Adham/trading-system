"""
╔══════════════════════════════════════════════════════════════════╗
║         SCYLLA AI ENGINE — Powered by Google Gemini             ║
║         المحرك الذكي المؤسسي — أساس كل تحليل في المنصة         ║
╚══════════════════════════════════════════════════════════════════╝

المهام:
  - تحليل السوق والهيكل
  - تحليل الأخبار والماكرو
  - توليد إشارات التداول
  - تحليل الحالة النفسية للتاجر
  - شرح الإشارات وتبريرها
  - الإجابة على أسئلة التحليل
"""

import os
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("⚠️  GEMINI_API_KEY not found in .env")

genai.configure(api_key=GEMINI_API_KEY)

# ── System Prompt المؤسسي ─────────────────────
SCYLLA_SYSTEM_PROMPT = """
أنت "Scylla AI" — محلل مؤسسي متخصص في أسواق العملات الرقمية.
هويتك: نظام ذكاء اصطناعي مدمج في منصة تداول مؤسسية اسمها Scylla.

خبراتك:
- Smart Money Concepts (SMC): BOS, CHoCH, Order Blocks, FVG, Liquidity
- التحليل Top-Down: 1D → 4H → 1H → 15m
- تحليل الماكرو: DXY, Federal Reserve, سياسة الفائدة
- إدارة المخاطر المؤسسية: Position Sizing, Portfolio Management
- تحليل المشاعر والسيكولوجيا النفسية للتاجر
- قراءة الأخبار الاقتصادية وتأثيرها على السوق

قواعدك الصارمة:
1. الدقة أولاً — لا تخمن، إذا لم تكن متأكداً قل ذلك
2. إدارة المخاطر فوق كل شيء — دائماً اذكر SL
3. كن محدداً — أسعار دقيقة، نسب واضحة
4. اللغة: أجب بنفس لغة السؤال (عربي أو إنجليزي)
5. الإيجاز المؤسسي — لا حشو، معلومات مباشرة ومفيدة
"""


# ══════════════════════════════════════════════
#  AI ENGINE CLASS
# ══════════════════════════════════════════════
class ScyllaAIEngine:
    """
    المحرك الذكي المركزي للمنصة.
    يُستخدم من كل الأقسام: SMC, Alerts, Portfolio, Psychology
    """

    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",  # مجاني وسريع
            system_instruction=SCYLLA_SYSTEM_PROMPT,
        )
        self.chat_session = None
        self._init_chat()
        logger.info("✅ Scylla AI Engine initialized — Gemini 1.5 Flash")

    def _init_chat(self):
        """تهيئة جلسة المحادثة مع الذاكرة"""
        self.chat_session = self.model.start_chat(history=[])

    # ══════════════════════════════════════════
    #  1. تحليل السوق العام
    # ══════════════════════════════════════════
    async def analyze_market(self, market_data: dict) -> dict:
        """
        تحليل شامل للسوق بناءً على بيانات الشموع والمؤشرات
        
        market_data: {
            symbol, price, trend_1d, trend_4h, trend_1h,
            bos, choch, ob_high, ob_low, rsi, volume_ratio
        }
        """
        prompt = f"""
        حلل السوق التالي وأعطني حكماً مؤسسياً:

        الرمز: {market_data.get('symbol', 'BTCUSDT')}
        السعر الحالي: {market_data.get('price', 0)}
        
        الهيكل:
        - اتجاه 1D: {market_data.get('trend_1d', 'NEUTRAL')}
        - اتجاه 4H: {market_data.get('trend_4h', 'NEUTRAL')}
        - اتجاه 1H: {market_data.get('trend_1h', 'NEUTRAL')}
        
        الأحداث:
        - BOS: {market_data.get('bos', False)}
        - CHoCH: {market_data.get('choch', False)}
        - Order Block: {market_data.get('ob_high', 0)} - {market_data.get('ob_low', 0)}
        - RSI: {market_data.get('rsi', 50)}
        
        المطلوب (JSON فقط):
        {{
            "verdict": "BUY/SELL/NO_TRADE",
            "confidence": 0.0-1.0,
            "reasoning": "سبب موجز",
            "key_levels": {{"entry": 0, "sl": 0, "tp1": 0, "tp2": 0}},
            "risk_warning": "تحذير إن وجد",
            "market_phase": "ACCUMULATION/DISTRIBUTION/MARKUP/MARKDOWN"
        }}
        """
        try:
            result = await self._ask(prompt)
            parsed = self._parse_json(result)
            logger.info(f"🤖 AI Market Analysis: {parsed.get('verdict')} | Conf: {parsed.get('confidence')}")
            return parsed
        except Exception as e:
            logger.error(f"AI market analysis failed: {e}")
            return {"verdict": "NO_TRADE", "confidence": 0, "reasoning": str(e)}

    # ══════════════════════════════════════════
    #  2. تحليل الأخبار والماكرو
    # ══════════════════════════════════════════
    async def analyze_news(self, news_items: list) -> dict:
        """
        تحليل الأخبار الاقتصادية وتأثيرها على السوق
        
        news_items: [{"title": str, "source": str, "time": str}]
        """
        if not news_items:
            return {"sentiment": "NEUTRAL", "impact": "LOW", "summary": "لا أخبار"}

        news_text = "\n".join([
            f"- {n.get('title')} ({n.get('source', '')})"
            for n in news_items[:10]
        ])

        prompt = f"""
        حلل هذه الأخبار الاقتصادية وتأثيرها على BTC والعملات الرقمية:

        {news_text}

        المطلوب (JSON فقط):
        {{
            "sentiment": "BULLISH/BEARISH/NEUTRAL",
            "impact": "HIGH/MEDIUM/LOW",
            "summary": "ملخص موجز بجملة واحدة",
            "key_event": "الحدث الأهم",
            "crypto_impact": "تأثير مباشر على السوق",
            "recommendation": "انتظر/ادخل/اخرج"
        }}
        """
        try:
            result = await self._ask(prompt)
            return self._parse_json(result)
        except Exception as e:
            logger.error(f"AI news analysis failed: {e}")
            return {"sentiment": "NEUTRAL", "impact": "LOW", "summary": str(e)}

    # ══════════════════════════════════════════
    #  3. تحليل الحالة النفسية
    # ══════════════════════════════════════════
    async def analyze_psychology(self, trading_data: dict) -> dict:
        """
        مراقبة الحالة النفسية للتاجر بناءً على سلوكه
        
        trading_data: {
            trades_today, win_rate, avg_hold_time,
            revenge_trades, overtrading, consecutive_losses
        }
        """
        prompt = f"""
        حلل الحالة النفسية لهذا التاجر بناءً على بياناته:

        صفقات اليوم: {trading_data.get('trades_today', 0)}
        نسبة الفوز: {trading_data.get('win_rate', 0)}%
        متوسط مدة الصفقة: {trading_data.get('avg_hold_time', 0)} دقيقة
        صفقات انتقامية محتملة: {trading_data.get('revenge_trades', 0)}
        تداول مفرط: {trading_data.get('overtrading', False)}
        خسائر متتالية: {trading_data.get('consecutive_losses', 0)}

        المطلوب (JSON فقط):
        {{
            "state": "OPTIMAL/STRESSED/REVENGE/OVERTRADING/FEARFUL",
            "risk_level": "LOW/MEDIUM/HIGH/CRITICAL",
            "recommendation": "نصيحة عملية",
            "should_stop": true/false,
            "message": "رسالة شخصية للتاجر"
        }}
        """
        try:
            result = await self._ask(prompt)
            parsed = self._parse_json(result)
            if parsed.get('should_stop'):
                logger.warning(f"⚠️  Psychology Alert: {parsed.get('state')}")
            return parsed
        except Exception as e:
            logger.error(f"AI psychology analysis failed: {e}")
            return {"state": "UNKNOWN", "risk_level": "MEDIUM", "recommendation": str(e)}

    # ══════════════════════════════════════════
    #  4. شرح الإشارة
    # ══════════════════════════════════════════
    async def explain_signal(self, signal: dict) -> str:
        """
        شرح إشارة التداول بلغة مؤسسية واضحة
        للإرسال عبر التيليغرام
        """
        prompt = f"""
        اشرح هذه الإشارة بشكل مؤسسي موجز لإرسالها عبر تيليغرام:

        الرمز: {signal.get('symbol')}
        النوع: {signal.get('bias')}
        POI: {signal.get('poi_price')}
        SL: {signal.get('sl')}
        TP1: {signal.get('tp1')}
        TP2: {signal.get('tp2')}
        TP3: {signal.get('tp3')}
        Confidence: {signal.get('confidence', 0)*100:.0f}%
        السبب: {signal.get('reason', '')}

        اكتب رسالة تيليغرام احترافية باللغة العربية،
        موجزة (5-7 أسطر)، تشمل: الإشارة، المستويات، التبرير، تحذير المخاطر.
        """
        try:
            return await self._ask(prompt)
        except Exception as e:
            return f"⚠️ فشل شرح الإشارة: {e}"

    # ══════════════════════════════════════════
    #  5. محادثة حرة (Chat)
    # ══════════════════════════════════════════
    async def chat(self, message: str) -> str:
        """
        محادثة حرة مع المحلل الذكي
        يستخدم في واجهة الداشبورد
        """
        try:
            response = await asyncio.to_thread(
                self.chat_session.send_message, message
            )
            return response.text
        except Exception as e:
            logger.error(f"AI chat failed: {e}")
            return f"⚠️ خطأ: {e}"

    # ══════════════════════════════════════════
    #  6. تحليل المحفظة
    # ══════════════════════════════════════════
    async def analyze_portfolio(self, portfolio: dict) -> dict:
        """
        تحليل أداء المحفظة وتقديم توصيات
        """
        prompt = f"""
        حلل هذه المحفظة وقدم توصيات مؤسسية:

        رأس المال: {portfolio.get('capital', 0)} USDT
        P&L اليوم: {portfolio.get('daily_pnl', 0)} USDT
        P&L الإجمالي: {portfolio.get('total_pnl', 0)} USDT
        نسبة الفوز: {portfolio.get('win_rate', 0)}%
        Drawdown أقصى: {portfolio.get('max_drawdown', 0)}%
        عدد الصفقات: {portfolio.get('total_trades', 0)}
        Sharpe Ratio: {portfolio.get('sharpe', 0)}

        المطلوب (JSON فقط):
        {{
            "performance": "EXCELLENT/GOOD/AVERAGE/POOR",
            "risk_assessment": "تقييم المخاطر",
            "strengths": ["نقطة قوة 1", "نقطة قوة 2"],
            "weaknesses": ["نقطة ضعف 1"],
            "recommendations": ["توصية 1", "توصية 2"],
            "suggested_risk_per_trade": 0.0
        }}
        """
        try:
            result = await self._ask(prompt)
            return self._parse_json(result)
        except Exception as e:
            logger.error(f"AI portfolio analysis failed: {e}")
            return {"performance": "UNKNOWN", "recommendations": [str(e)]}

    # ══════════════════════════════════════════
    #  INTERNAL HELPERS
    # ══════════════════════════════════════════
    async def _ask(self, prompt: str) -> str:
        """إرسال سؤال لـ Gemini وانتظار الرد"""
        response = await asyncio.to_thread(
            self.model.generate_content, prompt
        )
        return response.text.strip()

    def _parse_json(self, text: str) -> dict:
        """استخراج JSON من رد Gemini"""
        import json
        import re
        # نحاول استخراج JSON من النص
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"raw": text}

    def reset_chat(self):
        """إعادة تعيين جلسة المحادثة"""
        self._init_chat()
        logger.info("AI chat session reset")


# ── Singleton ────────────────────────────────
_ai_engine_instance = None

def get_ai_engine(event_bus=None) -> ScyllaAIEngine:
    """
    يرجع نسخة واحدة من الـ AI Engine
    يُستخدم من كل أجزاء المنصة
    """
    global _ai_engine_instance
    if _ai_engine_instance is None:
        _ai_engine_instance = ScyllaAIEngine(event_bus)
    return _ai_engine_instance