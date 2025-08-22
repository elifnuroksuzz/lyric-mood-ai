"""
Data Models for Emotion Analysis in LyricMood-AI Application

This module defines data classes and models for representing emotion analysis
results, confidence scores, and analysis metadata with validation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json
from pathlib import Path

from ..core.constants import EmotionCategory, AnalysisConstants
from ..utils.validators import EmotionAnalysisValidator
from .song_data import Song


class AnalysisStatus(Enum):
    """Enumeration of analysis status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"


@dataclass
class EmotionScore:
    """
    Data class representing a single emotion score with metadata.
    """
    emotion: EmotionCategory
    score: float
    confidence: Optional[float] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        """Validate emotion score data"""
        # Validate score range
        if not (0.0 <= self.score <= 100.0):
            raise ValueError(f"Score must be between 0 and 100, got {self.score}")
        
        # Validate confidence if provided
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")
        
        # Round score to 2 decimal places
        self.score = round(self.score, 2)
        
        # Set description if not provided
        if not self.description:
            self.description = AnalysisConstants.EMOTION_DESCRIPTIONS.get(
                self.emotion, f"Score for {self.emotion.value}"
            )
    
    @property
    def percentage_display(self) -> str:
        """Get formatted percentage display"""
        return f"{self.score:.1f}%"
    
    @property
    def normalized_score(self) -> float:
        """Get score normalized to 0-1 range"""
        return self.score / 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'emotion': self.emotion.value,
            'score': self.score,
            'confidence': self.confidence,
            'description': self.description,
            'percentage_display': self.percentage_display,
            'normalized_score': self.normalized_score
        }


@dataclass
class EmotionAnalysisResult:
    """
    Complete emotion analysis result with all emotions and metadata.
    """
    emotion_scores: Dict[EmotionCategory, EmotionScore]
    dominant_emotion: EmotionCategory
    overall_confidence: float
    summary: Optional[str] = None
    analysis_model: str = "groq-ai"
    processing_time: Optional[float] = None
    analyzed_at: datetime = field(default_factory=datetime.now)
    status: AnalysisStatus = AnalysisStatus.COMPLETED
    
    def __post_init__(self):
        """Validate and process analysis result"""
        # Validate overall confidence
        validator = EmotionAnalysisValidator()
        self.overall_confidence = validator.validate_confidence_score(self.overall_confidence)
        
        # Validate that all emotion categories are present
        expected_emotions = set(EmotionCategory)
        provided_emotions = set(self.emotion_scores.keys())
        
        if expected_emotions != provided_emotions:
            missing = expected_emotions - provided_emotions
            extra = provided_emotions - expected_emotions
            error_msg = []
            if missing:
                error_msg.append(f"Missing emotions: {[e.value for e in missing]}")
            if extra:
                error_msg.append(f"Unexpected emotions: {[e.value for e in extra]}")
            raise ValueError("; ".join(error_msg))
        
        # Verify dominant emotion is actually the highest scoring
        actual_dominant = self.get_dominant_emotion()
        if self.dominant_emotion != actual_dominant:
            self.dominant_emotion = actual_dominant
    
    @classmethod
    def from_api_response(cls, api_response: Dict[str, Any], 
                         processing_time: Optional[float] = None) -> 'EmotionAnalysisResult':
        """
        Create analysis result from API response.
        
        Args:
            api_response: Validated API response dictionary
            processing_time: Time taken for analysis in seconds
            
        Returns:
            EmotionAnalysisResult instance
        """
        # Create emotion scores
        emotion_scores = {}
        for emotion_cat in EmotionCategory:
            score_value = api_response.get(emotion_cat.value, 0.0)
            emotion_scores[emotion_cat] = EmotionScore(
                emotion=emotion_cat,
                score=float(score_value)
            )
        
        # Get dominant emotion
        dominant_emotion_str = api_response.get('dominant_emotion', '').lower()
        dominant_emotion = None
        for emotion_cat in EmotionCategory:
            if emotion_cat.value == dominant_emotion_str:
                dominant_emotion = emotion_cat
                break
        
        if not dominant_emotion:
            # Fall back to highest scoring emotion
            dominant_emotion = max(emotion_scores.keys(), 
                                 key=lambda x: emotion_scores[x].score)
        
        return cls(
            emotion_scores=emotion_scores,
            dominant_emotion=dominant_emotion,
            overall_confidence=api_response.get('confidence', 0.0),
            summary=api_response.get('summary'),
            processing_time=processing_time
        )
    
    def get_dominant_emotion(self) -> EmotionCategory:
        """Get the emotion with the highest score"""
        return max(self.emotion_scores.keys(), 
                  key=lambda x: self.emotion_scores[x].score)
    
    def get_top_emotions(self, count: int = 3) -> List[Tuple[EmotionCategory, EmotionScore]]:
        """
        Get top N emotions by score.
        
        Args:
            count: Number of top emotions to return
            
        Returns:
            List of tuples (emotion, score) sorted by score descending
        """
        sorted_emotions = sorted(
            self.emotion_scores.items(),
            key=lambda x: x[1].score,
            reverse=True
        )
        return sorted_emotions[:count]
    
    def get_emotion_score(self, emotion: EmotionCategory) -> float:
        """Get score for specific emotion"""
        return self.emotion_scores[emotion].score
    
    def get_emotion_percentage(self, emotion: EmotionCategory) -> str:
        """Get formatted percentage for specific emotion"""
        return self.emotion_scores[emotion].percentage_display
    
    @property
    def dominant_score(self) -> float:
        """Get score of dominant emotion"""
        return self.emotion_scores[self.dominant_emotion].score
    
    @property
    def is_high_confidence(self) -> bool:
        """Check if analysis has high confidence (>0.7)"""
        return self.overall_confidence > 0.7
    
    @property
    def analysis_quality(self) -> str:
        """Get qualitative assessment of analysis quality"""
        if self.overall_confidence >= 0.8:
            return "High"
        elif self.overall_confidence >= 0.6:
            return "Medium"
        else:
            return "Low"
    
    def get_summary_text(self) -> str:
        """Get formatted summary of analysis"""
        if self.summary:
            return self.summary
        
        dominant_score = self.dominant_score
        top_emotions = self.get_top_emotions(2)
        
        summary_parts = [
            f"The dominant emotion is {self.dominant_emotion.value} ({dominant_score:.1f}%)"
        ]
        
        if len(top_emotions) > 1 and top_emotions[1][1].score > 20:
            secondary = top_emotions[1]
            summary_parts.append(
                f"with secondary presence of {secondary[0].value} ({secondary[1].score:.1f}%)"
            )
        
        summary_parts.append(f"Analysis confidence: {self.overall_confidence:.1%}")
        
        return ". ".join(summary_parts) + "."
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'emotion_scores': {
                emotion.value: score.to_dict() 
                for emotion, score in self.emotion_scores.items()
            },
            'dominant_emotion': self.dominant_emotion.value,
            'dominant_score': self.dominant_score,
            'overall_confidence': self.overall_confidence,
            'summary': self.get_summary_text(),
            'analysis_model': self.analysis_model,
            'processing_time': self.processing_time,
            'analyzed_at': self.analyzed_at.isoformat(),
            'status': self.status.value,
            'analysis_quality': self.analysis_quality,
            'is_high_confidence': self.is_high_confidence,
            'top_emotions': [
                {
                    'emotion': emotion.value,
                    'score': score.score,
                    'percentage': score.percentage_display
                }
                for emotion, score in self.get_top_emotions(3)
            ]
        }


