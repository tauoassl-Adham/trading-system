import uuid
import asyncio
from typing import Dict

from backend.app.execution.models import (
    Order,
    OrderRequest,
    OrderStatus
)


class OMS:
    """
    Order Management System (OMS)
    - يستقبل أوامر من الاستراتيجيات أو API
    - يضمن idempotency عبر client_order_id
    - يرسل الأوامر إلى Execution Router
    - يحدث حالة الأمر بعد التنفيذ
    """

    def __init__(self, execution_router):
        self.router = execution_router
        self._orders: Dict[str, Order] = {}
        self._queue = asyncio.Queue()

    async def create_order(self, req: OrderRequest) -> Order:
        """
        إنشاء أمر جديد وإضافته إلى طابور التنفيذ.
        """
        # idempotency check
        if req.client_order_id:
            for o in self._orders.values():
                if o.request.client_order_id == req.client_order_id:
                    return o

        order_id = str(uuid.uuid4())
        order = Order(
            order_id=order_id,
            request=req,
            status=OrderStatus.NEW,
            filled_qty=0.0,
            remaining_qty=req.quantity
        )

        self._orders[order_id] = order
        await self._queue.put(order)

        return order

    async def cancel_order(self, order_id: str) -> bool:
        """
        إلغاء أمر (محاكاة فقط).
        """
        if order_id not in self._orders:
            return False

        order = self._orders[order_id]

        if order.status in (OrderStatus.FILLED, OrderStatus.CANCELED):
            return False

        order.status = OrderStatus.CANCELED
        return True

    async def get_order_status(self, order_id: str) -> OrderStatus:
        """
        إرجاع حالة الأمر الحالية.
        """
        if order_id not in self._orders:
            return OrderStatus.ERROR
        return self._orders[order_id].status

    async def run(self):
        """
        حلقة التنفيذ الرئيسية:
        - تستقبل الأوامر من الطابور
        - ترسلها للـ Execution Router
        - تحدث حالة الأمر بعد التنفيذ
        """
        while True:
            order = await self._queue.get()

            try:
                plan = await self.router.route_order(order)
                result = await self.router.execute_plan(plan)

                filled_qty = result["filled_qty"]

                order.filled_qty += filled_qty
                order.remaining_qty = order.request.quantity - order.filled_qty

                if order.remaining_qty <= 0:
                    order.status = OrderStatus.FILLED
                else:
                    order.status = OrderStatus.PARTIALLY_FILLED

            except Exception:
                order.status = OrderStatus.ERROR

            finally:
                self._queue.task_done()
