"""Test suite for state management components."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
import sys
from pathlib import Path
import tempfile
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from state.conversation_state import ConversationState, MessageRole, Message
from state.cache_manager import CacheManager, CacheEntry
from state.state_manager import StateManager


class TestMessage(unittest.TestCase):
    """Test cases for Message class."""
    
    def test_message_creation(self):
        """Test message creation."""
        msg = Message(
            role=MessageRole.USER,
            content="Hello, world!",
            metadata={"source": "test"}
        )
        
        self.assertEqual(msg.role, MessageRole.USER)
        self.assertEqual(msg.content, "Hello, world!")
        self.assertEqual(msg.metadata["source"], "test")
    
    def test_message_to_dict(self):
        """Test message serialization to dict."""
        msg = Message(
            role=MessageRole.ASSISTANT,
            content="Response"
        )
        
        data = msg.to_dict()
        
        self.assertEqual(data["role"], "assistant")
        self.assertEqual(data["content"], "Response")
        self.assertIn("timestamp", data)
    
    def test_message_from_dict(self):
        """Test message deserialization from dict."""
        data = {
            "role": "user",
            "content": "Test",
            "timestamp": datetime.now().isoformat(),
            "metadata": {}
        }
        
        msg = Message.from_dict(data)
        
        self.assertEqual(msg.role, MessageRole.USER)
        self.assertEqual(msg.content, "Test")


class TestConversationState(unittest.TestCase):
    """Test cases for ConversationState."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.conversation = ConversationState(
            session_id="test_session",
            system_prompt="You are a helpful assistant."
        )
    
    def test_initialization_with_system_prompt(self):
        """Test conversation initialization with system prompt."""
        messages = self.conversation.get_messages()
        
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].role, MessageRole.SYSTEM)
        self.assertEqual(messages[0].content, "You are a helpful assistant.")
    
    def test_add_message(self):
        """Test adding messages."""
        self.conversation.add_message(
            MessageRole.USER,
            "What is the weather?"
        )
        self.conversation.add_message(
            MessageRole.ASSISTANT,
            "I don't have access to weather data."
        )
        
        messages = self.conversation.get_messages()
        # Should have system + 2 messages = 3
        self.assertEqual(len(messages), 3)
    
    def test_get_messages_by_role(self):
        """Test filtering messages by role."""
        self.conversation.add_message(MessageRole.USER, "Question 1")
        self.conversation.add_message(MessageRole.ASSISTANT, "Answer 1")
        self.conversation.add_message(MessageRole.USER, "Question 2")
        
        user_messages = self.conversation.get_messages(role=MessageRole.USER)
        
        self.assertEqual(len(user_messages), 2)
        for msg in user_messages:
            self.assertEqual(msg.role, MessageRole.USER)
    
    def test_get_context_window(self):
        """Test getting context window."""
        for i in range(15):
            self.conversation.add_message(MessageRole.USER, f"Message {i}")
        
        context = self.conversation.get_context_window(window_size=5)
        
        self.assertEqual(len(context), 5)
    
    def test_message_limit(self):
        """Test that message history is limited."""
        conversation = ConversationState(
            session_id="test",
            max_history=10
        )
        
        # Add more messages than the limit
        for i in range(20):
            conversation.add_message(MessageRole.USER, f"Message {i}")
        
        # Should be capped at max_history
        self.assertLessEqual(len(conversation.get_messages()), 10)
    
    def test_clear_history(self):
        """Test clearing conversation history."""
        self.conversation.add_message(MessageRole.USER, "Test")
        self.conversation.add_message(MessageRole.ASSISTANT, "Response")
        
        self.conversation.clear_history(keep_system=True)
        
        messages = self.conversation.get_messages()
        # Should only have system message
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].role, MessageRole.SYSTEM)
    
    def test_get_message_count(self):
        """Test message counting by role."""
        self.conversation.add_message(MessageRole.USER, "Q1")
        self.conversation.add_message(MessageRole.ASSISTANT, "A1")
        self.conversation.add_message(MessageRole.USER, "Q2")
        
        counts = self.conversation.get_message_count()
        
        self.assertEqual(counts["system"], 1)
        self.assertEqual(counts["user"], 2)
        self.assertEqual(counts["assistant"], 1)
    
    def test_serialization(self):
        """Test conversation state serialization."""
        self.conversation.add_message(MessageRole.USER, "Test message")
        
        # Test to_dict
        data = self.conversation.to_dict()
        self.assertEqual(data["session_id"], "test_session")
        self.assertIn("messages", data)
        
        # Test to_json
        json_str = self.conversation.to_json()
        self.assertIsInstance(json_str, str)
        
        # Test from_json
        restored = ConversationState.from_json(json_str)
        self.assertEqual(restored.session_id, self.conversation.session_id)
        self.assertEqual(len(restored.get_messages()), len(self.conversation.get_messages()))
    
    def test_get_summary(self):
        """Test getting conversation summary."""
        self.conversation.add_message(MessageRole.USER, "Q1")
        self.conversation.add_message(MessageRole.ASSISTANT, "A1")
        
        summary = self.conversation.get_summary()
        
        self.assertEqual(summary["session_id"], "test_session")
        self.assertEqual(summary["total_messages"], 3)  # system + 2
        self.assertIn("created_at", summary)


