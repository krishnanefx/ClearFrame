"""
Model helper utilities for LangGraph agents.
Supports Holistic AI Bedrock (recommended) and OpenAI.
"""
import os
from typing import Optional
from langchain_openai import ChatOpenAI

class HolisticAIBedrockChat(ChatOpenAI):
    """
    Custom ChatOpenAI wrapper for Holistic AI Bedrock Proxy.
    Uses OpenAI-compatible API but routes through Bedrock.
    """
    def __init__(self, model: str = "claude-3-5-sonnet", **kwargs):
        # Map friendly names to Bedrock model IDs
        model_map = {
            "claude-3-5-sonnet": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "claude-3-5-haiku": "anthropic.claude-3-5-haiku-20241022-v1:0",
            "llama-3-3-70b": "meta.llama3-3-70b-instruct-v1:0",
            "nova-pro": "amazon.nova-pro-v1:0",
            "nova-lite": "amazon.nova-lite-v1:0"
        }
        
        bedrock_model = model_map.get(model, model)
        
        # Get credentials from environment
        team_id = os.getenv("HOLISTIC_AI_TEAM_ID")
        api_token = os.getenv("HOLISTIC_AI_API_TOKEN")
        
        if not team_id or not api_token:
            raise ValueError(
                "Missing Holistic AI Bedrock credentials. "
                "Set HOLISTIC_AI_TEAM_ID and HOLISTIC_AI_API_TOKEN in .env"
            )
        
        # Initialize with Bedrock proxy settings
        super().__init__(
            model=bedrock_model,
            base_url=f"https://api.holisticai.com/bedrock-proxy/teams/{team_id}/v1",
            api_key=api_token,
            **kwargs
        )

def get_chat_model(
    model_name: str = "claude-3-5-sonnet",
    use_openai: bool = False,
    **kwargs
) -> ChatOpenAI:
    """
    Get a chat model instance.
    
    Args:
        model_name: Model to use (claude-3-5-sonnet, claude-3-5-haiku, etc.)
        use_openai: If True, use OpenAI instead of Bedrock
        **kwargs: Additional arguments to pass to the model
    
    Returns:
        ChatOpenAI instance configured for Bedrock or OpenAI
    """
    if use_openai:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")
        return ChatOpenAI(model=model_name, api_key=api_key, **kwargs)
    
    # Use Holistic AI Bedrock by default
    return HolisticAIBedrockChat(model=model_name, **kwargs)