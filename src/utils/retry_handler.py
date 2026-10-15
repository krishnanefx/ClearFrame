"""Retry logic with exponential backoff for API calls."""
import time
import functools
from typing import Callable, Type, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    rate_limit_exceptions: Tuple[Type[Exception], ...] = (),
    rate_limit_delay: float = 10.0,
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
        rate_limit_exceptions: Specific exceptions indicating rate limiting
        rate_limit_delay: Fixed delay for rate limit errors
        
    Example:
        @retry_with_backoff(max_retries=3, exceptions=(requests.HTTPError,))
        def fetch_data(url):
            return requests.get(url).json()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except rate_limit_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Rate limit hit in {func.__name__} (attempt {attempt + 1}/{max_retries + 1}). "
                            f"Waiting {rate_limit_delay}s..."
                        )
                        time.sleep(rate_limit_delay)
                    else:
                        logger.error(f"Rate limit exceeded after {max_retries + 1} attempts in {func.__name__}")
                        raise
                        
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        actual_delay = min(delay, max_delay)
                        logger.warning(
                            f"Error in {func.__name__} (attempt {attempt + 1}/{max_retries + 1}): {str(e)}. "
                            f"Retrying in {actual_delay:.1f}s..."
                        )
                        time.sleep(actual_delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"Failed after {max_retries + 1} attempts in {func.__name__}: {str(e)}")
                        raise
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


class RateLimitError(Exception):
    """Exception for rate limit errors."""
    pass


class APIError(Exception):
    """General API error."""
    pass


def safe_api_call(func: Callable, fallback_value=None, log_errors: bool = True) -> Callable:
    """
    Decorator that wraps API calls with error handling and optional fallback.
    
    Args:
        func: Function to wrap
        fallback_value: Value to return if all retries fail (default: None)
        log_errors: Whether to log errors
        
    Example:
        @safe_api_call(fallback_value={'error': 'Service unavailable'})
        def fetch_external_data():
            return external_api.get_data()
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if log_errors:
                logger.error(f"Error in {func.__name__}: {str(e)}")
            if fallback_value is not None:
                logger.info(f"Returning fallback value for {func.__name__}")
                return fallback_value
            raise
    return wrapper
