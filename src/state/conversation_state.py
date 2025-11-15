"""Conversation state management for maintaining agent context."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class MessageRole(Enum):
    """Message roles in conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """A single message in the conversation."""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary."""
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {})
        )


class ConversationState:
    """
    Manages conversation history and context for an agent session.
    Supports message tracking, context windows, and conversation persistence.
    """
    
    def __init__(
        self,
        session_id: str,
        max_history: int = 100,
        system_prompt: Optional[str] = None
    ):
        """
        Initialize conversation state.
        
        Args:
            session_id: Unique identifier for this conversation
            max_history: Maximum number of messages to retain
            system_prompt: Optional system prompt to initialize conversation
        """
        self.session_id = session_id
        self.max_history = max_history
        self.messages: List[Message] = []
        self.metadata: Dict[str, Any] = {
            "created_at": datetime.now(),
            "last_updated": datetime.now()
        }
        
        # Add system prompt if provided
        if system_prompt:
            self.add_message(MessageRole.SYSTEM, system_prompt)
    
    def add_message(
        self,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Add a new message to the conversation.
        
        Args:
            role: Role of the message sender
            content: Message content
            metadata: Optional additional metadata
            
        Returns:
            The created message
        """
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        
        self.messages.append(message)
        self.metadata["last_updated"] = datetime.now()
        
        # Trim history if needed (keep system messages)
        if len(self.messages) > self.max_history:
            # Keep system messages at the start
            system_messages = [m for m in self.messages if m.role == MessageRole.SYSTEM]
            other_messages = [m for m in self.messages if m.role != MessageRole.SYSTEM]
            
            # Keep most recent messages
            trimmed_messages = other_messages[-(self.max_history - len(system_messages)):]
            self.messages = system_messages + trimmed_messages
        
        return message
    
    def get_messages(
        self,
        role: Optional[MessageRole] = None,
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        Retrieve messages from the conversation.
        
        Args:
            role: Optional filter by message role
            limit: Optional limit on number of messages
            
        Returns:
            List of messages
        """
        messages = self.messages
        
        if role:
            messages = [m for m in messages if m.role == role]
        
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    def get_context_window(self, window_size: int = 10) -> List[Message]:
        """
        Get the most recent messages as context window.
        
        Args:
            window_size: Number of recent messages to include
            
        Returns:
            Recent messages
        """
        return self.messages[-window_size:]
    
    def clear_history(self, keep_system: bool = True) -> None:
        """
        Clear conversation history.
        
        Args:
            keep_system: Whether to keep system messages
        """
        if keep_system:
            self.messages = [m for m in self.messages if m.role == MessageRole.SYSTEM]
        else:
            self.messages = []
        
        self.metadata["last_updated"] = datetime.now()
        self.metadata["cleared_at"] = datetime.now()
    
    def get_message_count(self) -> Dict[str, int]:
        """Get count of messages by role."""
        counts = {role.value: 0 for role in MessageRole}
        for message in self.messages:
            counts[message.role.value] += 1
        return counts
    
    def to_dict(self) -> Dict[str, Any]:
        """Export conversation state to dictionary."""
        return {
            "session_id": self.session_id,
            "max_history": self.max_history,
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """Export conversation state to JSON string."""
        return json.dumps(self.to_dict(), default=str, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationState':
        """Create conversation state from dictionary."""
        state = cls(
            session_id=data["session_id"],
            max_history=data.get("max_history", 100)
        )
        
        state.messages = [Message.from_dict(m) for m in data.get("messages", [])]
        state.metadata = data.get("metadata", {})
        
        return state
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ConversationState':
        """Create conversation state from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the conversation state."""
        return {
            "session_id": self.session_id,
            "total_messages": len(self.messages),
            "message_counts": self.get_message_count(),
            "created_at": self.metadata.get("created_at"),
            "last_updated": self.metadata.get("last_updated")
        }
