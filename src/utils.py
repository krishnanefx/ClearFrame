"""Utility functions for the news agent system."""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import hashlib
import json


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        log_format: Optional custom log format
    """
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    handlers = [logging.StreamHandler()]
    
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=handlers
    )


def generate_session_id() -> str:
    """
    Generate a unique session ID.
    
    Returns:
        Unique session identifier
    """
    timestamp = datetime.now().isoformat()
    random_component = hashlib.sha256(timestamp.encode()).hexdigest()[:8]
    return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random_component}"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    import re
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')
    return sanitized


def ensure_directory(path: str) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        Path object
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def load_json_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load JSON data from a file.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Parsed JSON data or None if error
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load JSON from {file_path}: {e}")
        return None


def save_json_file(data: Dict[str, Any], file_path: str) -> bool:
    """
    Save data to JSON file.
    
    Args:
        data: Data to save
        file_path: Path to save file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        logging.error(f"Failed to save JSON to {file_path}: {e}")
        return False


def format_timestamp(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a datetime object as a string.
    
    Args:
        dt: Datetime object
        format_str: Format string
        
    Returns:
        Formatted timestamp
    """
    return dt.strftime(format_str)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def calculate_token_estimate(text: str) -> int:
    """
    Estimate token count for text (rough approximation).
    
    Args:
        text: Input text
        
    Returns:
        Estimated token count
    """
    # Rough estimate: ~4 characters per token
    return len(text) // 4


def merge_dicts(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge two dictionaries.
    
    Args:
        base: Base dictionary
        update: Dictionary to merge in
        
    Returns:
        Merged dictionary
    """
    import copy
    result = copy.deepcopy(base)
    
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def retry_with_backoff(
    func,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0
):
    """
    Decorator for retrying a function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay between retries
        
    Returns:
        Decorated function
    """
    import time
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        delay = initial_delay
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    logging.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay} seconds..."
                    )
                    time.sleep(delay)
                    delay *= backoff_factor
        
        # If we get here, all retries failed
        logging.error(f"All {max_retries} retries failed")
        raise last_exception
    
    return wrapper


def validate_api_key(api_key: Optional[str], key_name: str = "API key") -> bool:
    """
    Validate that an API key is present and non-empty.
    
    Args:
        api_key: API key to validate
        key_name: Name of the key (for error messages)
        
    Returns:
        True if valid, False otherwise
    """
    if not api_key or not api_key.strip():
        logging.error(f"{key_name} is missing or empty")
        return False
    return True


def format_error_message(error: Exception) -> str:
    """
    Format an exception as a user-friendly error message.
    
    Args:
        error: Exception object
        
    Returns:
        Formatted error message
    """
    error_type = type(error).__name__
    error_message = str(error)
    return f"{error_type}: {error_message}"


def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes, or 0 if file doesn't exist
    """
    try:
        return Path(file_path).stat().st_size
    except FileNotFoundError:
        return 0


def create_example_config() -> Dict[str, Any]:
    """
    Create an example configuration dictionary.
    
    Returns:
        Example configuration
    """
    return {
        "agent": {
            "model": "gpt-4",
            "temperature": 0.7,
            "max_iterations": 10
        },
        "cache": {
            "enabled": True,
            "max_size": 1000
        },
        "tools": {
            "search": {"enabled": True},
            "summarization": {"enabled": True}
        }
    }
