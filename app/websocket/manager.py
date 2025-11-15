"""
WebSocket connection manager for real-time updates
"""
from typing import Dict, Set, List
from fastapi import WebSocket, WebSocketDisconnect
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for users and admin"""
    
    def __init__(self):
        # Map user_id -> Set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Admin connections
        self.admin_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, user_id: str = None, is_admin: bool = False):
        """Accept and store a WebSocket connection"""
        await websocket.accept()
        
        if is_admin:
            self.admin_connections.add(websocket)
            logger.info(f"Admin WebSocket connected. Total admin connections: {len(self.admin_connections)}")
        elif user_id:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
            logger.info(f"User {user_id} WebSocket connected. Total connections: {len(self.active_connections[user_id])}")
    
    def disconnect(self, websocket: WebSocket, user_id: str = None, is_admin: bool = False):
        """Remove a WebSocket connection"""
        if is_admin:
            self.admin_connections.discard(websocket)
            logger.info(f"Admin WebSocket disconnected. Total admin connections: {len(self.admin_connections)}")
        elif user_id and user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if len(self.active_connections[user_id]) == 0:
                del self.active_connections[user_id]
            logger.info(f"User {user_id} WebSocket disconnected")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to specific user"""
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected.add(connection)
            
            # Remove disconnected connections
            for conn in disconnected:
                self.active_connections[user_id].discard(conn)
    
    async def broadcast_to_admin(self, message: dict):
        """Broadcast message to all admin connections"""
        disconnected = set()
        for connection in self.admin_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to admin: {e}")
                disconnected.add(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.admin_connections.discard(conn)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all connected users and admin"""
        # Broadcast to all users
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)
        
        # Broadcast to admin
        await self.broadcast_to_admin(message)


# Global connection manager instance
manager = ConnectionManager()

