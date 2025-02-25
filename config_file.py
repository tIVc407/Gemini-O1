import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env file if it exists
load_dotenv()

# API Configuration
API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyACCbhYudSe-lQzqHZp_yi3KSMbka5kTG8")

# Model Configuration
MODELS = {
    "normal": "gemini-1.5-flash",
    "thinking": "gemini-2.0-flash-thinking-exp"
}

# Rate Limiting
RATE_LIMIT = {
    "max_calls": 15,
    "period": 60  # in seconds
}

# Logging Configuration
LOG_CONFIG = {
    "level": logging.INFO,
    "format": '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    "file": "app.log"
}

def get_model_name(model_type):
    """Get the model name based on the model type."""
    return MODELS.get(model_type, MODELS["normal"])

class AppConfig:
    """Application configuration settings."""
    
    # Window settings
    WINDOW_TITLE = "Gemini Chat Interface"
    DEFAULT_WIDTH = 1000
    DEFAULT_HEIGHT = 800
    
    # UI settings
    FONT_FAMILY = "Segoe UI"
    FONT_SIZE = 10
    MAX_MESSAGE_WIDTH = 600
    
    # File settings
    TEMP_DIR = "~/.cache/gemini_chat"
    SUPPORTED_IMAGE_FORMATS = ('.png', '.jpg', '.jpeg')
    
    # Style settings
    COLORS = {
        'background': '#121212',
        'header': '#1E1E1E',
        'input': '#2D2D2D',
        'user_message': '#4CAF50',
        'bot_message': '#121212',
        'text': '#FFFFFF',
        'disabled': '#666666'
    }
    
    # Message settings
    MAX_HISTORY = 100
    TYPING_INDICATOR = "_thinking..._"
    WELCOME_MESSAGE = """👋 Hello! I'm your AI assistant. I can help answer questions 
                        and analyze images. Try dropping an image or using the upload button!"""
