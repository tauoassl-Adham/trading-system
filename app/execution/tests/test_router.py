import asyncio
import pytest

from backend.app.execution.router import ExecutionRouter
from backend.app.execution.adapters.paper_adapter import PaperAdapter
from backend.app.execution.market_data.mock_market_data import MockMarketDataProvider
from backend.app.execution.models import OrderRequest, Side, OrderType


@pytest.mark.asyncio
async def test_route_market_and_limit():
    """
    Test that ExecutionRouter maps order types to expected plan types
    and that execute_plan returns a result structure when using PaperAdapter.
    """
    md = MockMarketDataProvider(initial_data={
        "BTCUSDT": {"mid_price": 60000.0, "avg_depth": 5.0}
    })
    adapter = PaperAdapter(market_data_provider=md)
    router = ExecutionRouter(adapter, slippage_cfg={"base_slippage": 0.0005, "k": 0.1}, latency_cfg={"mean_ms": 0, "std_ms": 0})

    # Create a fake Order-like object for routing (minimal)
    class FakeOrder:
        def __init__(self, req):
            self.request = req
            self.order_id = "fake-1"

    # MARKET order should route to MARKET plan
    market_req = OrderRequest(symbol="BTCUSDT", side=Side.BUY, type=OrderType.MARKET, quantity=0.001)
    market_order = FakeOrder(market_req)
    plan = await router.route_order(market_order)
    assert plan["type"] == "MARKET"

    result = await router.execute_plan(plan)
    assert "filled_qty" in result
    assert result["filled_qty"] > 0

    # LIMIT order should route to LIMIT plan
    limit_req = OrderRequest(symbol="BTCUSDT", side=Side.SELL, type=OrderType.LIMIT, quantity=0.001, price=60050.0)
    limit_order = FakeOrder(limit_req)
    plan2 = await router.route_order(limit_order)
    assert plan2["type"] == "LIMIT"

    result2 = await router.execute_plan(plan2)
    assert "filled_qty" in result2
import asyncio
import pytest

from backend.app.execution.router import ExecutionRouter
from backend.app.execution.adapters.paper_adapter import PaperAdapter
from backend.app.execution.market_data.mock_market_data import MockMarketDataProvider
from backend.app.execution.models import OrderRequest, Side, OrderType


@pytest.mark.asyncio
async def test_route_market_and_limit():
    """
    Test that ExecutionRouter maps order types to expected plan types
    and that execute_plan returns a result structure when using PaperAdapter.
    """
    md = MockMarketDataProvider(initial_data={
        "BTCUSDT": {"mid_price": 60000.0, "avg_depth": 5.0}
    })
    adapter = PaperAdapter(market_data_provider=md)
    router = ExecutionRouter(adapter, slippage_cfg={"base_slippage": 0.0005, "k": 0.1}, latency_cfg={"mean_ms": 0, "std_ms": 0})

    # Create a fake Order-like object for routing (minimal)
    class FakeOrder:
        def __init__(self, req):
            self.request = req
            self.order_id = "fake-1"

    # MARKET order should route to MARKET plan
    market_req = OrderRequest(symbol="BTCUSDT", side=Side.BUY, type=OrderType.MARKET, quantity=0.001)
    market_order = FakeOrder(market_req)
    plan = await router.route_order(market_order)
    assert plan["type"] == "MARKET"

    result = await router.execute_plan(plan)
    assert "filled_qty" in result
    assert result["filled_qty"] > 0

    # LIMIT order should route to LIMIT plan
    limit_req = OrderRequest(symbol="BTCUSDT", side=Side.SELL, type=OrderType.LIMIT, quantity=0.001, price=60050.0)
    limit_order = FakeOrder(limit_req)
    plan2 = await router.route_order(limit_order)
    assert plan2["type"] == "LIMIT"

    result2 = await router.execute_plan(plan2)
    assert "filled_qty" in result2
