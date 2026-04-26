import asyncio
import websockets
import json


async def stream(event_bus, symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT"]):
    """
    محرك استلام البيانات الحية - يدعم عدة رموز بشكل متزامن
    """
    # بناء رابط الـ WebSocket لعدة عملات
    stream_names = "/".join([f"{s.lower()}@trade" for s in symbols])
    url = f"wss://stream.binance.com:9443/stream?streams={stream_names}"

    while True:
        try:
            async with websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=10
            ) as ws:
                print(f"Connected to Binance for: {symbols}")

                while True:
                    try:
                        message = await ws.recv()
                        raw_data = json.loads(message)
                        
                        # البيانات تأتي مغلفة في حقل 'data' عند استخدام Multi-Stream
                        data = raw_data.get("data", {})
                        symbol = data.get("s")
                        price = float(data.get("p", 0))

                        if symbol and price:
                            event_bus.publish("tick", {
                                "symbol": symbol,
                                "price": price,
                                "timestamp": data.get("T")
                            })

                    except websockets.ConnectionClosed:
                        print("Connection closed by server")
                        break

        except Exception as e:
            print(f"WS ERROR: {str(e)}")

        print("Reconnecting in 5 seconds...")
        await asyncio.sleep(5)
