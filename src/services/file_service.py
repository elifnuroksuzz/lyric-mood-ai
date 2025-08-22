"""
File Service for LyricMood-AI Application

This module handles all file operations including saving analysis results,
managing output formats, and file system operations with proper error handling.
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import os

from ..core.config_manager import config
from ..core.constants import FileConstants, EmotionCategory
from ..core.exceptions import FileOperationError
from ..models.emotion_analysis import AnalysisSession, AnalysisHistory, EmotionAnalysisResult
from ..models.song_data import Song
from ..utils.logger import logger, performance_timer
from ..utils.validators import FileValidator


class FileService:
    """
    Comprehensive file service for managing analysis outputs and data persistence.
    """
    
    def __init__(self):
        """Initialize file service"""
        self.output_dir = config.output_directory
        self.ensure_directories()
        
        logger.info(f"File service initialized with output directory: {self.output_dir}")
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist"""
        directories = [
            self.output_dir,
            self.output_dir / FileConstants.LOGS_DIR,
            self.output_dir / FileConstants.CACHE_DIR
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Directory ensured: {directory}")
            except Exception as e:
                raise FileOperationError(
                    f"Failed to create directory {directory}: {str(e)}",
                    file_path=str(directory),
                    operation="create_directory"
                )
    
    def generate_filename(self, song: Song, file_format: str = "txt", 
                         include_timestamp: bool = True) -> str:
        """
        Generate a safe filename for analysis output.
        
        Args:
            song: Song object
            file_format: File format extension
            include_timestamp: Whether to include timestamp
            
        Returns:
            Generated filename
        """
        # Clean song and artist names for filename
        safe_song = self._sanitize_filename(song.metadata.title)
        safe_artist = self._sanitize_filename(song.metadata.artist_name)
        
        if include_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analysis_{safe_artist}_{safe_song}_{timestamp}.{file_format}"
        else:
            filename = f"analysis_{safe_artist}_{safe_song}.{file_format}"
        
        return filename
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize string for use in filename.
        
        Args:
            filename: Raw filename string
            
        Returns:
            Sanitized filename
        """
        # Replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove multiple underscores and trim
        filename = '_'.join(filter(None, filename.split('_')))
        
        # Limit length
        max_length = 50
        if len(filename) > max_length:
            filename = filename[:max_length].rstrip('_')
        
        return filename or "unknown"
    
    def save_analysis_txt(self, session: AnalysisSession, 
                         custom_path: Optional[Path] = None) -> Path:
        """
        Save analysis results as formatted text file.
        
        Args:
            session: Analysis session to save
            custom_path: Custom output path (optional)
            
        Returns:
            Path to saved file
            
        Raises:
            FileOperationError: If save operation fails
        """
        if custom_path:
            output_path = custom_path
        else:
            filename = self.generate_filename(session.song, "txt")
            output_path = self.output_dir / filename
        
        # Validate output path
        validator = FileValidator()
        output_path = validator.validate_output_path(output_path)
        
        try:
            with performance_timer("save_analysis_txt"):
                content = self._format_analysis_text(session)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                file_size = output_path.stat().st_size
                
                logger.log_file_operation(
                    operation="save_txt",
                    file_path=str(output_path),
                    success=True,
                    file_size=file_size
                )
                
                return output_path
                
        except Exception as e:
            logger.log_file_operation(
                operation="save_txt",
                file_path=str(output_path),
                success=False,
                error=str(e)
            )
            raise FileOperationError(
                f"Failed to save text file: {str(e)}",
                file_path=str(output_path),
                operation="save_txt"
            )
    
    def save_analysis_json(self, session: AnalysisSession,
                          custom_path: Optional[Path] = None) -> Path:
        """
        Save analysis results as JSON file.
        
        Args:
            session: Analysis session to save
            custom_path: Custom output path (optional)
            
        Returns:
            Path to saved file
        """
        if custom_path:
            output_path = custom_path
        else:
            filename = self.generate_filename(session.song, "json")
            output_path = self.output_dir / filename
        
        validator = FileValidator()
        output_path = validator.validate_output_path(output_path)
        
        try:
            with performance_timer("save_analysis_json"):
                data = session.to_dict()
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                file_size = output_path.stat().st_size
                
                logger.log_file_operation(
                    operation="save_json",
                    file_path=str(output_path),
                    success=True,
                    file_size=file_size
                )
                
                return output_path
                
        except Exception as e:
            logger.log_file_operation(
                operation="save_json",
                file_path=str(output_path),
                success=False,
                error=str(e)
            )
            raise FileOperationError(
                f"Failed to save JSON file: {str(e)}",
                file_path=str(output_path),
                operation="save_json"
            )
    
    def save_analysis_csv(self, sessions: List[AnalysisSession],
                         custom_path: Optional[Path] = None) -> Path:
        """
        Save multiple analysis results as CSV file.
        
        Args:
            sessions: List of analysis sessions to save
            custom_path: Custom output path (optional)
            
        Returns:
            Path to saved file
        """
        if custom_path:
            output_path = custom_path
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analysis_batch_{timestamp}.csv"
            output_path = self.output_dir / filename
        
        validator = FileValidator()
        output_path = validator.validate_output_path(output_path)
        
        try:
            with performance_timer("save_analysis_csv"):
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # Write header
                    header = [
                        'Session ID', 'Song Title', 'Artist', 'Happiness', 'Sadness',
                        'Anger', 'Fear', 'Love', 'Dominant Emotion', 'Confidence',
                        'Analysis Date', 'Status', 'Processing Time'
                    ]
                    writer.writerow(header)
                    
                    # Write data rows
                    for session in sessions:
                        if session.is_successful and session.analysis_result:
                            result = session.analysis_result
                            row = [
                                session.session_id,
                                session.song.metadata.title,
                                session.song.metadata.artist_name,
                                result.get_emotion_score(EmotionCategory.HAPPINESS),
                                result.get_emotion_score(EmotionCategory.SADNESS),
                                result.get_emotion_score(EmotionCategory.ANGER),
                                result.get_emotion_score(EmotionCategory.FEAR),
                                result.get_emotion_score(EmotionCategory.LOVE),
                                result.dominant_emotion.value,
                                result.overall_confidence,
                                session.completed_at.isoformat() if session.completed_at else '',
                                session.status.value,
                                result.processing_time or 0
                            ]
                        else:
                            row = [
                                session.session_id,
                                session.song.metadata.title,
                                session.song.metadata.artist_name,
                                '', '', '', '', '', '', '',
                                session.completed_at.isoformat() if session.completed_at else '',
                                session.status.value,
                                ''
                            ]
                        writer.writerow(row)
                
                file_size = output_path.stat().st_size
                
                logger.log_file_operation(
                    operation="save_csv",
                    file_path=str(output_path),
                    success=True,
                    file_size=file_size,
                    records_count=len(sessions)
                )
                
                return output_path
                
        except Exception as e:
            logger.log_file_operation(
                operation="save_csv",
                file_path=str(output_path),
                success=False,
                error=str(e)
            )
            raise FileOperationError(
                f"Failed to save CSV file: {str(e)}",
                file_path=str(output_path),
                operation="save_csv"
            )
    
    def _format_analysis_text(self, session: AnalysisSession) -> str:
        """
        Format analysis session as readable text.
        
        Args:
            session: Analysis session
            
        Returns:
            Formatted text content
        """
        lines = []
        
        # Header
        lines.append("=" * 70)
        lines.append(f"LyricMood-AI Analysis Report")
        lines.append("=" * 70)
        lines.append("")
        
        # Song information
        song = session.song
        lines.append("SONG INFORMATION:")
        lines.append(f"Title: {song.metadata.title}")
        lines.append(f"Artist: {song.metadata.artist_name}")
        if song.metadata.album:
            lines.append(f"Album: {song.metadata.album}")
        if song.metadata.release_date:
            lines.append(f"Release Date: {song.metadata.release_date}")
        lines.append("")
        
        # Lyrics preview
        if song.has_lyrics:
            lines.append("LYRICS PREVIEW:")
            preview = song.get_lyrics_preview(300)
            lines.append(preview)
            lines.append("")
            
            # Lyrics statistics
            stats = song.lyrics.summary_stats
            lines.append("LYRICS STATISTICS:")
            lines.append(f"Word Count: {stats['word_count']}")
            lines.append(f"Line Count: {stats['line_count']}")
            lines.append(f"Character Count: {stats['character_count']}")
            if stats['verse_count'] > 0:
                lines.append(f"Verses: {stats['verse_count']}")
            if stats['chorus_count'] > 0:
                lines.append(f"Choruses: {stats['chorus_count']}")
            lines.append("")
        
        # Analysis results
        if session.is_successful and session.analysis_result:
            result = session.analysis_result
            
            lines.append("EMOTION ANALYSIS RESULTS:")
            lines.append("-" * 40)
            
            # Emotion scores with visual bars
            for emotion, score_obj in result.emotion_scores.items():
                bar_length = int(score_obj.score / 5)  # Scale to 20 chars max
                bar = "█" * bar_length + "░" * (20 - bar_length)
                lines.append(f"{emotion.value.capitalize():12} {score_obj.percentage_display:>6} |{bar}|")
            
            lines.append("")
            lines.append(f"Dominant Emotion: {result.dominant_emotion.value.upper()}")
            lines.append(f"Confidence Score: {result.overall_confidence:.1%}")
            lines.append(f"Analysis Quality: {result.analysis_quality}")
            lines.append("")
            
            # Summary
            lines.append("ANALYSIS SUMMARY:")
            lines.append(result.get_summary_text())
            lines.append("")
            
            # Top emotions
            top_emotions = result.get_top_emotions(3)
            lines.append("TOP 3 EMOTIONS:")
            for i, (emotion, score) in enumerate(top_emotions, 1):
                lines.append(f"{i}. {emotion.value.capitalize()}: {score.percentage_display}")
            lines.append("")
        
        # Session metadata
        lines.append("ANALYSIS METADATA:")
        lines.append(f"Session ID: {session.session_id}")
        lines.append(f"Analysis Date: {session.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Status: {session.status.value}")
        if session.duration:
            lines.append(f"Processing Time: {session.duration:.2f} seconds")
        if session.analysis_result and session.analysis_result.analysis_model:
            lines.append(f"Analysis Model: {session.analysis_result.analysis_model}")
        lines.append("")
        
        # Footer
        lines.append("-" * 70)
        lines.append(f"Generated by {config.app_name} v{config.app_version}")
        lines.append(f"Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def save_history(self, history: AnalysisHistory, 
                    custom_path: Optional[Path] = None) -> Path:
        """
        Save analysis history to file.
        
        Args:
            history: Analysis history object
            custom_path: Custom output path (optional)
            
        Returns:
            Path to saved file
        """
        if custom_path:
            output_path = custom_path
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analysis_history_{timestamp}.json"
            output_path = self.output_dir / filename
        
        validator = FileValidator()
        output_path = validator.validate_output_path(output_path)
        
        try:
            with performance_timer("save_history"):
                data = history.to_dict()
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                file_size = output_path.stat().st_size
                
                logger.log_file_operation(
                    operation="save_history",
                    file_path=str(output_path),
                    success=True,
                    file_size=file_size,
                    records_count=history.total_sessions
                )
                
                return output_path
                
        except Exception as e:
            logger.log_file_operation(
                operation="save_history",
                file_path=str(output_path),
                success=False,
                error=str(e)
            )
            raise FileOperationError(
                f"Failed to save history file: {str(e)}",
                file_path=str(output_path),
                operation="save_history"
            )
    
    def load_history(self, file_path: Path) -> AnalysisHistory:
        """
        Load analysis history from file.
        
        Args:
            file_path: Path to history file
            
        Returns:
            Analysis history object
            
        Raises:
            FileOperationError: If load operation fails
        """
        if not file_path.exists():
            raise FileOperationError(
                f"History file not found: {file_path}",
                file_path=str(file_path),
                operation="load_history"
            )
        
        try:
            with performance_timer("load_history"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Reconstruct history object (simplified)
                history = AnalysisHistory()
                # Note: Full reconstruction would require recreating all nested objects
                # This is a simplified version for demonstration
                
                logger.log_file_operation(
                    operation="load_history",
                    file_path=str(file_path),
                    success=True,
                    records_count=len(data.get('sessions', []))
                )
                
                return history
                
        except Exception as e:
            logger.log_file_operation(
                operation="load_history",
                file_path=str(file_path),
                success=False,
                error=str(e)
            )
            raise FileOperationError(
                f"Failed to load history file: {str(e)}",
                file_path=str(file_path),
                operation="load_history"
            )
    
    def list_output_files(self, file_type: Optional[str] = None) -> List[Path]:
        """
        List all output files in the output directory.
        
        Args:
            file_type: Filter by file type (txt, json, csv)
            
        Returns:
            List of file paths
        """
        try:
            files = []
            
            if file_type:
                pattern = f"*.{file_type}"
                files = list(self.output_dir.glob(pattern))
            else:
                for ext in FileConstants.SUPPORTED_OUTPUT_FORMATS:
                    files.extend(self.output_dir.glob(f"*{ext}"))
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to list output files: {e}")
            return []
    
    def cleanup_old_files(self, days_old: int = 30) -> int:
        """
        Clean up old output files.
        
        Args:
            days_old: Files older than this many days will be deleted
            
        Returns:
            Number of files deleted
        """
        deleted_count = 0
        cutoff_time = datetime.now().timestamp() - (days_old * 24 * 3600)
        
        try:
            for file_path in self.list_output_files():
                if file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"Deleted old file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete {file_path}: {e}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old files (older than {days_old} days)")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cleanup operation failed: {e}")
            return 0
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics for output directory.
        
        Returns:
            Dictionary with storage statistics
        """
        try:
            total_size = 0
            file_counts = {}
            
            for file_path in self.list_output_files():
                total_size += file_path.stat().st_size
                ext = file_path.suffix
                file_counts[ext] = file_counts.get(ext, 0) + 1
            
            return {
                'total_files': sum(file_counts.values()),
                'total_size_mb': total_size / 1024 / 1024,
                'file_counts_by_type': file_counts,
                'output_directory': str(self.output_dir),
                'directory_exists': self.output_dir.exists()
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {
                'total_files': 0,
                'total_size_mb': 0,
                'file_counts_by_type': {},
                'output_directory': str(self.output_dir),
                'directory_exists': False,
                'error': str(e)
            }


# Factory function for creating file service
def create_file_service() -> FileService:
    """
    Factory function to create file service.
    
    Returns:
        File service instance
    """
    return FileService()