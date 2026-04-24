import asyncio
import websockets
import json


async def stream(event_bus):
    url = "wss://stream.binance.com:9443/ws/btcusdt@trade"

    async with websockets.connect(url) as ws:
        print("Connected to Binance")

        async for message in ws:
            data = json.loads(message)

            price = float(data["p"])

            print("TICK RECEIVED:", price)

            event_bus.publish("tick", {
                "symbol": "BTCUSDT",
                "price": price,
                "timestamp": data["T"]
            })