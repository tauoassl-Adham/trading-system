from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class Position:
    symbol: str
    side: str  # 'long' or 'short'
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    timestamp: datetime

@dataclass
class PortfolioMetrics:
    total_value: float
    available_balance: float
    used_margin: float
    total_pnl: float
    daily_pnl: float
    win_rate: float
    total_trades: int

class PortfolioManager:
    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.available_balance = initial_balance
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Dict] = []
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0

    def update_position(self, symbol: str, side: str, quantity: float, price: float):
        """تحديث أو إنشاء مركز جديد"""
        if symbol in self.positions:
            position = self.positions[symbol]
            # تحديث الكمية والسعر المتوسط
            total_quantity = position.quantity + quantity
            if total_quantity == 0:
                # إغلاق المركز
                self._close_position(symbol, price)
            else:
                # تحديث المركز
                position.entry_price = (position.entry_price * position.quantity + price * quantity) / total_quantity
                position.quantity = total_quantity
                position.current_price = price
                position.unrealized_pnl = self._calculate_pnl(position)
        else:
            # مركز جديد
            self.positions[symbol] = Position(
                symbol=symbol,
                side=side,
                quantity=quantity,
                entry_price=price,
                current_price=price,
                unrealized_pnl=0.0,
                timestamp=datetime.now()
            )
            # خصم رأس المال المستخدم
            self.available_balance -= abs(quantity) * price

        logger.info(f"Position updated: {symbol} {side} {quantity} @ {price}")

    def _close_position(self, symbol: str, exit_price: float):
        """إغلاق مركز وتسجيل التداول"""
        position = self.positions[symbol]
        pnl = self._calculate_pnl(position, exit_price)
        self.total_pnl += pnl
        self.daily_pnl += pnl
        self.total_trades += 1

        if pnl > 0:
            self.winning_trades += 1

        # تسجيل التداول
        trade = {
            'symbol': symbol,
            'side': position.side,
            'quantity': position.quantity,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'timestamp': datetime.now()
        }
        self.trade_history.append(trade)

        # إعادة رأس المال
        self.available_balance += abs(position.quantity) * exit_price

        # حذف المركز
        del self.positions[symbol]

        logger.info(f"Position closed: {symbol} PnL: {pnl}")

    def _calculate_pnl(self, position: Position, current_price: Optional[float] = None) -> float:
        """حساب PnL للمركز"""
        price = current_price or position.current_price
        if position.side == 'long':
            return (price - position.entry_price) * position.quantity
        else:  # short
            return (position.entry_price - price) * position.quantity

    def update_prices(self, prices: Dict[str, float]):
        """تحديث أسعار المراكز المفتوحة"""
        for symbol, position in self.positions.items():
            if symbol in prices:
                position.current_price = prices[symbol]
                position.unrealized_pnl = self._calculate_pnl(position)

    def get_positions(self) -> List[Dict]:
        """الحصول على جميع المراكز المفتوحة"""
        return [
            {
                'symbol': pos.symbol,
                'side': pos.side,
                'quantity': pos.quantity,
                'entry_price': pos.entry_price,
                'current_price': pos.current_price,
                'unrealized_pnl': pos.unrealized_pnl,
                'timestamp': pos.timestamp.isoformat()
            }
            for pos in self.positions.values()
        ]

    def get_portfolio_metrics(self) -> PortfolioMetrics:
        """الحصول على مقاييس المحفظة"""
        total_value = self.available_balance
        used_margin = 0.0

        for position in self.positions.values():
            total_value += position.current_price * abs(position.quantity)
            used_margin += position.entry_price * abs(position.quantity)

        win_rate = (self.winning_trades / self.total_trades) * 100 if self.total_trades > 0 else 0.0

        return PortfolioMetrics(
            total_value=total_value,
            available_balance=self.available_balance,
            used_margin=used_margin,
            total_pnl=self.total_pnl,
            daily_pnl=self.daily_pnl,
            win_rate=win_rate,
            total_trades=self.total_trades
        )

    def get_trade_history(self, limit: int = 10) -> List[Dict]:
        """الحصول على سجل التداول الأخير"""
        return self.trade_history[-limit:] if self.trade_history else []

    def reset_daily_pnl(self):
        """إعادة تعيين PnL اليومي"""
        self.daily_pnl = 0.0