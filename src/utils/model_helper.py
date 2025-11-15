"""Model helper utilities for LangGraph agents relying on Holistic AI Bedrock."""

from __future__ import annotations

import os
from typing import Any, Callable, ClassVar, Dict, List, Optional, Sequence, Union

import requests
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import LanguageModelInput
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import Field, model_validator
from resilience.circuit_breakers import holistic_ai_breaker, wrap_with_breaker


class HolisticAIBedrockChat(BaseChatModel):
    """Minimal chat model wrapper for the Holistic AI Bedrock proxy."""

    model: str = Field(default="anthropic.claude-3-5-sonnet-20241022-v2:0")
    team_id: str = Field(..., description="Holistic AI team identifier")
    api_token: str = Field(..., description="Holistic AI API token")
    base_url: str = Field(..., description="Base URL for the Holistic AI proxy")
    request_timeout: int = Field(default=30, description="HTTP timeout in seconds")
    temperature: float = Field(default=0.2, description="Sampling temperature")
    max_tokens: Optional[int] = Field(default=None, description="Max tokens for responses")
    additional_headers: Dict[str, str] = Field(default_factory=dict)
    extra_body: Dict[str, Any] = Field(default_factory=dict)

    MODEL_MAP: ClassVar[Dict[str, str]] = {
        "claude-3-5-sonnet": "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
        "llama3-70b-instruct": "meta.llama3-70b-instruct-v1:0",
    }

    @model_validator(mode="before")
    @classmethod
    def _populate_defaults(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        values = dict(data or {})

        # Resolve model alias into underlying Bedrock identifier
        requested_model = values.get("model", "claude-3-5-sonnet")
        values["model"] = cls.MODEL_MAP.get(requested_model, requested_model)

        # Resolve credentials from explicit kwargs or environment
        team_id = values.get("team_id") or os.getenv("HOLISTIC_AI_TEAM_ID")
        api_token = values.get("api_token") or os.getenv("HOLISTIC_AI_API_TOKEN")
        if not team_id or not api_token:
            raise ValueError(
                "Missing Holistic AI Bedrock credentials. Set HOLISTIC_AI_TEAM_ID and "
                "HOLISTIC_AI_API_TOKEN in the environment or pass them explicitly."
            )
        values["team_id"] = team_id
        values["api_token"] = api_token

        # Use the new AWS Lambda endpoint
        base_url = "https://ctwa92wg1b.execute-api.us-east-1.amazonaws.com/prod/invoke"
        values["base_url"] = base_url

        return values

    def _convert_messages(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        converted: List[Dict[str, Any]] = []
        system_parts = []
        
        for message in messages:
            content = message.content if isinstance(message.content, str) else str(message.content)
            if isinstance(message, SystemMessage):
                system_parts.append(content)
            elif isinstance(message, HumanMessage):
                role = "user"
                full_content = content
                if system_parts:
                    system_text = "\n".join(system_parts)
                    full_content = system_text + "\n\n" + content
                    system_parts = []  # Clear after using
                converted.append({"role": role, "content": full_content})
            elif isinstance(message, AIMessage):
                role = "assistant"
                converted.append({"role": role, "content": content})
            else:
                role = "user"
                converted.append({"role": role, "content": content})
        
        return converted

    def _default_payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"model": self.model, "temperature": self.temperature}
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        payload.update(self.extra_body)
        return payload

    def bind_tools(
        self,
        tools: Sequence[Union[Dict[str, Any], type, Callable, BaseTool]],
        *,
        tool_choice: Optional[Union[str, Dict[str, Any], bool]] = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, BaseMessage]:
        """Bind callable tools to the chat model in OpenAI-compatible format."""
        formatted_tools = [convert_to_openai_tool(tool) for tool in tools]

        resolved_choice: Optional[Union[str, Dict[str, Any]]] = None
        if tool_choice is not None:
            if isinstance(tool_choice, str):
                resolved_choice = {
                    "type": "function",
                    "function": {"name": tool_choice},
                }
            elif isinstance(tool_choice, bool):
                resolved_choice = "required"
            elif isinstance(tool_choice, dict):
                resolved_choice = tool_choice
            else:
                raise ValueError(
                    "tool_choice must be a tool name, dict, bool, or None."
                )

        return super().bind(
            tools=formatted_tools,
            tool_choice=resolved_choice,
            **kwargs,
        )

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        # Check for tool binding in kwargs, passed from .bind_tools()
        tools = kwargs.get("tools")
        tool_choice = kwargs.get("tool_choice")

        payload = {
            "team_id": self.team_id,
            "model": self.model,
            "messages": self._convert_messages(messages),
            "max_tokens": self.max_tokens or 4096,  # Increased default
            "temperature": self.temperature,
            **self.extra_body,
        }

        # Add tool-related parameters if they exist
        if tools:
            payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice

        headers = {
            "Content-Type": "application/json",
            "X-Api-Token": self.api_token,
            **self.additional_headers,
        }

        response = wrap_with_breaker(
            holistic_ai_breaker,
            requests.post,
            self.base_url,
            json=payload,
            headers=headers,
            timeout=self.request_timeout,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(
                f"Bedrock proxy request failed with status {response.status_code}: {response.text}"
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError(f"Failed to parse Bedrock proxy response: {response.text}") from exc

        # Handle both streaming and non-streaming content extraction
        content = data.get("content", "")
        if isinstance(content, list):
            # Handle structure from Bedrock's Claude integration
            text_parts = [part["text"] for part in content if part.get("type") == "text"]
            content = "".join(text_parts)

        # Fallback for OpenAI-like format
        if not content and "choices" in data:
            try:
                message_data = data["choices"][0]["message"]
                content = message_data.get("content", "")
            except (KeyError, IndexError):
                pass

        if run_manager:
            run_manager.on_llm_new_token(content or "")

        # Check for tool calls in the response
        tool_calls = []
        if "choices" in data and data["choices"]:
            message = data["choices"][0].get("message", {})
            if "tool_calls" in message:
                tool_calls = message["tool_calls"]

        ai_message = AIMessage(content=content or "", tool_calls=tool_calls)
        generation = ChatGeneration(
            message=ai_message,
            generation_info={
                "finish_reason": data.get("finish_reason")
                or data.get("choices", [{}])[0].get("finish_reason"),
                "usage": data.get("usage"),
            },
        )

        return ChatResult(
            generations=[generation],
            llm_output={"id": data.get("id"), "usage": data.get("usage")},
        )

    @property
    def _llm_type(self) -> str:
        return "holistic_ai_bedrock"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "team_id": self.team_id,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


def get_chat_model(
    model_name: str = "claude-3-5-sonnet",
    request_timeout: Optional[int] = None,
    **kwargs: Any,
) -> HolisticAIBedrockChat:
    """Instantiate the Holistic AI Bedrock chat model with sane defaults."""

    init_kwargs = dict(kwargs)
    if request_timeout is not None:
        init_kwargs["request_timeout"] = request_timeout

    return HolisticAIBedrockChat(model=model_name, **init_kwargs)
