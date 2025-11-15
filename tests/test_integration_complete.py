"""Integration tests for the complete system."""

import unittest
from unittest.mock import Mock, patch
import sys
from pathlib import Path
import tempfile
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from integration.tool_registry import ToolRegistry
from integration.event_bus import EventBus, EventType
from integration.agent_coordinator import AgentCoordinator
from state.state_manager import StateManager
from state.conversation_state import MessageRole


class TestSystemIntegration(unittest.TestCase):
    """Integration tests for the complete system."""
    
    def setUp(self):
        """Set up complete system for testing."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Initialize all components
        self.tool_registry = ToolRegistry()
        self.event_bus = EventBus()
        self.state_manager = StateManager(
            cache_enabled=True,
            persistence_dir=self.temp_dir
        )
        self.coordinator = AgentCoordinator(
            tool_registry=self.tool_registry,
            event_bus=self.event_bus,
            state_manager=self.state_manager
        )
        
        # Register some test tools
        self._register_test_tools()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _register_test_tools(self):
        """Register test tools."""
        def search_tool(query: str) -> dict:
            """Mock search tool."""
            return {
                "query": query,
                "results": ["result1", "result2", "result3"]
            }
        
        def summarize_tool(text: str) -> str:
            """Mock summarization tool."""
            return f"Summary of: {text[:50]}..."
        
        self.tool_registry.register_tool(
            name="search",
            function=search_tool,
            description="Search for information",
            category="search"
        )
        
        self.tool_registry.register_tool(
            name="summarize",
            function=summarize_tool,
            description="Summarize text",
            category="text_processing"
        )
    
    def test_complete_agent_workflow(self):
        """Test complete agent workflow from session creation to completion."""
        # Create session
        session = self.coordinator.create_session(
            "integration_test_session",
            config={"max_iterations": 5}
        )
        
        self.assertEqual(session["status"], "active")
        
        # Create conversation state
        conversation = self.state_manager.create_conversation(
            "integration_test_session",
            system_prompt="You are a helpful assistant."
        )
        
        # Add user message
        self.state_manager.add_message(
            "integration_test_session",
            MessageRole.USER,
            "Search for news about AI"
        )
        
        # Execute tool
        result = self.coordinator.execute_tool(
            "search",
            "integration_test_session",
            query="AI news"
        )
        
        self.assertTrue(result["success"])
        self.assertIn("results", result["result"])
        
        # Add assistant response
        self.state_manager.add_message(
            "integration_test_session",
            MessageRole.ASSISTANT,
            f"Found results: {result['result']['results']}"
        )
        
        # Get conversation context
        context = self.state_manager.get_conversation_context(
            "integration_test_session"
        )
        
        self.assertIsNotNone(context)
        self.assertGreater(len(context), 0)
        
        # End session
        summary = self.coordinator.end_session("integration_test_session")
        
        self.assertEqual(summary["total_tool_calls"], 1)
        self.assertEqual(summary["successful_tool_calls"], 1)
    
    def test_event_flow(self):
        """Test that events flow correctly through the system."""
        events_received = []
        
        def event_handler(event):
            events_received.append(event)
        
        # Subscribe to events
        self.event_bus.subscribe(EventType.AGENT_STARTED, event_handler)
        self.event_bus.subscribe(EventType.TOOL_EXECUTED, event_handler)
        self.event_bus.subscribe(EventType.AGENT_COMPLETED, event_handler)
        
        # Execute workflow
        self.coordinator.create_session("event_test_session")
        self.coordinator.execute_tool("search", "event_test_session", query="test")
        self.coordinator.end_session("event_test_session")
        
        # Verify events
        self.assertGreaterEqual(len(events_received), 3)
        
        event_types = [e.event_type for e in events_received]
        self.assertIn(EventType.AGENT_STARTED, event_types)
        self.assertIn(EventType.TOOL_EXECUTED, event_types)
        self.assertIn(EventType.AGENT_COMPLETED, event_types)
    
    def test_state_persistence_with_tool_execution(self):
        """Test that state persists correctly with tool executions."""
        session_id = "persistence_test_session"
        
        # Create session and conversation
        self.coordinator.create_session(session_id)
        self.state_manager.create_conversation(session_id)
        
        # Add messages and execute tools
        self.state_manager.add_message(session_id, MessageRole.USER, "Summarize this text")
        self.coordinator.execute_tool("summarize", session_id, text="Long text to summarize")
        self.state_manager.add_message(session_id, MessageRole.ASSISTANT, "Here is the summary")
        
        # Save conversation
        self.assertTrue(self.state_manager.save_conversation(session_id))
        
        # Delete from memory
        self.state_manager.delete_conversation(session_id)
        
        # Load back
        loaded_conversation = self.state_manager.load_conversation(session_id)
        
        self.assertIsNotNone(loaded_conversation)
        messages = loaded_conversation.get_messages()
        self.assertGreater(len(messages), 0)
    
    def test_multiple_concurrent_sessions(self):
        """Test handling multiple concurrent sessions."""
        # Create multiple sessions
        session_ids = ["session1", "session2", "session3"]
        
        for session_id in session_ids:
            self.coordinator.create_session(session_id)
            self.state_manager.create_conversation(session_id)
            self.state_manager.add_message(
                session_id,
                MessageRole.USER,
                f"Message for {session_id}"
            )
        
        # Verify all sessions are active
        active_sessions = self.coordinator.list_active_sessions()
        self.assertEqual(len(active_sessions), 3)
        
        # Execute tools in different sessions
        for session_id in session_ids:
            result = self.coordinator.execute_tool(
                "search",
                session_id,
                query=f"query for {session_id}"
            )
            self.assertTrue(result["success"])
        
        # Verify each session has correct state
        for session_id in session_ids:
            info = self.coordinator.get_session_info(session_id)
            self.assertEqual(len(info["tool_calls"]), 1)
    
    def test_tool_caching(self):
        """Test that tool results can be cached."""
        session_id = "cache_test_session"
        self.coordinator.create_session(session_id)
        
        # Execute tool and cache result
        tool_name = "search"
        args = {"query": "test query"}
        
        result = self.coordinator.execute_tool(tool_name, session_id, **args)
        
        # Manually cache the result
        self.state_manager.cache_manager.cache_tool_result(
            tool_name,
            args,
            result["result"]
        )
        
        # Retrieve from cache
        cached_result = self.state_manager.cache_manager.get_tool_result(
            tool_name,
            args
        )
        
        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result, result["result"])
    
    def test_error_recovery(self):
        """Test system behavior during error conditions."""
        session_id = "error_test_session"
        self.coordinator.create_session(session_id)
        
        # Try to execute non-existent tool
        with self.assertRaises(ValueError):
            self.coordinator.execute_tool("nonexistent_tool", session_id)
        
        # Session should still be active
        self.assertIn(session_id, self.coordinator.list_active_sessions())
        
        # Should still be able to execute valid tools
        result = self.coordinator.execute_tool("search", session_id, query="test")
        self.assertTrue(result["success"])
    
    def test_system_statistics(self):
        """Test that system statistics are collected correctly."""
        # Create some activity
        self.coordinator.create_session("stats_session")
        self.state_manager.create_conversation("stats_session")
        self.coordinator.execute_tool("search", "stats_session", query="test")
        
        # Get statistics
        state_stats = self.state_manager.get_system_stats()
        cache_stats = self.state_manager.get_cache_stats()
        
        # Verify stats contain expected information
        self.assertIn("active_conversations", state_stats)
        self.assertIn("cache_enabled", state_stats)
        self.assertIn("hits", cache_stats)
        self.assertIn("misses", cache_stats)


if __name__ == '__main__':
    unittest.main()
