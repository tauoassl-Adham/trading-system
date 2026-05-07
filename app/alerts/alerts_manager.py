"""
╔══════════════════════════════════════════════════════════════════╗
║         SCYLLA ALERTS MANAGER — نظام التنبيهات المؤسسي          ║
║         Telegram + WebSocket Toast + Sound                       ║
╚══════════════════════════════════════════════════════════════════╝

القنوات:
  - Telegram Bot       : إشعارات خارجية فورية
  - WebSocket Toast    : إشعارات داخل الداشبورد
  - Sound              : نغمات تنبيه مخصصة لكل نوع

أنواع التنبيهات:
  - SIGNAL_ENTRY       : إشارة دخول
  - SIGNAL_EXIT        : إشارة خروج
  - SIGNAL_CHOCH       : تغيير في الهيكل CHoCH
  - SIGNAL_BOS         : كسر هيكل BOS
  - NEWS_HIGH_IMPACT   : خبر اقتصادي مهم
  - PSYCHOLOGY_ALERT   : تحذير نفسي
  - PORTFOLIO_ALERT    : تنبيه محفظة (SL/TP/Drawdown)
  - SYSTEM             : تنبيهات النظام
"""

import os
import asyncio
import logging
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
#  ALERT TYPES
# ══════════════════════════════════════════════
class AlertType(Enum):
    SIGNAL_ENTRY      = "signal_entry"
    SIGNAL_EXIT       = "signal_exit"
    SIGNAL_CHOCH      = "signal_choch"
    SIGNAL_BOS        = "signal_bos"
    NEWS_HIGH_IMPACT  = "news_high_impact"
    PSYCHOLOGY_ALERT  = "psychology_alert"
    PORTFOLIO_ALERT   = "portfolio_alert"
    SYSTEM            = "system"

class AlertPriority(Enum):
    LOW      = 1
    MEDIUM   = 2
    HIGH     = 3
    CRITICAL = 4

# ══════════════════════════════════════════════
#  ALERT CONFIG — إعدادات لكل نوع
# ══════════════════════════════════════════════
ALERT_CONFIG = {
    AlertType.SIGNAL_ENTRY: {
        "emoji":    "🟢",
        "sound":    "entry",
        "telegram": True,
        "toast":    True,
        "priority": AlertPriority.HIGH,
        "enabled":  True,
    },
    AlertType.SIGNAL_EXIT: {
        "emoji":    "🔴",
        "sound":    "exit",
        "telegram": True,
        "toast":    True,
        "priority": AlertPriority.HIGH,
        "enabled":  True,
    },
    AlertType.SIGNAL_CHOCH: {
        "emoji":    "⚡",
        "sound":    "choch",
        "telegram": True,
        "toast":    True,
        "priority": AlertPriority.MEDIUM,
        "enabled":  True,
    },
    AlertType.SIGNAL_BOS: {
        "emoji":    "📐",
        "sound":    "bos",
        "telegram": True,
        "toast":    True,
        "priority": AlertPriority.MEDIUM,
        "enabled":  True,
    },
    AlertType.NEWS_HIGH_IMPACT: {
        "emoji":    "📰",
        "sound":    "news",
        "telegram": True,
        "toast":    True,
        "priority": AlertPriority.HIGH,
        "enabled":  True,
    },
    AlertType.PSYCHOLOGY_ALERT: {
        "emoji":    "🧠",
        "sound":    "warning",
        "telegram": True,
        "toast":    True,
        "priority": AlertPriority.CRITICAL,
        "enabled":  True,
    },
    AlertType.PORTFOLIO_ALERT: {
        "emoji":    "💼",
        "sound":    "portfolio",
        "telegram": True,
        "toast":    True,
        "priority": AlertPriority.HIGH,
        "enabled":  True,
    },
    AlertType.SYSTEM: {
        "emoji":    "⚙️",
        "sound":    "system",
        "telegram": False,
        "toast":    True,
        "priority": AlertPriority.LOW,
        "enabled":  True,
    },
}

