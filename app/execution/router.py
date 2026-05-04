import asyncio
from typing import Dict, Any

from backend.app.execution.models import Order, OrderRequest, Side, OrderType
from backend.app.execution.slippage import simulate_latency


class ExecutionRouter:
    """
    Execution Router
    - يقرر خطة التنفيذ لكل أمر (simple routing)
    - يدعم تنفيذ Market/Limit مباشرة عبر Exchange Adapter
    - يمكن توسيعه لاحقاً ليشمل TWAP, VWAP, Slicing, Smart Order Routing
    """

    def __init__(self, adapter, slippage_cfg=None, latency_cfg=None):
        self.adapter = adapter
        self.slippage_cfg = slippage_cfg or {"base_slippage": 0.0005, "k": 0.1}
        self.latency_cfg = latency_cfg or {"mean_ms": 30, "std_ms": 5}
        # semaphore to limit concurrent executions (configurable)
        self._concurrency_sem = asyncio.Semaphore(10)

    async def route_order(self, order: Order) -> Dict[str, Any]:
        """
        يبني خطة تنفيذ مبسطة بناءً على نوع الأمر واستراتيجية الطلب.
        ترجع dict تمثل الخطة التي سينفذها execute_plan.
        """
        req: OrderRequest = order.request

        # Simple routing rules
        if req.type == OrderType.MARKET or (req.strategy and req.strategy.upper() == "AGGRESSIVE"):
            return {"type": "MARKET", "order": order}

        if req.type == OrderType.LIMIT:
            return {"type": "LIMIT", "order": order}

        if req.type == OrderType.IOC:
            return {"type": "IOC", "order": order}

        # default fallback
        return {"type": "MARKET", "order": order}

    async def execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        ينفذ الخطة عبر Adapter المناسب.
        يدعم retries بسيطة ويدير الـ concurrency.
        يعيد dict يحتوي على filled_qty, fill_price, fee, event (اختياري).
        """
        order: Order = plan["order"]
        plan_type: str = plan.get("type", "MARKET")

        # Acquire concurrency slot
        async with self._concurrency_sem:
            # simulate router-level latency if configured
            simulate_latency(
                mean_ms=self.latency_cfg.get("mean_ms", 30),
                std_ms=self.latency_cfg.get("std_ms", 5)
            )

            # For MARKET orders we forward directly to adapter
            if plan_type == "MARKET":
                return await self._place_with_retries(order)

            # For LIMIT orders we attempt a simple place (adapter should handle limit semantics)
            if plan_type == "LIMIT":
                return await self._place_with_retries(order)

            # For IOC we place and expect adapter to honor IOC semantics
            if plan_type == "IOC":
                return await self._place_with_retries(order)

            # Future: implement TWAP/VWAP/slicing here
            return await self._place_with_retries(order)

    async def _place_with_retries(self, order: Order, max_retries: int = 3) -> Dict[str, Any]:
        """
        Helper: place order via adapter with retry policy and exponential backoff.
        """
        attempt = 0
        backoff_base = 0.1  # seconds

        while attempt < max_retries:
            try:
                # adapter.place_order may be async or sync; support both
                result = await self._maybe_await(self.adapter.place_order(order))
                # Expect result to be a dict with filled_qty, fill_price, fee, event
                return result
            except Exception as exc:
                attempt += 1
                if attempt >= max_retries:
                    # final failure: raise to caller (OMS will mark order ERROR)
                    raise
                # exponential backoff with jitter
                backoff = backoff_base * (2 ** (attempt - 1))
                jitter = backoff * 0.1
                await asyncio.sleep(backoff + (jitter * (0.5 - asyncio.get_event_loop().time() % 1)))

    async def _maybe_await(self, value):
        """
        Utility: await if value is awaitable, else return directly.
        """
        if asyncio.iscoroutine(value) or asyncio.isfuture(value):
            return await value
        return value
