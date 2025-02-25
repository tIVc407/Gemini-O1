#!/usr/bin/env python3
"""
Improved logging example for Gemini-O1

This script demonstrates enhanced logging capabilities
with colorized output, log rotation, and custom formatters.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
import time
import colorlog
from datetime import datetime

# Add parent directory to path so we can import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_file import LOG_CONFIG

class EnhancedLogger:
    """Enhanced logging with colorized console output and file rotation"""
    
    def __init__(self, name=None, log_file="enhanced_log.log", level=logging.INFO):
        self.name = name or __name__
        self.log_file = log_file
        self.level = level
        self.logger = self._setup_logger()
        
    def _setup_logger(self):
        """Set up logger with console and file handlers"""
        logger = logging.getLogger(self.name)
        logger.setLevel(self.level)
        
        # Clear existing handlers
        if logger.handlers:
            logger.handlers.clear()
            
        # Console handler with colors
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.level)
        
        # Color formatter
        color_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        
        console_handler.setFormatter(color_formatter)
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(self.level)
        
        # File formatter (no colors)
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        file_handler.setFormatter(file_formatter)
        
        # Add handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        return logger
    
    def debug(self, message):
        self.logger.debug(message)
        
    def info(self, message):
        self.logger.info(message)
        
    def warning(self, message):
        self.logger.warning(message)
        
    def error(self, message):
        self.logger.error(message)
        
    def critical(self, message):
        self.logger.critical(message)
        
    def log_api_call(self, endpoint, status_code, elapsed_time, payload=None):
        """Log an API call with details"""
        message = f"API CALL - Endpoint: {endpoint} | Status: {status_code} | Time: {elapsed_time:.2f}s"
        if payload:
            message += f" | Payload: {str(payload)[:100]}..."
        self.info(message)
        
    def log_network_event(self, event_type, details):
        """Log network events with structured details"""
        message = f"NETWORK EVENT - Type: {event_type} | {details}"
        self.info(message)
        
    def log_instance_activity(self, instance_id, activity, result=None):
        """Log instance activity"""
        message = f"INSTANCE {instance_id} - Activity: {activity}"
        if result:
            message += f" | Result: {str(result)[:100]}..."
        self.info(message)


def demonstrate_logging():
    """Run a demonstration of the enhanced logging"""
    logger = EnhancedLogger(name="demo_logger", log_file="enhanced_demo.log")
    
    print("\n=== Enhanced Logging Demonstration ===\n")
    
    # Basic log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
    # API call logs
    logger.log_api_call("/api/send_message", 200, 1.23, {"message": "Hello, Gemini!"})
    logger.log_api_call("/api/instances", 200, 0.45)
    logger.log_api_call("/api/network/stats", 500, 0.32, {"error": "Server error"})
    
    # Network events
    logger.log_network_event("INSTANCE_CREATED", "New instance 'researcher' created with ID inst_1")
    logger.log_network_event("CONNECTION_ESTABLISHED", "Connected mother -> inst_1")
    logger.log_network_event("TASK_COMPLETED", "Task 'research quantum physics' completed by inst_1")
    
    # Instance activities
    logger.log_instance_activity("mother", "Initializing network")
    logger.log_instance_activity("inst_1", "Processing query", "Found 5 relevant research papers")
    logger.log_instance_activity("inst_2", "Generating response", "Completed in 2.3 seconds")
    
    print("\n=== Log file written to enhanced_demo.log ===\n")


def simulate_network_activity():
    """Simulate a sequence of network activities with logging"""
    logger = EnhancedLogger(name="gemini_network", log_file="network_simulation.log")
    
    print("\n=== Simulating Network Activity ===\n")
    
    # Start network
    logger.info("Starting Gemini-O1 network")
    logger.log_network_event("NETWORK_INITIALIZED", "Mother node created with ID 'mother'")
    time.sleep(0.5)
    
    # Process a query
    query = "Analyze the impact of quantum computing on cryptography"
    logger.info(f"Received query: {query}")
    logger.log_api_call("/api/send_message", 200, 0.3, {"message": query})
    time.sleep(0.5)
    
    # Mother node creates instances
    logger.log_network_event("INSTANCE_CREATED", "New instance 'researcher' created with ID inst_1")
    logger.log_network_event("INSTANCE_CREATED", "New instance 'analyst' created with ID inst_2")
    logger.log_network_event("INSTANCE_CREATED", "New instance 'writer' created with ID inst_3")
    time.sleep(0.5)
    
    # Establish connections
    logger.log_network_event("CONNECTION_ESTABLISHED", "Connected mother -> inst_1")
    logger.log_network_event("CONNECTION_ESTABLISHED", "Connected mother -> inst_2")
    logger.log_network_event("CONNECTION_ESTABLISHED", "Connected mother -> inst_3")
    logger.log_network_event("CONNECTION_ESTABLISHED", "Connected inst_1 -> inst_2")
    time.sleep(0.5)
    
    # Instance activities
    logger.log_instance_activity("inst_1", "Researching quantum computing and cryptography")
    time.sleep(1)
    logger.log_instance_activity("inst_1", "Completed research", "Found information on Shor's algorithm and post-quantum cryptography")
    time.sleep(0.3)
    
    logger.log_instance_activity("inst_2", "Analyzing research findings")
    time.sleep(0.8)
    logger.log_instance_activity("inst_2", "Completed analysis", "Identified key vulnerabilities in RSA due to quantum computing")
    time.sleep(0.3)
    
    logger.log_instance_activity("inst_3", "Synthesizing final response")
    time.sleep(0.7)
    logger.log_instance_activity("inst_3", "Completed synthesis", "Generated comprehensive report on quantum computing threats")
    time.sleep(0.3)
    
    # Final response
    logger.log_network_event("RESPONSE_GENERATED", "Final response synthesized by mother node")
    logger.log_api_call("/api/network/stats", 200, 0.2)
    
    print("\n=== Simulation completed, log written to network_simulation.log ===\n")


if __name__ == "__main__":
    # Run demonstrations
    demonstrate_logging()
    time.sleep(1)
    simulate_network_activity()