"""
Input Validation System for LyricMood-AI Application

This module provides comprehensive validation for user inputs, API responses,
and data integrity checks throughout the application.
"""

import re
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import json

from ..core.constants import ValidationConstants, EmotionCategory
from ..core.exceptions import ValidationError
from ..utils.logger import logger


class InputValidator:
    """Comprehensive input validation class"""
    
    @staticmethod
    def validate_song_name(song_name: str) -> str:
        """
        Validate and sanitize song name input.
        
        Args:
            song_name: Raw song name input
            
        Returns:
            Cleaned and validated song name
            
        Raises:
            ValidationError: If song name is invalid
        """
        if not song_name or not isinstance(song_name, str):
            raise ValidationError(
                "Song name is required and must be a string",
                field_name="song_name",
                invalid_value=song_name
            )
        
        # Clean the input
        cleaned_name = song_name.strip()
        
        # Check length constraints
        if len(cleaned_name) < ValidationConstants.MIN_SONG_NAME_LENGTH:
            raise ValidationError(
                ValidationConstants.ERROR_MESSAGES["SONG_NAME_TOO_SHORT"],
                field_name="song_name",
                invalid_value=song_name
            )
        
        if len(cleaned_name) > ValidationConstants.MAX_SONG_NAME_LENGTH:
            raise ValidationError(
                ValidationConstants.ERROR_MESSAGES["SONG_NAME_TOO_LONG"],
                field_name="song_name", 
                invalid_value=song_name
            )
        
        # Check for valid characters
        if not re.match(ValidationConstants.VALID_SONG_PATTERN, cleaned_name):
            raise ValidationError(
                ValidationConstants.ERROR_MESSAGES["INVALID_SONG_NAME"],
                field_name="song_name",
                invalid_value=song_name
            )
        
        logger.debug(f"Song name validated successfully: '{cleaned_name}'")
        return cleaned_name
    
    @staticmethod
    def validate_artist_name(artist_name: str) -> str:
        """
        Validate and sanitize artist name input.
        
        Args:
            artist_name: Raw artist name input
            
        Returns:
            Cleaned and validated artist name
            
        Raises:
            ValidationError: If artist name is invalid
        """
        if not artist_name or not isinstance(artist_name, str):
            raise ValidationError(
                "Artist name is required and must be a string",
                field_name="artist_name",
                invalid_value=artist_name
            )
        
        # Clean the input
        cleaned_name = artist_name.strip()
        
        # Check length constraints
        if len(cleaned_name) < ValidationConstants.MIN_ARTIST_NAME_LENGTH:
            raise ValidationError(
                ValidationConstants.ERROR_MESSAGES["ARTIST_NAME_TOO_SHORT"],
                field_name="artist_name",
                invalid_value=artist_name
            )
        
        if len(cleaned_name) > ValidationConstants.MAX_ARTIST_NAME_LENGTH:
            raise ValidationError(
                ValidationConstants.ERROR_MESSAGES["ARTIST_NAME_TOO_LONG"],
                field_name="artist_name",
                invalid_value=artist_name
            )
        
        # Check for valid characters
        if not re.match(ValidationConstants.VALID_ARTIST_PATTERN, cleaned_name):
            raise ValidationError(
                ValidationConstants.ERROR_MESSAGES["INVALID_ARTIST_NAME"],
                field_name="artist_name",
                invalid_value=artist_name
            )
        
        logger.debug(f"Artist name validated successfully: '{cleaned_name}'")
        return cleaned_name
    
    @staticmethod
    def validate_lyrics_content(lyrics: str) -> str:
        """
        Validate lyrics content for analysis.
        
        Args:
            lyrics: Raw lyrics text
            
        Returns:
            Cleaned and validated lyrics
            
        Raises:
            ValidationError: If lyrics are invalid
        """
        if not lyrics or not isinstance(lyrics, str):
            raise ValidationError(
                "Lyrics content is required and must be a string",
                field_name="lyrics",
                invalid_value=type(lyrics).__name__
            )
        
        # Clean the lyrics
        cleaned_lyrics = lyrics.strip()
        
        if not cleaned_lyrics:
            raise ValidationError(
                "Lyrics cannot be empty after cleaning",
                field_name="lyrics"
            )
        
        # Check length constraints
        if len(cleaned_lyrics) > ValidationConstants.MAX_LYRICS_LENGTH:
            raise ValidationError(
                f"Lyrics too long. Maximum {ValidationConstants.MAX_LYRICS_LENGTH} characters allowed",
                field_name="lyrics",
                invalid_value=f"{len(cleaned_lyrics)} characters"
            )
        
        # Basic content validation - ensure it's not just whitespace or special chars
        words = re.findall(r'\b\w+\b', cleaned_lyrics)
        if len(words) < 5:  # Minimum word count
            raise ValidationError(
                "Lyrics must contain at least 5 words for meaningful analysis",
                field_name="lyrics",
                invalid_value=f"{len(words)} words found"
            )
        
        logger.debug(f"Lyrics validated successfully: {len(cleaned_lyrics)} characters, {len(words)} words")
        return cleaned_lyrics


