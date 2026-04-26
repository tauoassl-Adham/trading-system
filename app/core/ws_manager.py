import asyncio
from fastapi import WebSocket
from typing import List

class WSManager:
    def __init__(self):
        # قائمة بالاتصالات النشطة
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """إرسال البيانات لكل من يراقب المنصة الآن"""
        for connection in self.active_connections:
            await connection.send_json(message)

# نسخة واحدة للتحكم في كل الاتصالات
ws_manager = WSManager()