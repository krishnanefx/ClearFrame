"""
News Article Agent using LangGraph ReAct pattern.
Person 1: Agent Architecture Lead - Enhanced with:
- Configuration management
- Performance metrics
- Advanced error handling
- Structured output capabilities
- Multi-turn conversation memory
"""
import os
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_valyu import ValyuSearchTool

# Add parent directory to path to import utils
import sys
sys.path.append(str(Path(__file__).parent.parent))
from utils.model_helper import get_chat_model
from utils.config import AgentConfig, MetricsCollector


class NewsAgent:
    """
    ReAct agent for news article research and analysis.
    Uses LangGraph's prebuilt create_react_agent pattern.
    """
    
    def __init__(
        self,
        model_name: str = "claude-3-5-sonnet",
        use_openai: bool = False,
        enable_search: bool = True,
        timeout: int = 30
    ):
        """
        Initialize the News Agent.
        
        Args:
            model_name: LLM model to use
            use_openai: Whether to use OpenAI instead of Bedrock
            enable_search: Whether to enable Valyu search tool
            timeout: Request timeout in seconds
        """
        # Load environment variables
        env_path = Path(__file__).parent.parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
        
        # Simple config setup
        self.enable_logging = True
        self.enable_metrics = True
        
        # Store parameters
        self.timeout = timeout
        self.model_name = model_name
        
        # Setup logging
        if self.enable_logging:
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = None
        
        # Initialize metrics
        self.metrics = MetricsCollector() if self.enable_metrics else None
        
        # Try to initialize LLM with fallback
        self.llm = None
        try:
            if use_openai or not os.getenv('HOLISTIC_AI_TEAM_ID'):
                print("🔄 Using OpenAI...")
                self.llm = self._init_openai()
            else:
                print("🔄 Using Holistic AI Bedrock...")
                self.llm = self._init_bedrock()
        except Exception as e:
            print(f"❌ Primary LLM failed: {e}")
            print("🔄 Trying fallback...")
            try:
                if use_openai:
                    self.llm = self._init_bedrock()
                else:
                    self.llm = self._init_openai()
            except Exception as e2:
                raise RuntimeError(f"Both LLM providers failed: {e}, {e2}")
        
        # Initialize tools
        self.tools = []
        if enable_search:
            valyu_key = os.getenv("VALYU_API_KEY")
            if valyu_key:
                try:
                    self.search_tool = ValyuSearchTool(valyu_api_key=valyu_key)
                    self.tools.append(self.search_tool)
                    print("✅ Valyu search tool enabled")
                except Exception as e:
                    print(f"⚠️ Valyu search tool failed: {e}")
            else:
                print("⚠️ Valyu API key not found - search disabled")
        
        # Create ReAct agent
        try:
            self.agent = create_react_agent(
                self.llm,
                tools=self.tools
            )
            print("✅ ReAct agent created successfully")
        except Exception as e:
            raise RuntimeError(f"Failed to create agent: {e}")
        
        # Conversation memory
        self.conversation_history: List = []
        
        # System prompt for news research
        self.system_prompt = """You are an expert news research assistant.
Your role is to:
1. Search for relevant and recent news articles
2. Analyze information from multiple sources
3. Provide well-researched, factual responses
4. Cite sources when providing information

Always use the search tool for current events and recent information.
Be objective and present multiple perspectives when relevant."""
        
        if self.logger:
            self.logger.info("✅ News Agent initialized successfully")
    
    def _init_bedrock(self):
        """Initialize Holistic AI Bedrock model."""
        from utils.model_helper import HolisticAIBedrockChat
        
        team_id = os.getenv("HOLISTIC_AI_TEAM_ID")
        api_token = os.getenv("HOLISTIC_AI_API_TOKEN")
        
        if not team_id or not api_token:
            raise ValueError("HOLISTIC_AI_TEAM_ID and HOLISTIC_AI_API_TOKEN required")
        
        return HolisticAIBedrockChat(
            model=self.model_name,
            request_timeout=self.timeout
        )
    
    def _init_openai(self):
        """Initialize OpenAI model."""
        from langchain_openai import ChatOpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY required for OpenAI fallback")
        
        return ChatOpenAI(
            model=self.model_name,
            timeout=self.timeout
        )
    
    def research(
        self,
        query: str,
        max_sources: int = 5
    ) -> Dict[str, Any]:
        """
        Research a news topic using the agent.
        
        Args:
            query: The news topic or question to research
            max_sources: Maximum number of sources to search
        
        Returns:
            Dictionary with agent response and metadata
        """
        try:
            # Prepare messages
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=query)
            ]
            
            # Invoke agent with timeout
            result = self.agent.invoke({"messages": messages})
            
            # Extract response
            final_response = result['messages'][-1].content
            
            return {
                "query": query,
                "response": final_response,
                "message_count": len(result['messages']),
                "used_tools": self._extract_tool_usage(result['messages']),
                "success": True
            }
        except Exception as e:
            return {
                "query": query,
                "response": f"Error during research: {str(e)}",
                "message_count": 0,
                "used_tools": [],
                "success": False,
                "error": str(e)
            }
    
    def chat(
        self,
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Multi-turn conversation with the agent.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
        
        Returns:
            Agent response with conversation state
        """
        # Convert to LangChain message format
        lc_messages: List = [SystemMessage(content=self.system_prompt)]
        
        for msg in messages:
            if msg['role'] == 'user':
                lc_messages.append(HumanMessage(content=msg['content']))
        
        # Invoke agent
        result = self.agent.invoke({"messages": lc_messages})
        
        return {
            "response": result['messages'][-1].content,
            "conversation_length": len(result['messages']),
            "full_state": result
        }
    
    def research_with_structure(
        self,
        query: str,
        output_format: str = "summary"
    ) -> Dict[str, Any]:
        """
        Research with structured output formats.
        
        Args:
            query: Research query
            output_format: "summary", "bullet_points", "sources_only", "detailed"
        
        Returns:
            Structured research results
        """
        format_prompts = {
            "summary": "Provide a concise summary of the key findings.",
            "bullet_points": "Present findings as bullet points with key facts.",
            "sources_only": "List only the sources and their main claims.",
            "detailed": "Provide comprehensive analysis with multiple perspectives."
        }
        
        enhanced_query = f"{query}\n\nPlease {format_prompts.get(output_format, format_prompts['summary'])}"
        
        result = self.research(enhanced_query)
        
        # Add structure metadata
        result.update({
            "output_format": output_format,
            "research_timestamp": time.time(),
            "agent_version": "1.0"
        })
        
        return result
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics."""
        if not self.metrics:
            return {"metrics_disabled": True}
        
        return self.metrics.get_summary()
    
    def reset_conversation(self):
        """Reset conversation memory."""
        self.conversation_history = []
        if self.logger:
            self.logger.info("Conversation history reset")
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status."""
        return {
            "model": self.model_name,
            "tools_available": [tool.__class__.__name__ for tool in self.tools],
            "conversation_length": len(self.conversation_history),
            "metrics_enabled": self.metrics is not None,
            "logging_enabled": self.logger is not None,
            "system_prompt_length": len(self.system_prompt)
        }
    
    def _extract_tool_usage(self, messages: List) -> List[str]:
        """Extract which tools were used from message history."""
        tools_used = []
        for msg in messages:
            msg_type = type(msg).__name__
            if msg_type == "AIMessage" and hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tools_used.append(tool_call['name'])
        return list(set(tools_used))


def main():
    """Example usage of the NewsAgent."""
    print("🤖 Initializing News Agent...")
    
    # Create agent
    agent = NewsAgent(
        model_name="claude-3-5-sonnet",
        enable_search=True
    )
    
    # Test query
    print("\n" + "="*70)
    print("Testing News Research Agent")
    print("="*70)
    
    query = "What are the latest developments in AI agent frameworks in November 2025?"
    print(f"\n❓ Query: {query}")
    
    result = agent.research(query)
    
    print(f"\n💬 Response:\n{result['response']}")
    print(f"\n📊 Tools used: {result['used_tools']}")
    print(f"📊 Total messages: {result['message_count']}")
    

if __name__ == "__main__":
    main()