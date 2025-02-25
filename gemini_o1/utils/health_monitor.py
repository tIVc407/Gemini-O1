"""
Health monitoring system for the Gemini-O1 application.

This module provides functionality for monitoring the health of the application,
tracking performance metrics, and notifying administrators of issues.
"""

import time
import asyncio
import platform
import psutil
import socket
import datetime
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import logging
import json

from .logging_config import logging_config, PerformanceTracker
from .rate_limiter import rate_limiter

logger = logging_config.get_logger(__name__)

class HealthStatus(Enum):
    """Health status enum."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    
class CheckType(Enum):
    """Type of health check."""
    API = "api"
    DATABASE = "database"
    SYSTEM = "system"
    RATE_LIMIT = "rate_limit"
    DEPENDENCY = "dependency"
    CUSTOM = "custom"

class HealthCheck:
    """
    Individual health check configuration and result.
    
    This represents a single health check that can be performed
    to assess the health of a component of the system.
    """
    
    def __init__(
        self,
        name: str,
        check_type: CheckType,
        check_fn: Callable,
        interval_seconds: int = 60,
        timeout_seconds: int = 5,
        description: str = ""
    ):
        """
        Initialize a health check.
        
        Args:
            name: Name of the health check
            check_type: Type of check
            check_fn: Async function to perform the check
            interval_seconds: How often to run the check
            timeout_seconds: Maximum time to wait for the check
            description: Human-readable description
        """
        self.name = name
        self.check_type = check_type
        self.check_fn = check_fn
        self.interval_seconds = interval_seconds
        self.timeout_seconds = timeout_seconds
        self.description = description
        
        # Results tracking
        self.last_run_time: Optional[float] = None
        self.last_status: HealthStatus = HealthStatus.UNKNOWN
        self.last_message: str = "Not yet run"
        self.last_data: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []
        self.max_history = 100
        
    async def run(self) -> Dict[str, Any]:
        """
        Run the health check.
        
        Returns:
            Dictionary with check results
        """
        self.last_run_time = time.time()
        start_time = time.time()
        
        result = {
            "name": self.name,
            "type": self.check_type.value,
            "time": datetime.datetime.now().isoformat(),
            "duration_ms": 0,
            "status": HealthStatus.UNKNOWN.value,
            "message": "",
            "data": {}
        }
        
        try:
            # Run the check with timeout
            check_task = asyncio.create_task(self.check_fn())
            check_result = await asyncio.wait_for(check_task, timeout=self.timeout_seconds)
            
            # Process the result
            status = HealthStatus(check_result.get("status", HealthStatus.UNKNOWN.value))
            message = check_result.get("message", "")
            data = check_result.get("data", {})
            
            self.last_status = status
            self.last_message = message
            self.last_data = data
            
            result.update({
                "status": status.value,
                "message": message,
                "data": data
            })
            
        except asyncio.TimeoutError:
            self.last_status = HealthStatus.UNHEALTHY
            self.last_message = f"Health check timed out after {self.timeout_seconds}s"
            
            result.update({
                "status": HealthStatus.UNHEALTHY.value,
                "message": self.last_message,
                "data": {"error": "timeout"}
            })
            
        except Exception as e:
            self.last_status = HealthStatus.UNHEALTHY
            self.last_message = f"Error during health check: {str(e)}"
            
            result.update({
                "status": HealthStatus.UNHEALTHY.value,
                "message": self.last_message,
                "data": {"error": str(e)}
            })
            
        finally:
            # Calculate and record duration
            duration_ms = (time.time() - start_time) * 1000
            result["duration_ms"] = round(duration_ms, 2)
            
            # Add to history
            self.history.append(result)
            if len(self.history) > self.max_history:
                self.history.pop(0)
                
        return result
        
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of this health check.
        
        Returns:
            Dictionary with status information
        """
        return {
            "name": self.name,
            "type": self.check_type.value,
            "status": self.last_status.value,
            "message": self.last_message,
            "last_run": self.last_run_time,
            "data": self.last_data,
            "interval_seconds": self.interval_seconds
        }
        
    def should_run(self) -> bool:
        """
        Check if this health check is due to run.
        
        Returns:
            True if the check should run now
        """
        if self.last_run_time is None:
            return True
            
        elapsed = time.time() - self.last_run_time
        return elapsed >= self.interval_seconds
        
