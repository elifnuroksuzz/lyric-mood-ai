"""
Configuration Manager for LyricMood-AI Application

This module handles all configuration management including environment variables,
API keys, and application settings.
"""

import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing"""
    pass


class ConfigManager:
    """
    Centralized configuration management for the application.
    
    Handles environment variables, API keys, and application settings
    with validation and error handling.
    """
    
    def __init__(self, env_file: str = ".env"):
        """
        Initialize configuration manager.
        
        Args:
            env_file: Path to environment file
        """
        self.env_file = env_file
        self._load_environment()
        self._validate_required_configs()
        
    def _load_environment(self) -> None:
        """Load environment variables from .env file"""
        if Path(self.env_file).exists():
            load_dotenv(self.env_file)
            logging.info(f"Environment loaded from {self.env_file}")
        else:
            logging.warning(f"Environment file {self.env_file} not found")
    
    def _validate_required_configs(self) -> None:
        """Validate that all required configuration values are present"""
        required_vars = [
            "GENIUS_ACCESS_TOKEN",
            "GROQ_API_KEY"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not self.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return os.getenv(key, default)
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer configuration value"""
        try:
            return int(self.get(key, default))
        except (ValueError, TypeError):
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean configuration value"""
        value = self.get(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    @property
    def genius_token(self) -> str:
        """Get Genius API access token"""
        return self.get("GENIUS_ACCESS_TOKEN")
    
    @property
    def groq_api_key(self) -> str:
        """Get Groq API key"""
        return self.get("GROQ_API_KEY")
    
    @property
    def app_name(self) -> str:
        """Get application name"""
        return self.get("APP_NAME", "LyricMood-AI")
    
    @property
    def app_version(self) -> str:
        """Get application version"""
        return self.get("APP_VERSION", "1.0.0")
    
    @property
    def log_level(self) -> str:
        """Get logging level"""
        return self.get("LOG_LEVEL", "INFO")
    
    @property
    def output_directory(self) -> Path:
        """Get output directory path"""
        return Path(self.get("OUTPUT_DIRECTORY", "./outputs"))
    
    @property
    def genius_rate_limit(self) -> int:
        """Get Genius API rate limit"""
        return self.get_int("GENIUS_RATE_LIMIT", 5000)
    
    @property
    def groq_rate_limit(self) -> int:
        """Get Groq API rate limit"""
        return self.get_int("GROQ_RATE_LIMIT", 1000)
    
    @property
    def enable_file_output(self) -> bool:
        """Check if file output is enabled"""
        return self.get_bool("ENABLE_FILE_OUTPUT", True)
    
    @property
    def enable_detailed_logging(self) -> bool:
        """Check if detailed logging is enabled"""
        return self.get_bool("ENABLE_DETAILED_LOGGING", True)
    
    @property
    def enable_color_output(self) -> bool:
        """Check if color output is enabled"""
        return self.get_bool("ENABLE_COLOR_OUTPUT", True)
    
    def get_all_config(self) -> Dict[str, Any]:
        """
        Get all configuration as dictionary (excluding sensitive data).
        
        Returns:
            Dictionary of configuration values
        """
        return {
            "app_name": self.app_name,
            "app_version": self.app_version,
            "log_level": self.log_level,
            "output_directory": str(self.output_directory),
            "genius_rate_limit": self.genius_rate_limit,
            "groq_rate_limit": self.groq_rate_limit,
            "enable_file_output": self.enable_file_output,
            "enable_detailed_logging": self.enable_detailed_logging,
            "enable_color_output": self.enable_color_output
        }


# Global configuration instance
config = ConfigManager()