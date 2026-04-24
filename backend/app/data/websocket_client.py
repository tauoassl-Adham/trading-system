import asyncio
import websockets
import json


async def stream(event_bus):
    url = "wss://stream.binance.com:9443/ws/btcusdt@trade"

    while True:
        try:
            async with websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=10
            ) as ws:
                print("Connected to Binance")

                while True:
                    try:
                        message = await ws.recv()
                        data = json.loads(message)

                        price = float(data["p"])

                        print("TICK RECEIVED:", price)

                        event_bus.publish("tick", {
                            "symbol": "BTCUSDT",
                            "price": price,
                            "timestamp": data["T"]
                        })

                    except websockets.ConnectionClosed:
                        print("Connection closed by server")
                        break

        except Exception as e:
            import traceback
            print("WS ERROR:")
            traceback.print_exc()

        print("Reconnecting in 3 seconds...")
        await asyncio.sleep(3)