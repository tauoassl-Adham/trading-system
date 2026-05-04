import pytest
import math
import time

from backend.app.execution.market_data.mock_market_data import MockMarketDataProvider
from backend.app.execution.adapters.paper_adapter import PaperAdapter
from backend.app.execution.slippage import compute_slippage, apply_slippage_to_price
from backend.app.execution.models import OrderRequest, Side, OrderType, Order


@pytest.mark.asyncio
async def test_compute_slippage_behavior():
    """
    Verify slippage increases with order size relative to avg_depth and base_slippage floor.
    """
    base = 0.0005
    k = 0.1

    # small order vs deep market -> near base slippage
    sl_small = compute_slippage(order_qty=0.001, avg_depth=100.0, base_slippage=base, k=k)
    assert sl_small >= base
    assert sl_small < base + 0.01

    # large order vs shallow market -> larger slippage
    sl_large = compute_slippage(order_qty=10.0, avg_depth=1.0, base_slippage=base, k=k)
    assert sl_large > sl_small


@pytest.mark.asyncio
async def test_apply_slippage_to_price_buy_sell():
    """
    Ensure apply_slippage_to_price moves price up for BUY and down for SELL.
    """
    mid = 100.0
    sl = 0.01  # 1%

    buy_price = apply_slippage_to_price(mid_price=mid, slippage_pct=sl, side="BUY")
    sell_price = apply_slippage_to_price(mid_price=mid, slippage_pct=sl, side="SELL")

    assert buy_price > mid
    assert sell_price < mid
    assert math.isclose(buy_price, 101.0, rel_tol=1e-6)
    assert math.isclose(sell_price, 99.0, rel_tol=1e-6)


@pytest.mark.asyncio
async def test_paper_adapter_fill_and_fee():
    """
    Integration test for PaperAdapter:
    - Given a market snapshot, placing a market order returns filled_qty and reasonable fill_price and fee.
    """
    md = MockMarketDataProvider(initial_data={
        "BTCUSDT": {"mid_price": 50000.0, "avg_depth": 5.0}
    })

    adapter = PaperAdapter(market_data_provider=md, slippage_cfg={"base_slippage": 0.0005, "k": 0.1}, latency_cfg={"mean_ms": 0, "std_ms": 0})

    # Build a minimal Order-like object expected by adapter
    req = OrderRequest(client_order_id="t-adapter-1", symbol="BTCUSDT", side=Side.BUY, type=OrderType.MARKET, quantity=0.005)
    order = Order(order_id="o-adapter-1", request=req)

    result = await adapter.place_order(order)

    assert "filled_qty" in result
    assert "fill_price" in result
    assert "fee" in result
    assert result["filled_qty"] == pytest.approx(0.005, rel=1e-6)
    assert result["fill_price"] > 0
    assert result["fee"] > 0

    # Fee should be roughly filled_qty * fill_price * fee_rate (0.00075)
    expected_fee = result["filled_qty"] * result["fill_price"] * 0.00075
    assert pytest.approx(expected_fee, rel=1e-3) == result["fee"]
