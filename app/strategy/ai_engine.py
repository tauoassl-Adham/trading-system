"""
╔══════════════════════════════════════════════════════════════════╗
║         SCYLLA AI ENGINE v2 — Google Gemini 2.0 Flash           ║
║         Smart Quota: 1500 req/day                                ║
║         - News batch:    144 req/day (10%)                       ║
║         - SMC signals:   100 req/day (7%)                        ║
║         - Breaking news:  50 req/day (3%)                        ║
║         - Manual/Chat:  1200 req/day (80%)                       ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import asyncio
import logging
import json
import re
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
    USE_NEW_SDK = True
except ImportError:
    USE_NEW_SDK = False
    try:
        import google.generativeai as genai_old
    except ImportError:
        genai_old = None

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("⚠️ GEMINI_API_KEY not found in .env")

SCYLLA_SYSTEM_PROMPT = """
أنت "Scylla AI" — محلل مؤسسي متخصص في أسواق العملات الرقمية.
هويتك: نظام ذكاء اصطناعي مدمج في منصة تداول مؤسسية اسمها Scylla.

خبراتك:
- Smart Money Concepts (SMC): BOS, CHoCH, Order Blocks, FVG, Liquidity
- التحليل Top-Down: 1D → 4H → 1H → 15m
- تحليل الماكرو: DXY, Federal Reserve, سياسة الفائدة
- إدارة المخاطر المؤسسية: Position Sizing, Portfolio Management
- تحليل السيكولوجيا النفسية للتاجر
- قراءة الأخبار الاقتصادية وتأثيرها على السوق

قواعدك:
1. الدقة أولاً — لا تخمن
2. إدارة المخاطر فوق كل شيء — دائماً اذكر SL
3. كن محدداً — أسعار دقيقة، نسب واضحة
4. اللغة: أجب بنفس لغة السؤال (عربي أو إنجليزي)
5. الإيجاز المؤسسي — لا حشو
"""


class ScyllaAIEngine:
    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        self.client    = None
        self.model_id  = "gemini-2.0-flash"

        # ── إحصاءات الكوتا ──
        self.quota = {
            "total_limit":   1500,
            "requests_today": 0,
            "last_reset":    date.today().isoformat(),
            "breakdown": {
                "news":      0,
                "signals":   0,
                "breaking":  0,
                "chat":      0,
                "other":     0,
            }
        }

        self._init_client()
        logger.info(f"✅ Scylla AI Engine initialized — {self.model_id}")

    def _init_client(self):
        if not GEMINI_API_KEY:
            return
        try:
            if USE_NEW_SDK:
                self.client = genai.Client(api_key=GEMINI_API_KEY)
                logger.info("✅ Gemini client ready (new SDK)")
            else:
                genai_old.configure(api_key=GEMINI_API_KEY)
                self.client = genai_old.GenerativeModel(
                    model_name=self.model_id,
                    system_instruction=SCYLLA_SYSTEM_PROMPT,
                )
        except Exception as e:
            logger.error(f"Gemini init failed: {e}")

    # ══════════════════════════════════════════
    #  إدارة الكوتا اليومية
    # ══════════════════════════════════════════
    def _check_reset(self):
        """إعادة تعيين العداد كل يوم"""
        today = date.today().isoformat()
        if self.quota["last_reset"] != today:
            self.quota["requests_today"] = 0
            self.quota["last_reset"]     = today
            for k in self.quota["breakdown"]:
                self.quota["breakdown"][k] = 0
            logger.info("🔄 Quota reset for new day")

    def _track(self, category: str = "other"):
        self._check_reset()
        self.quota["requests_today"] += 1
        if category in self.quota["breakdown"]:
            self.quota["breakdown"][category] += 1
        remaining = self.quota["total_limit"] - self.quota["requests_today"]
        logger.debug(f"📊 Quota: {self.quota['requests_today']}/{self.quota['total_limit']} | Remaining: {remaining}")

    # ══════════════════════════════════════════
    #  دالة الإرسال مع Backoff ذكي
    # ══════════════════════════════════════════
    async def _ask(self, prompt: str, category: str = "other",
                   max_retries: int = 3) -> str:
        if not self.client:
            return "{}"

        for attempt in range(max_retries):
            try:
                if USE_NEW_SDK:
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model=self.model_id,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=SCYLLA_SYSTEM_PROMPT,
                            temperature=0.3,
                            max_output_tokens=2000,
                        )
                    )
                    self._track(category)
                    return response.text.strip()
                else:
                    response = await asyncio.to_thread(
                        self.client.generate_content, prompt
                    )
                    self._track(category)
                    return response.text.strip()

            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    # Exponential backoff: 30s → 60s → 90s
                    wait = 30 * (attempt + 1)
                    logger.warning(
                        f"⚠️ Rate limit 429 — Backoff {wait}s "
                        f"(attempt {attempt+1}/{max_retries})"
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"AI _ask failed: {e}")
                    return "{}"

        logger.error("❌ Max retries reached — skipping request")
        return "{}"

    def _parse_json(self, text: str) -> dict:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"raw": text}

    # ══════════════════════════════════════════
    #  1. ترجمة الأخبار (تُستخدم من news_engine)
    # ══════════════════════════════════════════
    #async def translate_headlines(self, headlines: list[str]) -> list[str]:
        """ترجمة جماعية — طلب واحد فقط"""
        if not headlines:
            return []
        numbered = "\n".join([f"{i+1}. {h}" for i,h in enumerate(headlines)])
        prompt = f"""ترجم هذه العناوين للعربية بأسلوب برقي مختصر.
