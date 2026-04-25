from typing import Dict, List, Any
from datetime import datetime, timedelta
import statistics
import logging

logger = logging.getLogger(__name__)

class AnalyticsEngine:
    """محرك تحليل الأداء والإحصائيات"""

    def __init__(self, portfolio_manager, risk_manager):
        self.portfolio_manager = portfolio_manager
        self.risk_manager = risk_manager
        self.performance_history = []
        self.daily_stats = {}

    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """حساب مقاييس الأداء الشاملة"""
        trades = self.portfolio_manager.get_trade_history(1000)  # آخر 1000 تداول

        if not trades:
            return self._empty_metrics()

        # حساب الأرباح/الخسائر
        pnl_values = [trade['pnl'] for trade in trades]
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]

        # المقاييس الأساسية
        total_trades = len(trades)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        total_pnl = sum(pnl_values)
        avg_win = statistics.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = statistics.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0

        # حساب Sharpe Ratio (إذا كان هناك بيانات كافية)
        sharpe_ratio = self._calculate_sharpe_ratio(pnl_values)

        # حساب Maximum Drawdown
        max_drawdown = self._calculate_max_drawdown(trades)

        # Profit Factor
        total_wins = sum([t['pnl'] for t in winning_trades])
        total_losses = abs(sum([t['pnl'] for t in losing_trades]))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        return {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "largest_win": max(pnl_values) if pnl_values else 0,
            "largest_loss": min(pnl_values) if pnl_values else 0,
            "avg_trade_duration": self._calculate_avg_trade_duration(trades)
        }

    def _empty_metrics(self) -> Dict[str, Any]:
        """مقاييس فارغة عند عدم وجود تداولات"""
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "largest_win": 0.0,
            "largest_loss": 0.0,
            "avg_trade_duration": 0.0
        }

    def _calculate_sharpe_ratio(self, pnl_values: List[float]) -> float:
        """حساب Sharpe Ratio"""
        if len(pnl_values) < 2:
            return 0.0

        try:
            returns = pnl_values
            avg_return = statistics.mean(returns)
            std_dev = statistics.stdev(returns)
            return avg_return / std_dev if std_dev > 0 else 0.0
        except:
            return 0.0

    def _calculate_max_drawdown(self, trades: List[Dict]) -> float:
        """حساب Maximum Drawdown"""
        if not trades:
            return 0.0

        cumulative_pnl = 0
        peak = 0
        max_drawdown = 0

        for trade in trades:
            cumulative_pnl += trade['pnl']
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            drawdown = peak - cumulative_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        return max_drawdown

    def _calculate_avg_trade_duration(self, trades: List[Dict]) -> float:
        """حساب متوسط مدة التداول"""
        if not trades:
            return 0.0

        durations = []
        for trade in trades:
            if 'exit_timestamp' in trade and 'timestamp' in trade:
                duration = trade['exit_timestamp'] - trade['timestamp']
                durations.append(duration)

        return statistics.mean(durations) if durations else 0.0

    def generate_performance_report(self) -> Dict[str, Any]:
        """توليد تقرير الأداء الشامل"""
        metrics = self.calculate_performance_metrics()
        portfolio_metrics = self.portfolio_manager.get_portfolio_metrics()

        return {
            "timestamp": datetime.now().isoformat(),
            "portfolio": {
                "total_value": portfolio_metrics.total_value,
                "available_balance": portfolio_metrics.available_balance,
                "total_pnl": portfolio_metrics.total_pnl,
                "win_rate": portfolio_metrics.win_rate,
                "total_trades": portfolio_metrics.total_trades
            },
            "performance": metrics,
            "risk_metrics": {
                "current_exposure": self.risk_manager.get_risk_status(),
                "daily_loss_limit": 500.0,  # من RiskManager
                "recommended_position_size": self._calculate_recommended_position_size(metrics)
            }
        }

    def _calculate_recommended_position_size(self, metrics: Dict[str, Any]) -> float:
        """حساب حجم المركز الموصى به بناءً على الأداء"""
        if metrics['total_trades'] < 10:
            return 0.01  # حجم صغير للاختبار

        win_rate = metrics['win_rate']
        avg_win = metrics['avg_win']
        avg_loss = abs(metrics['avg_loss'])

        if avg_loss == 0:
            return 0.05

        # حساب Kelly Criterion المبسط
        kelly = win_rate - ((1 - win_rate) / (avg_win / avg_loss))
        position_size = max(0.01, min(0.1, kelly))  # بين 1% و 10%

        return position_size

    def get_strategy_suggestions(self) -> List[str]:
        """اقتراحات لتحسين الاستراتيجية"""
        metrics = self.calculate_performance_metrics()
        suggestions = []

        if metrics['total_trades'] < 10:
            suggestions.append("قم بجمع المزيد من التداولات لتحليل أفضل")
            return suggestions

        if metrics['win_rate'] < 0.4:
            suggestions.append("فكر في تحسين منطق دخول التداول - معدل الفوز منخفض")

        if metrics['profit_factor'] < 1.5:
            suggestions.append("حسن إدارة المخاطر - نسبة الربح إلى الخسارة منخفضة")

        if metrics['max_drawdown'] > 1000:
            suggestions.append("قلل حجم المراكز أو أضف وقف خسائر أفضل")

        if metrics['sharpe_ratio'] < 0.5:
            suggestions.append("الاستراتيجية تحمل مخاطر عالية نسبياً بالعائد")

        if not suggestions:
            suggestions.append("الأداء جيد - استمر في نفس الاستراتيجية")

        return suggestions