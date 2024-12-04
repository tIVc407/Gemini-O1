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
