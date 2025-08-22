"""
Genius API Service for LyricMood-AI Application

This module provides a comprehensive service for interacting with the Genius API
to search for songs, retrieve lyrics, and manage API interactions with proper
error handling, rate limiting, and caching.
"""

import time
import requests
from typing import Optional, Dict, List, Any, Tuple
from urllib.parse import urljoin, quote
import re
from bs4 import BeautifulSoup
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..core.config_manager import config
from ..core.constants import APIEndpoints
from ..core.exceptions import (
    GeniusAPIError, RateLimitError, NetworkError, 
    LyricsNotFoundError, AuthenticationError
)
from ..models.song_data import Song, SongMetadata, LyricsData
from ..utils.logger import logger, performance_timer
from ..utils.validators import APIResponseValidator, InputValidator


@dataclass
class SearchResult:
    """Data class for search results"""
    song_id: int
    title: str
    artist_name: str
    url: str
    thumbnail_url: Optional[str] = None
    view_count: Optional[int] = None


class RateLimiter:
    """Simple rate limiter for API requests"""
    
    def __init__(self, max_requests: int = 60, time_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def can_make_request(self) -> bool:
        """Check if a request can be made"""
        now = datetime.now()
        # Remove old requests outside the time window
        self.requests = [
            req_time for req_time in self.requests 
            if now - req_time < timedelta(seconds=self.time_window)
        ]
        return len(self.requests) < self.max_requests
    
    def record_request(self) -> None:
        """Record a new request"""
        self.requests.append(datetime.now())
    
    def time_until_next_request(self) -> float:
        """Get time to wait until next request is allowed"""
        if self.can_make_request():
            return 0.0
        
        oldest_request = min(self.requests)
        wait_until = oldest_request + timedelta(seconds=self.time_window)
        return (wait_until - datetime.now()).total_seconds()


class GeniusAPIService:
    """
    Comprehensive service for Genius API interactions.
    
    Handles authentication, rate limiting, error handling, and response parsing.
    """
    
    def __init__(self):
        """Initialize Genius API service"""
        self.base_url = APIEndpoints.GENIUS_BASE_URL
        self.access_token = config.genius_token
        self.session = requests.Session()
        self.rate_limiter = RateLimiter(
            max_requests=min(config.genius_rate_limit // 60, 60),  # Per minute limit
            time_window=60
        )
        
        # Validate configuration
        if not self.access_token:
            raise AuthenticationError("Genius", "Access token not configured")
        
        # Setup session headers
        self.session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'User-Agent': f'{config.app_name}/{config.app_version}',
            'Accept': 'application/json'
        })
        
        logger.info("Genius API service initialized")
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None,
                     timeout: int = 30) -> Dict[str, Any]:
        """
        Make authenticated request to Genius API.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            timeout: Request timeout in seconds
            
        Returns:
            API response data
            
        Raises:
            Various API-related exceptions
        """
        # Rate limiting
        if not self.rate_limiter.can_make_request():
            wait_time = self.rate_limiter.time_until_next_request()
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f} seconds")
                raise RateLimitError("Genius", retry_after=int(wait_time))
        
        url = urljoin(self.base_url, endpoint)
        
        try:
            with performance_timer(f"genius_api_request_{endpoint.replace('/', '_')}"):
                response = self.session.get(url, params=params, timeout=timeout)
                
                # Record successful request for rate limiting
                self.rate_limiter.record_request()
                
                logger.log_api_request(
                    api_name="Genius",
                    endpoint=endpoint,
                    method="GET",
                    status_code=response.status_code,
                    response_time=response.elapsed.total_seconds()
                )
                
                # Handle different response codes
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise AuthenticationError("Genius", "Invalid access token")
                elif response.status_code == 403:
                    raise AuthenticationError("Genius", "Access forbidden")
                elif response.status_code == 404:
                    raise GeniusAPIError("Resource not found", response.status_code)
                elif response.status_code == 429:
                    retry_after = response.headers.get('Retry-After', '60')
                    raise RateLimitError("Genius", retry_after=int(retry_after))
                else:
                    raise GeniusAPIError(
                        f"API request failed with status {response.status_code}",
                        response.status_code,
                        response.text[:500] if response.text else None
                    )
                    
        except requests.exceptions.Timeout:
            raise NetworkError(f"Request to {url} timed out after {timeout} seconds")
        except requests.exceptions.ConnectionError:
            raise NetworkError(f"Failed to connect to {url}")
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Request failed: {str(e)}")
    
    def search_songs(self, query: str, limit: int = 10) -> List[SearchResult]:
        """
        Search for songs on Genius.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of search results
            
        Raises:
            GeniusAPIError: If search fails
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")
        
        logger.info(f"Searching Genius for: '{query}'")
        
        params = {
            'q': query.strip(),
            'per_page': min(limit, 50)  # Genius API limit
        }
        
        try:
            response_data = self._make_request(APIEndpoints.GENIUS_SEARCH_ENDPOINT, params)
            
            # Validate response structure
            validator = APIResponseValidator()
            validator.validate_genius_search_response(response_data)
            
            # Parse search results
            results = []
            hits = response_data.get('response', {}).get('hits', [])
            
            for hit in hits:
                song_data = hit.get('result', {})
                if not song_data:
                    continue
                
                try:
                    search_result = SearchResult(
                        song_id=song_data.get('id', 0),
                        title=song_data.get('title', ''),
                        artist_name=song_data.get('primary_artist', {}).get('name', ''),
                        url=song_data.get('url', ''),
                        thumbnail_url=song_data.get('song_art_image_thumbnail_url'),
                        view_count=song_data.get('stats', {}).get('pageviews')
                    )
                    
                    # Basic validation
                    if search_result.song_id > 0 and search_result.title and search_result.artist_name:
                        results.append(search_result)
                        
                except Exception as e:
                    logger.warning(f"Failed to parse search result: {e}")
                    continue
            
            logger.info(f"Found {len(results)} search results for '{query}'")
            return results
            
        except Exception as e:
            if isinstance(e, (GeniusAPIError, NetworkError, RateLimitError)):
                raise
            raise GeniusAPIError(f"Search failed: {str(e)}")
    
    def get_song_details(self, song_id: int) -> SongMetadata:
        """
        Get detailed song information.
        
        Args:
            song_id: Genius song ID
            
        Returns:
            Song metadata
            
        Raises:
            GeniusAPIError: If request fails
        """
        if not song_id or song_id <= 0:
            raise ValueError("Invalid song ID")
        
        logger.debug(f"Getting song details for ID: {song_id}")
        
        endpoint = APIEndpoints.GENIUS_SONG_ENDPOINT.format(song_id=song_id)
        
        try:
            response_data = self._make_request(endpoint)
            song_data = response_data.get('response', {}).get('song', {})
            
            if not song_data:
                raise GeniusAPIError(f"No song data found for ID {song_id}")
            
            metadata = SongMetadata.from_genius_api(song_data)
            logger.debug(f"Retrieved metadata for '{metadata.title}' by '{metadata.artist_name}'")
            
            return metadata
            
        except Exception as e:
            if isinstance(e, (GeniusAPIError, NetworkError, RateLimitError)):
                raise
            raise GeniusAPIError(f"Failed to get song details: {str(e)}")
    
    def scrape_lyrics(self, genius_url: str) -> str:
        """
        Scrape lyrics from Genius song page.
        
        Args:
            genius_url: URL to Genius song page
            
        Returns:
            Song lyrics text
            
        Raises:
            LyricsNotFoundError: If lyrics cannot be found
        """
        if not genius_url:
            raise ValueError("Genius URL is required")
        
        logger.debug(f"Scraping lyrics from: {genius_url}")
        
        try:
            with performance_timer("genius_lyrics_scraping"):
                response = self.session.get(genius_url, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find lyrics container (Genius uses different selectors)
                lyrics_selectors = [
                    'div[class*="lyrics"]',
                    'div[data-lyrics-container="true"]',
                    'div[class*="Lyrics__Container"]',
                    'div[class*="SongPageGrid-sc"]'
                ]
                
                lyrics_text = ""
                for selector in lyrics_selectors:
                    lyrics_containers = soup.select(selector)
                    if lyrics_containers:
                        for container in lyrics_containers:
                            # Remove ads and unwanted elements
                            for unwanted in container.select('div[class*="ad"], script, style'):
                                unwanted.decompose()
                            
                            text = container.get_text(separator='\n', strip=True)
                            if text and len(text) > 50:  # Minimum lyrics length
                                lyrics_text += text + '\n'
                
                if not lyrics_text:
                    # Fallback: try to find any div with substantial text
                    all_divs = soup.find_all('div')
                    for div in all_divs:
                        text = div.get_text(strip=True)
                        if len(text) > 200 and '\n' in text:
                            lyrics_text = text
                            break
                
                if not lyrics_text:
                    raise LyricsNotFoundError("", "")
                
                # Clean up the lyrics
                lyrics_text = self._clean_lyrics(lyrics_text)
                
                if len(lyrics_text.strip()) < 20:
                    raise LyricsNotFoundError("", "")
                
                logger.debug(f"Successfully scraped lyrics ({len(lyrics_text)} characters)")
                return lyrics_text
                
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Failed to scrape lyrics: {str(e)}")
        except Exception as e:
            if isinstance(e, LyricsNotFoundError):
                raise
            raise LyricsNotFoundError("", "")
    
    def _clean_lyrics(self, raw_lyrics: str) -> str:
        """
        Clean and format scraped lyrics.
        
        Args:
            raw_lyrics: Raw lyrics text
            
        Returns:
            Cleaned lyrics
        """
        # Remove common unwanted patterns
        cleaned = raw_lyrics
        
        # Remove section markers in brackets
        cleaned = re.sub(r'\[.*?\]', '', cleaned)
        
        # Remove extra whitespace
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        cleaned = re.sub(r' +', ' ', cleaned)
        
        # Remove common footers/headers
        unwanted_patterns = [
            r'.*?Lyrics.*?',
            r'.*?Embed.*?',
            r'.*?Share.*?',
            r'\d+Contributors.*?',
            r'.*?Translation.*?'
        ]
        
        for pattern in unwanted_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def find_and_fetch_song(self, song_name: str, artist_name: str) -> Song:
        """
        Find and fetch complete song data including lyrics.
        
        Args:
            song_name: Name of the song
            artist_name: Name of the artist
            
        Returns:
            Complete Song object with metadata and lyrics
            
        Raises:
            LyricsNotFoundError: If song or lyrics not found
        """
        # Validate inputs
        validator = InputValidator()
        song_name = validator.validate_song_name(song_name)
        artist_name = validator.validate_artist_name(artist_name)
        
        logger.log_analysis_start(song_name, artist_name)
        
        # Search for the song
        search_query = f"{song_name} {artist_name}"
        search_results = self.search_songs(search_query, limit=10)
        
        if not search_results:
            raise LyricsNotFoundError(song_name, artist_name)
        
        # Try to find the best match
        best_match = None
        for result in search_results:
            # Simple scoring based on title and artist similarity
            title_match = self._similarity_score(song_name.lower(), result.title.lower())
            artist_match = self._similarity_score(artist_name.lower(), result.artist_name.lower())
            
            if title_match > 0.7 and artist_match > 0.7:
                best_match = result
                break
        
        if not best_match:
            best_match = search_results[0]  # Use first result as fallback
        
        # Get detailed metadata
        metadata = self.get_song_details(best_match.song_id)
        
        # Scrape lyrics
        try:
            lyrics_content = self.scrape_lyrics(metadata.genius_url)
            lyrics_data = LyricsData(content=lyrics_content)
        except LyricsNotFoundError:
            logger.warning(f"Could not scrape lyrics for {song_name} by {artist_name}")
            raise LyricsNotFoundError(song_name, artist_name)
        
        # Create complete song object
        song = Song(
            metadata=metadata,
            lyrics=lyrics_data,
            search_query=search_query
        )
        
        logger.info(f"Successfully fetched song: '{song.full_title}'")
        return song
    
    def _similarity_score(self, str1: str, str2: str) -> float:
        """
        Calculate simple similarity score between two strings.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Similarity score between 0 and 1
        """
        # Simple Jaccard similarity based on words
        words1 = set(str1.lower().split())
        words2 = set(str2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def search_by_artist_only(self, artist_name: str, limit: int = 20) -> List[SearchResult]:
        """
        Search songs by artist name only.
        
        Args:
            artist_name: Name of the artist
            limit: Maximum number of results
            
        Returns:
            List of search results
        """
        logger.info(f"Searching songs by artist: '{artist_name}'")
        
        # Search for artist
        search_results = self.search_songs(artist_name, limit=limit * 2)
        
        # Filter and score results by artist similarity
        artist_songs = []
        for result in search_results:
            similarity = self._similarity_score(artist_name.lower(), result.artist_name.lower())
            if similarity > 0.6:  # Lower threshold for artist-only search
                artist_songs.append(result)
                if len(artist_songs) >= limit:
                    break
        
        logger.info(f"Found {len(artist_songs)} songs for artist '{artist_name}'")
        return artist_songs
    
    def search_by_song_only(self, song_name: str, limit: int = 20) -> List[SearchResult]:
        """
        Search for a song by title only (multiple artists may have same song).
        
        Args:
            song_name: Name of the song
            limit: Maximum number of results
            
        Returns:
            List of search results
        """
        logger.info(f"Searching for song title: '{song_name}'")
        
        # Search for song title
        search_results = self.search_songs(song_name, limit=limit)
        
        # Filter results by song title similarity
        song_matches = []
        for result in search_results:
            similarity = self._similarity_score(song_name.lower(), result.title.lower())
            if similarity > 0.5:  # Lower threshold for song-only search
                song_matches.append(result)
        
        logger.info(f"Found {len(song_matches)} matches for song '{song_name}'")
        return song_matches
    
    def smart_search(self, query: str, search_type: str = "auto") -> List[SearchResult]:
        """
        Smart search that can handle artist-only, song-only, or combined searches.
        
        Args:
            query: Search query
            search_type: "auto", "artist", "song", or "combined"
            
        Returns:
            List of search results
        """
        if search_type == "artist":
            return self.search_by_artist_only(query)
        elif search_type == "song":
            return self.search_by_song_only(query)
        elif search_type == "auto":
            # Try to determine if it's an artist or song name
            # Look for common song indicators
            song_indicators = ["feat", "ft", "featuring", "remix", "version", "cover"]
            is_likely_song = any(indicator in query.lower() for indicator in song_indicators)
            
            if is_likely_song:
                return self.search_by_song_only(query)
            else:
                # Try both and return combined results
                artist_results = self.search_by_artist_only(query, limit=10)
                song_results = self.search_by_song_only(query, limit=10)
                
                # Combine and deduplicate
                all_results = artist_results + song_results
                seen_ids = set()
                unique_results = []
                for result in all_results:
                    if result.song_id not in seen_ids:
                        unique_results.append(result)
                        seen_ids.add(result.song_id)
                
                return unique_results[:20]
        else:
            # Default combined search
            return self.search_songs(query)
    
    def batch_search(self, queries: List[str], max_results_per_query: int = 5) -> Dict[str, List[SearchResult]]:
        """
        Perform batch search for multiple queries.
        
        Args:
            queries: List of search queries
            max_results_per_query: Maximum results per query
            
        Returns:
            Dictionary mapping queries to their results
        """
        results = {}
        
        for query in queries:
            try:
                # Respect rate limits
                if not self.rate_limiter.can_make_request():
                    wait_time = self.rate_limiter.time_until_next_request()
                    if wait_time > 0:
                        time.sleep(wait_time + 0.1)  # Small buffer
                
                search_results = self.search_songs(query, limit=max_results_per_query)
                results[query] = search_results
                
            except Exception as e:
                logger.error(f"Batch search failed for query '{query}': {e}")
                results[query] = []
        
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
            # Try a simple search to validate connection
            self._make_request(APIEndpoints.GENIUS_SEARCH_ENDPOINT, {'q': 'test', 'per_page': 1})
            logger.info("Genius API connection validated successfully")
            return True
            
        except AuthenticationError:
            logger.error("Genius API authentication failed")
            raise
        except NetworkError:
            logger.error("Genius API network connection failed")
            raise
        except Exception as e:
            logger.error(f"Genius API validation failed: {e}")
            raise NetworkError(f"API validation failed: {str(e)}")


# Cache for storing recent API responses
class GeniusAPICache:
    """Simple in-memory cache for Genius API responses"""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of cached items
            ttl_seconds: Time to live for cache entries
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        if key not in self._cache:
            logger.log_cache_operation("get", key, hit=False)
            return None
        
        value, timestamp = self._cache[key]
        
        # Check if expired
        if datetime.now() - timestamp > timedelta(seconds=self.ttl_seconds):
            del self._cache[key]
            logger.log_cache_operation("get", key, hit=False, expired=True)
            return None
        
        logger.log_cache_operation("get", key, hit=True)
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set item in cache"""
        # Remove oldest items if cache is full
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
        
        self._cache[key] = (value, datetime.now())
        logger.log_cache_operation("set", key)
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
        logger.log_cache_operation("clear", "all")


