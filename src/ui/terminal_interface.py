"""
Terminal Interface for LyricMood-AI Application

This module provides a comprehensive terminal-based user interface with
menu systems, interactive prompts, and professional display formatting.
"""

import sys
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime

from ..core.config_manager import config
from ..core.constants import UIConstants
from ..core.exceptions import LyricMoodBaseException
from ..models.emotion_analysis import AnalysisSession, AnalysisHistory
from ..models.song_data import Song
from ..utils.logger import logger
from .output_formatter import OutputFormatter, ColorTheme, create_formatter


@dataclass
class MenuOption:
    """Represents a menu option"""
    key: str
    label: str
    description: str
    action: Callable
    enabled: bool = True


class TerminalInputValidator:
    """Helper class for validating user input"""
    
    @staticmethod
    def validate_menu_choice(choice: str, valid_options: List[str]) -> bool:
        """Validate menu choice"""
        return choice.strip().lower() in [opt.lower() for opt in valid_options]
    
    @staticmethod
    def validate_yes_no(input_str: str) -> Optional[bool]:
        """Validate yes/no input"""
        normalized = input_str.strip().lower()
        if normalized in ['y', 'yes', '1', 'true']:
            return True
        elif normalized in ['n', 'no', '0', 'false']:
            return False
        return None
    
    @staticmethod
    def validate_non_empty(input_str: str) -> bool:
        """Validate non-empty input"""
        return bool(input_str.strip())


