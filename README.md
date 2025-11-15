# News Agent Hackathon Project

## Integration Layer, State Management, Testing Framework, and AWS Data Pipeline

This repository contains the complete implementation for the News Agent hackathon project, including integration components, state management, and a production-ready AWS data pipeline for news ingestion.

## Project Structure

```
hackathon-news-agent/
├── src/
│   ├── integration/          # Integration layer components
│   │   ├── __init__.py
│   │   ├── tool_registry.py  # Central registry for managing tools
│   │   ├── event_bus.py      # Event system for component communication
│   │   └── agent_coordinator.py  # Coordinates agent execution
│   ├── state/                # State management system
│   │   ├── __init__.py
│   │   ├── conversation_state.py  # Conversation history management
│   │   ├── cache_manager.py      # Caching for tool results
│   │   └── state_manager.py      # Main state coordinator
│   ├── pipeline/             # AWS data pipeline (NEW)
│   │   ├── __init__.py
│   │   ├── source_config_loader.py  # Source configuration management
│   │   ├── orchestrator.py          # Step Functions orchestrator
│   │   ├── lambda_handlers.py       # Lambda function handlers
│   │   ├── sqs_retry_queue.py      # SQS retry logic + circuit breaker
│   │   ├── ecs_config.py           # ECS/Fargate task configurations
│   │   └── docker/                 # Docker images for ECS tasks
│   │       ├── Dockerfile.embed-cluster
│   │       ├── Dockerfile.bias-score
│   │       ├── embed_cluster_worker.py
│   │       ├── bias_score_worker.py
│   │       └── requirements-ecs.txt
│   └── utils.py              # Utility functions
├── config/                   # Configuration management
│   ├── __init__.py
│   ├── config.py            # Configuration loader (updated for AWS)
│   ├── default_config.json  # Default configuration
│   ├── sources.yaml         # News source configuration (NEW)
│   └── sources.json         # Alternative JSON format (NEW)
├── tests/                    # Comprehensive test suite
│   ├── __init__.py
│   ├── test_integration.py  # Integration layer tests
│   ├── test_state.py        # State management tests
│   ├── test_integration_complete.py  # End-to-end tests
│   └── test_pipeline.py     # Pipeline tests (NEW)
├── requirements.txt          # Python dependencies (updated)
├── example_usage.py         # Original integration examples
├── example_pipeline_usage.py # Pipeline usage examples (NEW)
├── README.md                # This file
├── PIPELINE_README.md       # Detailed pipeline documentation (NEW)
└── DEPLOYMENT_GUIDE.md      # AWS deployment guide (NEW)
```

## New Features: AWS Data Pipeline

### Overview

The AWS data pipeline provides a scalable, production-ready infrastructure for news ingestion and processing:

- **Source Management**: YAML/JSON configuration for RSS feeds, URLs, APIs, and diaspora blogs
- **AWS Step Functions**: Orchestrates multi-stage pipeline execution
- **Lambda Functions**: Lightweight processing for fetch, normalize, and store stages
- **ECS Fargate + GPU**: Heavy processing for embedding generation and bias scoring
- **SQS Retry Logic**: Exponential backoff with circuit breaker pattern
- **Valyu Integration**: AI-powered bias analysis and scoring

### Quick Start - Pipeline

