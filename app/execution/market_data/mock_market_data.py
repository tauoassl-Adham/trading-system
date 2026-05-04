import time
from typing import Dict, Any


class MarketSnapshot:
    """
    Simple container for market snapshot used by PaperAdapter.
    Attributes:
        symbol: market symbol string
        mid_price: float mid price (best bid/ask midpoint)
        avg_depth: float estimated average depth (size)
        timestamp: float epoch seconds
    """
    def __init__(self, symbol: str, mid_price: float, avg_depth: float):
        self.symbol = symbol
        self.mid_price = float(mid_price)
        self.avg_depth = float(avg_depth)
        self.timestamp = time.time()


class MockMarketDataProvider:
    """
    Mock Market Data Provider
    - يوفر لقطات سوق بسيطة (mid_price, avg_depth) للاختبارات والمحاكاة
    - يمكن تهيئته بقيم ابتدائية لكل رمز، ويمكن تحديث الأسعار برمجياً
    - الواجهة المستخدمة من PaperAdapter: get_snapshot(symbol) -> MarketSnapshot
    """

    def __init__(self, initial_data: Dict[str, Dict[str, float]] = None):
        """
        initial_data example:
        {
            "BTCUSDT": {"mid_price": 60000.0, "avg_depth": 5.0},
            "ETHUSDT": {"mid_price": 3500.0, "avg_depth": 20.0},
        }
        """
        self._data: Dict[str, Dict[str, float]] = {}
        if initial_data:
            for sym, vals in initial_data.items():
                self._data[sym.upper()] = {
                    "mid_price": float(vals.get("mid_price", 0.0)),
                    "avg_depth": float(vals.get("avg_depth", 1.0))
                }

    def register_symbol(self, symbol: str, mid_price: float, avg_depth: float = 1.0):
        self._data[symbol.upper()] = {"mid_price": float(mid_price), "avg_depth": float(avg_depth)}

    def update_price(self, symbol: str, mid_price: float, avg_depth: float = None):
        sym = symbol.upper()
        if sym not in self._data:
            self.register_symbol(sym, mid_price, avg_depth or 1.0)
            return
        self._data[sym]["mid_price"] = float(mid_price)
        if avg_depth is not None:
            self._data[sym]["avg_depth"] = float(avg_depth)

    def get_snapshot(self, symbol: str) -> MarketSnapshot:
        """
        Returns a MarketSnapshot for the requested symbol.
        If symbol not registered, returns a default snapshot with zeros to avoid crashes.
        """
        sym = symbol.upper()
        vals = self._data.get(sym)
        if not vals:
            # default safe snapshot
            return MarketSnapshot(symbol=sym, mid_price=0.0, avg_depth=1e-9)
        return MarketSnapshot(symbol=sym, mid_price=vals["mid_price"], avg_depth=vals["avg_depth"])

    def bulk_update(self, updates: Dict[str, Dict[str, float]]):
        """
        Update multiple symbols at once. Useful for tests.
        updates example:
        {
            "BTCUSDT": {"mid_price": 61000.0},
            "ETHUSDT": {"mid_price": 3600.0, "avg_depth": 25.0}
        }
        """
        for sym, vals in updates.items():
            if "mid_price" in vals:
                self.update_price(sym, vals["mid_price"], vals.get("avg_depth"))

    def list_symbols(self) -> Dict[str, Dict[str, float]]:
        return dict(self._data)