أعد JSON فقط:
{{"translations": ["الترجمة 1", "الترجمة 2"]}}

العناوين:
{numbered}"""
        try:
            result = await self._ask(prompt, category="news")
            parsed = self._parse_json(result)
            translations = parsed.get('translations', [])
            while len(translations) < len(headlines):
                translations.append(headlines[len(translations)])
            return translations[:len(headlines)]
        except Exception as e:
            logger.error(f"translate_headlines failed: {e}")
            return headlines

    # ══════════════════════════════════════════
    #  2. تحليل السوق
    # ══════════════════════════════════════════
    async def analyze_market(self, market_data: dict) -> dict:
        prompt = f"""حلل السوق (JSON فقط):
الرمز: {market_data.get('symbol','BTCUSDT')}
السعر: {market_data.get('price',0)}
1D: {market_data.get('trend_1d','NEUTRAL')} | 4H: {market_data.get('trend_4h','NEUTRAL')} | 1H: {market_data.get('trend_1h','NEUTRAL')}
BOS: {market_data.get('bos',False)} | CHoCH: {market_data.get('choch',False)} | RSI: {market_data.get('rsi',50)}

{{"verdict":"BUY/SELL/NO_TRADE","confidence":0.0,"reasoning":"سبب","key_levels":{{"entry":0,"sl":0,"tp1":0,"tp2":0}},"market_phase":"ACCUMULATION/DISTRIBUTION/MARKUP/MARKDOWN"}}"""
        try:
            return self._parse_json(await self._ask(prompt, category="signals"))
        except Exception as e:
            return {"verdict":"NO_TRADE","confidence":0,"reasoning":str(e)}

    # ══════════════════════════════════════════
    #  3. تحليل الأخبار
    # ══════════════════════════════════════════
    async def analyze_news(self, news_items: list) -> dict:
        if not news_items:
            return {"sentiment":"NEUTRAL","impact":"LOW","summary":"لا أخبار"}
        news_text = "\n".join([
            f"- {n.get('title', n.get('headline',''))}"
            for n in news_items[:10]
        ])
        prompt = f"""حلل الأخبار وتأثيرها (JSON فقط):
{news_text}

