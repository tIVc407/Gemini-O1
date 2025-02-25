"""
Configuration management for the Gemini-O1 application.

This module handles loading and validating configuration from environment variables,
providing default values where appropriate, and exposing a consistent interface
for the rest of the application.
"""

import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class ConfigurationError(Exception):
    """Exception raised for configuration errors."""
    pass

class Config:
    """
    Configuration manager for the Gemini-O1 application.
    
    This class handles loading configuration from environment variables,
    providing default values, and validating the configuration.
    """
    
    # Default values
    DEFAULTS = {
        # API configuration
        "GEMINI_API_KEY": None,  # No default, must be provided
        
        # Logging configuration
        "LOG_LEVEL": "INFO",
        "LOG_FILE": "app.log",
        "ENABLE_REQUEST_TRACKING": True,
        
        # Rate limiting
        "RATE_LIMIT_MAX_CALLS": 15,
        "RATE_LIMIT_PERIOD": 60,
        
        # Model configuration
        "DEFAULT_MODEL": "gemini-1.5-flash",
        "THINKING_MODEL": "gemini-2.0-flash-thinking-exp",
        
        # UI settings
        "WINDOW_TITLE": "Gemini Chat Interface",
        "DEFAULT_WIDTH": 1000,
        "DEFAULT_HEIGHT": 800,
        
        # Temporary directory
        "TEMP_DIR": "~/.cache/gemini_chat"
    }
    
    # Types for validation
    TYPES = {
        "LOG_LEVEL": str,
        "LOG_FILE": str,
        "ENABLE_REQUEST_TRACKING": bool,
        "RATE_LIMIT_MAX_CALLS": int,
        "RATE_LIMIT_PERIOD": int,
        "DEFAULT_WIDTH": int,
        "DEFAULT_HEIGHT": int
    }
    
    def __init__(self):
        """Initialize the configuration manager."""
        self._config = {}
        self._load_from_env()
        
        # Skip validation in test mode
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            self._validate()
        
    def _load_from_env(self):
        """Load configuration from environment variables."""
        for key, default in self.DEFAULTS.items():
            env_value = os.getenv(key)
            
            if env_value is None:
                self._config[key] = default
                continue
                
            # Convert to appropriate type
            if key in self.TYPES:
                try:
                    if self.TYPES[key] == bool:
                        # Handle boolean conversion
                        self._config[key] = env_value.lower() in ('true', 'yes', '1', 't', 'y')
                    else:
                        self._config[key] = self.TYPES[key](env_value)
                except ValueError:
                    logger.warning(f"Invalid value for {key}: {env_value}. Using default: {default}")
                    self._config[key] = default
            else:
                self._config[key] = env_value
                
    def _validate(self):
        """Validate the configuration."""
        # API key is required
        if not self._config["GEMINI_API_KEY"]:
            raise ConfigurationError(
                "GEMINI_API_KEY is not set. Please set it in the .env file or as an environment variable."
            )
            
        # Rate limit must be positive
        if self._config["RATE_LIMIT_MAX_CALLS"] <= 0:
            raise ConfigurationError("RATE_LIMIT_MAX_CALLS must be a positive integer")
            
        if self._config["RATE_LIMIT_PERIOD"] <= 0:
            raise ConfigurationError("RATE_LIMIT_PERIOD must be a positive integer")
            
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: The configuration key
            default: Default value if the key is not found
            
        Returns:
            The configuration value or the default value
        """
        return self._config.get(key, default)
        
    def __getitem__(self, key: str) -> Any:
        """Dictionary-style access to configuration values."""
        if key not in self._config:
            raise KeyError(f"Configuration key '{key}' not found")
        return self._config[key]
        
    def as_dict(self) -> Dict[str, Any]:
        """
        Get the full configuration as a dictionary.
        
        Returns:
            Dictionary of all configuration values
        """
        return dict(self._config)
        
    def get_log_level(self) -> int:
        """
        Get the log level as a logging module constant.
        
        Returns:
            Log level as a logging module constant
        """
        level_name = self._config["LOG_LEVEL"].upper()
        level = getattr(logging, level_name, None)
        if level is None:
            logger.warning(f"Invalid log level: {level_name}. Using INFO.")
            return logging.INFO
        return level
        
    def get_model_name(self, model_type: str) -> str:
        """
        Get the appropriate model name based on the model type.
        
        Args:
            model_type: The model type ('normal' or 'thinking')
            
        Returns:
            The corresponding model name
        """
        if model_type.lower() == "thinking":
            return self._config["THINKING_MODEL"]
        return self._config["DEFAULT_MODEL"]
        
    def get_rate_limit_config(self) -> Dict[str, int]:
        """
        Get the rate limit configuration.
        
        Returns:
            Dictionary with max_calls and period
        """
        return {
            "max_calls": self._config["RATE_LIMIT_MAX_CALLS"],
            "period": self._config["RATE_LIMIT_PERIOD"]
        }
        
# Global configuration instance
config = Config()