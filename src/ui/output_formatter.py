"""
Output Formatter for LyricMood-AI Application

This module provides comprehensive formatting utilities for terminal output
including colors, progress bars, tables, and styled text display.
"""

import os
import sys
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from ..core.config_manager import config
from ..core.constants import UIConstants, EmotionCategory
from ..models.emotion_analysis import EmotionAnalysisResult, AnalysisSession
from ..models.song_data import Song


class ColorTheme(Enum):
    """Color themes for terminal output"""
    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"
    COLORFUL = "colorful"


@dataclass
class DisplayConfig:
    """Configuration for display formatting"""
    use_colors: bool = True
    use_emoji: bool = True
    max_width: int = 80
    theme: ColorTheme = ColorTheme.DEFAULT
    
    def __post_init__(self):
        """Adjust settings based on terminal capabilities"""
        # Disable colors if not supported
        if not self._supports_color():
            self.use_colors = False
        
        # Adjust width to terminal size
        try:
            terminal_width = os.get_terminal_size().columns
            self.max_width = min(self.max_width, terminal_width - 2)
        except OSError:
            pass  # Use default width
    
    def _supports_color(self) -> bool:
        """Check if terminal supports colors"""
        return (
            hasattr(sys.stdout, 'isatty') and 
            sys.stdout.isatty() and 
            os.getenv('TERM') != 'dumb' and
            config.enable_color_output
        )


