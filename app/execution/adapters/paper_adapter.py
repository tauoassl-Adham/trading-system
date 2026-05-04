import time
from typing import Dict, Any

from backend.app.execution.slippage import (
    compute_slippage,
    apply_slippage_to_price,
    simulate_latency
)
from backend.app.execution.models import Side, Order, FillEvent


class PaperAdapter:
    """
    Paper Trading Adapter:
    - يحاكي تنفيذ الأوامر بدون اتصال حقيقي مع Binance
    - يعتمد على بيانات السوق القادمة من MarketDataProvider
    - يحسب slippage + fees
    - يرجع FillEvent جاهز للـ OMS
    """

    def __init__(self, market_data_provider, slippage_cfg=None, latency_cfg=None):
        self.market_data = market_data_provider
        self.slippage_cfg = slippage_cfg or {
            "base_slippage": 0.0005,
            "k": 0.1
        }
        self.latency_cfg = latency_cfg or {
            "mean_ms": 30,
            "std_ms": 5
        }

    async def place_order(self, order: Order) -> Dict[str, Any]:
        """
        تنفيذ أمر Market أو Limit بشكل فوري (محاكاة).
        """
        # latency simulation
        simulate_latency(
            mean_ms=self.latency_cfg["mean_ms"],
            std_ms=self.latency_cfg["std_ms"]
        )

        # snapshot from market data
        snapshot = self.market_data.get_snapshot(order.request.symbol)
        mid_price = snapshot.mid_price
        avg_depth = snapshot.avg_depth

        # compute slippage
        slippage_pct = compute_slippage(
            order_qty=order.request.quantity,
            avg_depth=avg_depth,
            base_slippage=self.slippage_cfg["base_slippage"],
            k=self.slippage_cfg["k"]
        )

        # apply slippage to price
        fill_price = apply_slippage_to_price(
            mid_price=mid_price,
            slippage_pct=slippage_pct,
            side=order.request.side.value
        )

        filled_qty = order.request.quantity
        fee = filled_qty * fill_price * 0.00075  # 0.075% fee simulation

        fill_event = FillEvent(
            order_id=order.order_id,
            filled_qty=filled_qty,
            fill_price=fill_price,
            fee=fee,
            timestamp=time.time()
        )

        return {
            "filled_qty": filled_qty,
            "fill_price": fill_price,
            "fee": fee,
            "event": fill_event
        }
