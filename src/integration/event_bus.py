"""Event Bus for inter-component communication."""

from typing import Dict, List, Callable, Any, Optional
from enum import Enum
import logging
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Supported event types in the system."""
    TOOL_EXECUTED = "tool_executed"
    TOOL_FAILED = "tool_failed"
    STATE_UPDATED = "state_updated"
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_ERROR = "agent_error"
    TASK_QUEUED = "task_queued"
    TASK_COMPLETED = "task_completed"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"


@dataclass
class Event:
    """Event data structure."""
    event_type: EventType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source
        }


class EventBus:
    """
    Event bus for publish-subscribe communication between components.
    Enables loose coupling and observability across the system.
    """
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_history: List[Event] = []
        self._max_history = 1000
        logger.info("EventBus initialized")
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event is published
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> bool:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            callback: Callback function to remove
            
        Returns:
            True if unsubscribed, False if not found
        """
        if event_type in self._subscribers and callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)
            logger.debug(f"Unsubscribed from {event_type.value}")
            return True
        return False
    
    def publish(self, event_type: EventType, data: Dict[str, Any], source: str = "unknown") -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: Type of event being published
            data: Event payload data
            source: Source component publishing the event
        """
        event = Event(
            event_type=event_type,
            data=data,
            source=source
        )
        
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Notify subscribers
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Error in event callback: {e}", exc_info=True)
        
        logger.debug(f"Published event: {event_type.value} from {source}")
    
    def get_history(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
        """
        Retrieve event history.
        
        Args:
            event_type: Optional filter by event type
            limit: Maximum number of events to return
            
        Returns:
            List of events
        """
        if event_type:
            filtered = [e for e in self._event_history if e.event_type == event_type]
            return filtered[-limit:]
        return self._event_history[-limit:]
    
    def clear_history(self) -> None:
        """Clear all event history."""
        self._event_history.clear()
        logger.info("Event history cleared")
    
    def get_subscriber_count(self, event_type: EventType) -> int:
        """Get number of subscribers for an event type."""
        return len(self._subscribers.get(event_type, []))
    
    def list_event_types(self) -> List[str]:
        """List all event types that have subscribers."""
        return [et.value for et in self._subscribers.keys()]
