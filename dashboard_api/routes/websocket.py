"""WebSocket routes for real-time updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import json
import logging

from websocket import manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None)
):
    """WebSocket endpoint for real-time updates.
    
    Clients can connect and receive real-time events:
    - stream_status_changed: Stream status updates
    - track_changed: Track change notifications
    - log_entry: Log entries
    - metric_update: Metrics updates
    
    Args:
        websocket: WebSocket connection.
        client_id: Optional client identifier.
    """
    # Generate client ID if not provided
    if not client_id:
        import uuid
        client_id = str(uuid.uuid4())
    
    # Connect client
    await manager.connect(websocket, client_id)
    
    # Send welcome message
    await manager.send_personal_message({
        'type': 'connected',
        'data': {
            'client_id': client_id,
            'message': 'Connected to dashboard WebSocket'
        }
    }, websocket)
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Handle subscription requests
                if message.get('type') == 'subscribe':
                    event_type = message.get('event_type')
                    if event_type:
                        manager.subscribe(websocket, event_type)
                        await manager.send_personal_message({
                            'type': 'subscribed',
                            'data': {'event_type': event_type}
                        }, websocket)
                
                elif message.get('type') == 'unsubscribe':
                    event_type = message.get('event_type')
                    if event_type:
                        manager.unsubscribe(websocket, event_type)
                        await manager.send_personal_message({
                            'type': 'unsubscribed',
                            'data': {'event_type': event_type}
                        }, websocket)
                
                elif message.get('type') == 'ping':
                    # Respond to ping with pong
                    await manager.send_personal_message({
                        'type': 'pong',
                        'data': {}
                    }, websocket)
            
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from client {client_id}")
            except Exception as e:
                logger.error(f"Error processing message from {client_id}: {e}")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        manager.disconnect(websocket)


