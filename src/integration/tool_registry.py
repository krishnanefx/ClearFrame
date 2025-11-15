"""Tool Registry for managing and organizing custom tools."""

from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolMetadata:
    """Metadata for a registered tool."""
    name: str
    description: str
    function: Callable
    category: str
    requires_auth: bool = False
    rate_limit: Optional[int] = None
    timeout: Optional[int] = 30


class ToolRegistry:
    """
    Central registry for managing all custom tools.
    Provides registration, discovery, and execution management.
    """
    
    def __init__(self):
        self._tools: Dict[str, ToolMetadata] = {}
        self._categories: Dict[str, List[str]] = {}
        logger.info("ToolRegistry initialized")
    
    def register_tool(
        self,
        name: str,
        function: Callable,
        description: str,
        category: str = "general",
        requires_auth: bool = False,
        rate_limit: Optional[int] = None,
        timeout: Optional[int] = 30
    ) -> None:
        """
        Register a new tool in the registry.
        
        Args:
            name: Unique identifier for the tool
            function: The callable function implementing the tool
            description: Human-readable description of what the tool does
            category: Category for organizing tools (e.g., 'search', 'summarization')
            requires_auth: Whether the tool requires authentication
            rate_limit: Maximum calls per minute (None for unlimited)
            timeout: Maximum execution time in seconds
        """
        if name in self._tools:
            logger.warning(f"Tool '{name}' already registered. Overwriting.")
        
        metadata = ToolMetadata(
            name=name,
            description=description,
            function=function,
            category=category,
            requires_auth=requires_auth,
            rate_limit=rate_limit,
            timeout=timeout
        )
        
        self._tools[name] = metadata
        
        # Add to category index
        if category not in self._categories:
            self._categories[category] = []
        if name not in self._categories[category]:
            self._categories[category].append(name)
        
        logger.info(f"Registered tool: {name} in category: {category}")
    
    def get_tool(self, name: str) -> Optional[ToolMetadata]:
        """Retrieve tool metadata by name."""
        return self._tools.get(name)
    
    def get_tool_function(self, name: str) -> Optional[Callable]:
        """Get the function for a specific tool."""
        tool = self._tools.get(name)
        return tool.function if tool else None
    
    def list_tools(self, category: Optional[str] = None) -> List[str]:
        """
        List all registered tools, optionally filtered by category.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of tool names
        """
        if category:
            return self._categories.get(category, [])
        return list(self._tools.keys())
    
    def list_categories(self) -> List[str]:
        """List all available tool categories."""
        return list(self._categories.keys())
    
    def get_tools_for_langchain(self) -> List[Dict[str, Any]]:
        """
        Get tools formatted for LangChain integration.
        
        Returns:
            List of tool dictionaries compatible with LangChain
        """
        langchain_tools = []
        for name, metadata in self._tools.items():
            tool_dict = {
                "name": name,
                "description": metadata.description,
                "func": metadata.function,
            }
            langchain_tools.append(tool_dict)
        return langchain_tools
    
    def validate_tool(self, name: str) -> bool:
        """Check if a tool is registered and valid."""
        return name in self._tools
    
    def unregister_tool(self, name: str) -> bool:
        """
        Remove a tool from the registry.
        
        Args:
            name: Name of the tool to unregister
            
        Returns:
            True if tool was removed, False if not found
        """
        if name not in self._tools:
            logger.warning(f"Tool '{name}' not found for unregistration")
            return False
        
        tool = self._tools[name]
        category = tool.category
        
        # Remove from main registry
        del self._tools[name]
        
        # Remove from category index
        if category in self._categories:
            self._categories[category].remove(name)
            if not self._categories[category]:
                del self._categories[category]
        
        logger.info(f"Unregistered tool: {name}")
        return True
    
    def get_tool_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """Get full metadata for a tool as a dictionary."""
        tool = self._tools.get(name)
        if not tool:
            return None
        
        return {
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "requires_auth": tool.requires_auth,
            "rate_limit": tool.rate_limit,
            "timeout": tool.timeout
        }