# ══════════════════════════════════════════════
#  ALERT DATA CLASS
# ══════════════════════════════════════════════
@dataclass
class Alert:
    type:      AlertType
    title:     str
    message:   str
    symbol:    Optional[str] = None
    data:      dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    sent_telegram: bool = False
    sent_toast:    bool = False

# ══════════════════════════════════════════════
#  TELEGRAM SENDER
# ══════════════════════════════════════════════
class TelegramSender:
    """إرسال إشعارات تيليغرام"""

    def __init__(self):
        self.token   = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.token and self.chat_id)
        if self.enabled:
            logger.info("✅ Telegram sender initialized")
        else:
            logger.warning("⚠️  Telegram credentials missing in .env")

    async def send(self, message: str, parse_mode: str = "HTML") -> bool:
        """إرسال رسالة نصية"""
        if not self.enabled:
            return False
        try:
            import httpx
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id":    self.chat_id,
                "text":       message,
                "parse_mode": parse_mode,
            }
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    logger.info("📨 Telegram sent successfully")
                    return True
                else:
                    logger.error(f"Telegram error: {resp.text}")
                    return False
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    def _format_signal_entry(self, alert: Alert) -> str:
        """تنسيق رسالة إشارة الدخول"""
        d = alert.data
        return (
            f"🟢 <b>SCYLLA SIGNAL — {alert.symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 <b>الاتجاه:</b> {d.get('bias','')}\n"
            f"🎯 <b>الدخول:</b> {d.get('poi_price','--')}\n"
            f"🛡️ <b>SL:</b> {d.get('sl','--')}\n"
            f"🎁 <b>TP1:</b> {d.get('tp1','--')}\n"
            f"🎁 <b>TP2:</b> {d.get('tp2','--')}\n"
            f"🎁 <b>TP3:</b> {d.get('tp3','--')}\n"
            f"📊 <b>Confidence:</b> {d.get('confidence',0)*100:.0f}%\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 {d.get('reason','')}\n"
            f"⏰ {alert.timestamp.strftime('%H:%M:%S UTC')}"
        )

    def _format_choch(self, alert: Alert) -> str:
        d = alert.data
        return (
            f"⚡ <b>CHoCH — {alert.symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔄 <b>التغيير:</b> {d.get('choch_type','')}\n"
            f"💰 <b>عند السعر:</b> {d.get('price','--')}\n"
            f"📈 <b>الإطار:</b> {d.get('timeframe','')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ تغيير محتمل في اتجاه السوق\n"
            f"⏰ {alert.timestamp.strftime('%H:%M:%S UTC')}"
        )

    def _format_bos(self, alert: Alert) -> str:
        d = alert.data
        return (
            f"📐 <b>BOS — {alert.symbol}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💥 <b>كسر الهيكل:</b> {d.get('direction','')}\n"
            f"💰 <b>عند السعر:</b> {d.get('price','--')}\n"
            f"📈 <b>الإطار:</b> {d.get('timeframe','')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ {alert.timestamp.strftime('%H:%M:%S UTC')}"
        )

    def _format_news(self, alert: Alert) -> str:
        d = alert.data
        return (
            f"📰 <b>خبر مهم</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 {alert.title}\n"
            f"📊 <b>التأثير:</b> {d.get('impact','')}\n"
            f"💬 {d.get('summary','')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ {alert.timestamp.strftime('%H:%M:%S UTC')}"
        )

    def _format_psychology(self, alert: Alert) -> str:
        d = alert.data
        return (
            f"🧠 <b>تنبيه نفسي</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <b>الحالة:</b> {d.get('state','')}\n"
            f"📊 <b>مستوى الخطر:</b> {d.get('risk_level','')}\n"
            f"💡 {d.get('message','')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{'🛑 يُنصح بالتوقف عن التداول الآن' if d.get('should_stop') else '⚠️ كن حذراً'}\n"
            f"⏰ {alert.timestamp.strftime('%H:%M:%S UTC')}"
        )

    def _format_portfolio(self, alert: Alert) -> str:
        d = alert.data
        return (
            f"💼 <b>تنبيه محفظة</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 {alert.title}\n"
            f"💰 <b>الرصيد:</b> {d.get('balance','--')} USDT\n"
            f"📊 <b>P&L:</b> {d.get('pnl','--')} USDT\n"
            f"💡 {alert.message}\n"
            f"⏰ {alert.timestamp.strftime('%H:%M:%S UTC')}"
        )

    def format_message(self, alert: Alert) -> str:
        """اختيار التنسيق المناسب لكل نوع"""
        formatters = {
            AlertType.SIGNAL_ENTRY:     self._format_signal_entry,
            AlertType.SIGNAL_EXIT:      self._format_signal_entry,
            AlertType.SIGNAL_CHOCH:     self._format_choch,
            AlertType.SIGNAL_BOS:       self._format_bos,
            AlertType.NEWS_HIGH_IMPACT: self._format_news,
            AlertType.PSYCHOLOGY_ALERT: self._format_psychology,
            AlertType.PORTFOLIO_ALERT:  self._format_portfolio,
        }
        formatter = formatters.get(alert.type)
        if formatter:
            return formatter(alert)
        # Default
        return (
            f"{ALERT_CONFIG[alert.type]['emoji']} <b>{alert.title}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{alert.message}\n"
            f"⏰ {alert.timestamp.strftime('%H:%M:%S UTC')}"
        )


