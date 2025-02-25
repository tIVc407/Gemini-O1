"""
Advanced rate limiting implementation with token bucket and exponential backoff.

This module provides a flexible rate limiter that can be used for API calls
with exponential backoff strategies for handling rate limit errors.
"""

import time
import random
import asyncio
import logging
from typing import Optional, Dict, Callable, Any, List
from collections import deque

from .logging_config import logging_config

logger = logging_config.get_logger(__name__)

class TokenBucket:
    """
    Token bucket rate limiter implementation.
    
    This implements a token bucket algorithm where tokens are added at a fixed rate
    and can be consumed when making API calls. If insufficient tokens are available,
    the call is delayed until enough tokens are available.
    """
    
    def __init__(self, max_tokens: int, refill_rate: float):
        """
        Initialize the token bucket.
        
        Args:
            max_tokens: Maximum number of tokens in the bucket
            refill_rate: Rate at which tokens are added (tokens per second)
        """
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.tokens = max_tokens
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
        
    async def _refill(self) -> None:
        """Refill the token bucket based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.refill_rate
        
        if new_tokens > 0:
            self.tokens = min(self.max_tokens, self.tokens + new_tokens)
            self.last_refill = now
            
    async def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens from the bucket, waiting if necessary.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            The delay in seconds before tokens could be acquired
        """
        if tokens > self.max_tokens:
            raise ValueError(f"Requested tokens ({tokens}) exceeds maximum ({self.max_tokens})")
            
        start_time = time.time()
        
        async with self.lock:
            await self._refill()
            
            # Calculate wait time if not enough tokens
            if self.tokens < tokens:
                deficit = tokens - self.tokens
                wait_time = deficit / self.refill_rate
                
                # Log wait information
                logger.debug(f"Rate limit: waiting {wait_time:.2f}s for {deficit:.2f} tokens")
                
                # Wait for tokens to refill
                await asyncio.sleep(wait_time)
                self.tokens = self.max_tokens - tokens
                self.last_refill = time.time()
            else:
                self.tokens -= tokens
                
        return time.time() - start_time

