import asyncio
from typing import Dict, List
from fastapi import WebSocket


class ConnectionManager:
    """
    Manage WebSocket connections per room.
    """

    def __init__(self):
        # room_id -> list of websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(room_id, []).append(websocket)

    def disconnect(self, room_id: str, websocket: WebSocket):
        conns = self.active_connections.get(room_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            # remove room if empty
            self.active_connections.pop(room_id, None)

    async def broadcast(self, room_id: str, message: dict):
        """
        Broadcast a JSON-able dict to all clients in room.
        """
        conns = self.active_connections.get(room_id, [])[:]
        if not conns:
            return

        # send concurrently
        await asyncio.gather(*(conn.send_json(message) for conn in conns))
