"""
Configuration management for News Agent
"""
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class AgentConfig:
    """Configuration for the News Agent"""
    model_name: str = "claude-3-5-sonnet"
    use_openai: bool = False
    enable_search: bool = True
    timeout: int = 30
    max_retries: int = 3
    enable_logging: bool = True
    enable_metrics: bool = True

    @classmethod
    def from_env(cls) -> 'AgentConfig':
        """Load configuration from environment variables"""
        return cls(
            model_name=os.getenv("AGENT_MODEL", "claude-3-5-sonnet"),
            use_openai=os.getenv("USE_OPENAI", "false").lower() == "true",
            enable_search=os.getenv("ENABLE_SEARCH", "true").lower() == "true",
            timeout=int(os.getenv("AGENT_TIMEOUT", "30")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            enable_logging=os.getenv("ENABLE_LOGGING", "true").lower() == "true",
            enable_metrics=os.getenv("ENABLE_METRICS", "true").lower() == "true"
        )

class MetricsCollector:
    """Collect and report agent performance metrics"""

    def __init__(self):
        self.metrics = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "tool_usage": {},
            "response_times": [],
            "error_types": {}
        }

    def record_query(self, success: bool, response_time: float, tools_used: list, error: Optional[str] = None):
        """Record a query execution"""
        self.metrics["total_queries"] += 1
        if success:
            self.metrics["successful_queries"] += 1
        else:
            self.metrics["failed_queries"] += 1

        self.metrics["response_times"].append(response_time)

        for tool in tools_used:
            self.metrics["tool_usage"][tool] = self.metrics["tool_usage"].get(tool, 0) + 1

        if error:
            error_type = type(error).__name__
            self.metrics["error_types"][error_type] = self.metrics["error_types"].get(error_type, 0) + 1

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        total_time = sum(self.metrics["response_times"])
        avg_time = total_time / len(self.metrics["response_times"]) if self.metrics["response_times"] else 0

        return {
            "total_queries": self.metrics["total_queries"],
            "success_rate": self.metrics["successful_queries"] / self.metrics["total_queries"] if self.metrics["total_queries"] > 0 else 0,
            "average_response_time": avg_time,
            "tool_usage": self.metrics["tool_usage"],
            "error_types": self.metrics["error_types"]
        }

    def reset(self):
        """Reset all metrics"""
        self.metrics = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "tool_usage": {},
            "response_times": [],
            "error_types": {}
        }