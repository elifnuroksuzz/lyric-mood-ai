"""
Data Models for Song Information in LyricMood-AI Application

This module defines data classes and models for representing song information,
metadata, and related data structures with proper validation and serialization.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
import json
from pathlib import Path

from ..core.constants import EmotionCategory


@dataclass
class SongMetadata:
    """
    Data class representing song metadata from Genius API.
    """
    song_id: int
    title: str
    artist_name: str
    album: Optional[str] = None
    release_date: Optional[str] = None
    genius_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    view_count: Optional[int] = None
    annotation_count: Optional[int] = None
    featured_artists: List[str] = field(default_factory=list)
    producers: List[str] = field(default_factory=list)
    writers: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate data after initialization"""
        # Validate required fields
        if not self.song_id or self.song_id <= 0:
            raise ValueError("Invalid song_id: must be positive integer")
        
        # Clean and validate title and artist - basic validation
        if not self.title or not self.title.strip():
            raise ValueError("Song title cannot be empty")
        if not self.artist_name or not self.artist_name.strip():
            raise ValueError("Artist name cannot be empty")
        
        self.title = self.title.strip()
        self.artist_name = self.artist_name.strip()
    
    @classmethod
    def from_genius_api(cls, api_data: Dict[str, Any]) -> 'SongMetadata':
        """
        Create SongMetadata instance from Genius API response.
        
        Args:
            api_data: Raw data from Genius API
            
        Returns:
            SongMetadata instance
        """
        return cls(
            song_id=api_data.get('id', 0),
            title=api_data.get('title', ''),
            artist_name=api_data.get('primary_artist', {}).get('name', ''),
            album=api_data.get('album', {}).get('name') if api_data.get('album') else None,
            release_date=api_data.get('release_date_for_display'),
            genius_url=api_data.get('url'),
            thumbnail_url=api_data.get('song_art_image_thumbnail_url'),
            view_count=api_data.get('stats', {}).get('pageviews'),
            annotation_count=api_data.get('annotation_count'),
            featured_artists=[
                artist.get('name', '') 
                for artist in api_data.get('featured_artists', [])
            ],
            producers=[
                producer.get('name', '')
                for producer in api_data.get('producer_artists', [])
            ],
            writers=[
                writer.get('name', '')
                for writer in api_data.get('writer_artists', [])
            ]
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'song_id': self.song_id,
            'title': self.title,
            'artist_name': self.artist_name,
            'album': self.album,
            'release_date': self.release_date,
            'genius_url': self.genius_url,
            'thumbnail_url': self.thumbnail_url,
            'view_count': self.view_count,
            'annotation_count': self.annotation_count,
            'featured_artists': self.featured_artists,
            'producers': self.producers,
            'writers': self.writers
        }


@dataclass
class LyricsData:
    """
    Data class representing song lyrics with metadata.
    """
    content: str
    language: str = "en"
    word_count: Optional[int] = None
    line_count: Optional[int] = None
    verse_count: Optional[int] = None
    chorus_count: Optional[int] = None
    bridge_count: Optional[int] = None
    retrieved_at: datetime = field(default_factory=datetime.now)
    source: str = "genius"
    
    def __post_init__(self):
        """Process lyrics and calculate metadata"""
        # Basic validation
        if not self.content or not self.content.strip():
            raise ValueError("Lyrics content cannot be empty")
        
        self.content = self.content.strip()
        
        # Calculate statistics
        self._calculate_statistics()
    
    def _calculate_statistics(self) -> None:
        """Calculate lyrics statistics"""
        lines = self.content.split('\n')
        self.line_count = len([line for line in lines if line.strip()])
        
        words = self.content.split()
        self.word_count = len(words)
        
        # Basic structure detection
        content_lower = self.content.lower()
        self.verse_count = content_lower.count('[verse') + content_lower.count('verse ')
        self.chorus_count = content_lower.count('[chorus') + content_lower.count('chorus ')
        self.bridge_count = content_lower.count('[bridge') + content_lower.count('bridge ')
    
    @property
    def summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics"""
        return {
            'word_count': self.word_count,
            'line_count': self.line_count,
            'verse_count': self.verse_count,
            'chorus_count': self.chorus_count,
            'bridge_count': self.bridge_count,
            'character_count': len(self.content),
            'language': self.language
        }
    
    def get_preview(self, max_length: int = 200) -> str:
        """Get a preview of the lyrics"""
        if len(self.content) <= max_length:
            return self.content
        
        # Find a good breaking point (end of sentence or line)
        preview = self.content[:max_length]
        last_period = preview.rfind('.')
        last_newline = preview.rfind('\n')
        
        break_point = max(last_period, last_newline)
        if break_point > max_length * 0.7:  # If break point is reasonable
            return preview[:break_point + 1] + "..."
        
        return preview + "..."
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'content': self.content,
            'language': self.language,
            'statistics': self.summary_stats,
            'retrieved_at': self.retrieved_at.isoformat(),
            'source': self.source
        }


@dataclass
class Song:
    """
    Complete song data model combining metadata and lyrics.
    """
    metadata: SongMetadata
    lyrics: Optional[LyricsData] = None
    search_query: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def full_title(self) -> str:
        """Get formatted full title"""
        return f"{self.metadata.title} - {self.metadata.artist_name}"
    
    @property
    def has_lyrics(self) -> bool:
        """Check if song has lyrics data"""
        return self.lyrics is not None and bool(self.lyrics.content.strip())
    
    @property
    def is_complete(self) -> bool:
        """Check if song data is complete for analysis"""
        return self.has_lyrics and self.metadata.song_id > 0
    
    def get_lyrics_preview(self, max_length: int = 200) -> str:
        """Get lyrics preview or placeholder"""
        if not self.has_lyrics:
            return "No lyrics available"
        return self.lyrics.get_preview(max_length)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert complete song data to dictionary"""
        return {
            'metadata': self.metadata.to_dict(),
            'lyrics': self.lyrics.to_dict() if self.lyrics else None,
            'search_query': self.search_query,
            'created_at': self.created_at.isoformat(),
            'full_title': self.full_title,
            'has_lyrics': self.has_lyrics,
            'is_complete': self.is_complete
        }