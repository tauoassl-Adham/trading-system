import asyncio
import websockets
import json
import logging

logger = logging.getLogger(__name__)

async def stream(event_bus, symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT"]):
    """
    محرك استلام البيانات الحية (Scylla Edition)
    """
    stream_names = "/".join([f"{s.lower()}@trade" for s in symbols])
    url = f"wss://stream.binance.com:9443/stream?streams={stream_names}"

    while True:
        try:
            logger.info(f"Connecting to Binance streams: {symbols}")
            async with websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=10
            ) as ws:
                while True:
                    message = await ws.recv()
                    raw_data = json.loads(message)
                    
                    data = raw_data.get("data", {})
                    symbol = data.get("s")
                    price = float(data.get("p", 0))
                    
                    # تحويل الوقت من مللي-ثانية إلى ثانية ليتوافق مع CandleEngine
                    timestamp_ms = data.get("T", 0)
                    timestamp_s = timestamp_ms / 1000

                    if symbol and price > 0:
                        event_bus.publish("tick", {
                            "symbol": symbol,
                            "price": price,
                            "timestamp": timestamp_s
                        })

        except websockets.ConnectionClosed:
            logger.warning("Connection closed by Binance, reconnecting...")
        except Exception as e:
            logger.error(f"WS ERROR: {e}")

        logger.info("Reconnecting in 5 seconds...")
        await asyncio.sleep(5)