# TheGreatAgentHack - News Article Agent

**Person 1: Agent Architecture Lead** - Advanced ReAct agent for news research and analysis.

## 🚀 Features

### Core Architecture
- **LangGraph ReAct Agent**: Modern function-calling pattern with reasoning + acting loops
- **Multi-Provider LLM Support**: Holistic AI Bedrock (Claude) with OpenAI fallback
- **Advanced Tool Integration**: Valyu AI search for real-time information
- **Robust Error Handling**: Automatic fallback between providers, timeout management

### Advanced Capabilities
- **Configuration Management**: Environment-based config with validation
- **Performance Metrics**: Query success rates, response times, tool usage analytics
- **Structured Output**: Multiple output formats (summary, bullet points, sources, detailed)
- **Conversation Memory**: Multi-turn conversations with context retention
- **Comprehensive Logging**: Debug and monitoring capabilities

### Agent Architecture Highlights
- **Fallback Strategy**: Primary → Secondary LLM provider switching
- **Tool Orchestration**: Dynamic tool selection and execution
- **State Management**: Message history and conversation flow
- **Performance Monitoring**: Real-time metrics collection and reporting
- **Modular Design**: Separated concerns (config, metrics, tools, agent logic)

## 🛠️ Setup

### Prerequisites
```bash
pip install langgraph langchain-core langchain-openai langchain-valyu python-dotenv requests pydantic
```

### Environment Configuration
```bash
# Copy and edit environment file
cp config/.env.example .env

# Required: Holistic AI Bedrock (recommended)
HOLISTIC_AI_TEAM_ID="your-team-id"
HOLISTIC_AI_API_TOKEN="your-token"

# Required: Valyu Search
VALYU_API_KEY="your-valyu-key"

# Optional: OpenAI fallback
OPENAI_API_KEY="your-openai-key"
```

### Quick Start
```python
from src.agents.news_agent import NewsAgent

# Create agent with automatic fallback
agent = NewsAgent(
    model_name="claude-3-5-sonnet",
    enable_search=True
)

# Research with structured output
result = agent.research_with_structure(
    "Latest AI developments November 2025",
    output_format="bullet_points"
)

print(result['response'])
```

## 📊 Architecture Improvements

### 1. **Configuration Management**
- Environment-based configuration
- Validation and defaults
- Runtime config updates

### 2. **Metrics & Monitoring**
```python
# Get performance stats
metrics = agent.get_performance_metrics()
print(f"Success rate: {metrics['success_rate']:.2%}")
print(f"Avg response time: {metrics['average_response_time']:.2f}s")
```

### 3. **Structured Research**
```python
# Different output formats
agent.research_with_structure(query, "summary")      # Concise overview
agent.research_with_structure(query, "bullet_points") # Key facts
agent.research_with_structure(query, "sources_only")  # Source citations
agent.research_with_structure(query, "detailed")      # Comprehensive analysis
```

### 4. **Advanced Error Handling**
- Automatic provider fallback
- Timeout management
- Graceful degradation
- Detailed error reporting

### 5. **Conversation Management**
```python
# Multi-turn conversations
agent.chat([
    {"role": "user", "content": "What are AI agents?"},
    {"role": "user", "content": "How do they compare to traditional AI?"}
])

# Reset conversation
agent.reset_conversation()
```

## 🔧 API Reference

### NewsAgent Class

#### Initialization
```python
NewsAgent(
    model_name="claude-3-5-sonnet",  # LLM model
    use_openai=False,                # Force OpenAI
    enable_search=True,              # Enable Valyu search
    timeout=30                       # Request timeout
)
```

#### Core Methods
- `research(query)` - Basic research query
- `research_with_structure(query, format)` - Structured output research
- `chat(messages)` - Multi-turn conversation
- `get_performance_metrics()` - Performance statistics
- `get_agent_status()` - Agent health check
- `reset_conversation()` - Clear conversation history

## 🧪 Testing

### Run Basic Test
```bash
python src/agents/news_agent.py
```

### Run Diagnostic Test
```bash
python test_agent.py
```

### Test Structured Output
```python
agent = NewsAgent()
result = agent.research_with_structure(
    "AI agent frameworks 2025",
    "bullet_points"
)
```

## 📈 Performance Metrics

The agent tracks:
- **Query Success Rate**: Percentage of successful research queries
- **Response Times**: Average time per query
- **Tool Usage**: Which tools are used most frequently
- **Error Types**: Common failure patterns
- **Conversation Length**: Multi-turn engagement metrics

## 🔄 Fallback Strategy

1. **Primary**: Holistic AI Bedrock (Claude models)
2. **Secondary**: OpenAI (GPT models)
3. **Graceful Failure**: Return error details instead of crashing

## 🎯 Next Steps for Team Integration

### Person 2: Custom Tools Development
- Add news scraping tools
- Implement fact-checking utilities
- Create summarization tools

### Person 3: Integration & Testing
- Connect to web interfaces
- Add comprehensive test suites
- Implement monitoring dashboards

### Person 4: Documentation & Demo
- Create demo applications
- Build presentation materials
- Document API usage

## 🚀 Production Readiness

- ✅ Error handling and logging
- ✅ Configuration management
- ✅ Performance monitoring
- ✅ Modular architecture
- ✅ Fallback strategies
- ✅ Comprehensive testing

---

**Built for The Great Agent Hack 2025** - Demonstrating advanced agent architecture principles with production-ready features.
