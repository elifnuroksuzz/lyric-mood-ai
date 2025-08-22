"""
AI Analysis Service for LyricMood-AI Application

This module provides emotion analysis capabilities using Groq AI API
with comprehensive error handling, response validation, and result processing.
"""

import time
import json
import re
import hashlib
from typing import Dict, List, Optional, Any
import requests
from datetime import datetime

from ..core.config_manager import config
from ..core.constants import APIEndpoints, AnalysisConstants, EmotionCategory
from ..core.exceptions import (
    GroqAPIError, RateLimitError, NetworkError, 
    AnalysisError, AuthenticationError
)
from ..models.emotion_analysis import EmotionAnalysisResult, AnalysisStatus
from ..models.song_data import Song
from ..utils.logger import logger, performance_timer
from ..utils.validators import APIResponseValidator, EmotionAnalysisValidator


class GroqAIService:
    """
    Service for emotion analysis using Groq AI API.
    
    Handles API communication, prompt engineering, response validation,
    and result processing with comprehensive error handling.
    """
    
    def __init__(self):
        """Initialize Groq AI service"""
        self.base_url = APIEndpoints.GROQ_BASE_URL
        self.api_key = config.groq_api_key
        self.session = requests.Session()
        
        # Validate configuration
        if not self.api_key:
            raise AuthenticationError("Groq", "API key not configured")
        
        # Setup session headers
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': f'{config.app_name}/{config.app_version}'
        })
        
        # Analysis configuration
        self.model_name = "meta-llama/llama-4-scout-17b-16e-instruct"  # Latest Llama 4 model
        self.max_tokens = 1000
        self.temperature = 0.3  # Lower temperature for more consistent results
        
        logger.info("Groq AI service initialized")
    
    def _make_request(self, payload: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
        """
        Make authenticated request to Groq API.
        
        Args:
            payload: Request payload
            timeout: Request timeout in seconds
            
        Returns:
            API response data
            
        Raises:
            Various API-related exceptions
        """
        url = self.base_url + APIEndpoints.GROQ_CHAT_ENDPOINT
        
        try:
            with performance_timer("groq_api_request"):
                response = self.session.post(url, json=payload, timeout=timeout)
                
                logger.log_api_request(
                    api_name="Groq",
                    endpoint="/chat/completions",
                    method="POST",
                    status_code=response.status_code,
                    response_time=response.elapsed.total_seconds()
                )
                
                # Handle different response codes
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise AuthenticationError("Groq", "Invalid API key")
                elif response.status_code == 403:
                    raise AuthenticationError("Groq", "Access forbidden")
                elif response.status_code == 429:
                    retry_after = response.headers.get('Retry-After', '60')
                    raise RateLimitError("Groq", retry_after=int(retry_after))
                elif response.status_code == 400:
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get('error', {}).get('message', 'Bad request')
                    raise GroqAPIError(f"Bad request: {error_msg}", response.status_code, error_data)
                else:
                    raise GroqAPIError(
                        f"API request failed with status {response.status_code}",
                        response.status_code,
                        response.text[:500] if response.text else None
                    )
                    
        except requests.exceptions.Timeout:
            raise NetworkError(f"Request to Groq API timed out after {timeout} seconds")
        except requests.exceptions.ConnectionError:
            raise NetworkError("Failed to connect to Groq API")
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Request failed: {str(e)}")
    
    def _create_analysis_prompt(self, lyrics: str) -> str:
        """
        Create optimized prompt for emotion analysis.
        
        Args:
            lyrics: Song lyrics to analyze
            
        Returns:
            Formatted prompt string
        """
        # Truncate lyrics if too long
        if len(lyrics) > AnalysisConstants.MAX_LYRICS_LENGTH:
            lyrics = lyrics[:AnalysisConstants.MAX_LYRICS_LENGTH] + "..."
            logger.warning(f"Lyrics truncated to {AnalysisConstants.MAX_LYRICS_LENGTH} characters")
        
        return AnalysisConstants.EMOTION_ANALYSIS_PROMPT.format(lyrics=lyrics)
    
    def _parse_analysis_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and validate API response.
        
        Args:
            response_data: Raw API response
            
        Returns:
            Parsed analysis data
            
        Raises:
            AnalysisError: If response parsing fails
        """
        try:
            # Extract content from response
            choices = response_data.get('choices', [])
            if not choices:
                raise AnalysisError("No choices in API response")
            
            message = choices[0].get('message', {})
            content = message.get('content', '')
            
            if not content:
                raise AnalysisError("Empty content in API response")
            
            # Clean the content - remove markdown formatting and extra text
            content = content.strip()
            
            # Find JSON in the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
            else:
                # If no JSON found, try to create a basic response
                logger.warning("No JSON found in response, creating fallback response")
                return self._create_fallback_response(content)
            
            try:
                parsed_data = json.loads(json_str)
            except json.JSONDecodeError:
                # Try to fix common JSON issues
                json_str = self._fix_json_format(json_str)
                try:
                    parsed_data = json.loads(json_str)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON, creating fallback response")
                    return self._create_fallback_response(content)
            
            # Validate required fields and add defaults if missing
            parsed_data = self._ensure_required_fields(parsed_data)
            
            return parsed_data
            
        except Exception as e:
            if isinstance(e, AnalysisError):
                raise
            logger.error(f"Unexpected error in response parsing: {e}")
            raise AnalysisError(f"Failed to parse analysis response: {str(e)}")
    
    def _fix_json_format(self, json_str: str) -> str:
        """Fix common JSON formatting issues"""
        # Remove markdown code blocks
        json_str = re.sub(r'```json\s*', '', json_str)
        json_str = re.sub(r'```\s*$', '', json_str)
        
        # Fix trailing commas
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Fix missing quotes on keys
        json_str = re.sub(r'(\w+):', r'"\1":', json_str)
        
        return json_str.strip()
    
    def _create_fallback_response(self, content: str) -> Dict[str, Any]:
        """Create a fallback response when JSON parsing fails"""
        # Simple keyword-based analysis as fallback
        content_lower = content.lower()
        
        # Basic emotion detection based on keywords
        emotion_scores = {
            "happiness": 20.0,
            "sadness": 20.0,
            "anger": 20.0,
            "fear": 20.0,
            "love": 20.0
        }
        
        # Adjust scores based on content
        if any(word in content_lower for word in ['happy', 'joy', 'good', 'positive']):
            emotion_scores["happiness"] += 30
        if any(word in content_lower for word in ['sad', 'melancholy', 'sorrow', 'grief']):
            emotion_scores["sadness"] += 30
        if any(word in content_lower for word in ['anger', 'rage', 'mad', 'fury']):
            emotion_scores["anger"] += 30
        if any(word in content_lower for word in ['fear', 'scared', 'afraid', 'anxious']):
            emotion_scores["fear"] += 30
        if any(word in content_lower for word in ['love', 'romance', 'affection', 'caring']):
            emotion_scores["love"] += 30
        
        # Find dominant emotion
        dominant = max(emotion_scores.keys(), key=lambda x: emotion_scores[x])
        
        return {
            "happiness": emotion_scores["happiness"],
            "sadness": emotion_scores["sadness"],
            "anger": emotion_scores["anger"],
            "fear": emotion_scores["fear"],
            "love": emotion_scores["love"],
            "dominant_emotion": dominant,
            "confidence": 0.6,  # Lower confidence for fallback
            "summary": f"Analysis completed using fallback method. Dominant emotion detected: {dominant}"
        }
    
    def _ensure_required_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all required fields are present with defaults"""
        required_fields = {
            "happiness": 0.0,
            "sadness": 0.0,
            "anger": 0.0,
            "fear": 0.0,
            "love": 0.0,
            "confidence": 0.5,
            "summary": "Analysis completed successfully"
        }
        
        # Add missing fields with defaults
        for field, default_value in required_fields.items():
            if field not in data:
                data[field] = default_value
        
        # Ensure dominant_emotion is set
        if "dominant_emotion" not in data:
            emotions = ["happiness", "sadness", "anger", "fear", "love"]
            scores = {emotion: float(data.get(emotion, 0)) for emotion in emotions}
            data["dominant_emotion"] = max(scores.keys(), key=lambda x: scores[x])
        
        return data
    
    def analyze_emotions(self, lyrics: str) -> EmotionAnalysisResult:
        """
        Analyze emotions in song lyrics.
        
        Args:
            lyrics: Song lyrics text
            
        Returns:
            Emotion analysis result
            
        Raises:
            AnalysisError: If analysis fails
        """
        if not lyrics or not lyrics.strip():
            raise AnalysisError("Lyrics cannot be empty")
        
        logger.debug(f"Starting emotion analysis for lyrics ({len(lyrics)} characters)")
        
        start_time = time.time()
        
        try:
            # Create analysis prompt
            prompt = self._create_analysis_prompt(lyrics.strip())
            
            # Prepare API payload
            payload = {
                'model': self.model_name,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'max_tokens': self.max_tokens,
                'temperature': self.temperature,
                'top_p': 0.9,
                'stream': False
            }
            
            # Make API request
            response_data = self._make_request(payload)
            
            # Parse response
            analysis_data = self._parse_analysis_response(response_data)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Create analysis result
            result = EmotionAnalysisResult.from_api_response(
                analysis_data, 
                processing_time=processing_time
            )
            
            logger.info(
                f"Emotion analysis completed - Dominant: {result.dominant_emotion.value} "
                f"({result.dominant_score:.1f}%), Confidence: {result.overall_confidence:.2f}"
            )
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            if isinstance(e, (GroqAPIError, NetworkError, RateLimitError, AnalysisError)):
                logger.error(f"Analysis failed after {processing_time:.2f}s: {e}")
                raise
            
            logger.error(f"Unexpected analysis error after {processing_time:.2f}s: {e}")
            raise AnalysisError(f"Analysis failed: {str(e)}")
    
    def batch_analyze(self, lyrics_list: List[str], 
                     delay_between_requests: float = 1.0) -> List[Optional[EmotionAnalysisResult]]:
        """
        Perform batch emotion analysis on multiple lyrics.
        
        Args:
            lyrics_list: List of lyrics to analyze
            delay_between_requests: Delay between API requests in seconds
            
        Returns:
            List of analysis results (None for failed analyses)
        """
        results = []
        
        logger.info(f"Starting batch analysis of {len(lyrics_list)} lyrics")
        
        for i, lyrics in enumerate(lyrics_list):
            try:
                # Add delay between requests to respect rate limits
                if i > 0 and delay_between_requests > 0:
                    time.sleep(delay_between_requests)
                
                result = self.analyze_emotions(lyrics)
                results.append(result)
                
                logger.debug(f"Batch analysis {i+1}/{len(lyrics_list)} completed")
                
            except Exception as e:
                logger.error(f"Batch analysis {i+1}/{len(lyrics_list)} failed: {e}")
                results.append(None)
        
        successful_analyses = len([r for r in results if r is not None])
        logger.info(f"Batch analysis completed: {successful_analyses}/{len(lyrics_list)} successful")
        
        return results
    
    def validate_connection(self) -> bool:
        """
        Validate API connection and credentials.
        
        Returns:
            True if connection is valid
            
        Raises:
            AuthenticationError: If credentials are invalid
            NetworkError: If connection fails
        """
        try:
            # Try a simple test request
            test_payload = {
                'model': self.model_name,
                'messages': [
                    {
                        'role': 'user',
                        'content': 'Test connection. Respond with "OK".'
                    }
                ],
                'max_tokens': 10,
                'temperature': 0
            }
            
            response = self._make_request(test_payload, timeout=30)
            
            if response.get('choices'):
                logger.info("Groq AI API connection validated successfully")
                return True
            else:
                raise NetworkError("Invalid response format from Groq API")
                
        except AuthenticationError:
            logger.error("Groq AI API authentication failed")
            raise
        except NetworkError:
            logger.error("Groq AI API network connection failed")
            raise
        except Exception as e:
            logger.error(f"Groq AI API validation failed: {e}")
            raise NetworkError(f"API validation failed: {str(e)}")


class EmotionAnalysisService:
    """
    High-level service for emotion analysis with caching and error handling.
    """
    
    def __init__(self, use_cache: bool = True):
        """
        Initialize emotion analysis service.
        
        Args:
            use_cache: Whether to enable result caching
        """
        self.groq_service = GroqAIService()
        self.use_cache = use_cache
        self._cache: Dict[str, EmotionAnalysisResult] = {}
        
        logger.info("Emotion analysis service initialized")
    
    def _get_cache_key(self, lyrics: str) -> str:
        """Generate cache key for lyrics"""
        return hashlib.md5(lyrics.encode('utf-8')).hexdigest()
    
    def analyze_song(self, song: Song) -> EmotionAnalysisResult:
        """
        Analyze emotions in a song.
        
        Args:
            song: Song object with lyrics
            
        Returns:
            Emotion analysis result
            
        Raises:
            AnalysisError: If song cannot be analyzed
        """
        if not song.has_lyrics:
            raise AnalysisError("Song has no lyrics to analyze")
        
        lyrics = song.lyrics.content
        
        logger.log_analysis_start(
            song.metadata.title,
            song.metadata.artist_name,
            len(lyrics)
        )
        
        # Check cache if enabled
        if self.use_cache:
            cache_key = self._get_cache_key(lyrics)
            if cache_key in self._cache:
                logger.debug(f"Using cached analysis result for '{song.full_title}'")
                return self._cache[cache_key]
        
        # Perform analysis
        try:
            result = self.groq_service.analyze_emotions(lyrics)
            
            # Cache result if enabled
            if self.use_cache:
                self._cache[cache_key] = result
            
            logger.log_analysis_result(
                song.metadata.title,
                song.metadata.artist_name,
                {emotion.value: score.score for emotion, score in result.emotion_scores.items()},
                result.dominant_emotion.value,
                result.overall_confidence,
                result.processing_time
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Failed to analyze '{song.full_title}': {e}",
                exc_info=True
            )
            raise
    
    def clear_cache(self) -> None:
        """Clear analysis cache"""
        self._cache.clear()
        logger.info("Analysis cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cache_enabled': self.use_cache,
            'cached_analyses': len(self._cache),
            'cache_size_mb': sum(
                len(str(result.to_dict())) for result in self._cache.values()
            ) / 1024 / 1024
        }


# Factory function for creating analysis service
def create_analysis_service(use_cache: bool = True) -> EmotionAnalysisService:
    """
    Factory function to create emotion analysis service.
    
    Args:
        use_cache: Whether to enable caching
        
    Returns:
        Emotion analysis service instance
    """
    return EmotionAnalysisService(use_cache=use_cache)