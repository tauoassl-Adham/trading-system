import asyncio
import pytest
import time

from backend.app.execution.oms import OMS
from backend.app.execution.router import ExecutionRouter
from backend.app.execution.adapters.paper_adapter import PaperAdapter
from backend.app.execution.market_data.mock_market_data import MockMarketDataProvider
from backend.app.execution.models import OrderRequest, Side, OrderType, OrderStatus


@pytest.mark.asyncio
async def test_market_order_fill():
    """
    Integration-style test:
    - Mock market data provider with a BTCUSDT snapshot
    - PaperAdapter uses slippage/latency defaults
    - ExecutionRouter routes MARKET orders to adapter
    - OMS.run processes the queue and updates order state to FILLED
    """
    # Setup mock market data
    md = MockMarketDataProvider(initial_data={
        "BTCUSDT": {"mid_price": 60000.0, "avg_depth": 5.0}
    })

    # Setup adapter, router, oms
    adapter = PaperAdapter(market_data_provider=md)
    router = ExecutionRouter(adapter, slippage_cfg={"base_slippage": 0.0005, "k": 0.1}, latency_cfg={"mean_ms": 0, "std_ms": 0})
    oms = OMS(router)

    # Start OMS run loop in background
    loop_task = asyncio.create_task(oms.run())

    # Create a market order request
    req = OrderRequest(
        client_order_id="test-c1",
        symbol="BTCUSDT",
        side=Side.BUY,
        type=OrderType.MARKET,
        quantity=0.001
    )

    order = await oms.create_order(req)

    # Wait briefly for the OMS loop to process the order
    await asyncio.sleep(0.2)

    # Assertions
    assert order.order_id in oms._orders
    assert order.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED)
    assert order.filled_qty > 0

    # Cleanup
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_idempotency_client_order_id():
    """
    Ensure that creating an order with the same client_order_id returns the same Order object (idempotency).
    """
    md = MockMarketDataProvider(initial_data={
        "ETHUSDT": {"mid_price": 3500.0, "avg_depth": 10.0}
    })
    adapter = PaperAdapter(market_data_provider=md)
    router = ExecutionRouter(adapter, latency_cfg={"mean_ms": 0, "std_ms": 0})
    oms = OMS(router)

    # Start OMS loop
    loop_task = asyncio.create_task(oms.run())

    req1 = OrderRequest(
        client_order_id="idem-123",
        symbol="ETHUSDT",
        side=Side.SELL,
        type=OrderType.MARKET,
        quantity=0.01
    )

    req2 = OrderRequest(
        client_order_id="idem-123",  # same idempotency key
        symbol="ETHUSDT",
        side=Side.SELL,
        type=OrderType.MARKET,
        quantity=0.01
    )

    order1 = await oms.create_order(req1)
    order2 = await oms.create_order(req2)

    # They should be the same object (idempotent)
    assert order1.order_id == order2.order_id
    assert order1 is order2

    # Cleanup
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass
