"""Configuration management for the news agent system."""

import os
from typing import Dict, Any, Optional
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class Config:
    """
    Configuration manager for the agent system.
    Supports loading from environment variables, JSON files, and defaults.
    """
    
    # Default configuration
    DEFAULTS = {
        "agent": {
            "model": "gpt-4",
            "temperature": 0.7,
            "max_iterations": 10,
            "timeout": 300
        },
        "cache": {
            "enabled": True,
            "max_size": 1000,
            "default_ttl": 3600
        },
        "state": {
            "max_history": 100,
            "persistence_enabled": True,
            "persistence_dir": "./data/state"
        },
        "tools": {
            "search": {
                "enabled": True,
                "rate_limit": 60,
                "timeout": 30
            },
            "summarization": {
                "enabled": True,
                "max_length": 500,
                "timeout": 60
            }
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "./logs/agent.log"
        },
        "api_keys": {
            "openai": None,
            "valyu": None,
            "news_api": None
        },
        "aws": {
            "region": "us-east-1",
            "step_functions": {
                "state_machine_arn": None
            },
            "sqs": {
                "main_queue_url": None,
                "retry_queue_url": None,
                "dlq_url": None
            },
            "s3": {
                "pipeline_bucket": None
            },
            "ecs": {
                "cluster_arn": None,
                "subnets": [],
                "security_groups": []
            },
            "dynamodb": {
                "articles_table": None
            }
        },
        "pipeline": {
            "sources_config": "./config/sources.yaml",
            "max_retries": 3,
            "base_delay": 2,
            "batch_size": 50
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Optional path to JSON config file
        """
        self._config = self._deep_copy_dict(self.DEFAULTS)
        
        # Load from file if provided
        if config_path and Path(config_path).exists():
            self.load_from_file(config_path)
        
        # Override with environment variables
        self._load_from_env()
        
        logger.info("Configuration initialized")
    
    def _deep_copy_dict(self, d: Dict) -> Dict:
        """Deep copy a dictionary."""
        import copy
        return copy.deepcopy(d)
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # API Keys
        if os.getenv("OPENAI_API_KEY"):
            self._config["api_keys"]["openai"] = os.getenv("OPENAI_API_KEY")
        
        if os.getenv("VALYU_API_KEY"):
            self._config["api_keys"]["valyu"] = os.getenv("VALYU_API_KEY")
        
        if os.getenv("NEWS_API_KEY"):
            self._config["api_keys"]["news_api"] = os.getenv("NEWS_API_KEY")
        
        # Agent settings
        if os.getenv("AGENT_MODEL"):
            self._config["agent"]["model"] = os.getenv("AGENT_MODEL")
        
        if os.getenv("AGENT_TEMPERATURE"):
            self._config["agent"]["temperature"] = float(os.getenv("AGENT_TEMPERATURE"))
        
        # Cache settings
        if os.getenv("CACHE_ENABLED"):
            self._config["cache"]["enabled"] = os.getenv("CACHE_ENABLED").lower() == "true"
        
        # State settings
        if os.getenv("STATE_PERSISTENCE_DIR"):
            self._config["state"]["persistence_dir"] = os.getenv("STATE_PERSISTENCE_DIR")
        
        # Logging
        if os.getenv("LOG_LEVEL"):
            self._config["logging"]["level"] = os.getenv("LOG_LEVEL")
    
    def load_from_file(self, config_path: str) -> None:
        """
        Load configuration from JSON file.
        
        Args:
            config_path: Path to JSON config file
        """
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
            
            # Merge with existing config
            self._merge_config(self._config, file_config)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
    
    def _merge_config(self, base: Dict, update: Dict) -> None:
        """Recursively merge update dict into base dict."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated path.
        
        Args:
            key_path: Dot-separated path (e.g., 'agent.model')
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any) -> None:
        """
        Set configuration value by dot-separated path.
        
        Args:
            key_path: Dot-separated path (e.g., 'agent.model')
            value: Value to set
        """
        keys = key_path.split('.')
        config = self._config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section.
        
        Args:
            section: Section name (e.g., 'agent', 'cache')
            
        Returns:
            Section configuration dict
        """
        return self._config.get(section, {})
    
    def to_dict(self) -> Dict[str, Any]:
        """Get complete configuration as dictionary."""
        return self._deep_copy_dict(self._config)
    
    def save_to_file(self, config_path: str) -> None:
        """
        Save current configuration to JSON file.
        
        Args:
            config_path: Path to save config file
        """
        try:
            Path(config_path).parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(self._config, f, indent=2)
            logger.info(f"Saved configuration to {config_path}")
        except Exception as e:
            logger.error(f"Failed to save config to {config_path}: {e}")
    
    def validate(self) -> bool:
        """
        Validate configuration.
        
        Returns:
            True if valid, False otherwise
        """
        # Check required API keys
        if not self.get("api_keys.openai"):
            logger.warning("OpenAI API key not configured")
            return False
        
        # Validate numeric ranges
        temp = self.get("agent.temperature")
        if not (0 <= temp <= 2):
            logger.error(f"Invalid temperature: {temp}")
            return False
        
        return True


# Global config instance
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """Get or create global config instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


def load_config(config_path: str) -> Config:
    """
    Load configuration from file and set as global instance.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Config instance
    """
    global _config_instance
    _config_instance = Config(config_path)
    return _config_instance
