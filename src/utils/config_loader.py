"""Configuration loader and validator."""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import os


class Config:
    """Configuration manager for news analysis system."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Load configuration from YAML file."""
        if config_path is None:
            # Try default locations
            for path in ['config/config.yaml', 'config.yaml', '../config/config.yaml']:
                if Path(path).exists():
                    config_path = path
                    break
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = self._get_defaults()
    
    def _get_defaults(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            'valyu': {
                'search_type': 'web',
                'max_results': 5,
                'relevance_threshold': 0.3,
                'max_price': 10,
                'language': None,
                'region': None,
                'date_from': None,
                'date_to': None,
                'preferred_sources': 'bbc.com,reuters.com,aljazeera.com,apnews.com'
            },
            'llm': {
                'model': 'claude-3-5-sonnet',
                'temperature': 0.1,
                'max_tokens': 3072,
                'streaming': False
            },
            'tools': {
                'bias_scoring': True,
                'credibility_check': True,
                'conflict_analysis': True,
                'corruption_detection': True,
                'fact_checking': True,
                'citation_extraction': True,
                'claim_tracking': True,
                'google_fact_check_api_key': None,
                'mediabiasfactcheck_api_key': None
            },
            'analysis': {
                'default_mode': 'agent',
                'auto_detect_tools': True,
                'include_trace': False
            },
            'output': {
                'format': 'text',
                'save_results': False,
                'export_path': 'data/results/',
                'include_citations': True,
                'highlight_bias_indicators': True,
                'show_confidence_scores': True
            },
            'language': {
                'auto_detect': True,
                'auto_translate': False,
                'translation_service': 'google'
            },
            'retry': {
                'max_retries': 3,
                'base_delay': 1.0,
                'max_delay': 60.0,
                'backoff_factor': 2.0,
                'rate_limit_delay': 10.0
            },
            'cache': {
                'enabled': False,
                'ttl_hours': 24,
                'cache_path': 'data/cache/'
            },
            'logging': {
                'level': 'INFO',
                'file': 'logs/news_analysis.log',
                'console': True
            }
        }
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get config value by dot-notation path.
        
        Example:
            config.get('valyu.max_results') -> 5
            config.get('tools.fact_checking') -> True
        """
        keys = path.split('.')
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, path: str, value: Any):
        """Set config value by dot-notation path."""
        keys = path.split('.')
        config = self._config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
    
    def parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """
        Parse date string to ISO format.
        
        Supports:
        - ISO format: "2024-01-01"
        - Relative: "-7d", "-1m", "-1y"
        - Keywords: "today", "yesterday"
        """
        if not date_str:
            return None
        
        if date_str == 'today':
            return datetime.now().strftime('%Y-%m-%d')
        elif date_str == 'yesterday':
            return (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        elif date_str.startswith('-'):
            # Relative date
            value = int(date_str[1:-1])
            unit = date_str[-1]
            
            if unit == 'd':
                date = datetime.now() - timedelta(days=value)
            elif unit == 'w':
                date = datetime.now() - timedelta(weeks=value)
            elif unit == 'm':
                date = datetime.now() - timedelta(days=value * 30)
            elif unit == 'y':
                date = datetime.now() - timedelta(days=value * 365)
            else:
                return None
            
            return date.strftime('%Y-%m-%d')
        else:
            # Assume ISO format
            return date_str
    
    def get_valyu_params(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get Valyu search parameters with optional overrides."""
        params = {
            'search_type': self.get('valyu.search_type'),
            'max_results': self.get('valyu.max_results'),
            'relevance_threshold': self.get('valyu.relevance_threshold'),
            'max_price': self.get('valyu.max_price'),
        }
        
        # Optional params
        if lang := self.get('valyu.language'):
            params['language'] = lang
        if region := self.get('valyu.region'):
            params['region'] = region
        if date_from := self.parse_date(self.get('valyu.date_from')):
            params['date_from'] = date_from
        if date_to := self.parse_date(self.get('valyu.date_to')):
            params['date_to'] = date_to
        
        # Apply overrides
        if overrides:
            params.update(overrides)
        
        return params
    
    def get_retry_params(self) -> Dict[str, Any]:
        """Get retry configuration."""
        return {
            'max_retries': self.get('retry.max_retries'),
            'base_delay': self.get('retry.base_delay'),
            'max_delay': self.get('retry.max_delay'),
            'backoff_factor': self.get('retry.backoff_factor'),
            'rate_limit_delay': self.get('retry.rate_limit_delay'),
        }
    
    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check if a specific tool is enabled."""
        return self.get(f'tools.{tool_name}', True)
    
    def get_api_key(self, service: str) -> Optional[str]:
        """Get API key from config or environment."""
        # Try config first
        key = self.get(f'tools.{service}_api_key')
        if key:
            return key
        
        # Try environment
        env_key = f"{service.upper().replace('-', '_')}_API_KEY"
        return os.getenv(env_key)