1. **Configure news sources**:
   ```bash
   # Edit config/sources.yaml with your sources
   nano config/sources.yaml
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up AWS infrastructure** (see DEPLOYMENT_GUIDE.md):
   ```bash
   # Deploy CloudFormation stack
   # Create Lambda functions
   # Register ECS task definitions
   # Create Step Functions state machine
   ```

4. **Run example**:
   ```bash
   python example_pipeline_usage.py
   ```

### Pipeline Stages

1. **FetchArticles** (Lambda): Scrape RSS, URLs, APIs with retry logic
2. **NormalizeContent** (Lambda): Language detection, HTML cleaning
3. **EmbedAndCluster** (ECS Fargate + GPU): Generate embeddings, cluster articles
4. **BiasScoreAndExplain** (ECS Fargate + GPU + Valyu): Score bias with AI
5. **StoreResults** (Lambda): Save to DynamoDB and S3

**For complete pipeline documentation, see [PIPELINE_README.md](./PIPELINE_README.md)**

**For deployment instructions, see [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)**

## Components Overview

### 1. Integration Layer (`src/integration/`)

#### ToolRegistry (`tool_registry.py`)
- Central registry for managing all custom tools
- Features:
  - Tool registration with metadata (name, description, category)
  - Tool discovery and retrieval
  - Category-based organization
  - LangChain integration support
  - Rate limiting and timeout configuration

#### EventBus (`event_bus.py`)
- Publish-subscribe event system for loose coupling
- Features:
  - Event publication and subscription
  - Event history tracking
  - Multiple subscribers per event type
  - Error isolation in event handlers
  - Support for: TOOL_EXECUTED, TOOL_FAILED, AGENT_STARTED, AGENT_COMPLETED, etc.

#### AgentCoordinator (`agent_coordinator.py`)
- Main coordinator for agent execution and tool integration
- Features:
  - Session management (create, track, end)
  - Tool execution within session context
  - Automatic event publishing
  - Execution metrics and timing
  - Session summaries and statistics

### 2. State Management (`src/state/`)

#### ConversationState (`conversation_state.py`)
- Manages conversation history and context
- Features:
  - Message tracking with roles (System, User, Assistant, Tool)
  - Context window management
  - Message history limits
  - Serialization (to/from JSON)
  - Message filtering by role

#### CacheManager (`cache_manager.py`)
- Caching system for tool results and data
- Features:
  - TTL-based expiration
  - LRU eviction when cache is full
  - Tool result caching
  - Cache statistics (hits, misses, hit rate)
  - Automatic cleanup of expired entries

#### StateManager (`state_manager.py`)
- Central coordinator for all state management
- Features:
  - Conversation state management
  - Cache integration
  - Persistence to disk (JSON)
  - Load/save conversations
  - System-wide statistics

### 3. Configuration (`config/`)

#### Config (`config.py`)
- Configuration management system
- Features:
  - Default configuration
  - Load from JSON files
  - Environment variable override
  - Dot-notation access (e.g., `config.get('agent.model')`)
  - Configuration validation
  - Save configuration to file

### 4. Testing Framework (`tests/`)

#### Comprehensive Test Coverage
- **test_integration.py**: Tests for integration layer
  - ToolRegistry: registration, retrieval, categories, metadata
  - EventBus: publish/subscribe, history, error handling
  - AgentCoordinator: sessions, tool execution, summaries

- **test_state.py**: Tests for state management
  - Message: creation, serialization
  - ConversationState: history, context windows, limits
  - CacheManager: caching, expiration, LRU eviction
  - StateManager: persistence, conversation management

- **test_integration_complete.py**: End-to-end integration tests
  - Complete agent workflows
  - Event flow verification
  - State persistence with tool execution
  - Multiple concurrent sessions
  - Error recovery
  - System statistics

## Usage Examples

### 1. Basic Setup

```python
from integration import ToolRegistry, EventBus, AgentCoordinator
from state import StateManager
from config import get_config

# Initialize components
config = get_config()
tool_registry = ToolRegistry()
event_bus = EventBus()
state_manager = StateManager(cache_enabled=True)
coordinator = AgentCoordinator(tool_registry, event_bus, state_manager)
```

### 2. Register Tools

```python
def search_news(query: str) -> dict:
    """Search for news articles."""
    # Implementation here
    return {"results": [...]}

tool_registry.register_tool(
    name="search_news",
    function=search_news,
    description="Search for news articles",
    category="search",
    rate_limit=60
)
```

### 3. Create Agent Session

```python
# Create session
session = coordinator.create_session("session_123")

# Create conversation
conversation = state_manager.create_conversation(
    "session_123",
    system_prompt="You are a helpful news assistant."
)

# Add user message
state_manager.add_message(
    "session_123",
    MessageRole.USER,
    "Find news about AI"
)

# Execute tool
result = coordinator.execute_tool(
    "search_news",
    "session_123",
    query="AI news"
)

