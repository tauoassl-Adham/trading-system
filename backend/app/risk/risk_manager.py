import logging
from typing import Optional, Dict, Any
from app.strategy.base_strategy import Signal

logger = logging.getLogger(__name__)


class RiskManager:
    """مدير المخاطر - يتحقق من صحة الإشارات قبل التنفيذ"""

    def __init__(self, event_bus, initial_capital=10000):
        self.event_bus = event_bus
        self.initial_capital = initial_capital
        self.current_capital = initial_capital

        # حدود المخاطر
        self.max_risk_per_trade = 0.02  # 2% من رأس المال لكل صفقة
        self.max_daily_loss = 0.05  # 5% خسارة يومية كحد أقصى
        self.max_exposure_per_asset = 0.1  # 10% تعرض لكل أصل

        # تتبع الخسائر اليومية
        self.daily_loss = 0.0
        self.daily_start_capital = initial_capital

        # المراكز النشطة
        self.active_positions: Dict[str, Dict[str, Any]] = {}

        # الاشتراك في الأحداث
        self.event_bus.subscribe("strategy_signal", self.on_strategy_signal)

    def on_strategy_signal(self, data):
        """معالجة إشارة الاستراتيجية"""
        strategy = data["strategy"]
        symbol = data["symbol"]
        signal: Signal = data["signal"]
        candle = data["candle"]

        logger.info(f"RiskManager: Received signal from {strategy} for {symbol}: {signal}")

        # التحقق من صحة الإشارة
        if self.validate_signal(signal, symbol):
            # حساب حجم المركز
            position_size = self.calculate_position_size(signal, symbol)

            if position_size > 0:
                # إنشاء أمر تنفيذ
                order = self.create_order(signal, symbol, position_size)

                # نشر أمر التنفيذ
                self.event_bus.publish("risk_approved_order", {
                    "order": order,
                    "signal": signal,
                    "strategy": strategy,
                    "candle": candle
                })

                logger.info(f"RiskManager: Approved order for {symbol}: {order}")
            else:
                logger.warning(f"RiskManager: Rejected signal for {symbol} - position size 0")
        else:
            logger.warning(f"RiskManager: Rejected signal for {symbol} - validation failed")

    def validate_signal(self, signal: Signal, symbol: str) -> bool:
        """التحقق من صحة الإشارة"""

        # 1. التحقق من حدود الخسارة اليومية
        if self.daily_loss >= self.max_daily_loss * self.daily_start_capital:
            logger.warning("Daily loss limit reached")
            return False

        # 2. التحقق من عدم وجود مركز نشط لنفس الأصل
        if symbol in self.active_positions:
            logger.warning(f"Position already exists for {symbol}")
            return False

        # 3. التحقق من stop loss
        if not signal.stop_loss:
            logger.warning("Signal missing stop loss")
            return False

        # 4. التحقق من تعرض الأصل
        exposure = self.calculate_exposure(symbol)
        if exposure >= self.max_exposure_per_asset * self.current_capital:
            logger.warning(f"Max exposure reached for {symbol}")
            return False

        return True

    def calculate_position_size(self, signal: Signal, symbol: str) -> float:
        """حساب حجم المركز بناءً على المخاطر"""

        # حساب المخاطر لكل صفقة
        risk_amount = self.max_risk_per_trade * self.current_capital

        # حساب حجم المركز بناءً على stop loss
        if signal.direction == "BUY":
            risk_per_unit = abs(signal.entry_price - signal.stop_loss)
        else:  # SELL
            risk_per_unit = abs(signal.stop_loss - signal.entry_price)

        if risk_per_unit == 0:
            return 0

        position_size = risk_amount / risk_per_unit

        # التحقق من عدم تجاوز التعرض الأقصى
        max_exposure = self.max_exposure_per_asset * self.current_capital
        position_value = position_size * signal.entry_price

        if position_value > max_exposure:
            position_size = max_exposure / signal.entry_price

        return position_size

    def calculate_exposure(self, symbol: str) -> float:
        """حساب التعرض الحالي للأصل"""
        if symbol in self.active_positions:
            position = self.active_positions[symbol]
            return position["size"] * position["entry_price"]
        return 0.0

    def create_order(self, signal: Signal, symbol: str, size: float) -> Dict[str, Any]:
        """إنشاء أمر التنفيذ"""
        return {
            "symbol": symbol,
            "direction": signal.direction,
            "size": size,
            "entry_price": signal.entry_price,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "timestamp": None  # سيتم تعيينه عند التنفيذ
        }

    def update_position(self, symbol: str, order: Dict[str, Any]):
        """تحديث المركز بعد التنفيذ"""
        self.active_positions[symbol] = {
            "size": order["size"],
            "entry_price": order["entry_price"],
            "stop_loss": order["stop_loss"],
            "direction": order["direction"]
        }

    def close_position(self, symbol: str, exit_price: float):
        """إغلاق المركز وحساب الربح/الخسارة"""
        if symbol not in self.active_positions:
            return

        position = self.active_positions[symbol]

        if position["direction"] == "BUY":
            pnl = (exit_price - position["entry_price"]) * position["size"]
        else:
            pnl = (position["entry_price"] - exit_price) * position["size"]

        self.current_capital += pnl

        if pnl < 0:
            self.daily_loss += abs(pnl)

        del self.active_positions[symbol]

        logger.info(f"Closed position for {symbol}: PnL = {pnl}")

    def get_risk_status(self) -> Dict[str, Any]:
        """الحصول على حالة المخاطر"""
        return {
            "current_capital": self.current_capital,
            "daily_loss": self.daily_loss,
            "daily_loss_limit": self.max_daily_loss * self.daily_start_capital,
            "active_positions": len(self.active_positions),
            "total_exposure": sum(self.calculate_exposure(sym) for sym in self.active_positions)
        }