{{"sentiment":"BULLISH/BEARISH/NEUTRAL","impact":"HIGH/MEDIUM/LOW","summary":"ملخص","key_event":"الأهم","recommendation":"انتظر/ادخل/اخرج"}}"""
        try:
            return self._parse_json(await self._ask(prompt, category="news"))
        except Exception as e:
            return {"sentiment":"NEUTRAL","impact":"LOW","summary":str(e)}

    # ══════════════════════════════════════════
    #  4. تحليل الحالة النفسية
    # ══════════════════════════════════════════
    async def analyze_psychology(self, trading_data: dict) -> dict:
        prompt = f"""حلل الحالة النفسية (JSON فقط):
صفقات اليوم: {trading_data.get('trades_today',0)}
نسبة الفوز: {trading_data.get('win_rate',0)}%
خسائر متتالية: {trading_data.get('consecutive_losses',0)}
تداول مفرط: {trading_data.get('overtrading',False)}

{{"state":"OPTIMAL/STRESSED/REVENGE/OVERTRADING/FEARFUL","risk_level":"LOW/MEDIUM/HIGH/CRITICAL","recommendation":"نصيحة","should_stop":false,"message":"رسالة للتاجر"}}"""
        try:
            return self._parse_json(await self._ask(prompt, category="other"))
        except Exception as e:
            return {"state":"UNKNOWN","risk_level":"MEDIUM","recommendation":str(e)}

    # ══════════════════════════════════════════
    #  5. شرح الإشارة
    # ══════════════════════════════════════════
    async def explain_signal(self, signal: dict) -> str:
        prompt = f"""اكتب رسالة تيليغرام احترافية بالعربية (5-7 أسطر):
{signal.get('symbol')} | {signal.get('bias')} | Entry: {signal.get('poi_price')}
SL: {signal.get('sl')} | TP1: {signal.get('tp1')} | TP2: {signal.get('tp2')} | TP3: {signal.get('tp3')}
Confidence: {signal.get('confidence',0)*100:.0f}% | {signal.get('reason','')}"""
        try:
            return await self._ask(prompt, category="signals")
        except Exception as e:
            return f"⚠️ فشل شرح الإشارة: {e}"

    # ══════════════════════════════════════════
    #  6. محادثة حرة
    # ══════════════════════════════════════════
    async def chat(self, message: str) -> str:
        try:
            return await self._ask(message, category="chat")
        except Exception as e:
            return f"⚠️ خطأ: {e}"

    # ══════════════════════════════════════════
    #  7. تحليل المحفظة
    # ══════════════════════════════════════════
    async def analyze_portfolio(self, portfolio: dict) -> dict:
        prompt = f"""حلل المحفظة (JSON فقط):
رأس المال: {portfolio.get('capital',0)} USDT | P&L: {portfolio.get('daily_pnl',0)}
Win Rate: {portfolio.get('win_rate',0)}% | Drawdown: {portfolio.get('max_drawdown',0)}%

{{"performance":"EXCELLENT/GOOD/AVERAGE/POOR","risk_assessment":"تقييم","strengths":["قوة"],"weaknesses":["ضعف"],"recommendations":["توصية"],"suggested_risk_per_trade":0.01}}"""
        try:
            return self._parse_json(await self._ask(prompt, category="other"))
        except Exception as e:
            return {"performance":"UNKNOWN","recommendations":[str(e)]}

    # ══════════════════════════════════════════
    #  إحصاءات الكوتا
    # ══════════════════════════════════════════
    def get_quota_stats(self) -> dict:
        self._check_reset()
        return {
            **self.quota,
            "remaining": self.quota["total_limit"] - self.quota["requests_today"],
            "usage_pct": round(self.quota["requests_today"] / self.quota["total_limit"] * 100, 1),
        }


# ── Singleton ────────────────────────────────
_ai_engine_instance = None

def get_ai_engine(event_bus=None) -> ScyllaAIEngine:
    global _ai_engine_instance
    if _ai_engine_instance is None:
        _ai_engine_instance = ScyllaAIEngine(event_bus)
    return _ai_engine_instance