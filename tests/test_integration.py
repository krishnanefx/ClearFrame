"""Test suite for integration layer components."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from integration.tool_registry import ToolRegistry, ToolMetadata
from integration.event_bus import EventBus, EventType, Event
from integration.agent_coordinator import AgentCoordinator


class TestToolRegistry(unittest.TestCase):
    """Test cases for ToolRegistry."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = ToolRegistry()
    
    def test_register_tool(self):
        """Test tool registration."""
        def sample_tool(x: int) -> int:
            return x * 2
        
        self.registry.register_tool(
            name="multiply",
            function=sample_tool,
            description="Multiplies by 2",
            category="math"
        )
        
        self.assertTrue(self.registry.validate_tool("multiply"))
        self.assertEqual(len(self.registry.list_tools()), 1)
    
    def test_get_tool_function(self):
        """Test retrieving tool function."""
        def sample_tool(x: int) -> int:
            return x * 2
        
        self.registry.register_tool(
            name="multiply",
            function=sample_tool,
            description="Multiplies by 2"
        )
        
        func = self.registry.get_tool_function("multiply")
        self.assertIsNotNone(func)
        self.assertEqual(func(5), 10)
    
    def test_list_tools_by_category(self):
        """Test listing tools by category."""
        self.registry.register_tool(
            name="add",
            function=lambda x, y: x + y,
            description="Addition",
            category="math"
        )
        self.registry.register_tool(
            name="search",
            function=lambda q: f"Results for {q}",
            description="Search tool",
            category="search"
        )
        
        math_tools = self.registry.list_tools(category="math")
        self.assertEqual(len(math_tools), 1)
        self.assertIn("add", math_tools)
    
    def test_unregister_tool(self):
        """Test tool unregistration."""
        self.registry.register_tool(
            name="temp_tool",
            function=lambda: None,
            description="Temporary tool"
        )
        
        self.assertTrue(self.registry.validate_tool("temp_tool"))
        self.assertTrue(self.registry.unregister_tool("temp_tool"))
        self.assertFalse(self.registry.validate_tool("temp_tool"))
    
    def test_get_tool_metadata(self):
        """Test retrieving tool metadata."""
        self.registry.register_tool(
            name="test_tool",
            function=lambda: None,
            description="Test description",
            category="test",
            requires_auth=True,
            rate_limit=10
        )
        
        metadata = self.registry.get_tool_metadata("test_tool")
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata["name"], "test_tool")
        self.assertEqual(metadata["category"], "test")
        self.assertTrue(metadata["requires_auth"])
        self.assertEqual(metadata["rate_limit"], 10)


class TestEventBus(unittest.TestCase):
    """Test cases for EventBus."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
    
    def test_publish_and_subscribe(self):
        """Test event publishing and subscription."""
        received_events = []
        
        def handler(event: Event):
            received_events.append(event)
        
        self.event_bus.subscribe(EventType.TOOL_EXECUTED, handler)
        self.event_bus.publish(
            EventType.TOOL_EXECUTED,
            {"tool_name": "test_tool"},
            source="test"
        )
        
        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].event_type, EventType.TOOL_EXECUTED)
        self.assertEqual(received_events[0].data["tool_name"], "test_tool")
    
    def test_multiple_subscribers(self):
        """Test multiple subscribers for same event."""
        counter1 = {"count": 0}
        counter2 = {"count": 0}
        
        def handler1(event):
            counter1["count"] += 1
        
        def handler2(event):
            counter2["count"] += 1
        
        self.event_bus.subscribe(EventType.AGENT_STARTED, handler1)
        self.event_bus.subscribe(EventType.AGENT_STARTED, handler2)
        
        self.event_bus.publish(EventType.AGENT_STARTED, {}, source="test")
        
        self.assertEqual(counter1["count"], 1)
        self.assertEqual(counter2["count"], 1)
    
    def test_unsubscribe(self):
        """Test unsubscribing from events."""
        received_events = []
        
        def handler(event):
            received_events.append(event)
        
        self.event_bus.subscribe(EventType.TOOL_EXECUTED, handler)
        self.event_bus.publish(EventType.TOOL_EXECUTED, {}, source="test")
        
        self.assertEqual(len(received_events), 1)
        
        self.event_bus.unsubscribe(EventType.TOOL_EXECUTED, handler)
        self.event_bus.publish(EventType.TOOL_EXECUTED, {}, source="test")
        
        # Should still be 1, not 2
        self.assertEqual(len(received_events), 1)
    
    def test_event_history(self):
        """Test event history tracking."""
        self.event_bus.publish(EventType.TOOL_EXECUTED, {"test": 1}, source="test")
        self.event_bus.publish(EventType.TOOL_FAILED, {"test": 2}, source="test")
        
        history = self.event_bus.get_history()
        self.assertEqual(len(history), 2)
        
        tool_executed_history = self.event_bus.get_history(EventType.TOOL_EXECUTED)
        self.assertEqual(len(tool_executed_history), 1)
    
    def test_error_handling_in_callback(self):
        """Test that errors in callbacks don't break event bus."""
        def bad_handler(event):
            raise ValueError("Test error")
        
        def good_handler(event):
            pass  # This should still execute
        
        self.event_bus.subscribe(EventType.AGENT_STARTED, bad_handler)
        self.event_bus.subscribe(EventType.AGENT_STARTED, good_handler)
        
        # Should not raise exception
        self.event_bus.publish(EventType.AGENT_STARTED, {}, source="test")


