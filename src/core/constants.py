"""
Application Constants for LyricMood-AI

This module contains all constants used throughout the application
including emotion categories, API endpoints, and UI elements.
"""

from enum import Enum
from typing import Dict, List


class EmotionCategory(Enum):
    """Enumeration of emotion categories for analysis"""
    HAPPINESS = "happiness"
    SADNESS = "sadness" 
    ANGER = "anger"
    FEAR = "fear"
    LOVE = "love"


class APIEndpoints:
    """API endpoint constants"""
    GENIUS_BASE_URL = "https://api.genius.com"
    GENIUS_SEARCH_ENDPOINT = "/search"
    GENIUS_SONG_ENDPOINT = "/songs/{song_id}"
    
    GROQ_BASE_URL = "https://api.groq.com/openai/v1"
    GROQ_CHAT_ENDPOINT = "/chat/completions"


class UIConstants:
    """UI and display constants"""
    
    # Colors for terminal output
    COLORS = {
        "RED": "\033[91m",
        "GREEN": "\033[92m", 
        "YELLOW": "\033[93m",
        "BLUE": "\033[94m",
        "MAGENTA": "\033[95m",
        "CYAN": "\033[96m",
        "WHITE": "\033[97m",
        "BOLD": "\033[1m",
        "UNDERLINE": "\033[4m",
        "END": "\033[0m"
    }
    
    # Emotion colors mapping
    EMOTION_COLORS = {
        EmotionCategory.HAPPINESS: "YELLOW",
        EmotionCategory.SADNESS: "BLUE", 
        EmotionCategory.ANGER: "RED",
        EmotionCategory.FEAR: "MAGENTA",
        EmotionCategory.LOVE: "MAGENTA"
    }
    
    # Progress bar characters
    PROGRESS_BAR_FILL = "█"
    PROGRESS_BAR_EMPTY = "░"
    PROGRESS_BAR_WIDTH = 50
    
    # Menu options
    MAIN_MENU_OPTIONS = [
        "1. Analyze Song Lyrics",
        "2. View Analysis History", 
        "3. Settings",
        "4. Exit"
    ]


class AnalysisConstants:
    """Constants related to emotion analysis"""
    
    # Default emotion categories with descriptions
    EMOTION_DESCRIPTIONS = {
        EmotionCategory.HAPPINESS: "Joy, contentment, positive emotions",
        EmotionCategory.SADNESS: "Melancholy, grief, sorrow",
        EmotionCategory.ANGER: "Rage, frustration, hostility", 
        EmotionCategory.FEAR: "Anxiety, worry, dread",
        EmotionCategory.LOVE: "Affection, romance, caring"
    }
    
    # Minimum confidence threshold for analysis
    MIN_CONFIDENCE_THRESHOLD = 0.1
    MAX_CONFIDENCE_THRESHOLD = 1.0
    
    # Maximum text length for analysis
    MAX_LYRICS_LENGTH = 10000
    
    # Analysis prompt template
    EMOTION_ANALYSIS_PROMPT = """
    Analyze the emotional content of the following song lyrics and provide scores 
    for each emotion category on a scale of 0-100. Be precise and consider the 
    overall emotional tone, specific words, and context.

    Emotion Categories:
    - Happiness: Joy, contentment, positive emotions
    - Sadness: Melancholy, grief, sorrow  
    - Anger: Rage, frustration, hostility
    - Fear: Anxiety, worry, dread
    - Love: Affection, romance, caring

    Lyrics:
    {lyrics}

    Please respond with only a JSON object in this exact format:
    {{
        "happiness": <score>,
        "sadness": <score>,
        "anger": <score>, 
        "fear": <score>,
        "love": <score>,
        "dominant_emotion": "<emotion_name>",
        "confidence": <overall_confidence>,
        "summary": "<brief_analysis_summary>"
    }}
    """


class FileConstants:
    """File and directory related constants"""
    
    # File extensions
    SUPPORTED_OUTPUT_FORMATS = [".txt", ".json", ".csv"]
    DEFAULT_OUTPUT_FORMAT = ".txt"
    
    # Directory names
    OUTPUT_DIR = "outputs"
    LOGS_DIR = "logs"
    CACHE_DIR = "cache"
    
    # File naming patterns
    ANALYSIS_FILE_PATTERN = "analysis_{artist}_{song}_{timestamp}.{format}"
    LOG_FILE_PATTERN = "lyricmood_{date}.log"
    
    # Maximum file size (in MB)
    MAX_OUTPUT_FILE_SIZE = 10
    
    # Cache expiry time (in seconds)
    CACHE_EXPIRY_TIME = 3600  # 1 hour


class ValidationConstants:
    """Input validation constants"""
    
    # String length limits
    MIN_SONG_NAME_LENGTH = 1
    MAX_SONG_NAME_LENGTH = 200
    MIN_ARTIST_NAME_LENGTH = 1 
    MAX_ARTIST_NAME_LENGTH = 100
    
    # Regex patterns
    VALID_SONG_PATTERN = r'^[a-zA-Z0-9\s\-\'\"\(\)\[\]\.!?]+$'
    VALID_ARTIST_PATTERN = r'^[a-zA-Z0-9\s\-\'\"\(\)\.&]+$'
    
    # Error messages
    ERROR_MESSAGES = {
        "INVALID_SONG_NAME": "Song name contains invalid characters",
        "INVALID_ARTIST_NAME": "Artist name contains invalid characters",
        "SONG_NAME_TOO_SHORT": f"Song name must be at least {MIN_SONG_NAME_LENGTH} characters",
        "SONG_NAME_TOO_LONG": f"Song name must not exceed {MAX_SONG_NAME_LENGTH} characters",
        "ARTIST_NAME_TOO_SHORT": f"Artist name must be at least {MIN_ARTIST_NAME_LENGTH} characters", 
        "ARTIST_NAME_TOO_LONG": f"Artist name must not exceed {MAX_ARTIST_NAME_LENGTH} characters"
    }


class LoggingConstants:
    """Logging configuration constants"""
    
    # Log levels
    LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    # Log format
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # Log file settings
    MAX_LOG_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    BACKUP_COUNT = 5