"""Source configuration loader for news sources."""

import os
import json
import yaml
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from string import Template

logger = logging.getLogger(__name__)


class SourceConfigLoader:
    """
    Loads and manages source configurations from YAML/JSON files.
    Supports tags: region, state_aligned, independent, diaspora, language.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the source config loader.
        
        Args:
            config_path: Path to YAML or JSON config file
        """
        self.config_path = config_path
        self.sources: List[Dict[str, Any]] = []
        self.source_lists: List[Dict[str, Any]] = []
        
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> None:
        """
        Load configuration from YAML or JSON file.
        
        Args:
            config_path: Path to configuration file
        """
        path = Path(config_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        # Determine file type and load
        if path.suffix.lower() in ['.yaml', '.yml']:
            config = self._load_yaml(path)
        elif path.suffix.lower() == '.json':
            config = self._load_json(path)
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}")
        
        # Parse configuration
        self.sources = config.get('sources', [])
        self.source_lists = config.get('source_lists', [])
        
        # Substitute environment variables
        self._substitute_env_vars()
        
        logger.info(f"Loaded {len(self.sources)} sources from {config_path}")
    
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML configuration."""
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON configuration."""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _substitute_env_vars(self) -> None:
        """Substitute environment variables in configuration values."""
        def substitute_dict(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {k: substitute_dict(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [substitute_dict(item) for item in obj]
            elif isinstance(obj, str) and '${' in obj:
                # Use Template for environment variable substitution
                try:
                    template = Template(obj)
                    return template.safe_substitute(os.environ)
                except Exception as e:
                    logger.warning(f"Failed to substitute env var in '{obj}': {e}")
                    return obj
            return obj
        
        self.sources = substitute_dict(self.sources)
        self.source_lists = substitute_dict(self.source_lists)
    
    def get_sources(self, 
                   source_type: Optional[str] = None,
                   tags: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get sources filtered by type and tags.
        
        Args:
            source_type: Filter by source type (rss, url, api)
            tags: Filter by tags (e.g., {'diaspora': True, 'language': 'en'})
            
        Returns:
            List of matching source configurations
        """
        filtered = self.sources
        
        # Filter by type
        if source_type:
            filtered = [s for s in filtered if s.get('type') == source_type]
        
        # Filter by tags
        if tags:
            def matches_tags(source: Dict[str, Any]) -> bool:
                source_tags = source.get('tags', {})
                return all(
                    source_tags.get(key) == value 
                    for key, value in tags.items()
                )
            
            filtered = [s for s in filtered if matches_tags(s)]
        
        return filtered
    
    def get_sources_by_region(self, region: str) -> List[Dict[str, Any]]:
        """Get sources for a specific region."""
        return self.get_sources(tags={'region': region})
    
    def get_diaspora_sources(self) -> List[Dict[str, Any]]:
        """Get all diaspora sources."""
        return self.get_sources(tags={'diaspora': True})
    
    def get_independent_sources(self) -> List[Dict[str, Any]]:
        """Get all independent sources."""
        return self.get_sources(tags={'independent': True})
    
    def get_state_aligned_sources(self) -> List[Dict[str, Any]]:
        """Get all state-aligned sources."""
        return self.get_sources(tags={'state_aligned': True})
    
    def get_sources_by_language(self, language: str) -> List[Dict[str, Any]]:
        """Get sources for a specific language."""
        return self.get_sources(tags={'language': language})
    
    def get_all_sources(self) -> List[Dict[str, Any]]:
        """Get all configured sources."""
        return self.sources
    
    def get_source_lists(self) -> List[Dict[str, Any]]:
        """Get external source list configurations."""
        return self.source_lists
    
    def validate_sources(self) -> Dict[str, List[str]]:
        """
        Validate source configurations.
        
        Returns:
            Dictionary with 'valid' and 'invalid' source names
        """
        valid = []
        invalid = []
        
        required_fields = ['type', 'url', 'name', 'tags']
        required_tags = ['region', 'state_aligned', 'independent', 'diaspora', 'language']
        
        for source in self.sources:
            source_name = source.get('name', 'Unknown')
            
            # Check required fields
            if not all(field in source for field in required_fields):
                invalid.append(f"{source_name}: Missing required fields")
                continue
            
            # Check required tags
            tags = source.get('tags', {})
            if not all(tag in tags for tag in required_tags):
                invalid.append(f"{source_name}: Missing required tags")
                continue
            
            # Validate source type
            if source['type'] not in ['rss', 'url', 'api']:
                invalid.append(f"{source_name}: Invalid type '{source['type']}'")
                continue
            
            valid.append(source_name)
        
        return {'valid': valid, 'invalid': invalid}