class TestAgentCoordinator(unittest.TestCase):
    """Test cases for AgentCoordinator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tool_registry = ToolRegistry()
        self.event_bus = EventBus()
        self.coordinator = AgentCoordinator(
            tool_registry=self.tool_registry,
            event_bus=self.event_bus
        )
    
    def test_create_session(self):
        """Test session creation."""
        session = self.coordinator.create_session("test_session_1")
        
        self.assertEqual(session["session_id"], "test_session_1")
        self.assertEqual(session["status"], "active")
        self.assertIn("test_session_1", self.coordinator.list_active_sessions())
    
    def test_execute_tool_success(self):
        """Test successful tool execution."""
        # Register a test tool
        def test_tool(value: int) -> int:
            return value * 2
        
        self.tool_registry.register_tool(
            name="test_tool",
            function=test_tool,
            description="Test tool"
        )
        
        # Create session and execute tool
        self.coordinator.create_session("test_session")
        result = self.coordinator.execute_tool(
            "test_tool",
            "test_session",
            value=5
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], 10)
        self.assertIn("execution_time", result)
    
    def test_execute_tool_failure(self):
        """Test tool execution failure handling."""
        # Register a tool that raises an error
        def failing_tool():
            raise ValueError("Test error")
        
        self.tool_registry.register_tool(
            name="failing_tool",
            function=failing_tool,
            description="Failing tool"
        )
        
        self.coordinator.create_session("test_session")
        result = self.coordinator.execute_tool(
            "failing_tool",
            "test_session"
        )
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)
    
    def test_execute_nonexistent_tool(self):
        """Test executing a tool that doesn't exist."""
        self.coordinator.create_session("test_session")
        
        with self.assertRaises(ValueError):
            self.coordinator.execute_tool(
                "nonexistent_tool",
                "test_session"
            )
    
    def test_end_session(self):
        """Test session ending and summary generation."""
        # Register a test tool
        self.tool_registry.register_tool(
            name="test_tool",
            function=lambda x: x,
            description="Test"
        )
        
        # Create session and execute some tools
        self.coordinator.create_session("test_session")
        self.coordinator.execute_tool("test_tool", "test_session", x=1)
        self.coordinator.execute_tool("test_tool", "test_session", x=2)
        
        summary = self.coordinator.end_session("test_session")
        
        self.assertEqual(summary["session_id"], "test_session")
        self.assertEqual(summary["total_tool_calls"], 2)
        self.assertEqual(summary["successful_tool_calls"], 2)
        self.assertNotIn("test_session", self.coordinator.list_active_sessions())
    
    def test_get_session_info(self):
        """Test retrieving session information."""
        self.coordinator.create_session("test_session", config={"key": "value"})
        
        info = self.coordinator.get_session_info("test_session")
        
        self.assertIsNotNone(info)
        self.assertEqual(info["session_id"], "test_session")
        self.assertEqual(info["config"]["key"], "value")
    
    def test_validate_tool_availability(self):
        """Test tool availability validation."""
        self.tool_registry.register_tool(
            name="tool1",
            function=lambda: None,
            description="Tool 1"
        )
        
        availability = self.coordinator.validate_tool_availability(
            ["tool1", "tool2", "tool3"]
        )
        
        self.assertTrue(availability["tool1"])
        self.assertFalse(availability["tool2"])
        self.assertFalse(availability["tool3"])


if __name__ == '__main__':
    unittest.main()
