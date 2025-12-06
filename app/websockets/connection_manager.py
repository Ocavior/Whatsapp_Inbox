from typing import Set
from fastapi import WebSocket
from app.utils.logger import logger
from datetime import datetime


class ConnectionManager:
    """Manage WebSocket connections for real-time notifications"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"✅ WebSocket connected. Total connections: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.discard(websocket)
        logger.info(f"🔌 WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Send notification to all connected clients"""
        if not self.active_connections:
            logger.warning("⚠️ No active WebSocket connections to broadcast to")
            return
            
        dead_connections = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
                logger.info(f"📤 Sent notification to client: {message.get('type')}")
            except Exception as e:
                logger.error(f"❌ Error sending to client: {e}")
                dead_connections.add(connection)
        
        # Remove dead connections
        for conn in dead_connections:
            self.active_connections.discard(conn)
            logger.warning("🗑️ Removed dead connection")
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)


# Create global instance
manager = ConnectionManager()