# ══════════════════════════════════════════════
#  ALERTS MANAGER
# ══════════════════════════════════════════════
class AlertsManager:
    """
    المدير المركزي لكل التنبيهات في المنصة.
    يُستخدم من: SMC Engine, News Engine, Portfolio Manager,
                Psychology Tracker, Strategy Engine
    """

    def __init__(self, event_bus=None, ws_manager=None):
        self.event_bus  = event_bus
        self.ws_manager = ws_manager   # لإرسال toast للداشبورد
        self.telegram   = TelegramSender()
        self.history    = []           # سجل التنبيهات
        self.config     = {t: dict(c) for t, c in ALERT_CONFIG.items()}
        self._queue     = asyncio.Queue()
        logger.info("✅ AlertsManager initialized")

    # ── إرسال تنبيه ──────────────────────────
    async def send(
        self,
        alert_type: AlertType,
        title: str,
        message: str,
        symbol: str = None,
        data: dict = None,
    ) -> Alert:
        """
        الدالة الرئيسية — أرسل تنبيهاً لكل القنوات المفعّلة
        """
        cfg = self.config.get(alert_type, {})

        # تحقق من التفعيل
        if not cfg.get("enabled", True):
            logger.debug(f"Alert {alert_type.value} is disabled — skipped")
            return None

        alert = Alert(
            type=alert_type,
            title=title,
            message=message,
            symbol=symbol,
            data=data or {},
        )

        # إرسال للقنوات
        tasks = []

        if cfg.get("telegram") and self.telegram.enabled:
            msg = self.telegram.format_message(alert)
            tasks.append(self._send_telegram(alert, msg))

        if cfg.get("toast") and self.ws_manager:
            tasks.append(self._send_toast(alert))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # حفظ في السجل
        self.history.append(alert)
        if len(self.history) > 500:
            self.history.pop(0)

        # نشر حدث في EventBus
        if self.event_bus:
            self.event_bus.publish("alert_sent", {
                "type":    alert_type.value,
                "title":   title,
                "symbol":  symbol,
                "message": message,
            })

        logger.info(f"🔔 Alert sent: [{alert_type.value}] {title}")
        return alert

    async def _send_telegram(self, alert: Alert, message: str):
        """إرسال للتيليغرام"""
        ok = await self.telegram.send(message)
        alert.sent_telegram = ok

    async def _send_toast(self, alert: Alert):
        """إرسال toast للداشبورد عبر WebSocket"""
        try:
            cfg = self.config[alert.type]
            await self.ws_manager.broadcast({
                "type":     "alert",
                "alert_type": alert.type.value,
                "title":    alert.title,
                "message":  alert.message,
                "symbol":   alert.symbol,
                "emoji":    cfg.get("emoji", "🔔"),
                "sound":    cfg.get("sound", "default"),
                "priority": cfg.get("priority", AlertPriority.MEDIUM).value,
                "timestamp": alert.timestamp.isoformat(),
            })
            alert.sent_toast = True
        except Exception as e:
            logger.error(f"Toast send failed: {e}")

    # ── تفعيل / إيقاف نوع تنبيه ──────────────
    def toggle(self, alert_type: AlertType, enabled: bool):
        if alert_type in self.config:
            self.config[alert_type]["enabled"] = enabled
            status = "✅ مفعّل" if enabled else "❌ موقوف"
            logger.info(f"Alert {alert_type.value}: {status}")

    def toggle_telegram(self, alert_type: AlertType, enabled: bool):
        if alert_type in self.config:
            self.config[alert_type]["telegram"] = enabled

    # ── الحصول على السجل ─────────────────────
    def get_history(self, limit: int = 50) -> list:
        return [
            {
                "type":      a.type.value,
                "title":     a.title,
                "message":   a.message,
                "symbol":    a.symbol,
                "timestamp": a.timestamp.isoformat(),
                "telegram":  a.sent_telegram,
            }
            for a in self.history[-limit:]
        ]

    def get_config(self) -> dict:
        """إرجاع إعدادات التنبيهات للداشبورد"""
        return {
            t.value: {
                "enabled":  c["enabled"],
                "telegram": c["telegram"],
                "toast":    c["toast"],
                "emoji":    c["emoji"],
                "priority": c["priority"].value,
            }
            for t, c in self.config.items()
        }

    # ── Shortcuts للاستخدام من أجزاء المنصة ──
    async def signal_entry(self, symbol: str, data: dict):
        await self.send(
            AlertType.SIGNAL_ENTRY,
            f"إشارة دخول — {symbol}",
            data.get("reason", ""),
            symbol=symbol, data=data,
        )

    async def signal_exit(self, symbol: str, data: dict):
        await self.send(
            AlertType.SIGNAL_EXIT,
            f"إشارة خروج — {symbol}",
            data.get("reason", ""),
            symbol=symbol, data=data,
        )

    async def signal_choch(self, symbol: str, data: dict):
        await self.send(
            AlertType.SIGNAL_CHOCH,
            f"CHoCH — {symbol}",
            f"تغيير هيكل {data.get('choch_type','')}",
            symbol=symbol, data=data,
        )

    async def signal_bos(self, symbol: str, data: dict):
        await self.send(
            AlertType.SIGNAL_BOS,
            f"BOS — {symbol}",
            f"كسر هيكل {data.get('direction','')}",
            symbol=symbol, data=data,
        )

    async def news_alert(self, title: str, data: dict):
        await self.send(
            AlertType.NEWS_HIGH_IMPACT,
            title, data.get("summary", ""),
            data=data,
        )

    async def psychology_alert(self, data: dict):
        await self.send(
            AlertType.PSYCHOLOGY_ALERT,
            "تنبيه نفسي",
            data.get("message", ""),
            data=data,
        )

    async def portfolio_alert(self, title: str, message: str, data: dict):
        await self.send(
            AlertType.PORTFOLIO_ALERT,
            title, message, data=data,
        )


# ── Singleton ────────────────────────────────
_alerts_manager = None

def get_alerts_manager(event_bus=None, ws_manager=None) -> AlertsManager:
    global _alerts_manager
    if _alerts_manager is None:
        _alerts_manager = AlertsManager(event_bus, ws_manager)
    return _alerts_manager