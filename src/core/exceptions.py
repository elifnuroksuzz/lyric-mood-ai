"""
Custom Exception Classes for LyricMood-AI Application

This module defines all custom exceptions used throughout the application
to provide specific error handling and meaningful error messages.
"""

from typing import Optional, Dict, Any


class LyricMoodBaseException(Exception):
    """Base exception class for all LyricMood-AI specific exceptions"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize base exception.
        
        Args:
            message: Human readable error message
            error_code: Optional error code for programmatic handling
            context: Additional context information
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
    
    def __str__(self) -> str:
        """Return string representation of the exception"""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class ConfigurationError(LyricMoodBaseException):
    """Raised when there are configuration-related errors"""
    
    def __init__(self, message: str, missing_config: Optional[str] = None):
        super().__init__(
            message, 
            error_code="CONFIG_ERROR",
            context={"missing_config": missing_config}
        )


class APIError(LyricMoodBaseException):
    """Base class for API-related errors"""
    
    def __init__(self, message: str, api_name: str, status_code: Optional[int] = None,
                 response_data: Optional[Dict] = None):
        super().__init__(
            message,
            error_code="API_ERROR",
            context={
                "api_name": api_name,
                "status_code": status_code,
                "response_data": response_data
            }
        )
        self.api_name = api_name
        self.status_code = status_code


class GeniusAPIError(APIError):
    """Raised when Genius API operations fail"""
    
    def __init__(self, message: str, status_code: Optional[int] = None,
                 response_data: Optional[Dict] = None):
        super().__init__(
            f"Genius API Error: {message}",
            api_name="Genius",
            status_code=status_code,
            response_data=response_data
        )
        self.error_code = "GENIUS_API_ERROR"


class GroqAPIError(APIError):
    """Raised when Groq AI API operations fail"""
    
    def __init__(self, message: str, status_code: Optional[int] = None,
                 response_data: Optional[Dict] = None):
        super().__init__(
            f"Groq AI API Error: {message}",
            api_name="Groq",
            status_code=status_code, 
            response_data=response_data
        )
        self.error_code = "GROQ_API_ERROR"


class ValidationError(LyricMoodBaseException):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, field_name: Optional[str] = None,
                 invalid_value: Optional[Any] = None):
        super().__init__(
            message,
            error_code="VALIDATION_ERROR",
            context={
                "field_name": field_name,
                "invalid_value": str(invalid_value) if invalid_value else None
            }
        )
        self.field_name = field_name


class LyricsNotFoundError(LyricMoodBaseException):
    """Raised when lyrics cannot be found for a song"""
    
    def __init__(self, song_name: str, artist_name: str):
        message = f"Lyrics not found for '{song_name}' by '{artist_name}'"
        super().__init__(
            message,
            error_code="LYRICS_NOT_FOUND",
            context={
                "song_name": song_name,
                "artist_name": artist_name
            }
        )


class AnalysisError(LyricMoodBaseException):
    """Raised when emotion analysis fails"""
    
    def __init__(self, message: str, lyrics_length: Optional[int] = None,
                 analysis_stage: Optional[str] = None):
        super().__init__(
            message,
            error_code="ANALYSIS_ERROR",
            context={
                "lyrics_length": lyrics_length,
                "analysis_stage": analysis_stage
            }
        )


class FileOperationError(LyricMoodBaseException):
    """Raised when file operations fail"""
    
    def __init__(self, message: str, file_path: Optional[str] = None,
                 operation: Optional[str] = None):
        super().__init__(
            message,
            error_code="FILE_OPERATION_ERROR",
            context={
                "file_path": file_path,
                "operation": operation
            }
        )


class RateLimitError(APIError):
    """Raised when API rate limits are exceeded"""
    
    def __init__(self, api_name: str, retry_after: Optional[int] = None):
        message = f"{api_name} API rate limit exceeded"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        
        super().__init__(
            message,
            api_name=api_name,
            status_code=429
        )
        self.error_code = "RATE_LIMIT_ERROR"
        self.retry_after = retry_after


class NetworkError(LyricMoodBaseException):
    """Raised when network operations fail"""
    
    def __init__(self, message: str, url: Optional[str] = None,
                 timeout: Optional[float] = None):
        super().__init__(
            message,
            error_code="NETWORK_ERROR",
            context={
                "url": url,
                "timeout": timeout
            }
        )


class AuthenticationError(APIError):
    """Raised when API authentication fails"""
    
    def __init__(self, api_name: str, message: str = "Invalid or missing API credentials"):
        super().__init__(
            f"{api_name} Authentication Error: {message}",
            api_name=api_name,
            status_code=401
        )
        self.error_code = "AUTHENTICATION_ERROR"


class DataProcessingError(LyricMoodBaseException):
    """Raised when data processing operations fail"""
    
    def __init__(self, message: str, data_type: Optional[str] = None,
                 processing_stage: Optional[str] = None):
        super().__init__(
            message,
            error_code="DATA_PROCESSING_ERROR",
            context={
                "data_type": data_type,
                "processing_stage": processing_stage
            }
        )


class CacheError(LyricMoodBaseException):
    """Raised when cache operations fail"""
    
    def __init__(self, message: str, cache_key: Optional[str] = None,
                 operation: Optional[str] = None):
        super().__init__(
            message,
            error_code="CACHE_ERROR",
            context={
                "cache_key": cache_key,
                "operation": operation
            }
        )


# Exception mapping for HTTP status codes
HTTP_EXCEPTION_MAP = {
    400: ValidationError,
    401: AuthenticationError,
    403: AuthenticationError,
    404: LyricsNotFoundError,
    429: RateLimitError,
    500: APIError,
    502: NetworkError,
    503: APIError,
    504: NetworkError
}