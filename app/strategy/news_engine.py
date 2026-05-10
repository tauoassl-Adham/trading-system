"""
╔══════════════════════════════════════════════════════════════════╗
║         SCYLLA NEWS ENGINE v4 — Arabic First                     ║
║                                                                  ║
║  المصادر بالأولوية:                                              ║
║  1. GNews API (ar)       — أخبار عربية مباشرة ✅                ║
║  2. RSS Arabic Feeds     — CoinTelegraph AR / Al Arabiya         ║
║  3. Finnhub (EN)         — للأخبار المؤسسية الكبيرة فقط         ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import asyncio
import logging
import httpx
import re
from datetime import datetime
from xml.etree import ElementTree as ET
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

FINNHUB_KEY  = os.getenv("FINNHUB_API_KEY", "")
GNEWS_KEY    = os.getenv("GNEWS_API_KEY", "")
FINNHUB_URL  = "https://finnhub.io/api/v1"
GNEWS_URL    = "https://gnews.io/api/v4"

BROWSER_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Accept":          "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "ar,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Cache-Control":   "no-cache",
}

# ── مصادر RSS العربية ───────────────────────
ARABIC_RSS = [
    {
        "name":  "CoinTelegraph Arabic",
        "url":   "https://ar.cointelegraph.com/rss",
        "emoji": "₿",
        "cat":   "crypto",
    },
    {
        "name":  "Al Arabiya Economy",
        "url":   "https://www.alarabiya.net/tools/rss/economy.xml",
        "emoji": "📊",
        "cat":   "macro",
    },
    {
        "name":  "Mubasher Finance",
        "url":   "https://www.mubasher.info/rss/news?lang=ar",
        "emoji": "🏦",
        "cat":   "markets",
    },
    {
        "name":  "Argaam Markets",
        "url":   "https://www.argaam.com/ar/rss/markets",
        "emoji": "📈",
        "cat":   "markets",
    },
]

# كلمات مفتاحية للأهمية
IMPORTANT_KW = [
    'بيتكوين','bitcoin','btc','إيثريوم','eth','كريبتو','crypto',
    'الفيدرالي','fed','فائدة','تضخم','gdp','ناتج','تنظيم',
    'بلاك روك','blackrock','sec','ترامب','trump','ماسك','musk',
    'etf','صندوق','تدفق','inflow','انهيار','crash','ارتفاع',
    'بينانس','binance','coinbase','مايكروستراتيجي','whale','حوت',
    'سايلر','saylor','سولانا','solana','ريبل','xrp',
]


class NewsEngine:
    def __init__(self, event_bus=None, ai_engine=None):
        self.event_bus  = event_bus
        self.ai         = ai_engine
        self.cache      = []
        self.last_fetch = None
        self.running    = False
        self._seen_ids: set = set()
        logger.info("✅ NewsEngine v4 — Arabic First Strategy")

    # ══════════════════════════════════════════
    #  1. GNews API — عربي مباشر ✅
    # ══════════════════════════════════════════
    async def fetch_gnews(self) -> list:
        if not GNEWS_KEY:
            logger.info("ℹ️ GNEWS_API_KEY not set — skipping GNews")
            return []
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # جلب أخبار كريبتو بالعربية
                r = await client.get(f"{GNEWS_URL}/search", params={
                    "q":        "bitcoin OR crypto OR ethereum OR بيتكوين OR كريبتو",
                    "lang":     "ar",
                    "country":  "any",
                    "max":      10,
                    "apikey":   GNEWS_KEY,
                    "sortby":   "publishedAt",
                })
                if r.status_code != 200:
                    logger.warning(f"GNews error: {r.status_code}")
                    return []
                data     = r.json()
                articles = data.get("articles", [])
                items    = []
                for a in articles:
                    title = a.get("title", "")
                    if not title:
                        continue
                    item_id = a.get("url", title[:60])
                    items.append({
                        "id":          item_id,
                        "headline":    title,
                        "headline_ar": title,        # عربي بالفعل ✅
                        "summary":     a.get("description", "")[:200],
                        "source":      a.get("source", {}).get("name", "GNews"),
                        "url":         a.get("url", ""),
                        "datetime":    self._parse_iso(a.get("publishedAt", "")),
                        "emoji":       "🌐",
                        "is_important": self._is_important(title),
                        "lang":        "ar",
                        "ai_analyzed": False,
                    })
                logger.info(f"✅ GNews Arabic: {len(items)} articles")
                return items
        except Exception as e:
            logger.warning(f"GNews failed: {e}")
            return []

    # ══════════════════════════════════════════
    #  2. RSS Arabic Feeds
    # ══════════════════════════════════════════
    async def fetch_rss(self, source: dict) -> list:
        try:
            async with httpx.AsyncClient(
                timeout=10,
                headers=BROWSER_HEADERS,
                follow_redirects=True,
            ) as client:
                r = await client.get(source["url"])
                if r.status_code != 200:
                    logger.warning(f"RSS {source['name']}: {r.status_code}")
                    return []
                items = self._parse_rss_xml(r.text, source)
                if items:
                    logger.info(f"✅ RSS {source['name']}: {len(items)} items")
                return items
        except Exception as e:
            logger.warning(f"RSS {source['name']} failed: {e}")
            return []

    def _parse_rss_xml(self, xml_text: str, source: dict) -> list:
        items = []
        try:
            xml_text = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', xml_text)
            root     = ET.fromstring(xml_text.encode("utf-8"))

            entries = (
                root.findall(".//item") or
                root.findall(".//{http://www.w3.org/2005/Atom}entry")
            )

            for entry in entries[:15]:
                title = self._el(entry, ["title", "{http://www.w3.org/2005/Atom}title"])
                link  = self._el(entry, ["link", "guid", "{http://www.w3.org/2005/Atom}id"])
                desc  = self._el(entry, ["description", "summary", "{http://www.w3.org/2005/Atom}summary"])
                date  = self._el(entry, ["pubDate", "published", "updated"])

                title = re.sub(r"<[^>]+>", "", title).strip()
                desc  = re.sub(r"<[^>]+>", "", desc).strip()[:200]

                if not title:
                    continue

                item_id = link or title[:60]
                items.append({
                    "id":          item_id,
                    "headline":    title,
                    "headline_ar": title,   # عربي مباشر من المصدر ✅
                    "summary":     desc,
                    "source":      source["name"],
                    "url":         link,
                    "datetime":    self._parse_rfc(date),
                    "emoji":       source["emoji"],
                    "is_important": self._is_important(title + " " + desc),
                    "lang":        "ar",
                    "ai_analyzed": False,
                })
        except Exception as e:
            logger.warning(f"RSS parse error [{source['name']}]: {e}")
        return items

    def _el(self, entry, tags: list) -> str:
        for tag in tags:
            el = entry.find(tag)
            if el is not None:
                return (el.text or el.get("href", "") or "").strip()
        return ""

    # ══════════════════════════════════════════
    #  3. Finnhub — للأخبار المؤسسية الكبيرة
    # ══════════════════════════════════════════
    async def fetch_finnhub_top(self) -> list:
        if not FINNHUB_KEY:
            return []
        INST_KW = [
            "blackrock", "sec", "federal reserve", "fidelity",
            "bitcoin etf", "microstrategy", "trump", "executive order",
            "grayscale", "coinbase nasdaq", "jpmorgan bitcoin",
        ]
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"{FINNHUB_URL}/news",
                    params={"category": "crypto", "token": FINNHUB_KEY},
                )
                if r.status_code != 200:
                    return []
                items = []
                for a in r.json()[:30]:
                    hl = a.get("headline", "").lower()
                    if not any(kw in hl for kw in INST_KW):
                        continue
                    item_id = str(a.get("id", a.get("headline","")[:60]))
                    items.append({
                        "id":          item_id,
                        "headline":    a.get("headline", ""),
                        "headline_ar": f"🏛️ {a.get('headline','')}",
                        "summary":     a.get("summary","")[:200],
                        "source":      a.get("source","Finnhub"),
                        "url":         a.get("url",""),
                        "datetime":    a.get("datetime", int(datetime.utcnow().timestamp())),
                        "emoji":       "🏛️",
                        "is_important": True,
                        "lang":        "en",
                        "ai_analyzed": False,
                    })
                logger.info(f"🏛️ Finnhub institutional: {len(items)} items")
                return items
        except Exception as e:
            logger.warning(f"Finnhub failed: {e}")
            return []

    # ══════════════════════════════════════════
    #  Helpers
    # ══════════════════════════════════════════
    def _is_important(self, text: str) -> bool:
        t = text.lower()
        return any(kw in t for kw in IMPORTANT_KW)

    def _parse_rfc(self, date_str: str) -> int:
        if not date_str:
            return int(datetime.utcnow().timestamp())
        try:
            from email.utils import parsedate_to_datetime
            return int(parsedate_to_datetime(date_str).timestamp())
        except Exception:
            pass
        try:
            return int(datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S").timestamp())
        except Exception:
            return int(datetime.utcnow().timestamp())

    def _parse_iso(self, date_str: str) -> int:
        if not date_str:
            return int(datetime.utcnow().timestamp())
        try:
            return int(datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S").timestamp())
        except Exception:
            return int(datetime.utcnow().timestamp())

    # ══════════════════════════════════════════
    #  الدورة الرئيسية
    # ══════════════════════════════════════════
    async def run_loop(self, interval_minutes: int = 15):
        self.running = True
        logger.info(f"📡 NewsEngine v4 — Arabic First | every {interval_minutes} min")
        while self.running:
            try:
                await self._fetch_and_process()
            except Exception as e:
                logger.error(f"NewsEngine loop error: {e}")
            await asyncio.sleep(interval_minutes * 60)

    async def _fetch_and_process(self):
        # ── جلب كل المصادر بالتوازي ──
        tasks = [self.fetch_gnews()]
        for src in ARABIC_RSS:
            tasks.append(self.fetch_rss(src))
        tasks.append(self.fetch_finnhub_top())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items = []
        for r in results:
            if isinstance(r, list):
                all_items.extend(r)

        # ترتيب وإزالة تكرار
        all_items.sort(key=lambda x: x.get("datetime", 0), reverse=True)
        seen, unique = set(), []
        for item in all_items:
            key = item.get("id") or item.get("headline","")[:60]
            if key and key not in seen:
                seen.add(key)
                unique.append(item)

        self.cache      = unique[:30]
        self.last_fetch = datetime.utcnow().isoformat()

        # نشر
        if self.event_bus:
            self.event_bus.publish("news_update", {
                "items":     self.cache,
                "count":     len(self.cache),
                "timestamp": self.last_fetch,
            })

        ar  = len([n for n in self.cache if n.get("lang") == "ar"])
        imp = len([n for n in self.cache if n.get("is_important")])
        logger.info(f"✅ News: {len(self.cache)} total | {ar} Arabic | {imp} important")

    def stop(self):
        self.running = False

    def get_latest(self, limit: int = 20) -> list:
        return self.cache[:limit]

    def get_important(self) -> list:
        return [n for n in self.cache if n.get("is_important")]


_news_engine = None

def get_news_engine(event_bus=None, ai_engine=None) -> NewsEngine:
    global _news_engine
    if _news_engine is None:
        _news_engine = NewsEngine(event_bus, ai_engine)
    return _news_engine