class OutputFormatter:
    """
    Comprehensive output formatter for terminal display.
    
    Provides methods for formatting various types of content with colors,
    styling, and consistent layout.
    """
    
    def __init__(self, display_config: Optional[DisplayConfig] = None):
        """
        Initialize output formatter.
        
        Args:
            display_config: Display configuration settings
        """
        self.config = display_config or DisplayConfig()
        self.colors = UIConstants.COLORS if self.config.use_colors else {}
        
        # Theme-specific color schemes
        self._setup_theme_colors()
    
    def _setup_theme_colors(self):
        """Setup theme-specific color schemes"""
        if not self.config.use_colors:
            return
        
        if self.config.theme == ColorTheme.DARK:
            self.primary_color = self.colors.get("CYAN", "")
            self.secondary_color = self.colors.get("BLUE", "")
            self.accent_color = self.colors.get("MAGENTA", "")
        elif self.config.theme == ColorTheme.LIGHT:
            self.primary_color = self.colors.get("BLUE", "")
            self.secondary_color = self.colors.get("GREEN", "")
            self.accent_color = self.colors.get("YELLOW", "")
        elif self.config.theme == ColorTheme.COLORFUL:
            self.primary_color = self.colors.get("MAGENTA", "")
            self.secondary_color = self.colors.get("CYAN", "")
            self.accent_color = self.colors.get("YELLOW", "")
        else:  # DEFAULT
            self.primary_color = self.colors.get("GREEN", "")
            self.secondary_color = self.colors.get("BLUE", "")
            self.accent_color = self.colors.get("YELLOW", "")
        
        self.reset = self.colors.get("END", "")
    
    def colorize(self, text: str, color: str) -> str:
        """
        Apply color to text.
        
        Args:
            text: Text to colorize
            color: Color name from UIConstants.COLORS
            
        Returns:
            Colorized text
        """
        if not self.config.use_colors or color not in self.colors:
            return text
        
        return f"{self.colors[color]}{text}{self.reset}"
    
    def bold(self, text: str) -> str:
        """Make text bold"""
        if not self.config.use_colors:
            return text
        return f"{self.colors.get('BOLD', '')}{text}{self.reset}"
    
    def underline(self, text: str) -> str:
        """Underline text"""
        if not self.config.use_colors:
            return text
        return f"{self.colors.get('UNDERLINE', '')}{text}{self.reset}"
    
    def format_header(self, title: str, level: int = 1) -> str:
        """
        Format a header with appropriate styling.
        
        Args:
            title: Header title
            level: Header level (1-3)
            
        Returns:
            Formatted header
        """
        emoji_map = {1: "🎵", 2: "📊", 3: "📋"}
        emoji = emoji_map.get(level, "•") if self.config.use_emoji else ""
        
        if level == 1:
            # Main header
            border = "=" * min(len(title) + 10, self.config.max_width)
            formatted_title = self.bold(self.colorize(title, "CYAN"))
            return f"\n{border}\n{emoji} {formatted_title}\n{border}"
        
        elif level == 2:
            # Section header
            border = "-" * min(len(title) + 6, self.config.max_width)
            formatted_title = self.colorize(title, "BLUE")
            return f"\n{border}\n{emoji} {formatted_title}\n{border}"
        
        else:
            # Subsection header
            formatted_title = self.bold(title)
            return f"\n{emoji} {formatted_title}"
    
    def format_progress_bar(self, current: int, total: int, width: int = 30,
                          show_percentage: bool = True) -> str:
        """
        Create a visual progress bar.
        
        Args:
            current: Current progress value
            total: Total/maximum value
            width: Width of progress bar in characters
            show_percentage: Whether to show percentage
            
        Returns:
            Formatted progress bar
        """
        if total == 0:
            percentage = 0
        else:
            percentage = min(100, max(0, (current / total) * 100))
        
        filled_width = int((percentage / 100) * width)
        
        filled_char = UIConstants.PROGRESS_BAR_FILL
        empty_char = UIConstants.PROGRESS_BAR_EMPTY
        
        bar = filled_char * filled_width + empty_char * (width - filled_width)
        
        if self.config.use_colors:
            if percentage >= 80:
                bar = self.colorize(bar, "GREEN")
            elif percentage >= 50:
                bar = self.colorize(bar, "YELLOW")
            else:
                bar = self.colorize(bar, "RED")
        
        if show_percentage:
            return f"|{bar}| {percentage:5.1f}%"
        else:
            return f"|{bar}|"
    
    def format_emotion_score(self, emotion: EmotionCategory, score: float,
                           bar_width: int = 20) -> str:
        """
        Format an emotion score with visual bar.
        
        Args:
            emotion: Emotion category
            score: Score value (0-100)
            bar_width: Width of the visual bar
            
        Returns:
            Formatted emotion score line
        """
        # Get emotion-specific color
        emotion_color = UIConstants.EMOTION_COLORS.get(emotion, "WHITE")
        
        # Format emotion name
        emotion_name = emotion.value.capitalize()
        if self.config.use_colors:
            emotion_name = self.colorize(emotion_name, emotion_color)
        
        # Create visual bar
        bar_filled = int((score / 100) * bar_width)
        bar = "█" * bar_filled + "░" * (bar_width - bar_filled)
        
        if self.config.use_colors:
            bar = self.colorize(bar, emotion_color)
        
        # Format score percentage
        score_text = f"{score:5.1f}%"
        if self.config.use_colors:
            if score >= 70:
                score_text = self.colorize(score_text, "GREEN")
            elif score >= 40:
                score_text = self.colorize(score_text, "YELLOW")
            else:
                score_text = self.colorize(score_text, "RED")
        
        return f"  {emotion_name:12} {score_text:>8} |{bar}|"
    
    def format_analysis_results(self, session: AnalysisSession) -> str:
        """
        Format complete analysis results for display.
        
        Args:
            session: Analysis session with results
            
        Returns:
            Formatted analysis display
        """
        if not session.is_successful or not session.analysis_result:
            return self.colorize("❌ Analysis failed or incomplete", "RED")
        
        result = session.analysis_result
        song = session.song
        
        lines = []
        
        # Header
        lines.append(self.format_header("Emotion Analysis Results", level=1))
        
        # Song information
        lines.append(f"\n{self.bold('Song:')} {song.metadata.title}")
        lines.append(f"{self.bold('Artist:')} {song.metadata.artist_name}")
        if song.metadata.album:
            lines.append(f"{self.bold('Album:')} {song.metadata.album}")
        
        # Emotion scores
        lines.append(self.format_header("Emotion Scores", level=3))
        
        for emotion, score_obj in result.emotion_scores.items():
            lines.append(self.format_emotion_score(emotion, score_obj.score))
        
        # Summary information
        lines.append(f"\n{self.format_summary_info(result)}")
        
        return "\n".join(lines)
    
    def format_summary_info(self, result: EmotionAnalysisResult) -> str:
        """Format analysis summary information"""
        lines = []
        
        # Dominant emotion
        dominant_emoji = self._get_emotion_emoji(result.dominant_emotion)
        dominant_text = f"{dominant_emoji} Dominant Emotion: {result.dominant_emotion.value.upper()}"
        lines.append(self.bold(self.colorize(dominant_text, "CYAN")))
        
        # Confidence score
        confidence_emoji = "📊"
        confidence_color = "GREEN" if result.is_high_confidence else "YELLOW"
        confidence_text = f"{confidence_emoji} Confidence: {result.overall_confidence:.1%}"
        lines.append(self.colorize(confidence_text, confidence_color))
        
        # Quality indicator
        quality_emoji = {"High": "⭐", "Medium": "⚡", "Low": "⚠️"}.get(result.analysis_quality, "❓")
        quality_text = f"{quality_emoji} Quality: {result.analysis_quality}"
        lines.append(quality_text)
        
        # Processing time
        if result.processing_time:
            time_emoji = "⏱️"
            time_text = f"{time_emoji} Processing Time: {result.processing_time:.2f}s"
            lines.append(self.colorize(time_text, "BLUE"))
        
        return "\n".join(lines)
    
    def _get_emotion_emoji(self, emotion: EmotionCategory) -> str:
        """Get emoji for emotion category"""
        if not self.config.use_emoji:
            return ""
        
        emoji_map = {
            EmotionCategory.HAPPINESS: "😊",
            EmotionCategory.SADNESS: "😢",
            EmotionCategory.ANGER: "😠",
            EmotionCategory.FEAR: "😨",
            EmotionCategory.LOVE: "❤️"
        }
        return emoji_map.get(emotion, "🎵")
    
    def format_table(self, headers: List[str], rows: List[List[str]],
                    column_widths: Optional[List[int]] = None) -> str:
        """
        Format data as a table.
        
        Args:
            headers: Table headers
            rows: Table rows
            column_widths: Optional column widths
            
        Returns:
            Formatted table
        """
        if not rows:
            return "No data to display"
        
        # Calculate column widths if not provided
        if column_widths is None:
            column_widths = []
            for i in range(len(headers)):
                max_width = len(headers[i])
                for row in rows:
                    if i < len(row):
                        max_width = max(max_width, len(str(row[i])))
                column_widths.append(min(max_width, 25))  # Cap at 25 chars
        
        lines = []
        
        # Table header
        header_line = " | ".join(
            f"{header:<{width}}" for header, width in zip(headers, column_widths)
        )
        lines.append(self.bold(header_line))
        
        # Separator line
        separator = "-+-".join("-" * width for width in column_widths)
        lines.append(separator)
        
        # Table rows
        for row in rows:
            row_line = " | ".join(
                f"{str(cell):<{width}}" if i < len(row) else f"{'':>{width}}"
                for i, (cell, width) in enumerate(zip(row + [""] * len(column_widths), column_widths))
            )
            lines.append(row_line)
        
        return "\n".join(lines)
    
    def format_song_info(self, song: Song, include_lyrics_preview: bool = True) -> str:
        """
        Format song information display.
        
        Args:
            song: Song object
            include_lyrics_preview: Whether to include lyrics preview
            
        Returns:
            Formatted song information
        """
        lines = []
        
        # Basic information
        lines.append(self.format_header("Song Information", level=2))
        lines.append(f"{self.bold('Title:')} {song.metadata.title}")
        lines.append(f"{self.bold('Artist:')} {song.metadata.artist_name}")
        
        if song.metadata.album:
            lines.append(f"{self.bold('Album:')} {song.metadata.album}")
        
        if song.metadata.release_date:
            lines.append(f"{self.bold('Release Date:')} {song.metadata.release_date}")
        
        # Lyrics information
        if song.has_lyrics:
            stats = song.lyrics.summary_stats
            lines.append(f"\n{self.bold('Lyrics Statistics:')}")
            lines.append(f"  Words: {stats['word_count']}")
            lines.append(f"  Lines: {stats['line_count']}")
            lines.append(f"  Characters: {stats['character_count']}")
            
            if stats['verse_count'] > 0:
                lines.append(f"  Verses: {stats['verse_count']}")
            if stats['chorus_count'] > 0:
                lines.append(f"  Choruses: {stats['chorus_count']}")
            
            # Lyrics preview
            if include_lyrics_preview:
                lines.append(f"\n{self.bold('Lyrics Preview:')}")
                preview = song.get_lyrics_preview(200)
                lines.append(f"  {preview}")
        else:
            lines.append(self.colorize("\n❌ No lyrics available", "RED"))
        
        return "\n".join(lines)
    
    def format_error(self, error: str, context: Optional[str] = None) -> str:
        """Format error message"""
        error_text = f"❌ {error}"
        if context:
            error_text += f" ({context})"
        
        return self.colorize(error_text, "RED")
    
    def format_success(self, message: str) -> str:
        """Format success message"""
        return self.colorize(f"✅ {message}", "GREEN")
    
    def format_warning(self, message: str) -> str:
        """Format warning message"""
        return self.colorize(f"⚠️ {message}", "YELLOW")
    
    def format_info(self, message: str) -> str:
        """Format info message"""
        return self.colorize(f"ℹ️ {message}", "BLUE")
    
    def create_separator(self, char: str = "-", width: Optional[int] = None) -> str:
        """Create a separator line"""
        separator_width = width or self.config.max_width
        return char * separator_width
    
    def center_text(self, text: str, width: Optional[int] = None,
                   fill_char: str = " ") -> str:
        """Center text within specified width"""
        center_width = width or self.config.max_width
        return text.center(center_width, fill_char)


# Factory function for creating formatter
def create_formatter(theme: ColorTheme = ColorTheme.DEFAULT,
                    max_width: int = 80) -> OutputFormatter:
    """
    Factory function to create output formatter.
    
    Args:
        theme: Color theme to use
        max_width: Maximum display width
        
    Returns:
        OutputFormatter instance
    """
    display_config = DisplayConfig(
        use_colors=config.enable_color_output,
        theme=theme,
        max_width=max_width
    )
    return OutputFormatter(display_config)