class TerminalInterface:
    """
    Professional terminal interface for LyricMood-AI.
    
    Provides a complete user interface with menus, prompts, displays,
    and interactive elements with consistent styling and error handling.
    """
    
    def __init__(self, formatter: Optional[OutputFormatter] = None):
        """
        Initialize terminal interface.
        
        Args:
            formatter: Output formatter instance
        """
        self.formatter = formatter or create_formatter()
        self.validator = TerminalInputValidator()
        self._running = False
        self._current_menu = "main"
        
        # Interface state
        self.show_timestamps = True
        self.auto_clear_screen = False
        self.prompt_prefix = "LyricMood"
        
        logger.info("Terminal interface initialized")
    
    def start(self) -> None:
        """Start the terminal interface"""
        self._running = True
        self.display_welcome()
        logger.log_user_action("interface_started")
    
    def stop(self) -> None:
        """Stop the terminal interface"""
        self._running = False
        self.display_goodbye()
        logger.log_user_action("interface_stopped")
    
    def is_running(self) -> bool:
        """Check if interface is running"""
        return self._running
    
    def clear_screen(self) -> None:
        """Clear the terminal screen"""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def display_welcome(self) -> None:
        """Display welcome screen"""
        if self.auto_clear_screen:
            self.clear_screen()
        
        welcome_lines = [
            self.formatter.create_separator("=", 70),
            self.formatter.center_text(f"🎵 {config.app_name} v{config.app_version} 🎵", 70),
            self.formatter.center_text("Professional Song Emotion Analysis", 70),
            self.formatter.create_separator("=", 70),
            "",
            self.formatter.colorize("Welcome to the most advanced lyrics emotion analyzer!", "CYAN"),
            "",
            "Features:",
            "• 🎯 AI-powered emotion detection",
            "• 🎵 Automatic lyrics retrieval",
            "• 📊 Professional analysis reports",
            "• 💾 Multiple output formats",
            "",
            self.formatter.create_separator("-", 70)
        ]
        
        for line in welcome_lines:
            print(line)
        
        # Show current timestamp
        if self.show_timestamps:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(self.formatter.colorize(f"Session started: {timestamp}", "BLUE"))
        
        print()
    
    def display_goodbye(self) -> None:
        """Display goodbye message"""
        goodbye_lines = [
            "",
            self.formatter.create_separator("=", 50),
            self.formatter.center_text("👋 Thank you for using LyricMood-AI!", 50),
            self.formatter.center_text("Music brings emotions to life", 50),
            self.formatter.create_separator("=", 50),
            ""
        ]
        
        for line in goodbye_lines:
            print(line)
    
    def display_main_menu(self) -> str:
        """
        Display main menu and get user choice.
        
        Returns:
            User's menu choice
        """
        menu_options = [
            "1. 🎵 Analyze Song Lyrics",
            "2. 📊 View Analysis History", 
            "3. 🔄 Batch Analysis",
            "4. ⚙️  Settings & Statistics",
            "5. ℹ️  Help & About",
            "6. 🚪 Exit"
        ]
        
        print(self.formatter.format_header("Main Menu", level=2))
        
        for option in menu_options:
            print(f"  {option}")
        
        print()
        return self.prompt_user("Select an option (1-6)")
    
    def prompt_user(self, message: str, validation_func: Optional[Callable] = None,
                   error_message: str = "Invalid input. Please try again.",
                   max_attempts: int = 3) -> str:
        """
        Prompt user for input with validation.
        
        Args:
            message: Prompt message
            validation_func: Function to validate input
            error_message: Error message for invalid input
            max_attempts: Maximum number of attempts
            
        Returns:
            Validated user input
        """
        attempts = 0
        
        while attempts < max_attempts:
            try:
                prompt_text = f"{self.formatter.colorize(self.prompt_prefix, 'CYAN')}> {message}: "
                user_input = input(prompt_text).strip()
                
                if validation_func and not validation_func(user_input):
                    print(self.formatter.format_error(error_message))
                    attempts += 1
                    continue
                
                logger.log_user_action("user_input", prompt=message, input_length=len(user_input))
                return user_input
                
            except KeyboardInterrupt:
                print(self.formatter.format_warning("\nOperation cancelled by user."))
                raise
            except EOFError:
                print(self.formatter.format_error("\nUnexpected end of input."))
                raise
        
        raise ValueError(f"Maximum attempts ({max_attempts}) exceeded for user input")
    
    def prompt_song_details(self) -> Tuple[str, str]:
        """
        Prompt user for song and artist details.
        
        Returns:
            Tuple of (song_name, artist_name)
        """
        print(self.formatter.format_header("Song Details", level=3))
        
        song_name = self.prompt_user(
            "Enter song name",
            validation_func=self.validator.validate_non_empty,
            error_message="Song name cannot be empty"
        )
        
        artist_name = self.prompt_user(
            "Enter artist name", 
            validation_func=self.validator.validate_non_empty,
            error_message="Artist name cannot be empty"
        )
        
        return song_name, artist_name
    
    def prompt_yes_no(self, message: str, default: Optional[bool] = None) -> bool:
        """
        Prompt user for yes/no response.
        
        Args:
            message: Prompt message
            default: Default value if user just presses enter
            
        Returns:
            Boolean response
        """
        default_text = ""
        if default is True:
            default_text = " [Y/n]"
        elif default is False:
            default_text = " [y/N]"
        else:
            default_text = " [y/n]"
        
        while True:
            response = self.prompt_user(f"{message}{default_text}")
            
            if not response and default is not None:
                return default
            
            validated = self.validator.validate_yes_no(response)
            if validated is not None:
                return validated
            
            print(self.formatter.format_error("Please enter 'y' for yes or 'n' for no."))
    
    def prompt_choice(self, message: str, choices: List[str],
                     case_sensitive: bool = False) -> str:
        """
        Prompt user to choose from a list of options.
        
        Args:
            message: Prompt message
            choices: List of valid choices
            case_sensitive: Whether choices are case sensitive
            
        Returns:
            User's choice
        """
        choices_display = ", ".join(choices)
        full_message = f"{message} ({choices_display})"
        
        def validate_choice(input_str: str) -> bool:
            if case_sensitive:
                return input_str in choices
            else:
                return input_str.lower() in [c.lower() for c in choices]
        
        response = self.prompt_user(
            full_message,
            validation_func=validate_choice,
            error_message=f"Please choose from: {choices_display}"
        )
        
        # Return the original case from choices if not case sensitive
        if not case_sensitive:
            for choice in choices:
                if choice.lower() == response.lower():
                    return choice
        
        return response
    
    def display_progress(self, message: str, current: int, total: int) -> None:
        """
        Display progress information.
        
        Args:
            message: Progress message
            current: Current progress value
            total: Total/maximum value
        """
        progress_bar = self.formatter.format_progress_bar(current, total)
        progress_line = f"\r{message}: {progress_bar}"
        
        print(progress_line, end="", flush=True)
        
        if current >= total:
            print()  # New line when complete
    
    def display_loading(self, message: str, duration: float = 2.0) -> None:
        """
        Display loading animation.
        
        Args:
            message: Loading message
            duration: Duration in seconds
        """
        spinner_chars = "|/-\\"
        steps = int(duration * 10)  # 10 FPS
        
        for i in range(steps):
            spinner = spinner_chars[i % len(spinner_chars)]
            loading_line = f"\r{self.formatter.colorize(spinner, 'YELLOW')} {message}..."
            print(loading_line, end="", flush=True)
            time.sleep(0.1)
        
        print(f"\r{self.formatter.format_success(f'{message} completed!')}")
    
    def display_song_info(self, song: Song, include_lyrics: bool = False) -> None:
        """
        Display song information.
        
        Args:
            song: Song object to display
            include_lyrics: Whether to include lyrics preview
        """
        formatted_info = self.formatter.format_song_info(song, include_lyrics)
        print(formatted_info)
    
    def display_analysis_results(self, session: AnalysisSession) -> None:
        """
        Display emotion analysis results.
        
        Args:
            session: Analysis session with results
        """
        if not session.is_successful:
            print(self.formatter.format_error(f"Analysis failed: {session.error_message}"))
            return
        
        # Display additional insights
        if session.analysis_result:
            self._display_analysis_insights(session.analysis_result)
    
    def _display_analysis_insights(self, result) -> None:
        """Display additional analysis insights"""
        print(f"\n{self.formatter.format_header('Analysis Insights', level=3)}")
        
        # Top emotions
        top_emotions = result.get_top_emotions(3)
        print("Top 3 Emotions:")
        for i, (emotion, score) in enumerate(top_emotions, 1):
            emoji = self.formatter._get_emotion_emoji(emotion)
            print(f"  {i}. {emoji} {emotion.value.capitalize()}: {score.percentage_display}")
        
        # Analysis summary
        print(f"\n{self.formatter.bold('Summary:')}")
        print(f"  {result.get_summary_text()}")
        
        # Confidence assessment
        if result.is_high_confidence:
            confidence_msg = "High confidence - Results are very reliable"
            confidence_color = "GREEN"
        elif result.overall_confidence > 0.5:
            confidence_msg = "Medium confidence - Results are moderately reliable"
            confidence_color = "YELLOW"
        else:
            confidence_msg = "Low confidence - Results should be interpreted carefully"
            confidence_color = "RED"
        
        print(f"\n{self.formatter.colorize(f'📊 {confidence_msg}', confidence_color)}")
    
    def display_analysis_history(self, history: AnalysisHistory, limit: int = 10) -> None:
        """
        Display analysis history in table format.
        
        Args:
            history: Analysis history object
            limit: Maximum number of entries to show
        """
        if not history.sessions:
            print(self.formatter.format_info("No analysis history available."))
            return
        
        print(self.formatter.format_header("Analysis History", level=2))
        
        recent_sessions = history.get_recent_sessions(limit)
        
        # Prepare table data
        headers = ["#", "Song", "Artist", "Dominant Emotion", "Confidence", "Date", "Status"]
        rows = []
        
        for i, session in enumerate(recent_sessions, 1):
            if session.is_successful and session.analysis_result:
                emotion = session.analysis_result.dominant_emotion.value.capitalize()
                confidence = f"{session.analysis_result.overall_confidence:.1%}"
                status = "✅ Success"
            else:
                emotion = "N/A"
                confidence = "N/A"
                status = "❌ Failed"
            
            date_str = session.completed_at.strftime("%m/%d %H:%M") if session.completed_at else "Pending"
            
            row = [
                str(i),
                session.song.metadata.title[:20] + ("..." if len(session.song.metadata.title) > 20 else ""),
                session.song.metadata.artist_name[:15] + ("..." if len(session.song.metadata.artist_name) > 15 else ""),
                emotion,
                confidence,
                date_str,
                status
            ]
            rows.append(row)
        
        # Display table
        table = self.formatter.format_table(headers, rows)
        print(table)
        
        # Summary statistics
        print(f"\n{self.formatter.bold('Statistics:')}")
        print(f"  Total Sessions: {history.total_sessions}")
        print(f"  Successful: {history.successful_sessions_count}")
        print(f"  Success Rate: {history.success_rate:.1%}")
    
    def display_statistics(self, stats: Dict[str, Any]) -> None:
        """
        Display application statistics.
        
        Args:
            stats: Statistics dictionary
        """
        print(self.formatter.format_header("Application Statistics", level=2))
        
        # Analysis statistics
        if "analysis" in stats:
            analysis_stats = stats["analysis"]
            print(f"{self.formatter.bold('Analysis Statistics:')}")
            print(f"  Total Analyses: {analysis_stats.get('total', 0)}")
            print(f"  Successful: {analysis_stats.get('successful', 0)}")
            print(f"  Success Rate: {analysis_stats.get('success_rate', 0):.1%}")
            print()
        
        # Cache statistics
        if "cache" in stats:
            cache_stats = stats["cache"]
            print(f"{self.formatter.bold('Cache Statistics:')}")
            print(f"  Cache Enabled: {'Yes' if cache_stats.get('enabled', False) else 'No'}")
            print(f"  Cached Items: {cache_stats.get('items', 0)}")
            print(f"  Cache Size: {cache_stats.get('size_mb', 0):.2f} MB")
            print(f"  Hit Rate: {cache_stats.get('hit_rate', 0):.1%}")
            print()
        
        # Storage statistics
        if "storage" in stats:
            storage_stats = stats["storage"]
            print(f"{self.formatter.bold('Storage Statistics:')}")
            print(f"  Output Files: {storage_stats.get('total_files', 0)}")
            print(f"  Total Size: {storage_stats.get('total_size_mb', 0):.2f} MB")
            print(f"  Output Directory: {storage_stats.get('directory', 'N/A')}")
            print()
        
        # Performance statistics
        if "performance" in stats:
            perf_stats = stats["performance"]
            print(f"{self.formatter.bold('Performance Statistics:')}")
            print(f"  Average Analysis Time: {perf_stats.get('avg_analysis_time', 0):.2f}s")
            print(f"  API Response Time: {perf_stats.get('avg_api_time', 0):.2f}s")
            print(f"  Uptime: {perf_stats.get('uptime', 'N/A')}")
    
    def display_error(self, error: Exception, context: Optional[str] = None) -> None:
        """
        Display error information with proper formatting.
        
        Args:
            error: Exception object
            context: Additional context information
        """
        if isinstance(error, LyricMoodBaseException):
            error_msg = str(error)
            if hasattr(error, 'error_code') and error.error_code:
                error_msg = f"[{error.error_code}] {error_msg}"
        else:
            error_msg = str(error)
        
        formatted_error = self.formatter.format_error(error_msg, context)
        print(formatted_error)
        
        # Log the error
        logger.error(f"UI Error: {error_msg}", exc_info=True, context=context)
    
    def display_warning(self, message: str) -> None:
        """Display warning message"""
        print(self.formatter.format_warning(message))
    
    def display_info(self, message: str) -> None:
        """Display info message"""
        print(self.formatter.format_info(message))
    
    def display_success(self, message: str) -> None:
        """Display success message"""
        print(self.formatter.format_success(message))
    
    def confirm_action(self, action: str, consequences: Optional[str] = None) -> bool:
        """
        Ask user to confirm an action.
        
        Args:
            action: Description of the action
            consequences: Optional description of consequences
            
        Returns:
            True if user confirms
        """
        print(f"\n{self.formatter.colorize('⚠️ Confirmation Required', 'YELLOW')}")
        print(f"Action: {action}")
        
        if consequences:
            print(f"Consequences: {consequences}")
        
        return self.prompt_yes_no("Do you want to proceed?", default=False)
    
    def display_save_options(self) -> Optional[str]:
        """
        Display save options and get user choice.
        
        Returns:
            Selected save format or None if cancelled
        """
        if not self.prompt_yes_no("Save analysis results?", default=True):
            return None
        
        save_formats = ["txt", "json", "csv"]
        format_choice = self.prompt_choice(
            "Choose save format",
            save_formats,
            case_sensitive=False
        )
        
        return format_choice.lower()
    
    def display_batch_progress(self, current: int, total: int, 
                             current_song: Optional[str] = None) -> None:
        """
        Display batch analysis progress.
        
        Args:
            current: Current song number
            total: Total number of songs
            current_song: Name of current song being processed
        """
        progress_msg = f"Analyzing songs ({current}/{total})"
        if current_song:
            progress_msg += f" - {current_song}"
        
        self.display_progress(progress_msg, current, total)
    
    def display_help(self) -> None:
        """Display help information"""
        help_content = [
            self.formatter.format_header("Help & Usage Guide", level=1),
            "",
            f"{self.formatter.bold('Getting Started:')}",
            "1. Select 'Analyze Song Lyrics' from the main menu",
            "2. Enter the song name and artist name when prompted",
            "3. Wait for the analysis to complete",
            "4. View results and optionally save them",
            "",
            f"{self.formatter.bold('Features:')}",
            "• 🎵 Single song emotion analysis",
            "• 📊 Analysis history tracking",
            "• 🔄 Batch processing (coming soon)",
            "• 💾 Multiple output formats (TXT, JSON, CSV)",
            "• 📈 Performance statistics",
            "",
            f"{self.formatter.bold('Emotion Categories:')}",
            "• 😊 Happiness - Joy, contentment, positive emotions",
            "• 😢 Sadness - Melancholy, grief, sorrow",
            "• 😠 Anger - Rage, frustration, hostility",
            "• 😨 Fear - Anxiety, worry, dread",
            "• ❤️ Love - Affection, romance, caring",
            "",
            f"{self.formatter.bold('Tips for Best Results:')}",
            "• Use exact song titles when possible",
            "• Include featured artists in the artist field",
            "• Try alternative spellings if a song isn't found",
            "• Popular songs generally have better lyrics data",
            "",
            f"{self.formatter.bold('Keyboard Shortcuts:')}",
            "• Ctrl+C - Cancel current operation",
            "• Enter - Accept default option (when available)",
            "",
            f"{self.formatter.bold('Troubleshooting:')}",
            "• If a song isn't found, check spelling and try variations",
            "• For connection errors, check your internet connection",
            "• Contact support if you encounter persistent issues",
            "",
            self.formatter.create_separator("-", 50)
        ]
        
        for line in help_content:
            print(line)
    
    def display_about(self) -> None:
        """Display about information"""
        about_content = [
            self.formatter.format_header("About LyricMood-AI", level=1),
            "",
            f"{self.formatter.bold('Application Information:')}",
            f"  Name: {config.app_name}",
            f"  Version: {config.app_version}",
            f"  Description: Professional Song Emotion Analysis",
            "",
            f"{self.formatter.bold('Technology Stack:')}",
            "  • Genius API - Lyrics data retrieval",
            "  • Groq AI - Advanced emotion analysis",
            "  • Python 3.8+ - Core application",
            "  • Beautiful Soup - Web scraping",
            "",
            f"{self.formatter.bold('Features:')}",
            "  • AI-powered emotion detection",
            "  • Professional analysis reports",
            "  • Multiple output formats",
            "  • Comprehensive error handling",
            "  • Performance monitoring",
            "  • Intelligent caching",
            "",
            f"{self.formatter.bold('Developer:')}",
            "  Mustafa Kemal Çıngıl",
            "  LinkedIn: linkedin.com/in/mustafakemalcingil",
            "  GitHub: github.com/mustafakemal0146",
            "",
            f"{self.formatter.bold('License:')}",
            "  MIT License - Free for personal and commercial use",
            "",
            self.formatter.center_text("🎵 Thank you for using LyricMood-AI! 🎵", 50),
            self.formatter.create_separator("-", 50)
        ]
        
        for line in about_content:
            print(line)
    
    def wait_for_keypress(self, message: str = "Press Enter to continue...") -> None:
        """Wait for user to press a key"""
        try:
            input(f"\n{self.formatter.colorize(message, 'BLUE')}")
        except KeyboardInterrupt:
            pass
    
    def create_menu(self, title: str, options: List[MenuOption]) -> MenuOption:
        """
        Create and display a menu, return selected option.
        
        Args:
            title: Menu title
            options: List of menu options
            
        Returns:
            Selected menu option
        """
        while True:
            print(self.formatter.format_header(title, level=2))
            
            # Display options
            valid_keys = []
            for option in options:
                if option.enabled:
                    status_indicator = ""
                    valid_keys.append(option.key)
                else:
                    status_indicator = self.formatter.colorize(" (disabled)", "RED")
                
                print(f"  {option.key}. {option.label}{status_indicator}")
                if option.description:
                    print(f"     {self.formatter.colorize(option.description, 'BLUE')}")
            
            print()
            
            # Get user choice
            choice = self.prompt_user(f"Select option ({'/'.join(valid_keys)})")
            
            # Find matching option
            for option in options:
                if option.key.lower() == choice.lower() and option.enabled:
                    logger.log_user_action("menu_selection", menu=title, option=option.label)
                    return option
            
            print(self.formatter.format_error("Invalid option. Please try again."))
            print()


# Factory function for creating terminal interface
def create_terminal_interface(theme: ColorTheme = ColorTheme.DEFAULT) -> TerminalInterface:
    """
    Factory function to create terminal interface.
    
    Args:
        theme: Color theme for the interface
        
    Returns:
        TerminalInterface instance
    """
    formatter = create_formatter(theme)
    return TerminalInterface(formatter)