class EmotionAnalysisValidator:
    """Validator for emotion analysis results"""
    
    @staticmethod
    def validate_emotion_scores(emotion_scores: Dict[str, float]) -> Dict[str, float]:
        """
        Validate emotion analysis scores.
        
        Args:
            emotion_scores: Dictionary of emotion scores
            
        Returns:
            Validated emotion scores
            
        Raises:
            ValidationError: If scores are invalid
        """
        if not isinstance(emotion_scores, dict):
            raise ValidationError(
                "Emotion scores must be a dictionary",
                field_name="emotion_scores",
                invalid_value=type(emotion_scores).__name__
            )
        
        validated_scores = {}
        expected_emotions = {e.value for e in EmotionCategory}
        
        # Check if all required emotions are present
        missing_emotions = expected_emotions - set(emotion_scores.keys())
        if missing_emotions:
            raise ValidationError(
                f"Missing emotion scores: {', '.join(missing_emotions)}",
                field_name="emotion_scores",
                invalid_value=list(emotion_scores.keys())
            )
        
        # Validate each score
        for emotion, score in emotion_scores.items():
            if emotion not in expected_emotions:
                logger.warning(f"Unexpected emotion category: {emotion}")
                continue
            
            # Validate score type and range
            try:
                score_float = float(score)
            except (ValueError, TypeError):
                raise ValidationError(
                    f"Invalid score type for {emotion}: must be numeric",
                    field_name=f"emotion_scores.{emotion}",
                    invalid_value=score
                )
            
            if not (0.0 <= score_float <= 100.0):
                raise ValidationError(
                    f"Score for {emotion} must be between 0 and 100",
                    field_name=f"emotion_scores.{emotion}",
                    invalid_value=score_float
                )
            
            validated_scores[emotion] = round(score_float, 2)
        
        logger.debug(f"Emotion scores validated successfully: {validated_scores}")
        return validated_scores
    
    @staticmethod
    def validate_dominant_emotion(dominant_emotion: str, 
                                emotion_scores: Dict[str, float]) -> str:
        """
        Validate dominant emotion determination.
        
        Args:
            dominant_emotion: Claimed dominant emotion
            emotion_scores: All emotion scores
            
        Returns:
            Validated dominant emotion
            
        Raises:
            ValidationError: If dominant emotion is invalid
        """
        if not isinstance(dominant_emotion, str):
            raise ValidationError(
                "Dominant emotion must be a string",
                field_name="dominant_emotion",
                invalid_value=type(dominant_emotion).__name__
            )
        
        dominant_emotion = dominant_emotion.lower().strip()
        expected_emotions = {e.value for e in EmotionCategory}
        
        if dominant_emotion not in expected_emotions:
            raise ValidationError(
                f"Invalid dominant emotion: {dominant_emotion}",
                field_name="dominant_emotion",
                invalid_value=dominant_emotion
            )
        
        # Verify it's actually the highest scoring emotion
        if emotion_scores:
            actual_dominant = max(emotion_scores.keys(), 
                                key=lambda x: emotion_scores[x])
            if dominant_emotion != actual_dominant:
                logger.warning(
                    f"Dominant emotion mismatch: claimed '{dominant_emotion}', "
                    f"actual highest '{actual_dominant}'"
                )
        
        logger.debug(f"Dominant emotion validated: {dominant_emotion}")
        return dominant_emotion
    
    @staticmethod
    def validate_confidence_score(confidence: Union[int, float]) -> float:
        """
        Validate confidence score.
        
        Args:
            confidence: Confidence score
            
        Returns:
            Validated confidence score
            
        Raises:
            ValidationError: If confidence is invalid
        """
        try:
            confidence_float = float(confidence)
        except (ValueError, TypeError):
            raise ValidationError(
                "Confidence must be numeric",
                field_name="confidence",
                invalid_value=confidence
            )
        
        if not (0.0 <= confidence_float <= 1.0):
            raise ValidationError(
                "Confidence must be between 0.0 and 1.0",
                field_name="confidence", 
                invalid_value=confidence_float
            )
        
        return round(confidence_float, 3)


