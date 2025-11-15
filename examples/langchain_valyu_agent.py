#!/usr/bin/env python3
"""
LangChain Agent with Valyu Search Capabilities

This script demonstrates how to create a conversational LangChain agent
that can use Valyu search to answer questions with real-time data from the web.

Setup Requirements:
1. VALYU_API_KEY in .env file
2. ANTHROPIC_API_KEY in .env file
3. langchain-valyu package installed

Usage:
    python examples/langchain_valyu_agent.py
"""

import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_valyu import ValyuSearchTool
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory

# Load environment variables
load_dotenv()

# Verify API keys
if not os.getenv("VALYU_API_KEY"):
    raise ValueError("VALYU_API_KEY not found in .env file. Please add it.")

if not os.getenv("ANTHROPIC_API_KEY"):
    raise ValueError("ANTHROPIC_API_KEY not found in .env file. Please add it.")

# Initialize the Valyu search tool
valyu_tool = ValyuSearchTool(
    api_key=os.getenv("VALYU_API_KEY"),
    max_results=10  # Adjust as needed
)

# Create the LangChain agent
def create_valyu_agent():
    """Create a LangChain agent with Valyu search capabilities."""

    # Initialize the Claude model
    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        temperature=0.1,
        max_tokens=4096
    )

    # Define the system prompt
    system_prompt = """You are a helpful AI assistant with access to real-time web search capabilities through Valyu.

You can search the web to find current information, news, and data to answer user questions accurately.

When using the search tool:
- Be specific with your search queries
- Use site filters when looking for information from specific sources
- Always cite your sources when providing information from search results
- Explain your reasoning clearly

Available tools:
- valyu_search: Search the web for real-time information

Always provide well-reasoned answers with citations when using search results."""

    # Create the prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # Create the agent
    agent = create_openai_tools_agent(
        llm=llm,
        tools=[valyu_tool],
        prompt=prompt
    )

    # Create the agent executor with memory
    agent_executor = AgentExecutor(
        agent=agent,
        tools=[valyu_tool],
        memory=ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        ),
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5
    )

    return agent_executor

def main():
    """Demonstrate the Valyu-powered LangChain agent."""

    print("🚀 Setting up LangChain Agent with Valyu Search")
    print("=" * 60)

    try:
        # Create the agent
        agent = create_valyu_agent()
        print("✅ Agent created successfully!")

        # Example queries to demonstrate
        example_queries = [
            "What are the latest developments in AI regulation in the EU?",
            "Find recent news about climate change policies in the US",
            "Search for information about the current state of the Sudan conflict from BBC News",
            "What are the top trending topics on social media today?"
        ]

        print("\n🔍 Testing the agent with example queries:")
        print("-" * 60)

        for i, query in enumerate(example_queries, 1):
            print(f"\n📝 Query {i}: {query}")
            print("-" * 40)

            try:
                response = agent.invoke({"input": query})
                print(f"🤖 Response: {response['output'][:500]}...")
                print("✅ Success!")

            except Exception as e:
                print(f"❌ Error: {str(e)}")

        # Interactive mode
        print("\n" + "=" * 60)
        print("💬 Interactive Mode")
        print("Type 'quit' to exit")
        print("=" * 60)

        while True:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                break

            if user_input:
                try:
                    response = agent.invoke({"input": user_input})
                    print(f"\n🤖 Agent: {response['output']}")
                except Exception as e:
                    print(f"❌ Error: {str(e)}")

    except Exception as e:
        print(f"❌ Setup failed: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Check that VALYU_API_KEY and ANTHROPIC_API_KEY are set in .env")
        print("2. Ensure langchain-valyu and langchain-anthropic are installed")
        print("3. Verify your API keys are valid")

if __name__ == "__main__":
    main()