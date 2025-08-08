from typing import List
from fastapi import WebSocket
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"=== WebSocket connected. Total connections: {len(self.active_connections)} ===")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"=== WebSocket disconnected. Total connections: {len(self.active_connections)} ===")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected WebSocket clients."""
        if not self.active_connections:
            print("=== No active WebSocket connections to broadcast to ===")
            return
            
        print(f"=== Broadcasting to {len(self.active_connections)} connections ===")
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"=== WebSocket broadcast error: {e} ===")
                # Remove bad connection
                self.disconnect(connection)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to a specific WebSocket client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"=== WebSocket personal message error: {e} ===")
            self.disconnect(websocket)