@dataclass
class AnalysisSession:
    """
    Complete analysis session containing song and emotion analysis.
    """
    session_id: str
    song: Song
    analysis_result: Optional[EmotionAnalysisResult] = None
    error_message: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: AnalysisStatus = AnalysisStatus.PENDING
    
    @property
    def duration(self) -> Optional[float]:
        """Get session duration in seconds"""
        if not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()
    
    @property
    def is_successful(self) -> bool:
        """Check if analysis was successful"""
        return (self.status == AnalysisStatus.COMPLETED and 
                self.analysis_result is not None and 
                self.error_message is None)
    
    def mark_completed(self, analysis_result: EmotionAnalysisResult) -> None:
        """Mark session as completed with results"""
        self.analysis_result = analysis_result
        self.completed_at = datetime.now()
        self.status = AnalysisStatus.COMPLETED
        self.error_message = None
    
    def mark_failed(self, error_message: str) -> None:
        """Mark session as failed with error"""
        self.error_message = error_message
        self.completed_at = datetime.now()
        self.status = AnalysisStatus.FAILED
        self.analysis_result = None
    
    def mark_cached(self, analysis_result: EmotionAnalysisResult) -> None:
        """Mark session as using cached results"""
        self.analysis_result = analysis_result
        self.completed_at = datetime.now()
        self.status = AnalysisStatus.CACHED
        self.error_message = None
    
    def get_display_title(self) -> str:
        """Get formatted title for display"""
        return self.song.full_title
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert complete session to dictionary"""
        return {
            'session_id': self.session_id,
            'song': self.song.to_dict(),
            'analysis_result': self.analysis_result.to_dict() if self.analysis_result else None,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration': self.duration,
            'status': self.status.value,
            'is_successful': self.is_successful,
            'display_title': self.get_display_title()
        }
    
    def save_to_file(self, output_path: Path) -> None:
        """Save session data to file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


@dataclass 
class AnalysisHistory:
    """
    Collection of analysis sessions with management capabilities.
    """
    sessions: List[AnalysisSession] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_session(self, session: AnalysisSession) -> None:
        """Add new session to history"""
        self.sessions.append(session)
    
    def get_successful_sessions(self) -> List[AnalysisSession]:
        """Get only successful analysis sessions"""
        return [s for s in self.sessions if s.is_successful]
    
    def get_recent_sessions(self, count: int = 10) -> List[AnalysisSession]:
        """Get most recent sessions"""
        return sorted(self.sessions, key=lambda x: x.started_at, reverse=True)[:count]
    
    def get_session_by_song(self, song_title: str, artist_name: str) -> Optional[AnalysisSession]:
        """Find session by song and artist name"""
        for session in self.sessions:
            if (session.song.metadata.title.lower() == song_title.lower() and
                session.song.metadata.artist_name.lower() == artist_name.lower()):
                return session
        return None
    
    @property
    def total_sessions(self) -> int:
        """Get total number of sessions"""
        return len(self.sessions)
    
    @property
    def successful_sessions_count(self) -> int:
        """Get count of successful sessions"""
        return len(self.get_successful_sessions())
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if not self.sessions:
            return 0.0
        return self.successful_sessions_count / self.total_sessions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert history to dictionary"""
        return {
            'sessions': [session.to_dict() for session in self.sessions],
            'created_at': self.created_at.isoformat(),
            'total_sessions': self.total_sessions,
            'successful_sessions_count': self.successful_sessions_count,
            'success_rate': self.success_rate
        }