Utility Modules
==============

Configuration
-----------

.. py:module:: gemini_o1.utils.config

.. py:class:: Config

   Configuration manager for the Gemini-O1 application.
   
   This class handles loading configuration from environment variables,
   providing default values, and validating the configuration.

   .. py:method:: get(key, default=None)

      Get a configuration value.
      
      :param key: The configuration key
      :param default: Default value if the key is not found
      :return: The configuration value or the default value
      :rtype: Any

   .. py:method:: as_dict()

      Get the full configuration as a dictionary.
      
      :return: Dictionary of all configuration values
      :rtype: dict

Logging Configuration
-------------------

.. py:module:: gemini_o1.utils.logging_config

.. py:class:: LoggingConfig

   Configure logging for the application.
   
   .. py:method:: setup_logging(level=None, log_file=None, enable_console=True, enable_request_tracking=None, enable_structured_logging=False, max_log_size_mb=10, backup_count=5)

      Set up logging for the application.
      
      :param level: Log level to use (defaults to config value)
      :param log_file: Path to log file (defaults to config value)
      :param enable_console: Whether to log to console
      :param enable_request_tracking: Whether to track request IDs (defaults to config value)
      :param enable_structured_logging: Whether to use JSON structured logging
      :param max_log_size_mb: Maximum log file size in MB before rotation
      :param backup_count: Number of backup logs to keep

   .. py:method:: set_request_id(request_id=None)

      Set the request ID for the current context.
      
      :param request_id: The request ID to use, or None to generate a new one
      
.. py:class:: PerformanceTracker

   Utility to track and log performance metrics.
   
   .. py:method:: start()

      Start timing the operation.
      
   .. py:method:: checkpoint(name)

      Record a checkpoint in the operation.
      
      :param name: Name of the checkpoint
      :return: Time since the start in seconds
      :rtype: float
      
   .. py:method:: stop(log_level=logging.DEBUG)

      Stop timing and log the results.
      
      :param log_level: Log level to use
      :return: Dictionary with timing information
      :rtype: dict

Rate Limiting
------------

.. py:module:: gemini_o1.utils.rate_limiter

.. py:class:: TokenBucket

   Token bucket rate limiter implementation.
   
   This implements a token bucket algorithm where tokens are added at a fixed rate
   and can be consumed when making API calls. If insufficient tokens are available,
   the call is delayed until enough tokens are available.
   
   .. py:method:: acquire(tokens=1)

      Acquire tokens from the bucket, waiting if necessary.
      
      :param tokens: Number of tokens to acquire
      :return: The delay in seconds before tokens could be acquired
      :rtype: float

.. py:class:: AdvancedRateLimiter

   Advanced rate limiter with per-endpoint configuration and backoff strategies.
   
   This provides a flexible rate limiter that can be configured per endpoint
   with different backoff strategies for handling rate limit errors.
   
   .. py:method:: configure_endpoint(endpoint, max_tokens, refill_rate, max_retries=3)

      Configure a rate limiter for a specific endpoint.
      
      :param endpoint: Name of the endpoint
      :param max_tokens: Maximum number of tokens for this endpoint
      :param refill_rate: Rate at which tokens are added (tokens per second)
      :param max_retries: Maximum number of retries for this endpoint
      
   .. py:method:: get_call_metrics(endpoint=None)

      Get metrics about API calls for monitoring.
      
      :param endpoint: Optional endpoint to get metrics for (all if None)
      :return: Dictionary with call metrics
      :rtype: dict

Health Monitoring
---------------

.. py:module:: gemini_o1.utils.health_monitor

.. py:class:: HealthMonitor

   Health monitoring system for the application.
   
   This class manages health checks, system metrics collection,
   and provides a health dashboard for the application.
   
   .. py:method:: register_check(health_check)

      Register a health check with the monitor.
      
      :param health_check: The health check to register

   .. py:method:: start()

      Start the health monitor.
      
   .. py:method:: get_health_status()

      Get the overall health status.
      
      :return: Dictionary with health status information
      :rtype: dict

.. py:class:: HealthCheck

   Individual health check configuration and result.
   
   This represents a single health check that can be performed
   to assess the health of a component of the system.
   
   .. py:method:: run()

      Run the health check.
      
      :return: Dictionary with check results
      :rtype: dict