class CachedGeniusAPIService(GeniusAPIService):
    """Genius API service with caching capabilities"""
    
    def __init__(self, cache_size: int = 100, cache_ttl: int = 3600):
        """
        Initialize cached service.
        
        Args:
            cache_size: Maximum cache size
            cache_ttl: Cache time to live in seconds
        """
        super().__init__()
        self.cache = GeniusAPICache(cache_size, cache_ttl)
    
    def search_songs(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search with caching"""
        cache_key = f"search:{query.lower()}:{limit}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result is not None:
            return cached_result
        
        result = super().search_songs(query, limit)
        self.cache.set(cache_key, result)
        return result
    
    def get_song_details(self, song_id: int) -> SongMetadata:
        """Get song details with caching"""
        cache_key = f"song:{song_id}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result is not None:
            return cached_result
        
        result = super().get_song_details(song_id)
        self.cache.set(cache_key, result)
        return result
    
    def scrape_lyrics(self, genius_url: str) -> str:
        """Scrape lyrics with caching"""
        cache_key = f"lyrics:{genius_url}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result is not None:
            return cached_result
        
        result = super().scrape_lyrics(genius_url)
        self.cache.set(cache_key, result)
        return result


# Factory function for creating service instances
def create_genius_service(use_cache: bool = True) -> GeniusAPIService:
    """
    Factory function to create Genius API service.
    
    Args:
        use_cache: Whether to use caching
        
    Returns:
        Genius API service instance
    """
    if use_cache:
        return CachedGeniusAPIService()
    else:
        return GeniusAPIService()