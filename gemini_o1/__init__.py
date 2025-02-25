"""
Gemini-O1: An Enhanced Multi-Agent Network Using Gemini API.

This package provides a framework for creating and coordinating specialized AI instances
that collaborate on complex tasks using Google's Gemini API.
"""

from .models.network import GeminiNetwork
from .models.instance import GeminiInstance

__version__ = "1.0.0"
__all__ = ["GeminiNetwork", "GeminiInstance"]