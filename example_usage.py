"""Example usage of the integration layer and state management."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from integration import ToolRegistry, EventBus, AgentCoordinator
from state import StateManager, MessageRole
from config import get_config
from utils import setup_logging, generate_session_id


def demo_tool_1(query: str) -> dict:
    """Mock search tool."""
    return {
        "query": query,
        "results": [
            {"title": "AI News Article 1", "url": "http://example.com/1"},
            {"title": "AI News Article 2", "url": "http://example.com/2"},
        ]
    }


def demo_tool_2(text: str, max_length: int = 100) -> str:
    """Mock summarization tool."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def main():
    """Run demonstration of the system."""
    # Setup logging
    setup_logging(level="INFO")
    print("=" * 60)
    print("News Agent System - Demo")
    print("=" * 60)
    
    # Initialize configuration
    config = get_config()
    print("\n1. Configuration loaded")
    print(f"   - Agent model: {config.get('agent.model')}")
    print(f"   - Cache enabled: {config.get('cache.enabled')}")
    
    # Initialize components
    print("\n2. Initializing components...")
    tool_registry = ToolRegistry()
    event_bus = EventBus()
    state_manager = StateManager(
        cache_enabled=True,
        persistence_dir="./demo_data/state"
    )
    coordinator = AgentCoordinator(
        tool_registry=tool_registry,
        event_bus=event_bus,
        state_manager=state_manager
    )
    print("   ✓ Components initialized")
    
    # Register tools
    print("\n3. Registering tools...")
    tool_registry.register_tool(
        name="search_news",
        function=demo_tool_1,
        description="Search for news articles",
        category="search"
    )
    tool_registry.register_tool(
        name="summarize_text",
        function=demo_tool_2,
        description="Summarize text content",
        category="text_processing"
    )
    print(f"   ✓ Registered {len(tool_registry.list_tools())} tools")
    print(f"   - Tools: {', '.join(tool_registry.list_tools())}")
    
    # Set up event listeners
    print("\n4. Setting up event listeners...")
    events_log = []
    
    def log_event(event):
        events_log.append(event)
        print(f"   [EVENT] {event.event_type.value}: {event.data}")
    
    event_bus.subscribe(EventType.AGENT_STARTED, log_event)
    event_bus.subscribe(EventType.TOOL_EXECUTED, log_event)
    event_bus.subscribe(EventType.AGENT_COMPLETED, log_event)
    print("   ✓ Event listeners configured")
    
    # Create session
    print("\n5. Creating agent session...")
    session_id = generate_session_id()
    session = coordinator.create_session(session_id)
    print(f"   ✓ Session created: {session_id}")
    
    # Create conversation
    print("\n6. Creating conversation state...")
    conversation = state_manager.create_conversation(
        session_id,
        system_prompt="You are a helpful news assistant."
    )
    print(f"   ✓ Conversation created")
    
    # Simulate user interaction
    print("\n7. Simulating user interaction...")
    user_query = "Find recent news about artificial intelligence"
    state_manager.add_message(session_id, MessageRole.USER, user_query)
    print(f"   User: {user_query}")
    
    # Execute search tool
    print("\n8. Executing search tool...")
    search_result = coordinator.execute_tool(
        "search_news",
        session_id,
        query="artificial intelligence"
    )
    print(f"   ✓ Tool executed in {search_result['execution_time']:.3f}s")
    print(f"   ✓ Found {len(search_result['result']['results'])} results")
    
    # Cache the result
    print("\n9. Caching tool result...")
    cache_key = state_manager.cache_manager.cache_tool_result(
        "search_news",
        {"query": "artificial intelligence"},
        search_result["result"]
    )
    print(f"   ✓ Result cached with key: {cache_key[:16]}...")
    
    # Add assistant response
    assistant_response = f"I found {len(search_result['result']['results'])} articles about AI."
    state_manager.add_message(session_id, MessageRole.ASSISTANT, assistant_response)
    print(f"   Assistant: {assistant_response}")
    
    # Get conversation context
    print("\n10. Retrieving conversation context...")
    context = state_manager.get_conversation_context(session_id, window_size=5)
    print(f"    ✓ Retrieved {len(context)} messages")
    for msg in context:
        print(f"    - {msg['role']}: {msg['content'][:50]}...")
    
    # Save conversation
    print("\n11. Saving conversation to disk...")
    saved = state_manager.save_conversation(session_id)
    print(f"    ✓ Conversation saved: {saved}")
    
    # End session
    print("\n12. Ending session...")
    summary = coordinator.end_session(session_id)
    print(f"    ✓ Session ended")
    print(f"    - Duration: {summary['duration']:.2f}s")
    print(f"    - Total tool calls: {summary['total_tool_calls']}")
    print(f"    - Successful calls: {summary['successful_tool_calls']}")
    
    # Display statistics
    print("\n13. System Statistics:")
    state_stats = state_manager.get_system_stats()
    cache_stats = state_manager.get_cache_stats()
    
    print(f"    State:")
    print(f"    - Active conversations: {state_stats['active_conversations']}")
    print(f"    - Cache enabled: {state_stats['cache_enabled']}")
    
    print(f"    Cache:")
    print(f"    - Size: {cache_stats['size']}/{cache_stats['max_size']}")
    print(f"    - Hit rate: {cache_stats['hit_rate']:.2%}")
    print(f"    - Hits: {cache_stats['hits']}, Misses: {cache_stats['misses']}")
    
    print(f"\n    Events:")
    print(f"    - Total events: {len(events_log)}")
    for event in events_log:
        print(f"    - {event.event_type.value}")
    
    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    from integration.event_bus import EventType
    main()