class APIResponseValidator:
    """Validator for API responses"""
    
    @staticmethod
    def validate_genius_search_response(response_data: Dict[str, Any]) -> bool:
        """
        Validate Genius API search response format.
        
        Args:
            response_data: API response data
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If response format is invalid
        """
        if not isinstance(response_data, dict):
            raise ValidationError(
                "Genius API response must be a dictionary",
                field_name="api_response"
            )
        
        # Check for required fields
        if 'response' not in response_data:
            raise ValidationError(
                "Missing 'response' field in Genius API response",
                field_name="api_response"
            )
        
        response_section = response_data['response']
        if 'hits' not in response_section:
            raise ValidationError(
                "Missing 'hits' field in Genius API response",
                field_name="api_response.response"
            )
        
        return True
    
    @staticmethod
    def validate_groq_analysis_response(response_text: str) -> Dict[str, Any]:
        """
        Validate and parse Groq AI analysis response.
        
        Args:
            response_text: Raw response text from Groq
            
        Returns:
            Parsed and validated response data
            
        Raises:
            ValidationError: If response is invalid
        """
        if not isinstance(response_text, str):
            raise ValidationError(
                "Groq response must be a string",
                field_name="groq_response"
            )
        
        # Try to extract JSON from response
        try:
            # Remove any markdown formatting
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            response_data = json.loads(cleaned_text.strip())
        except json.JSONDecodeError as e:
            raise ValidationError(
                f"Invalid JSON in Groq response: {str(e)}",
                field_name="groq_response",
                invalid_value=response_text[:100] + "..." if len(response_text) > 100 else response_text
            )
        
        # Validate required fields
        required_fields = ['happiness', 'sadness', 'anger', 'fear', 'love', 
                          'dominant_emotion', 'confidence']
        
        for field in required_fields:
            if field not in response_data:
                raise ValidationError(
                    f"Missing required field '{field}' in Groq response",
                    field_name="groq_response"
                )
        
        return response_data


class FileValidator:
    """Validator for file operations"""
    
    @staticmethod
    def validate_output_path(file_path: Union[str, Path]) -> Path:
        """
        Validate output file path.
        
        Args:
            file_path: File path to validate
            
        Returns:
            Validated Path object
            
        Raises:
            ValidationError: If path is invalid
        """
        try:
            path_obj = Path(file_path)
        except Exception as e:
            raise ValidationError(
                f"Invalid file path: {str(e)}",
                field_name="file_path",
                invalid_value=str(file_path)
            )
        
        # Check if parent directory exists or can be created
        parent_dir = path_obj.parent
        if not parent_dir.exists():
            try:
                parent_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ValidationError(
                    f"Cannot create output directory: {str(e)}",
                    field_name="file_path",
                    invalid_value=str(parent_dir)
                )
        
        # Check file extension
        if path_obj.suffix not in ValidationConstants.SUPPORTED_OUTPUT_FORMATS:
            raise ValidationError(
                f"Unsupported file format. Supported: {ValidationConstants.SUPPORTED_OUTPUT_FORMATS}",
                field_name="file_path",
                invalid_value=path_obj.suffix
            )
        
        return path_obj


# Convenience validation functions
def validate_song_input(song_name: str, artist_name: str) -> tuple[str, str]:
    """
    Validate both song and artist names together.
    
    Returns:
        Tuple of (validated_song_name, validated_artist_name)
    """
    validator = InputValidator()
    return (
        validator.validate_song_name(song_name),
        validator.validate_artist_name(artist_name)
    )


def validate_analysis_result(emotion_scores: Dict[str, float], 
                           dominant_emotion: str,
                           confidence: float) -> tuple[Dict[str, float], str, float]:
    """
    Validate complete analysis result.
    
    Returns:
        Tuple of validated (emotion_scores, dominant_emotion, confidence)
    """
    validator = EmotionAnalysisValidator()
    return (
        validator.validate_emotion_scores(emotion_scores),
        validator.validate_dominant_emotion(dominant_emotion, emotion_scores),
        validator.validate_confidence_score(confidence)
    )