class AdvancedRateLimiter:
    """
    Advanced rate limiter with per-endpoint configuration and backoff strategies.
    
    This provides a flexible rate limiter that can be configured per endpoint
    with different backoff strategies for handling rate limit errors.
    """
    
    # Default jitter range for backoff
    DEFAULT_JITTER = (0.9, 1.1)
    
    def __init__(self):
        """Initialize the advanced rate limiter."""
        self.limiters: Dict[str, TokenBucket] = {}
        self.retries: Dict[str, int] = {}
        self.history: Dict[str, deque] = {}
        self.max_history = 100
        
    def configure_endpoint(
        self, 
        endpoint: str, 
        max_tokens: int, 
        refill_rate: float,
        max_retries: int = 3
    ) -> None:
        """
        Configure a rate limiter for a specific endpoint.
        
        Args:
            endpoint: Name of the endpoint
            max_tokens: Maximum number of tokens for this endpoint
            refill_rate: Rate at which tokens are added (tokens per second)
            max_retries: Maximum number of retries for this endpoint
        """
        self.limiters[endpoint] = TokenBucket(max_tokens, refill_rate)
        self.retries[endpoint] = max_retries
        self.history[endpoint] = deque(maxlen=self.max_history)
        
        logger.info(f"Configured rate limiter for {endpoint}: {max_tokens} tokens, {refill_rate} refill rate")
        
    async def wait_for_token(self, endpoint: str, tokens: int = 1) -> float:
        """
        Wait for tokens to become available for the given endpoint.
        
        Args:
            endpoint: Name of the endpoint
            tokens: Number of tokens to acquire
            
        Returns:
            Delay in seconds
        """
        if endpoint not in self.limiters:
            logger.warning(f"No rate limiter configured for {endpoint}, proceeding without rate limiting")
            return 0
            
        return await self.limiters[endpoint].acquire(tokens)
    
    def calculate_backoff_time(
        self, 
        endpoint: str, 
        retry_count: int,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: Optional[tuple] = None
    ) -> float:
        """
        Calculate backoff time with exponential strategy and jitter.
        
        Args:
            endpoint: Name of the endpoint
            retry_count: Current retry count
            base_delay: Base delay for first retry
            max_delay: Maximum delay between retries
            jitter: Tuple of (min, max) jitter multipliers
            
        Returns:
            Backoff time in seconds
        """
        if jitter is None:
            jitter = self.DEFAULT_JITTER
            
        # Calculate exponential backoff
        delay = min(base_delay * (2 ** retry_count), max_delay)
        
        # Add jitter
        jitter_multiplier = random.uniform(jitter[0], jitter[1])
        delay *= jitter_multiplier
        
        logger.debug(f"Backoff for {endpoint}: Retry #{retry_count}, delay {delay:.2f}s")
        return delay
        
    def record_call(self, endpoint: str, success: bool, status_code: Optional[int] = None) -> None:
        """
        Record a call to an endpoint for monitoring.
        
        Args:
            endpoint: Name of the endpoint
            success: Whether the call was successful
            status_code: Optional status code for the response
        """
        if endpoint not in self.history:
            self.history[endpoint] = deque(maxlen=self.max_history)
            
        self.history[endpoint].append({
            'timestamp': time.time(),
            'success': success,
            'status_code': status_code
        })
        
    def get_success_rate(self, endpoint: str, window_seconds: int = 300) -> float:
        """
        Calculate the success rate for an endpoint over a time window.
        
        Args:
            endpoint: Name of the endpoint
            window_seconds: Time window in seconds
            
        Returns:
            Success rate as a percentage (0-100)
        """
        if endpoint not in self.history or not self.history[endpoint]:
            return 100.0
            
        now = time.time()
        window_start = now - window_seconds
        
        # Filter calls within window
        recent_calls = [call for call in self.history[endpoint] 
                        if call['timestamp'] >= window_start]
                        
        if not recent_calls:
            return 100.0
            
        success_count = sum(1 for call in recent_calls if call['success'])
        return (success_count / len(recent_calls)) * 100
    
    def get_call_metrics(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metrics about API calls for monitoring.
        
        Args:
            endpoint: Optional endpoint to get metrics for (all if None)
            
        Returns:
            Dictionary with call metrics
        """
        metrics = {}
        endpoints = [endpoint] if endpoint else self.history.keys()
        
        for ep in endpoints:
            if ep not in self.history:
                continue
                
            calls = list(self.history[ep])
            if not calls:
                continue
                
            # Calculate metrics
            total_calls = len(calls)
            success_calls = sum(1 for call in calls if call['success'])
            last_minute_calls = sum(1 for call in calls 
                                   if call['timestamp'] >= time.time() - 60)
            
            metrics[ep] = {
                'total_calls': total_calls,
                'success_rate': (success_calls / total_calls) * 100 if total_calls else 100,
                'calls_last_minute': last_minute_calls,
                'most_recent': calls[-1]['timestamp'] if calls else None
            }
            
        return metrics

async def with_rate_limit(
    endpoint: str,
    func: Callable,
    rate_limiter: AdvancedRateLimiter,
    *args,
    tokens: int = 1,
    **kwargs
) -> Any:
    """
    Execute a function with rate limiting and exponential backoff.
    
    Args:
        endpoint: Name of the endpoint for rate limiting
        func: Function to execute
        rate_limiter: Rate limiter instance
        *args: Arguments to pass to the function
        tokens: Number of tokens to consume
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the function
        
    Raises:
        Exception: If max retries are exceeded
    """
    if endpoint not in rate_limiter.retries:
        logger.warning(f"No rate limit configuration for {endpoint}, using defaults")
        rate_limiter.configure_endpoint(endpoint, 10, 1.0, 3)
        
    max_retries = rate_limiter.retries.get(endpoint, 3)
    retry_count = 0
    
    while True:
        # Wait for token
        delay = await rate_limiter.wait_for_token(endpoint, tokens)
        if delay > 0.1:
            logger.info(f"Rate limited {endpoint}: waited {delay:.2f}s for {tokens} token(s)")
            
        try:
            # Call the function
            result = await func(*args, **kwargs)
            
            # Record successful call
            rate_limiter.record_call(endpoint, True)
            
            return result
            
        except Exception as e:
            # Check if it's a rate limit error
            is_rate_limit_error = any(error_text in str(e).lower() 
                                     for error_text in ['rate limit', 'too many requests', '429'])
            
            # Record failed call
            status_code = 429 if is_rate_limit_error else None
            rate_limiter.record_call(endpoint, False, status_code)
            
            # If not a rate limit error or max retries exceeded, re-raise
            if not is_rate_limit_error or retry_count >= max_retries:
                logger.error(f"Failed call to {endpoint}: {e}")
                raise
                
            # Calculate backoff time
            retry_count += 1
            backoff_time = rate_limiter.calculate_backoff_time(endpoint, retry_count)
            
            logger.warning(
                f"Rate limit error on {endpoint}, retry {retry_count}/{max_retries} "
                f"after {backoff_time:.2f}s backoff"
            )
            
            # Wait before retry
            await asyncio.sleep(backoff_time)
            
# Global rate limiter instance
rate_limiter = AdvancedRateLimiter()