# Add assistant response
state_manager.add_message(
    "session_123",
    MessageRole.ASSISTANT,
    f"Found {len(result['result']['results'])} articles"
)

# End session
summary = coordinator.end_session("session_123")
```

### 4. Event Handling

```python
def on_tool_executed(event):
    print(f"Tool {event.data['tool_name']} executed successfully")

event_bus.subscribe(EventType.TOOL_EXECUTED, on_tool_executed)
```

### 5. Caching Tool Results

```python
# Check cache first
cached_result = state_manager.cache_manager.get_tool_result(
    "search_news",
    {"query": "AI"}
)

if not cached_result:
    # Execute tool and cache result
    result = coordinator.execute_tool("search_news", session_id, query="AI")
    state_manager.cache_manager.cache_tool_result(
        "search_news",
        {"query": "AI"},
        result,
        ttl=3600
    )
```

## Running Tests

```bash
# Run all tests
python tests/__init__.py --suite all

# Run specific test suites
python tests/__init__.py --suite integration
python tests/__init__.py --suite state
python tests/__init__.py --suite complete

# Or use pytest
pytest tests/ -v
pytest tests/test_integration.py -v
pytest tests/ --cov=src --cov-report=html
```

## Configuration

### Environment Variables

```bash
# API Keys
export OPENAI_API_KEY="your-key-here"
export VALYU_API_KEY="your-key-here"
export NEWS_API_KEY="your-key-here"

# Agent Settings
export AGENT_MODEL="gpt-4"
export AGENT_TEMPERATURE="0.7"

# Cache Settings
export CACHE_ENABLED="true"

# State Settings
export STATE_PERSISTENCE_DIR="./data/state"

# Logging
export LOG_LEVEL="INFO"
```

### Configuration File

Create a `config.json` file:

```json
{
  "agent": {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_iterations": 10
  },
  "cache": {
    "enabled": true,
    "max_size": 1000,
    "default_ttl": 3600
  },
  "state": {
    "persistence_dir": "./data/state"
  }
}
```

Load it:

```python
from config import load_config

config = load_config("config.json")
```

## Integration with Other Team Members

### With Person 1 (ReAct Agent)
- Use `ToolRegistry` to register all agent tools
- Use `AgentCoordinator` to manage agent sessions
- Use `EventBus` to track agent execution events

### With Person 2 (Custom Tools)
- Register all custom tools in `ToolRegistry`
- Use `CacheManager` to cache expensive tool results
- Emit events via `EventBus` for tool execution tracking

### With Person 4 (Documentation)
- All components have comprehensive docstrings
- Test files demonstrate usage patterns
- This README provides complete overview

## Key Features

### ✅ Modularity
- Loosely coupled components
- Clear interfaces and contracts
- Easy to extend and modify

### ✅ Observability
- Event system for tracking all operations
- Comprehensive logging
- Detailed statistics and metrics

### ✅ Reliability
- Comprehensive error handling
- Session management
- State persistence

### ✅ Performance
- Intelligent caching with TTL and LRU
- Efficient state management
- Configurable rate limiting

### ✅ Testing
- 100+ unit tests
- Integration tests
- End-to-end tests
- High code coverage

## Next Steps

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Up Environment**
   - Configure API keys
   - Set up logging directory
   - Create state persistence directory

3. **Run Tests**
   ```bash
   pytest tests/ -v
   ```

4. **Integrate with Team Code**
   - Import integration layer in agent code
   - Register custom tools
   - Set up event handlers

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                  Agent Application                  │
└────────────────┬────────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │  AgentCoordinator       │
    │  - Session Management   │
    │  - Tool Execution       │
    └─┬──────────┬──────────┬─┘
      │          │          │
┌─────┴─────┐ ┌─┴──────┐ ┌─┴───────────┐
│ToolRegistry│ │EventBus│ │StateManager│
│- Register  │ │- Pub/Sub│ │- Conv State│
│- Execute   │ │- History│ │- Cache     │
└────────────┘ └────────┘ └─────────────┘
```

## Contact & Support

For questions or issues with the integration layer, state management, or testing framework, contact Person 3.

## License

MIT License - Hackathon Project 2025