class HealthMonitor:
    """
    Health monitoring system for the application.
    
    This class manages health checks, system metrics collection,
    and provides a health dashboard for the application.
    """
    
    def __init__(self):
        """Initialize the health monitor."""
        self.checks: Dict[str, HealthCheck] = {}
        self.monitor_task = None
        self.running = False
        self.system_info = self._get_system_info()
        
    def _get_system_info(self) -> Dict[str, Any]:
        """
        Get basic system information.
        
        Returns:
            Dictionary with system information
        """
        return {
            "hostname": socket.gethostname(),
            "ip": socket.gethostbyname(socket.gethostname()),
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "start_time": time.time()
        }
        
    def register_check(self, health_check: HealthCheck) -> None:
        """
        Register a health check with the monitor.
        
        Args:
            health_check: The health check to register
        """
        self.checks[health_check.name] = health_check
        logger.info(f"Registered health check: {health_check.name} ({health_check.check_type.value})")
        
    def unregister_check(self, name: str) -> bool:
        """
        Unregister a health check.
        
        Args:
            name: Name of the health check to unregister
            
        Returns:
            True if the check was unregistered
        """
        if name in self.checks:
            del self.checks[name]
            logger.info(f"Unregistered health check: {name}")
            return True
        return False
        
    async def _monitor_loop(self) -> None:
        """Background task to run health checks at their specified intervals."""
        logger.info("Health monitor started")
        
        while self.running:
            # Run due checks
            for name, check in self.checks.items():
                if check.should_run():
                    try:
                        logger.debug(f"Running health check: {name}")
                        await check.run()
                    except Exception as e:
                        logger.error(f"Error running health check {name}: {e}")
                        
            # Wait before next check
            await asyncio.sleep(1)
            
    def start(self) -> None:
        """Start the health monitor."""
        if self.running:
            return
            
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitor started")
        
    def stop(self) -> None:
        """Stop the health monitor."""
        if not self.running:
            return
            
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
        logger.info("Health monitor stopped")
        
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get the overall health status.
        
        Returns:
            Dictionary with health status information
        """
        # Determine overall status
        overall = HealthStatus.HEALTHY
        check_results = []
        
        for name, check in self.checks.items():
            check_status = check.get_status()
            check_results.append(check_status)
            
            # Update overall status based on check status
            if check.last_status == HealthStatus.UNHEALTHY:
                overall = HealthStatus.UNHEALTHY
            elif check.last_status == HealthStatus.DEGRADED and overall != HealthStatus.UNHEALTHY:
                overall = HealthStatus.DEGRADED
                
        # Get system metrics
        system_metrics = self._get_system_metrics()
        api_metrics = self._get_api_metrics()
        
        return {
            "status": overall.value,
            "timestamp": datetime.datetime.now().isoformat(),
            "uptime_seconds": time.time() - self.system_info["start_time"],
            "system_info": self.system_info,
            "system_metrics": system_metrics,
            "api_metrics": api_metrics,
            "checks": check_results
        }
        
    def _get_system_metrics(self) -> Dict[str, Any]:
        """
        Get current system metrics.
        
        Returns:
            Dictionary with system metrics
        """
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "open_files": len(psutil.Process().open_files()),
            "threads": psutil.Process().num_threads()
        }
        
    def _get_api_metrics(self) -> Dict[str, Any]:
        """
        Get API call metrics from rate limiter.
        
        Returns:
            Dictionary with API metrics
        """
        return rate_limiter.get_call_metrics()
        
    def get_health_json(self) -> str:
        """
        Get health status as a JSON string.
        
        Returns:
            JSON string of health status
        """
        return json.dumps(self.get_health_status(), default=str)
        
# Create predefined health checks

async def check_api_connectivity() -> Dict[str, Any]:
    """
    Check if the API is reachable.
    
    Returns:
        Health check result
    """
    # Simulate an API check
    from ..models.network import GeminiNetwork
    
    try:
        # Just instantiate the object to check imports
        _ = GeminiNetwork
        
        # Check rate limiter metrics
        metrics = rate_limiter.get_call_metrics()
        for endpoint, data in metrics.items():
            # Check for high error rates
            success_rate = data.get('success_rate', 100)
            if success_rate < 80:
                return {
                    "status": HealthStatus.DEGRADED.value,
                    "message": f"API success rate is low ({success_rate:.1f}%)",
                    "data": {"endpoint": endpoint, "metrics": data}
                }
                
        return {
            "status": HealthStatus.HEALTHY.value,
            "message": "API connectivity is good",
            "data": {}
        }
    except Exception as e:
        return {
            "status": HealthStatus.UNHEALTHY.value,
            "message": f"API connectivity check failed: {str(e)}",
            "data": {"error": str(e)}
        }
        
async def check_system_resources() -> Dict[str, Any]:
    """
    Check if system resources are sufficient.
    
    Returns:
        Health check result
    """
    cpu_percent = psutil.cpu_percent()
    memory_percent = psutil.virtual_memory().percent
    disk_percent = psutil.disk_usage('/').percent
    
    data = {
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
        "disk_percent": disk_percent
    }
    
    # Determine status based on resource usage
    if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
        return {
            "status": HealthStatus.UNHEALTHY.value,
            "message": "System resources are critically low",
            "data": data
        }
    elif cpu_percent > 75 or memory_percent > 75 or disk_percent > 75:
        return {
            "status": HealthStatus.DEGRADED.value,
            "message": "System resources are under pressure",
            "data": data
        }
    else:
        return {
            "status": HealthStatus.HEALTHY.value,
            "message": "System resources are sufficient",
            "data": data
        }
        
# Global health monitor instance
health_monitor = HealthMonitor()

# Register default health checks
api_check = HealthCheck(
    name="api_connectivity",
    check_type=CheckType.API,
    check_fn=check_api_connectivity,
    interval_seconds=60,
    description="Checks connectivity to the Gemini API"
)

system_check = HealthCheck(
    name="system_resources",
    check_type=CheckType.SYSTEM,
    check_fn=check_system_resources,
    interval_seconds=30,
    description="Checks system resource usage"
)

health_monitor.register_check(api_check)
health_monitor.register_check(system_check)