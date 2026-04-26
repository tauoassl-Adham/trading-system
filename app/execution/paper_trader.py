import logging
from app.core.event_bus import event_bus

logger = logging.getLogger(__name__)

class PaperTrader:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.active_trades = []
        self.balance = 10000.0  # الرصيد الابتدائي
        self.history = []

        # 1. الاشتراك في طلبات التنفيذ القادمة من RiskManager
        self.event_bus.subscribe("execution_request", self.open_position)
        
        # 2. الاشتراك في التكات السعرية لمراقبة الصفقات المفتوحة
        self.event_bus.subscribe("tick", self.monitor_trades)

    def open_position(self, data):
        """فتح صفقة وهمية وتخزينها في قائمة الصفقات النشطة"""
        trade = {
            "symbol": data["symbol"],
            "action": data["action"],
            "quantity": data["quantity"],
            "entry_price": data["price"],
            "sl": data["sl"],
            "tp": data["tp"],
            "status": "OPEN"
        }
        
        self.active_trades.append(trade)
        
        logger.info(f"🟢 [EXECUTION] Position Opened: {trade['action']} {trade['quantity']:.4f} "
                    f"{trade['symbol']} at {trade['entry_price']}")
        print(f"\n🚀 --- TRADE EXECUTED ---")
        print(f"Symbol: {trade['symbol']} | Type: {trade['action']}")
        print(f"Qty: {trade['quantity']:.6f} | SL: {trade['sl']} | TP: {trade['tp']}\n")

    def monitor_trades(self, data):
        """مراقبة السعر الحالي لإغلاق الصفقة عند الهدف أو الوقف"""
        current_price = data["price"]
        
        for trade in self.active_trades[:]:
            is_closed = False
            pnl = 0
            reason = ""

            # منطق الخروج لصفقات الشراء (LONG)
            if trade["action"] == "BUY":
                if current_price <= trade["sl"]:
                    is_closed = True
                    reason = "🛑 STOP LOSS HIT"
                    pnl = (trade["sl"] - trade["entry_price"]) * trade["quantity"]
                elif current_price >= trade["tp"]:
                    is_closed = True
                    reason = "🎯 TAKE PROFIT HIT"
                    pnl = (trade["tp"] - trade["entry_price"]) * trade["quantity"]

            # منطق الخروج لصفقات البيع (SHORT)
            elif trade["action"] == "SELL":
                if current_price >= trade["sl"]:
                    is_closed = True
                    reason = "🛑 STOP LOSS HIT"
                    pnl = (trade["entry_price"] - trade["sl"]) * trade["quantity"]
                elif current_price <= trade["tp"]:
                    is_closed = True
                    reason = "🎯 TAKE PROFIT HIT"
                    pnl = (trade["entry_price"] - trade["tp"]) * trade["quantity"]

            if is_closed:
                self.close_position(trade, pnl, reason, current_price)

    def close_position(self, trade, pnl, reason, exit_price):
        """إغلاق الصفقة وتحديث المحفظة"""
        self.balance += pnl
        trade["status"] = "CLOSED"
        trade["pnl"] = pnl
        trade["exit_price"] = exit_price
        
        self.history.append(trade)
        self.active_trades.remove(trade)
        
        logger.info(f"🔴 [EXECUTION] {reason} | PnL: ${pnl:.2f} | New Balance: ${self.balance:.2f}")
        print(f"🏁 --- POSITION CLOSED ---")
        print(f"Reason: {reason} | PnL: ${pnl:.2f} | Final Balance: ${self.balance:.2f}\n")