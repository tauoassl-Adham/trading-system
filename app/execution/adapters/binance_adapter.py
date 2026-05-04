import asyncio
import time
import hmac
import hashlib
import json
from typing import Dict, Any, Optional

import aiohttp

from backend.app.execution.models import Order, FillEvent


class BinanceAdapter:
    """
    Binance Adapter (skeleton)
    - طبقة تجريدية للتعامل مع Binance REST و WebSocket
    - هذا الملف هو هيكل أولي فقط: لا يحوي مفاتيح أو تشغيل حي تلقائي
    - يدعم: place_order, cancel_order, get_order_book, translate responses إلى FillEvent
    - لاحقاً يمكن توسيعها لتدعم futures, margin, signed endpoints, rate-limit handling
    """

    BASE_REST = "https://api.binance.com"
    BASE_WS = "wss://stream.binance.com:9443/ws"

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
        recv_window: int = 5000,
        rate_limit_sleep: float = 0.2,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.recv_window = recv_window
        self.rate_limit_sleep = rate_limit_sleep
        self._session = session or aiohttp.ClientSession()
        self._lock = asyncio.Lock()

    def _sign_payload(self, payload: Dict[str, Any]) -> str:
        """
        Sign query string using HMAC SHA256 (Binance style).
        """
        if not self.api_secret:
            raise RuntimeError("API secret not configured for BinanceAdapter")
        qs = "&".join(f"{k}={payload[k]}" for k in sorted(payload))
        signature = hmac.new(self.api_secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
        return signature

    async def _request(self, method: str, path: str, params: Dict[str, Any] = None, signed: bool = False) -> Dict[str, Any]:
        """
        Low-level REST helper with basic rate-limit/backoff handling.
        """
        url = f"{self.BASE_REST}{path}"
        params = params or {}

        headers = {}
        if self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key

        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = self.recv_window
            signature = self._sign_payload(params)
            params["signature"] = signature

        async with self._lock:
            # basic rate-limit protection: small sleep between signed requests
            await asyncio.sleep(self.rate_limit_sleep)
            async with self._session.request(method, url, params=params, headers=headers, timeout=10) as resp:
                text = await resp.text()
                try:
                    data = json.loads(text)
                except Exception:
                    data = {"raw": text}
                if resp.status >= 400:
                    raise RuntimeError(f"Binance API error {resp.status}: {data}")
                return data

    async def place_order(self, order: Order) -> Dict[str, Any]:
        """
        Place an order on Binance (synchronous REST call).
        - For now this is a skeleton that demonstrates parameter mapping.
        - In paper mode the PaperAdapter will be used instead.
        """
        # Map internal Order -> Binance params
        req = order.request
        params = {
            "symbol": req.symbol,
            "side": req.side.value,
            "type": req.type.value,
            "quantity": str(req.quantity),
        }
        if req.price is not None:
            params["price"] = str(req.price)
        if req.time_in_force:
            params["timeInForce"] = req.time_in_force
        if req.stop_price is not None:
            params["stopPrice"] = str(req.stop_price)
        # Signed endpoint required for order placement
        resp = await self._request("POST", "/api/v3/order", params=params, signed=True)

        # Translate Binance response to FillEvent-like dict when possible
        filled_qty = float(resp.get("executedQty", 0) or 0)
        avg_price = float(resp.get("avgPrice", 0) or 0) if resp.get("avgPrice") else None
        # If avg_price not provided, try to compute from fills
        fill_price = avg_price or self._extract_fill_price_from_fills(resp.get("fills", []))
        fee = self._extract_fee_from_fills(resp.get("fills", []))

        event = FillEvent(
            order_id=order.order_id,
            filled_qty=filled_qty,
            fill_price=fill_price or 0.0,
            fee=fee,
            timestamp=time.time()
        )

        return {"filled_qty": filled_qty, "fill_price": event.fill_price, "fee": fee, "event": event, "raw": resp}

    async def cancel_order(self, symbol: str, order_id: Optional[str] = None, orig_client_order_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Cancel an order by orderId or origClientOrderId.
        """
        params = {"symbol": symbol}
        if order_id:
            params["orderId"] = order_id
        if orig_client_order_id:
            params["origClientOrderId"] = orig_client_order_id

        resp = await self._request("DELETE", "/api/v3/order", params=params, signed=True)
        return resp

    async def get_order_book(self, symbol: str, limit: int = 50) -> Dict[str, Any]:
        """
        Fetch order book snapshot.
        """
        params = {"symbol": symbol, "limit": limit}
        resp = await self._request("GET", "/api/v3/depth", params=params, signed=False)
        # Normalize snapshot: compute mid_price and avg_depth estimate
        bids = resp.get("bids", [])
        asks = resp.get("asks", [])
        mid_price = self._compute_mid_price(bids, asks)
        avg_depth = self._estimate_avg_depth(bids, asks)
        return {"raw": resp, "mid_price": mid_price, "avg_depth": avg_depth}

    def _compute_mid_price(self, bids, asks) -> float:
        try:
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            return (best_bid + best_ask) / 2.0
        except Exception:
            return 0.0

    def _estimate_avg_depth(self, bids, asks) -> float:
        """
        Very simple avg depth estimator: sum top N sizes.
        """
        try:
            depth_n = 5
            bid_depth = sum(float(b[1]) for b in bids[:depth_n])
            ask_depth = sum(float(a[1]) for a in asks[:depth_n])
            return max(1e-9, (bid_depth + ask_depth) / 2.0)
        except Exception:
            return 1e-9

    def _extract_fill_price_from_fills(self, fills) -> Optional[float]:
        try:
            if not fills:
                return None
            # weighted average price
            total_qty = 0.0
            total_value = 0.0
            for f in fills:
                qty = float(f.get("qty", 0))
                price = float(f.get("price", 0))
                total_qty += qty
                total_value += qty * price
            if total_qty == 0:
                return None
            return total_value / total_qty
        except Exception:
            return None

    def _extract_fee_from_fills(self, fills) -> float:
        try:
            fee = 0.0
            for f in fills:
                fee += float(f.get("commission", 0) or 0)
            return fee
        except Exception:
            return 0.0

    async def close(self):
        """
        Cleanup session when shutting down.
        """
        try:
            await self._session.close()
        except Exception:
            pass
