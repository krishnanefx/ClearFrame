# Quick Start Guide - Person 3 Deliverables

## Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env and add your API keys
```

## Running the Demo

```bash
python example_usage.py
```

This will demonstrate:
- Component initialization
- Tool registration
- Session management
- Tool execution
- Event handling
- Caching
- State persistence
- Statistics collection

## Running Tests

```bash
# Install pytest if not already installed
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test files
pytest tests/test_integration.py -v
pytest tests/test_state.py -v
pytest tests/test_integration_complete.py -v
```

## Integration with Team Code

### For Person 1 (ReAct Agent Developer):

```python
from integration import ToolRegistry, EventBus, AgentCoordinator
from state import StateManager

# Initialize the integration layer
tool_registry = ToolRegistry()
event_bus = EventBus()
state_manager = StateManager()
coordinator = AgentCoordinator(tool_registry, event_bus, state_manager)

# Create a session for your agent
session_id = "agent_session_1"
coordinator.create_session(session_id)

# Execute tools through the coordinator
result = coordinator.execute_tool("your_tool_name", session_id, **tool_args)
```

### For Person 2 (Custom Tools Developer):

```python
from integration import ToolRegistry

# Get the registry instance
tool_registry = ToolRegistry()

# Register your custom tools
def my_news_scraper(url: str) -> dict:
    # Your implementation
    return {"content": "..."}

tool_registry.register_tool(
    name="news_scraper",
    function=my_news_scraper,
    description="Scrape news from URL",
    category="scraping",
    timeout=30
)

# Register summarization tool
def my_summarizer(text: str) -> str:
    # Your implementation
    return "Summary..."

tool_registry.register_tool(
    name="summarizer",
    function=my_summarizer,
    description="Summarize text",
    category="text_processing"
)
```

### For Person 4 (Documentation Developer):

All components are well-documented with:
- Comprehensive docstrings
- Type hints
- Usage examples in `example_usage.py`
- Complete README with architecture diagrams
- Test files showing usage patterns

## Key Files to Review

1. **Integration Layer:**
   - `src/integration/tool_registry.py` - Tool management
   - `src/integration/event_bus.py` - Event system
   - `src/integration/agent_coordinator.py` - Session & execution management

2. **State Management:**
   - `src/state/conversation_state.py` - Message history
   - `src/state/cache_manager.py` - Result caching
   - `src/state/state_manager.py` - Central coordinator

3. **Testing:**
   - `tests/test_integration.py` - Unit tests for integration layer
   - `tests/test_state.py` - Unit tests for state management
   - `tests/test_integration_complete.py` - End-to-end integration tests

4. **Configuration:**
   - `config/config.py` - Configuration management
   - `config/default_config.json` - Default settings

## Project Structure

```
hackathon-news-agent/
├── src/
│   ├── integration/     # Integration layer
│   ├── state/          # State management
│   └── utils.py        # Utility functions
├── config/             # Configuration
├── tests/              # Test suite
├── requirements.txt    # Dependencies
├── example_usage.py    # Demo script
└── README.md          # Full documentation
```

## Next Steps

1. Run the demo: `python example_usage.py`
2. Run tests: `pytest tests/ -v`
3. Review the README.md for detailed documentation
4. Integrate with your team members' code
5. Customize configuration in `config/default_config.json` or via environment variables

## Support

All components include:
- ✅ Comprehensive error handling
- ✅ Logging for debugging
- ✅ Type hints for IDE support
- ✅ Docstrings for documentation
- ✅ Unit and integration tests

Ready to integrate with the team's ReAct agent and custom tools!
