"""Agent Coordinator for managing agent execution and tool integration."""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import asyncio

from .tool_registry import ToolRegistry
from .event_bus import EventBus, EventType

logger = logging.getLogger(__name__)


class AgentCoordinator:
    """
    Coordinates agent execution, tool usage, and state management.
    Acts as the main integration point for the system.
    """
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        event_bus: EventBus,
        state_manager: Any = None
    ):
        """
        Initialize the coordinator.
        
        Args:
            tool_registry: Registry of available tools
            event_bus: Event bus for system communication
            state_manager: Optional state manager instance
        """
        self.tool_registry = tool_registry
        self.event_bus = event_bus
        self.state_manager = state_manager
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Subscribe to relevant events
        self._setup_event_subscriptions()
        
        logger.info("AgentCoordinator initialized")
    
    def _setup_event_subscriptions(self) -> None:
        """Set up event subscriptions for monitoring."""
        self.event_bus.subscribe(EventType.TOOL_EXECUTED, self._on_tool_executed)
        self.event_bus.subscribe(EventType.TOOL_FAILED, self._on_tool_failed)
        self.event_bus.subscribe(EventType.AGENT_ERROR, self._on_agent_error)
    
    def _on_tool_executed(self, event) -> None:
        """Handle tool execution events."""
        logger.info(f"Tool executed: {event.data.get('tool_name')}")
    
    def _on_tool_failed(self, event) -> None:
        """Handle tool failure events."""
        logger.error(f"Tool failed: {event.data.get('tool_name')} - {event.data.get('error')}")
    
    def _on_agent_error(self, event) -> None:
        """Handle agent error events."""
        logger.error(f"Agent error: {event.data.get('error')}")
    
    def create_session(self, session_id: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new agent session.
        
        Args:
            session_id: Unique identifier for the session
            config: Optional session configuration
            
        Returns:
            Session metadata
        """
        if session_id in self._active_sessions:
            logger.warning(f"Session {session_id} already exists")
            return self._active_sessions[session_id]
        
        session = {
            "session_id": session_id,
            "created_at": datetime.now(),
            "config": config or {},
            "tool_calls": [],
            "status": "active"
        }
        
        self._active_sessions[session_id] = session
        self.event_bus.publish(
            EventType.AGENT_STARTED,
            {"session_id": session_id},
            source="AgentCoordinator"
        )
        
        logger.info(f"Created session: {session_id}")
        return session
    
    def execute_tool(
        self,
        tool_name: str,
        session_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a tool within a session context.
        
        Args:
            tool_name: Name of the tool to execute
            session_id: Session identifier
            **kwargs: Tool-specific arguments
            
        Returns:
            Tool execution result
        """
        if session_id not in self._active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        tool_func = self.tool_registry.get_tool_function(tool_name)
        if not tool_func:
            error_msg = f"Tool {tool_name} not found"
            self.event_bus.publish(
                EventType.TOOL_FAILED,
                {"tool_name": tool_name, "error": error_msg, "session_id": session_id},
                source="AgentCoordinator"
            )
            raise ValueError(error_msg)
        
        start_time = datetime.now()
        
        try:
            # Execute tool
            result = tool_func(**kwargs)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Record tool call
            tool_call_record = {
                "tool_name": tool_name,
                "timestamp": start_time,
                "execution_time": execution_time,
                "success": True,
                "args": kwargs
            }
            self._active_sessions[session_id]["tool_calls"].append(tool_call_record)
            
            # Publish success event
            self.event_bus.publish(
                EventType.TOOL_EXECUTED,
                {
                    "tool_name": tool_name,
                    "session_id": session_id,
                    "execution_time": execution_time
                },
                source="AgentCoordinator"
            )
            
            return {
                "success": True,
                "result": result,
                "execution_time": execution_time
            }
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Tool execution failed: {tool_name}", exc_info=True)
            
            # Record failed tool call
            tool_call_record = {
                "tool_name": tool_name,
                "timestamp": start_time,
                "execution_time": execution_time,
                "success": False,
                "error": str(e),
                "args": kwargs
            }
            self._active_sessions[session_id]["tool_calls"].append(tool_call_record)
            
            # Publish failure event
            self.event_bus.publish(
                EventType.TOOL_FAILED,
                {
                    "tool_name": tool_name,
                    "session_id": session_id,
                    "error": str(e),
                    "execution_time": execution_time
                },
                source="AgentCoordinator"
            )
            
            return {
                "success": False,
                "error": str(e),
                "execution_time": execution_time
            }
    
    def end_session(self, session_id: str) -> Dict[str, Any]:
        """
        End an agent session and return summary.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session summary
        """
        if session_id not in self._active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self._active_sessions[session_id]
        session["status"] = "completed"
        session["ended_at"] = datetime.now()
        
        # Calculate statistics
        total_tools = len(session["tool_calls"])
        successful_tools = sum(1 for call in session["tool_calls"] if call["success"])
        total_time = sum(call["execution_time"] for call in session["tool_calls"])
        
        summary = {
            "session_id": session_id,
            "duration": (session["ended_at"] - session["created_at"]).total_seconds(),
            "total_tool_calls": total_tools,
            "successful_tool_calls": successful_tools,
            "failed_tool_calls": total_tools - successful_tools,
            "total_execution_time": total_time
        }
        
        self.event_bus.publish(
            EventType.AGENT_COMPLETED,
            summary,
            source="AgentCoordinator"
        )
        
        # Remove from active sessions
        del self._active_sessions[session_id]
        
        logger.info(f"Ended session: {session_id}")
        return summary
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about an active session."""
        return self._active_sessions.get(session_id)
    
    def list_active_sessions(self) -> List[str]:
        """List all active session IDs."""
        return list(self._active_sessions.keys())
    
    def get_available_tools(self, category: Optional[str] = None) -> List[str]:
        """Get list of available tools, optionally filtered by category."""
        return self.tool_registry.list_tools(category=category)
    
    def validate_tool_availability(self, tool_names: List[str]) -> Dict[str, bool]:
        """
        Check if multiple tools are available.
        
        Args:
            tool_names: List of tool names to validate
            
        Returns:
            Dictionary mapping tool names to availability status
        """
        return {
            name: self.tool_registry.validate_tool(name)
            for name in tool_names
        }
