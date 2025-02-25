import os
import shutil
from pathlib import Path
import logging
from datetime import datetime, timedelta
import time
import asyncio
from collections import deque

logger = logging.getLogger(__name__)

def create_temp_dir():
    """Create temporary directory for image storage."""
    temp_dir = os.path.expanduser("~/.cache/gemini_chat")
    try:
        os.makedirs(temp_dir, exist_ok=True)
        logger.info(f"Temporary directory created/verified: {temp_dir}")
        return temp_dir
    except Exception as e:
        logger.error(f"Failed to create temporary directory: {e}")
        return None

def cleanup_temp_files(max_age_hours=24):
    """Clean up temporary files older than specified hours."""
    temp_dir = Path(os.path.expanduser("~/.cache/gemini_chat"))
    if not temp_dir.exists():
        return
    
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    
    try:
        for file_path in temp_dir.glob("*"):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_time:
                    file_path.unlink()
                    logger.info(f"Cleaned up old temporary file: {file_path}")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

def sanitize_filename(filename):
    """Sanitize filename for safe storage."""
    # Remove potentially dangerous characters
    safe_chars = "".join(c if c.isalnum() or c in "._- " else "_" for c in filename)
    # Ensure the filename isn't too long
    return safe_chars[:255]

def get_unique_filename(base_path, filename):
    """Generate a unique filename in the given path."""
    path = Path(base_path)
    name_stem = Path(filename).stem
    name_suffix = Path(filename).suffix
    counter = 1
    
    while True:
        if counter == 1:
            new_name = f"{name_stem}{name_suffix}"
        else:
            new_name = f"{name_stem}_{counter}{name_suffix}"
            
        if not (path / new_name).exists():
            return new_name
        counter += 1

def format_file_size(size_in_bytes):
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.1f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.1f} TB"

class RateLimiter:
    """Rate limiter that can be used for both synchronous and asynchronous code.
    
    This class implements a token bucket algorithm for rate limiting API calls
    or other resources. It can be used in both synchronous code (using wait() method)
    and asynchronous code (using async_wait() method).
    """
    def __init__(self, max_calls: int, period: float):
        """Initialize the rate limiter.
        
        Args:
            max_calls: Maximum number of calls allowed in the period
            period: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = period
        self.call_times = deque()
        self.last_check = time.time()
        self.allowance = max_calls  # For token bucket algorithm

    def wait(self):
        """Wait if necessary to enforce rate limiting (synchronous version)."""
        current = time.time()
        time_passed = current - self.last_check
        self.last_check = current
        self.allowance += time_passed * (self.max_calls / self.period)
        if self.allowance > self.max_calls:
            self.allowance = self.max_calls
        if self.allowance < 1.0:
            sleep_time = (1.0 - self.allowance) * (self.period / self.max_calls)
            time.sleep(sleep_time)
            self.allowance = 0.0
        else:
            self.allowance -= 1.0

    async def async_wait(self):
        """Wait if necessary to enforce rate limiting (asynchronous version)."""
        current_time = time.time()
        # Clean up old timestamps
        while self.call_times and current_time - self.call_times[0] >= self.period:
            self.call_times.popleft()
        # If at capacity, wait until we can make another call
        if len(self.call_times) >= self.max_calls:
            wait_time = self.period - (current_time - self.call_times[0])
            logger.info(f"Rate limit exceeded. Waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        # Record this call
        self.call_times.append(current_time)
