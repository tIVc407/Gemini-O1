"""
Retry decorator for handling transient errors.
"""

import asyncio
import functools
import logging
from typing import Callable, TypeVar, Any

logger = logging.getLogger(__name__)

T = TypeVar('T')

def retry_on_exception(max_retries=5, initial_delay=1, backoff_factor=2):
    """
    Decorator that retries an async function on exception with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        backoff_factor: Multiplier for the delay between retries
        
    Returns:
        Decorated function that will retry on exceptions
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        logger.error(f"Max retries reached for {func.__name__}.")
                        raise
                    logger.warning(f"{e} - Retrying {func.__name__} in {delay} seconds... (Attempt {attempt}/{max_retries})")
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
        return wrapper
    return decorator