class TestCacheManager(unittest.TestCase):
    """Test cases for CacheManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cache = CacheManager(max_size=5, default_ttl=60)
    
    def test_set_and_get(self):
        """Test basic cache set and get."""
        self.cache.set("key1", "value1")
        
        result = self.cache.get("key1")
        
        self.assertEqual(result, "value1")
    
    def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        result = self.cache.get("nonexistent")
        
        self.assertIsNone(result)
    
    def test_ttl_expiration(self):
        """Test that entries expire based on TTL."""
        # Set with 0 second TTL (immediate expiration)
        self.cache.set("key1", "value1", ttl=0)
        
        # Should be expired
        result = self.cache.get("key1")
        
        self.assertIsNone(result)
    
    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        # Fill cache to max size
        for i in range(5):
            self.cache.set(f"key{i}", f"value{i}")
        
        # Access key0 to make it recently used
        self.cache.get("key0")
        
        # Add new item, should evict least recently used (key1)
        self.cache.set("key5", "value5")
        
        # key1 should be evicted
        self.assertIsNone(self.cache.get("key1"))
        # key0 should still exist
        self.assertIsNotNone(self.cache.get("key0"))
    
    def test_cache_tool_result(self):
        """Test caching tool results."""
        tool_name = "search"
        args = {"query": "test"}
        result = {"results": ["item1", "item2"]}
        
        key = self.cache.cache_tool_result(tool_name, args, result)
        
        cached_result = self.cache.get_tool_result(tool_name, args)
        
        self.assertEqual(cached_result, result)
    
    def test_delete(self):
        """Test cache entry deletion."""
        self.cache.set("key1", "value1")
        
        self.assertTrue(self.cache.delete("key1"))
        self.assertIsNone(self.cache.get("key1"))
    
    def test_clear(self):
        """Test clearing all cache entries."""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        
        self.cache.clear()
        
        stats = self.cache.get_stats()
        self.assertEqual(stats["size"], 0)
    
    def test_get_stats(self):
        """Test cache statistics."""
        self.cache.set("key1", "value1")
        self.cache.get("key1")  # Hit
        self.cache.get("key2")  # Miss
        
        stats = self.cache.get_stats()
        
        self.assertEqual(stats["size"], 1)
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertAlmostEqual(stats["hit_rate"], 0.5)
    
    def test_get_entry_info(self):
        """Test getting cache entry information."""
        self.cache.set("key1", "value1", ttl=120)
        
        info = self.cache.get_entry_info("key1")
        
        self.assertIsNotNone(info)
        self.assertEqual(info["key"], "key1")
        self.assertEqual(info["ttl"], 120)
        self.assertFalse(info["is_expired"])


class TestStateManager(unittest.TestCase):
    """Test cases for StateManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use temporary directory for persistence tests
        self.temp_dir = tempfile.mkdtemp()
        self.state_manager = StateManager(
            cache_enabled=True,
            persistence_dir=self.temp_dir
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_conversation(self):
        """Test creating a new conversation."""
        conversation = self.state_manager.create_conversation(
            session_id="test_session",
            system_prompt="Test prompt"
        )
        
        self.assertIsNotNone(conversation)
        self.assertEqual(conversation.session_id, "test_session")
    
    def test_get_conversation(self):
        """Test retrieving a conversation."""
        self.state_manager.create_conversation("test_session")
        
        conversation = self.state_manager.get_conversation("test_session")
        
        self.assertIsNotNone(conversation)
        self.assertEqual(conversation.session_id, "test_session")
    
    def test_delete_conversation(self):
        """Test deleting a conversation."""
        self.state_manager.create_conversation("test_session")
        
        self.assertTrue(self.state_manager.delete_conversation("test_session"))
        self.assertIsNone(self.state_manager.get_conversation("test_session"))
    
    def test_add_message(self):
        """Test adding a message to a conversation."""
        self.state_manager.create_conversation("test_session")
        
        result = self.state_manager.add_message(
            "test_session",
            MessageRole.USER,
            "Test message"
        )
        
        self.assertTrue(result)
    
    def test_get_conversation_context(self):
        """Test getting conversation context."""
        self.state_manager.create_conversation("test_session")
        self.state_manager.add_message("test_session", MessageRole.USER, "Message 1")
        self.state_manager.add_message("test_session", MessageRole.ASSISTANT, "Response 1")
        
        context = self.state_manager.get_conversation_context("test_session", window_size=5)
        
        self.assertIsNotNone(context)
        self.assertIsInstance(context, list)
    
    def test_save_and_load_conversation(self):
        """Test persisting and loading conversations."""
        # Create and save a conversation
        self.state_manager.create_conversation("test_session")
        self.state_manager.add_message("test_session", MessageRole.USER, "Test")
        
        self.assertTrue(self.state_manager.save_conversation("test_session"))
        
        # Delete from memory
        self.state_manager.delete_conversation("test_session")
        
        # Load from disk
        loaded = self.state_manager.load_conversation("test_session")
        
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.session_id, "test_session")
        # Should have at least the user message
        self.assertGreater(len(loaded.get_messages()), 0)
    
    def test_list_conversations(self):
        """Test listing all conversations."""
        self.state_manager.create_conversation("session1")
        self.state_manager.create_conversation("session2")
        
        conversations = self.state_manager.list_conversations()
        
        self.assertEqual(len(conversations), 2)
        self.assertIn("session1", conversations)
        self.assertIn("session2", conversations)
    
    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        stats = self.state_manager.get_cache_stats()
        
        self.assertIsNotNone(stats)
        self.assertIn("size", stats)
        self.assertIn("hits", stats)
        self.assertIn("misses", stats)
    
    def test_clear_cache(self):
        """Test clearing cache."""
        result = self.state_manager.clear_cache()
        
        self.assertTrue(result)
    
    def test_get_system_stats(self):
        """Test getting system statistics."""
        self.state_manager.create_conversation("session1")
        
        stats = self.state_manager.get_system_stats()
        
        self.assertEqual(stats["active_conversations"], 1)
        self.assertTrue(stats["cache_enabled"])
        self.assertTrue(stats["persistence_enabled"])
        self.assertIn("conversations", stats)


if __name__ == '__main__':
    unittest.main()
