import logging
from typing import Dict, Any
import time

logger = logging.getLogger(__name__)


class PaperTrader:
    """محاكي التداول الورقي - تنفيذ الأوامر دون مخاطر حقيقية"""

    def __init__(self, event_bus, risk_manager):
        self.event_bus = event_bus
        self.risk_manager = risk_manager

        # المراكز المحاكاة
        self.positions: Dict[str, Dict[str, Any]] = {}

        # سجل التداول
        self.trade_history = []

        # الاشتراك في الأحداث
        self.event_bus.subscribe("risk_approved_order", self.on_risk_approved_order)

    def on_risk_approved_order(self, data):
        """معالجة الأمر المعتمد من RiskManager"""
        order = data["order"]
        signal = data["signal"]
        strategy = data["strategy"]

        logger.info(f"PaperTrader: Executing order for {order['symbol']}: {order}")

        # تنفيذ الأمر (محاكاة)
        executed_order = self.execute_order(order)

        if executed_order:
            # تحديث RiskManager
            self.risk_manager.update_position(order["symbol"], executed_order)

            # تسجيل التداول
            trade_record = {
                "timestamp": time.time(),
                "strategy": strategy,
                "symbol": order["symbol"],
                "direction": order["direction"],
                "size": order["size"],
                "entry_price": order["entry_price"],
                "stop_loss": order["stop_loss"],
                "take_profit": order["take_profit"],
                "status": "OPEN"
            }

            self.trade_history.append(trade_record)
            self.positions[order["symbol"]] = executed_order

            logger.info(f"PaperTrader: Position opened for {order['symbol']}")

            # التحقق من إغلاق المركز تلقائياً (stop loss / take profit)
            self.check_position_exit(order["symbol"])

    def execute_order(self, order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """تنفيذ الأمر (محاكاة)"""
        # في التداول الحقيقي، هنا ستكون استدعاء API
        # للورقي، نفترض التنفيذ الفوري بالسعر المطلوب

        executed_order = order.copy()
        executed_order["timestamp"] = time.time()
        executed_order["status"] = "EXECUTED"

        return executed_order

    def check_position_exit(self, symbol: str):
        """التحقق من إغلاق المركز تلقائياً"""
        if symbol not in self.positions:
            return

        position = self.positions[symbol]
        # نفترض الحصول على السعر الحالي من data_store
        # للتبسيط، سنستخدم منطق بسيط

        # في التطبيق الحقيقي، هذا سيتم في loop منفصل
        # للآن، سنضيف منطق للإغلاق عند stop loss

        # مثال: إذا كان السعر يصل إلى stop loss، أغلق
        # هذا يحتاج إلى مراقبة مستمرة

        pass  # سيتم تطويره لاحقاً

    def close_position(self, symbol: str, exit_price: float):
        """إغلاق مركز يدوياً"""
        if symbol not in self.positions:
            logger.warning(f"No position found for {symbol}")
            return

        position = self.positions[symbol]

        # حساب PnL
        if position["direction"] == "BUY":
            pnl = (exit_price - position["entry_price"]) * position["size"]
        else:
            pnl = (position["entry_price"] - exit_price) * position["size"]

        # تحديث RiskManager
        self.risk_manager.close_position(symbol, exit_price)

        # تحديث سجل التداول
        for trade in self.trade_history:
            if trade["symbol"] == symbol and trade["status"] == "OPEN":
                trade["status"] = "CLOSED"
                trade["exit_price"] = exit_price
                trade["pnl"] = pnl
                trade["exit_timestamp"] = time.time()
                break

        del self.positions[symbol]

        logger.info(f"PaperTrader: Closed position for {symbol} at {exit_price}, PnL: {pnl}")

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """الحصول على المراكز النشطة"""
        return self.positions.copy()

    def get_trade_history(self, limit: int = 50) -> list:
        """الحصول على سجل التداول"""
        return self.trade_history[-limit:]