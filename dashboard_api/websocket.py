"""WebSocket manager for real-time updates."""

from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Set
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_ids: Dict[WebSocket, str] = {}
        self.subscriptions: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection.
            client_id: Unique client identifier.
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_ids[websocket] = client_id
        logger.info(f"WebSocket connected: {client_id}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove.
        """
        if websocket in self.active_connections:
            client_id = self.connection_ids.get(websocket, "unknown")
            self.active_connections.remove(websocket)
            del self.connection_ids[websocket]

            # Remove from all subscriptions
            for subscribers in self.subscriptions.values():
                subscribers.discard(websocket)

            logger.info(f"WebSocket disconnected: {client_id}")

    def subscribe(self, websocket: WebSocket, event_type: str):
        """Subscribe a client to an event type.

        Args:
            websocket: WebSocket connection.
            event_type: Event type to subscribe to.
        """
        if event_type not in self.subscriptions:
            self.subscriptions[event_type] = set()
        self.subscriptions[event_type].add(websocket)

    def unsubscribe(self, websocket: WebSocket, event_type: str):
        """Unsubscribe a client from an event type.

        Args:
            websocket: WebSocket connection.
            event_type: Event type to unsubscribe from.
        """
        if event_type in self.subscriptions:
            self.subscriptions[event_type].discard(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific client.

        Args:
            message: Message to send.
            websocket: Target WebSocket connection.
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast(self, message: dict, event_type: str = None):
        """Broadcast a message to all connected clients or subscribers.

        Args:
            message: Message to broadcast.
            event_type: Optional event type for targeted broadcast.
        """
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()

        # Determine recipients
        if event_type and event_type in self.subscriptions:
            recipients = list(self.subscriptions[event_type])
        else:
            recipients = self.active_connections.copy()

        # Send to all recipients
        disconnected = []
        for connection in recipients:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_stream_status(self, status: str, **kwargs):
        """Broadcast stream status change.

        Args:
            status: Stream status (running, stopped, error).
            **kwargs: Additional status information.
        """
        await self.broadcast(
            {"type": "stream_status_changed", "data": {"status": status, **kwargs}},
            event_type="stream_status",
        )

    async def broadcast_track_change(self, artist: str, title: str, **kwargs):
        """Broadcast track change event.

        Args:
            artist: Track artist.
            title: Track title.
            **kwargs: Additional track information.
        """
        await self.broadcast(
            {"type": "track_changed", "data": {"artist": artist, "title": title, **kwargs}},
            event_type="track_change",
        )

    async def broadcast_log_entry(self, level: str, message: str, **kwargs):
        """Broadcast log entry.

        Args:
            level: Log level (info, warning, error).
            message: Log message.
            **kwargs: Additional context.
        """
        await self.broadcast(
            {"type": "log_entry", "data": {"level": level, "message": message, **kwargs}},
            event_type="logs",
        )

    async def broadcast_metric_update(self, metrics: dict):
        """Broadcast metrics update.

        Args:
            metrics: Metrics data.
        """
        await self.broadcast({"type": "metric_update", "data": metrics}, event_type="metrics")


# Global connection manager instance
manager = ConnectionManager()
