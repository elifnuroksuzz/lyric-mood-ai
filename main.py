import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.config_manager import config
from src.core.exceptions import (
    LyricMoodBaseException, ConfigurationError, 
    LyricsNotFoundError, AnalysisError
)
from src.services.genius_service import create_genius_service
from src.services.ai_analysis_service import create_analysis_service
from src.services.file_service import create_file_service
from src.models.emotion_analysis import AnalysisSession, AnalysisHistory, AnalysisStatus
from src.utils.logger import logger
from src.utils.validators import validate_song_input
from src.ui.terminal_interface import create_terminal_interface, MenuOption
from src.ui.output_formatter import ColorTheme


class LyricMoodApp:
    """
    Main application class for LyricMood-AI.
    
    Orchestrates all services and handles the application workflow.
    """
    
    def __init__(self):
        """Initialize the application"""
        try:
            logger.info(f"Initializing {config.app_name} v{config.app_version}")
            
            # Initialize services
            self.genius_service = create_genius_service(use_cache=True)
            self.analysis_service = create_analysis_service(use_cache=True)
            self.file_service = create_file_service()
            
            # Initialize UI
            self.ui = create_terminal_interface(ColorTheme.DEFAULT)
            
            # Initialize analysis history
            self.analysis_history = AnalysisHistory()
            
            logger.info("Application initialized successfully")
            
        except ConfigurationError as e:
            logger.critical(f"Configuration error: {e}")
            print(f"❌ Configuration Error: {e}")
            sys.exit(1)
        except Exception as e:
            logger.critical(f"Failed to initialize application: {e}")
            print(f"❌ Initialization Error: {e}")
            sys.exit(1)
    
    def run(self):
        """Run the main application"""
        try:
            self.ui.start()
            self._validate_api_connections()
            self._main_menu_loop()
            
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
            self.ui.display_info("Application terminated by user.")
        except Exception as e:
            logger.critical(f"Unexpected error in main application: {e}", exc_info=True)
            self.ui.display_error(e, "main application")
            sys.exit(1)
        finally:
            self.ui.stop()
    
    def _validate_api_connections(self):
        """Validate all API connections"""
        self.ui.display_info("Validating API connections...")
        
        try:
            # Validate Genius API
            self.genius_service.validate_connection()
            self.ui.display_success("Genius API connection validated")
            
            # Validate Groq AI API
            self.analysis_service.groq_service.validate_connection()
            self.ui.display_success("Groq AI API connection validated")
            
        except Exception as e:
            self.ui.display_error(e, "API validation")
            sys.exit(1)
    
    def _main_menu_loop(self):
        """Main application menu loop"""
        menu_options = [
            MenuOption("1", "🎵 Analyze Song Lyrics", "Analyze emotions in a single song", self._analyze_song),
            MenuOption("2", "📊 View Analysis History", "Review past analysis results", self._view_analysis_history),
            MenuOption("3", "🔄 Batch Analysis", "Analyze multiple songs", self._batch_analysis),
            MenuOption("4", "📈 View Statistics", "Application performance metrics", self._view_statistics),
            MenuOption("5", "ℹ️ Help & About", "Usage guide and information", self._show_help_about),
            MenuOption("6", "🚪 Exit", "Close the application", self._exit_application)
        ]
        
        while self.ui.is_running():
            try:
                selected = self.ui.create_menu("Main Menu", menu_options)
                selected.action()
            except KeyboardInterrupt:
                self.ui.display_warning("Operation cancelled.")
            except Exception as e:
                self.ui.display_error(e, "menu operation")
            
            if self.ui.is_running():
                self.ui.wait_for_keypress()
    
    def _analyze_song(self):
        """Handle single song analysis"""
        try:
            # Get user input using UI
            song_name, artist_name = self.ui.prompt_song_details()
            
            # Validate input
            try:
                song_name, artist_name = validate_song_input(song_name, artist_name)
            except Exception as e:
                self.ui.display_error(e, "input validation")
                return
            
            # Create analysis session
            session_id = str(uuid.uuid4())[:8]
            
            self.ui.display_info(f"Starting analysis for '{song_name}' by '{artist_name}'...")
            
            # Fetch song data
            try:
                self.ui.display_loading("Fetching song data", 1.5)
                song = self.genius_service.find_and_fetch_song(song_name, artist_name)
                self.ui.display_success(f"Found: {song.full_title}")
            except LyricsNotFoundError:
                self.ui.display_error(Exception("Song or lyrics not found. Please check the song name and artist."))
                return
            except Exception as e:
                self.ui.display_error(e, "song retrieval")
                return
            
            # Display song info
            self.ui.display_song_info(song, include_lyrics=True)
            
            # Confirm analysis
            if not self.ui.prompt_yes_no("Proceed with emotion analysis?", default=True):
                self.ui.display_info("Analysis cancelled.")
                return
            
            # Create analysis session
            session = AnalysisSession(
                session_id=session_id,
                song=song,
                status=AnalysisStatus.IN_PROGRESS
            )
            
            # Perform emotion analysis
            try:
                self.ui.display_loading("Analyzing emotions", 2.0)
                analysis_result = self.analysis_service.analyze_song(song)
                session.mark_completed(analysis_result)
                self.ui.display_success("Analysis completed!")
            except AnalysisError as e:
                session.mark_failed(str(e))
                self.ui.display_error(e, "emotion analysis")
                return
            except Exception as e:
                session.mark_failed(str(e))
                self.ui.display_error(e, "unexpected analysis error")
                return
            
            # Display results
            self.ui.display_analysis_results(session)
            
            # Save results
            if config.enable_file_output:
                self._save_analysis_results(session)
            
            # Add to history
            self.analysis_history.add_session(session)
            
        except Exception as e:
            logger.error(f"Error in song analysis: {e}", exc_info=True)
            self.ui.display_error(e, "song analysis")
    
    def _save_analysis_results(self, session: AnalysisSession):
        """Save analysis results to file"""
        try:
            save_format = self.ui.display_save_options()
            if not save_format:
                return
            
            if save_format == "txt":
                file_path = self.file_service.save_analysis_txt(session)
            elif save_format == "json":
                file_path = self.file_service.save_analysis_json(session)
            else:
                self.ui.display_warning("CSV format requires multiple sessions. Saving as TXT.")
                file_path = self.file_service.save_analysis_txt(session)
            
            self.ui.display_success(f"Results saved to: {file_path}")
            
        except Exception as e:
            self.ui.display_error(e, "file save")
    
    def _view_analysis_history(self):
        """Display analysis history"""
        self.ui.display_analysis_history(self.analysis_history)
    
    def _batch_analysis(self):
        """Handle batch analysis of multiple songs"""
        self.ui.display_info("🔄 Batch Analysis")
        self.ui.display_info("This feature allows analysis of multiple songs from a file.")
        self.ui.display_warning("Feature coming in next update!")
    
    def _view_statistics(self):
        """Display application statistics"""
        # Gather statistics
        stats = {
            "analysis": {
                "total": self.analysis_history.total_sessions,
                "successful": self.analysis_history.successful_sessions_count,
                "success_rate": self.analysis_history.success_rate
            },
            "cache": self.analysis_service.get_cache_stats(),
            "storage": self.file_service.get_storage_stats()
        }
        
        self.ui.display_statistics(stats)
    
    def _show_help_about(self):
        """Show help and about information"""
        help_menu = [
            MenuOption("1", "📖 Help Guide", "Usage instructions and tips", lambda: self.ui.display_help()),
            MenuOption("2", "ℹ️ About", "Application information", lambda: self.ui.display_about()),
            MenuOption("3", "🔙 Back", "Return to main menu", lambda: None)
        ]
        
        selected = self.ui.create_menu("Help & About", help_menu)
        selected.action()
    
    def _exit_application(self):
        """Exit the application"""
        if self.ui.confirm_action("Exit LyricMood-AI", "All unsaved data will be lost"):
            self.ui.stop()

def main():
    """Main entry point"""
    try:
        app = LyricMoodApp()
        app.run()
        
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()