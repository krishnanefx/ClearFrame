"""Main state manager coordinating conversation state and caching."""

from typing import Dict, Any, Optional
import logging
from pathlib import Path
import json

from .conversation_state import ConversationState, MessageRole
from .cache_manager import CacheManager

logger = logging.getLogger(__name__)


class StateManager:
    """
    Central state management system coordinating conversation history,
    caching, and persistence across agent sessions.
    """
    
    def __init__(
        self,
        cache_enabled: bool = True,
        cache_size: int = 1000,
        cache_ttl: int = 3600,
        persistence_dir: Optional[str] = None
    ):
        """
        Initialize state manager.
        
        Args:
            cache_enabled: Whether to enable caching
            cache_size: Maximum cache size
            cache_ttl: Default cache TTL in seconds
            persistence_dir: Directory for persisting state (None to disable)
        """
        self._conversations: Dict[str, ConversationState] = {}
        self.cache_manager = CacheManager(max_size=cache_size, default_ttl=cache_ttl) if cache_enabled else None
        self.persistence_dir = Path(persistence_dir) if persistence_dir else None
        
        if self.persistence_dir:
            self.persistence_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"StateManager initialized (cache_enabled={cache_enabled}, persistence={bool(self.persistence_dir)})")
    
    def create_conversation(
        self,
        session_id: str,
        system_prompt: Optional[str] = None,
        max_history: int = 100
    ) -> ConversationState:
        """
        Create a new conversation state.
        
        Args:
            session_id: Unique session identifier
            system_prompt: Optional system prompt
            max_history: Maximum message history
            
        Returns:
            Created conversation state
        """
        if session_id in self._conversations:
            logger.warning(f"Conversation {session_id} already exists")
            return self._conversations[session_id]
        
        conversation = ConversationState(
            session_id=session_id,
            max_history=max_history,
            system_prompt=system_prompt
        )
        
        self._conversations[session_id] = conversation
        logger.info(f"Created conversation: {session_id}")
        
        return conversation
    
    def get_conversation(self, session_id: str) -> Optional[ConversationState]:
        """Retrieve a conversation state by session ID."""
        return self._conversations.get(session_id)
    
    def delete_conversation(self, session_id: str) -> bool:
        """
        Delete a conversation state.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted, False if not found
        """
        if session_id in self._conversations:
            del self._conversations[session_id]
            logger.info(f"Deleted conversation: {session_id}")
            return True
        return False
    
    def add_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a message to a conversation.
        
        Args:
            session_id: Session identifier
            role: Message role
            content: Message content
            metadata: Optional metadata
            
        Returns:
            True if added, False if conversation not found
        """
        conversation = self.get_conversation(session_id)
        if not conversation:
            logger.warning(f"Conversation {session_id} not found")
            return False
        
        conversation.add_message(role, content, metadata)
        return True
    
    def get_conversation_context(
        self,
        session_id: str,
        window_size: int = 10
    ) -> Optional[list]:
        """
        Get recent conversation context.
        
        Args:
            session_id: Session identifier
            window_size: Number of recent messages
            
        Returns:
            List of recent messages or None
        """
        conversation = self.get_conversation(session_id)
        if not conversation:
            return None
        
        return [m.to_dict() for m in conversation.get_context_window(window_size)]
    
    def save_conversation(self, session_id: str) -> bool:
        """
        Persist a conversation to disk.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if saved, False otherwise
        """
        if not self.persistence_dir:
            logger.warning("Persistence not enabled")
            return False
        
        conversation = self.get_conversation(session_id)
        if not conversation:
            logger.warning(f"Conversation {session_id} not found")
            return False
        
        try:
            file_path = self.persistence_dir / f"{session_id}.json"
            with open(file_path, 'w') as f:
                f.write(conversation.to_json())
            
            logger.info(f"Saved conversation: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save conversation {session_id}: {e}")
            return False
    
    def load_conversation(self, session_id: str) -> Optional[ConversationState]:
        """
        Load a persisted conversation from disk.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Loaded conversation or None
        """
        if not self.persistence_dir:
            logger.warning("Persistence not enabled")
            return None
        
        try:
            file_path = self.persistence_dir / f"{session_id}.json"
            if not file_path.exists():
                logger.warning(f"Conversation file not found: {session_id}")
                return None
            
            with open(file_path, 'r') as f:
                conversation = ConversationState.from_json(f.read())
            
            self._conversations[session_id] = conversation
            logger.info(f"Loaded conversation: {session_id}")
            return conversation
        except Exception as e:
            logger.error(f"Failed to load conversation {session_id}: {e}")
            return None
    
    def list_conversations(self) -> list:
        """List all active conversation session IDs."""
        return list(self._conversations.keys())
    
    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get cache statistics if caching is enabled."""
        if not self.cache_manager:
            return None
        return self.cache_manager.get_stats()
    
    def clear_cache(self) -> bool:
        """
        Clear all cached data.
        
        Returns:
            True if cache cleared, False if caching not enabled
        """
        if not self.cache_manager:
            return False
        
        self.cache_manager.clear()
        return True
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics."""
        stats = {
            "active_conversations": len(self._conversations),
            "persistence_enabled": bool(self.persistence_dir),
            "cache_enabled": bool(self.cache_manager)
        }
        
        if self.cache_manager:
            stats["cache_stats"] = self.cache_manager.get_stats()
        
        # Add conversation summaries
        conversation_summaries = []
        for conv in self._conversations.values():
            conversation_summaries.append(conv.get_summary())
        stats["conversations"] = conversation_summaries
        
        return stats
