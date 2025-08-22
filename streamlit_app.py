"""
Streamlit Web UI for LyricMood-AI - Turkish Interface

Modern web interface for song emotion analysis with real-time updates,
interactive charts, and professional design in Turkish.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import time
import uuid
from datetime import datetime
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.config_manager import config
from src.core.exceptions import LyricsNotFoundError, AnalysisError
from src.services.genius_service import create_genius_service
from src.services.ai_analysis_service import create_analysis_service
from src.services.file_service import create_file_service
from src.models.emotion_analysis import AnalysisSession, AnalysisHistory, AnalysisStatus
from src.utils.validators import validate_song_input


# Page configuration
st.set_page_config(
    page_title="LyricMood-AI",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling with fixed text visibility
st.markdown("""
<style>
.main-header {
    text-align: center;
    background: linear-gradient(90deg, #FF6B6B, #4ECDC4, #45B7D1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 3rem;
    font-weight: bold;
    margin-bottom: 1rem;
}

.emotion-card {
    background: white;
    padding: 1rem;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    text-align: center;
    border-left: 4px solid #FF6B6B;
    color: #333333 !important;
}

.emotion-card h3 {
    color: #333333 !important;
    margin: 0.5rem 0;
}

.emotion-card h2 {
    color: #FF6B6B !important;
    margin: 0.5rem 0;
}

.search-result-card {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 8px;
    border-left: 3px solid #007bff;
    margin-bottom: 0.5rem;
    color: #333333 !important;
}

.search-result-card h4 {
    color: #333333 !important;
    margin: 0.5rem 0;
}

.search-result-card p {
    color: #555555 !important;
    margin: 0.5rem 0;
}

.metric-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #ffffff !important;
    padding: 1rem;
    border-radius: 10px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)


class StreamlitApp:
    """Main Streamlit application class"""
    
    def __init__(self):
        """Initialize the application"""
        self.initialize_services()
        self.initialize_session_state()
    
    def initialize_services(self):
        """Initialize backend services"""
        if 'services_initialized' not in st.session_state:
            try:
                with st.spinner("Servisler başlatılıyor..."):
                    self.genius_service = create_genius_service(use_cache=True)
                    self.analysis_service = create_analysis_service(use_cache=True)
                    self.file_service = create_file_service()
                    st.session_state.services_initialized = True
                    st.session_state.genius_service = self.genius_service
                    st.session_state.analysis_service = self.analysis_service
                    st.session_state.file_service = self.file_service
            except Exception as e:
                st.error(f"Servisler başlatılamadı: {e}")
                st.stop()
        else:
            self.genius_service = st.session_state.genius_service
            self.analysis_service = st.session_state.analysis_service
            self.file_service = st.session_state.file_service
    
    def initialize_session_state(self):
        """Initialize session state variables"""
        if 'analysis_history' not in st.session_state:
            st.session_state.analysis_history = AnalysisHistory()
        
        if 'current_analysis' not in st.session_state:
            st.session_state.current_analysis = None
        
        if 'page' not in st.session_state:
            st.session_state.page = "Analiz"
        
        if 'search_results' not in st.session_state:
            st.session_state.search_results = []
        
        if 'search_mode' not in st.session_state:
            st.session_state.search_mode = "combined"
    
    def render_header(self):
        """Render the main header"""
        st.markdown('<h1 class="main-header">🎵 LyricMood-AI</h1>', unsafe_allow_html=True)
        st.markdown("**Profesyonel Şarkı Duygu Analizi**")
        
        # Status indicators
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Uygulama Sürümü", config.app_version)
        with col2:
            st.metric("Toplam Analiz", len(st.session_state.analysis_history.sessions))
        with col3:
            success_rate = st.session_state.analysis_history.success_rate * 100
            st.metric("Başarı Oranı", f"{success_rate:.1f}%")
    
    def render_sidebar(self):
        """Render the sidebar navigation"""
        with st.sidebar:
            st.header("🎛️ Navigasyon")
            
            # Main navigation selectbox with unique key - removed "Hakkında"
            page = st.selectbox(
                "Sayfa Seçin",
                ["🎵 Analiz", "🔍 Arama", "📊 Geçmiş", "📈 İstatistikler"],
                index=0,
                key="main_navigation_selectbox"
            )
            st.session_state.page = page.split(" ", 1)[1]  # Remove emoji
            
            st.divider()
            
            # API Status
            st.subheader("🔗 API Durumu")
            
            # Genius API Status
            try:
                self.genius_service.validate_connection()
                st.success("✅ Genius API")
            except:
                st.error("❌ Genius API")
            
            # Groq AI Status
            try:
                self.analysis_service.groq_service.validate_connection()
                st.success("✅ Groq AI")
            except:
                st.error("❌ Groq AI")
            
            st.divider()
            
            # Quick Stats
            st.subheader("📊 Hızlı İstatistikler")
            history = st.session_state.analysis_history
            st.write(f"📝 Toplam: {history.total_sessions}")
            st.write(f"✅ Başarılı: {history.successful_sessions_count}")
            if history.total_sessions > 0:
                st.write(f"📊 Oran: {history.success_rate:.1%}")
    
    def render_search_page(self):
        """Render the search page for browsing songs"""
        st.header("🔍 Şarkı Arama ve Keşfet")
        
        # Search options
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_query = st.text_input(
                "Arama",
                placeholder="Şarkı adı veya sanatçı adı girin...",
                help="Sadece şarkı adı, sanatçı adı veya ikisini birden arayabilirsiniz",
                key="search_query_input"
            )
        
        with col2:
            search_type = st.selectbox(
                "Arama Türü",
                ["Otomatik", "Sadece Sanatçı", "Sadece Şarkı", "Birleşik"],
                help="Arama türünü seçin",
                key="search_type_selectbox"
            )
        
        # Search button
        if st.button("🔍 Ara", type="primary", use_container_width=True, key="search_button"):
            if search_query:
                self.perform_search(search_query, search_type)
            else:
                st.warning("Lütfen arama terimi girin.")
        
        # Display search results
        if st.session_state.search_results:
            st.subheader(f"📋 Arama Sonuçları ({len(st.session_state.search_results)} adet)")
            
            for i, result in enumerate(st.session_state.search_results[:20]):
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.markdown(f"""
                        <div class="search-result-card">
                            <h4>🎵 {result.title}</h4>
                            <p><strong>🎤 Sanatçı:</strong> {result.artist_name}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        if result.view_count:
                            st.write(f"👁️ Görüntülenme: {result.view_count:,}")
                        if result.thumbnail_url:
                            st.image(result.thumbnail_url, width=100)
                    
                    with col3:
                        if st.button(f"Analiz Et", key=f"analyze_search_result_{i}_{result.song_id}"):
                            self.analyze_from_search_result(result)
                
                st.divider()
    
    def perform_search(self, query: str, search_type: str):
        """Perform search based on type"""
        with st.spinner("Aranıyor..."):
            try:
                # Map Turkish search types to English
                type_mapping = {
                    "Otomatik": "auto",
                    "Sadece Sanatçı": "artist", 
                    "Sadece Şarkı": "song",
                    "Birleşik": "combined"
                }
                
                english_type = type_mapping.get(search_type, "auto")
                results = self.genius_service.smart_search(query, english_type)
                
                st.session_state.search_results = results
                
                if results:
                    st.success(f"✅ {len(results)} sonuç bulundu!")
                else:
                    st.warning("🔍 Sonuç bulunamadı. Farklı arama terimleri deneyin.")
                    
            except Exception as e:
                st.error(f"❌ Arama hatası: {e}")
    
    def analyze_from_search_result(self, search_result):
        """Analyze song from search result"""
        try:
            # Get detailed song info
            with st.spinner("Şarkı bilgileri alınıyor..."):
                song_metadata = self.genius_service.get_song_details(search_result.song_id)
                lyrics_content = self.genius_service.scrape_lyrics(song_metadata.genius_url)
                
                # Create song object
                from src.models.song_data import Song, LyricsData
                lyrics_data = LyricsData(content=lyrics_content)
                song = Song(metadata=song_metadata, lyrics=lyrics_data)
            
            # Perform analysis
            with st.spinner("Duygular analiz ediliyor..."):
                session_id = str(uuid.uuid4())[:8]
                session = AnalysisSession(
                    session_id=session_id,
                    song=song,
                    status=AnalysisStatus.IN_PROGRESS
                )
                
                analysis_result = self.analysis_service.analyze_song(song)
                session.mark_completed(analysis_result)
                
                # Add to history and display
                st.session_state.analysis_history.add_session(session)
                st.session_state.current_analysis = session
                
                # Switch to analysis page and display results
                st.session_state.page = "Analiz"
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ Analiz hatası: {e}")
    
    def render_analyze_page(self):
        """Render the song analysis page"""
        st.header("🎵 Şarkı Duygu Analizi")
        
        # Display current analysis if available
        if st.session_state.current_analysis:
            self.display_analysis_results(st.session_state.current_analysis)
            st.divider()
            st.subheader("🆕 Yeni Analiz")
        
        # Input form
        with st.form("song_analysis_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            
            with col1:
                song_name = st.text_input(
                    "🎵 Şarkı Adı",
                    placeholder="Şarkı adını girin...",
                    help="En iyi sonuçlar için tam şarkı adını girin"
                )
            
            with col2:
                artist_name = st.text_input(
                    "🎤 Sanatçı Adı", 
                    placeholder="Sanatçı adını girin...",
                    help="Ana sanatçı veya grup adını girin"
                )
            
            # Advanced options
            with st.expander("🔧 Gelişmiş Seçenekler"):
                include_lyrics_preview = st.checkbox("Şarkı sözü önizlemesi göster", value=True)
                save_results = st.checkbox("Sonuçları otomatik kaydet", value=True)
                output_format = st.selectbox(
                    "Çıktı formatı", 
                    ["txt", "json"], 
                    index=0,
                    key="output_format_selectbox"
                )
            
            submit_button = st.form_submit_button(
                "🎯 Duyguları Analiz Et",
                type="primary",
                use_container_width=True
            )
        
        # Process analysis
        if submit_button:
            if not song_name or not artist_name:
                st.error("Lütfen hem şarkı adını hem de sanatçı adını girin.")
                return
            
            self.perform_analysis(song_name, artist_name, include_lyrics_preview, save_results, output_format)
    
    def perform_analysis(self, song_name, artist_name, include_lyrics_preview, save_results, output_format):
        """Perform the emotion analysis"""
        
        # Validate inputs
        try:
            song_name, artist_name = validate_song_input(song_name, artist_name)
        except Exception as e:
            st.error(f"Girdi doğrulama hatası: {e}")
            return
        
        # Create progress indicators
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Fetch song data
            status_text.text("🔍 Şarkı aranıyor...")
            progress_bar.progress(20)
            
            song = self.genius_service.find_and_fetch_song(song_name, artist_name)
            
            status_text.text("✅ Şarkı bulundu! Sözler alınıyor...")
            progress_bar.progress(50)
            
            # Display song info
            if include_lyrics_preview:
                self.display_song_info(song)
            
            # Step 2: Perform analysis
            status_text.text("🧠 Duygular analiz ediliyor...")
            progress_bar.progress(80)
            
            session_id = str(uuid.uuid4())[:8]
            session = AnalysisSession(
                session_id=session_id,
                song=song,
                status=AnalysisStatus.IN_PROGRESS
            )
            
            analysis_result = self.analysis_service.analyze_song(song)
            session.mark_completed(analysis_result)
            
            status_text.text("🎉 Analiz tamamlandı!")
            progress_bar.progress(100)
            
            # Add to history
            st.session_state.analysis_history.add_session(session)
            st.session_state.current_analysis = session
            
            # Display results
            time.sleep(0.5)  # Brief pause for UX
            status_text.empty()
            progress_bar.empty()
            
            self.display_analysis_results(session)
            
            # Save results if requested
            if save_results:
                self.save_analysis_results(session, output_format)
            
        except LyricsNotFoundError:
            progress_bar.empty()
            status_text.empty()
            st.error("❌ Şarkı veya şarkı sözü bulunamadı. Lütfen şarkı adını ve sanatçıyı kontrol edin.")
        except AnalysisError as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Analiz başarısız: {e}")
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Beklenmeyen hata: {e}")
    
    def display_song_info(self, song):
        """Display song information"""
        st.subheader("📋 Şarkı Bilgileri")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Başlık:** {song.metadata.title}")
            st.write(f"**Sanatçı:** {song.metadata.artist_name}")
            if song.metadata.album:
                st.write(f"**Albüm:** {song.metadata.album}")
            if song.metadata.release_date:
                st.write(f"**Çıkış Tarihi:** {song.metadata.release_date}")
        
        with col2:
            if song.has_lyrics:
                stats = song.lyrics.summary_stats
                st.write(f"**Kelime Sayısı:** {stats['word_count']}")
                st.write(f"**Satır Sayısı:** {stats['line_count']}")
                st.write(f"**Karakter Sayısı:** {stats['character_count']}")
        
        # Lyrics preview - show full lyrics
        if song.has_lyrics:
            with st.expander("📝 Şarkı Sözleri (Tam Metin)"):
                # Show complete lyrics instead of preview
                full_lyrics = song.lyrics.content
                st.text_area("Şarkı Sözleri", full_lyrics, height=300, disabled=True, key=f"lyrics_full_textarea_{hash(song.metadata.title + song.metadata.artist_name)}")
    
    def display_analysis_results(self, session):
        """Display analysis results with interactive charts"""
        if not session.is_successful or not session.analysis_result:
            st.error("❌ Analiz başarısız veya tamamlanmamış")
            return
        
        result = session.analysis_result
        
        st.header("📊 Duygu Analizi Sonuçları")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        # Turkish emotion names
        emotion_names_tr = {
            "happiness": "Mutluluk",
            "sadness": "Hüzün", 
            "anger": "Öfke",
            "fear": "Korku",
            "love": "Aşk"
        }
        
        with col1:
            dominant_tr = emotion_names_tr.get(result.dominant_emotion.value, result.dominant_emotion.value.title())
            st.metric(
                "🏆 Baskın Duygu",
                dominant_tr,
                f"{result.dominant_score:.1f}%"
            )
        
        with col2:
            st.metric(
                "📊 Güven",
                f"{result.overall_confidence:.1%}",
                help="Analiz güven seviyesi"
            )
        
        with col3:
            quality_tr = {"High": "Yüksek", "Medium": "Orta", "Low": "Düşük"}.get(result.analysis_quality, result.analysis_quality)
            st.metric(
                "⭐ Kalite",
                quality_tr,
                help="Genel analiz kalitesi değerlendirmesi"
            )
        
        with col4:
            if result.processing_time:
                st.metric(
                    "⏱️ İşlem Süresi",
                    f"{result.processing_time:.2f}s"
                )
        
        # Emotion scores visualization
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Bar chart with Turkish labels
            emotions_tr = [emotion_names_tr.get(emotion.value, emotion.value.title()) for emotion in result.emotion_scores.keys()]
            scores = [score.score for score in result.emotion_scores.values()]
            
            fig = px.bar(
                x=emotions_tr,
                y=scores,
                title="🎭 Duygu Skorları",
                labels={'x': 'Duygular', 'y': 'Skor (%)'},
                color=scores,
                color_continuous_scale=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
            )
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True, key=f"emotion_bar_chart_{session.session_id}")
        
        with col2:
            # Pie chart for top emotions
            top_emotions = result.get_top_emotions(5)
            labels_tr = [emotion_names_tr.get(emotion.value, emotion.value.title()) for emotion, _ in top_emotions]
            values = [score.score for _, score in top_emotions]
            
            fig = go.Figure(data=[go.Pie(
                labels=labels_tr,
                values=values,
                hole=0.4,
                textinfo='label+percent'
            )])
            fig.update_layout(
                title="🥧 Duygu Dağılımı",
                height=400,
                showlegend=True
            )
            st.plotly_chart(fig, use_container_width=True, key=f"emotion_pie_chart_{session.session_id}")
        
        # Detailed breakdown
        st.subheader("📋 Detaylı Analiz")
        
        # Create DataFrame for emotion details
        emotion_data = []
        for emotion, score in result.emotion_scores.items():
            emotion_tr = emotion_names_tr.get(emotion.value, emotion.value.title())
            emotion_data.append({
                'Duygu': emotion_tr,
                'Skor': f"{score.score:.1f}%",
                'Açıklama': self.translate_emotion_description(score.description)
            })
        
        df = pd.DataFrame(emotion_data)
        st.dataframe(df, use_container_width=True, hide_index=True, key=f"emotion_details_dataframe_{session.session_id}")
        
        # Analysis summary
        st.subheader("📝 Özet")
        summary_tr = result.get_summary_text()
        st.info(summary_tr)
        
        # Top 3 emotions
        st.subheader("🏅 İlk 3 Duygu")
        top_3 = result.get_top_emotions(3)
        
        cols = st.columns(3)
        medals = ["🥇", "🥈", "🥉"]
        
        for i, (emotion, score) in enumerate(top_3):
            with cols[i]:
                emotion_tr = emotion_names_tr.get(emotion.value, emotion.value.title())
                st.markdown(f"""
                <div class="emotion-card">
                    <h3>{medals[i]} {emotion_tr}</h3>
                    <h2>{score.score:.1f}%</h2>
                </div>
                """, unsafe_allow_html=True)
    
    def translate_emotion_description(self, description):
        """Translate emotion descriptions to Turkish"""
        translations = {
            "Joy, contentment, positive emotions": "Neşe, memnuniyet, pozitif duygular",
            "Melancholy, grief, sorrow": "Melankoli, keder, hüzün",
            "Rage, frustration, hostility": "Öfke, hayal kırıklığı, düşmanlık",
            "Anxiety, worry, dread": "Kaygı, endişe, korku",
            "Affection, romance, caring": "Sevgi, romantizm, ilgi"
        }
        return translations.get(description, description)
    
    def save_analysis_results(self, session, output_format):
        """Save analysis results and provide download"""
        try:
            # Validate output format
            supported_formats = ["txt", "json"]
            if output_format not in supported_formats:
                st.error(f"❌ Desteklenmeyen format: {output_format}")
                return
            
            # Try to use the file service, but handle ValidationConstants error
            try:
                if output_format == "txt":
                    file_path = self.file_service.save_analysis_txt(session)
                else:
                    file_path = self.file_service.save_analysis_json(session)
                
                # Provide download button
                with open(file_path, 'rb') as f:
                    st.download_button(
                        label=f"📥 Sonuçları İndir ({output_format.upper()})",
                        data=f.read(),
                        file_name=file_path.name,
                        mime=f"text/{output_format}",
                        key=f"download_results_{session.session_id}_{output_format}"
                    )
                
                st.success(f"✅ Sonuçlar kaydedildi: {file_path}")
                
            except AttributeError as attr_error:
                if 'SUPPORTED_OUTPUT_FORMATS' in str(attr_error):
                    # Handle ValidationConstants error by creating content manually
                    self.create_manual_download(session, output_format)
                else:
                    raise attr_error
            
        except Exception as e:
            st.error(f"❌ Sonuçlar kaydedilemedi: {e}")
    
    def create_manual_download(self, session, output_format):
        """Create download content manually when file service fails"""
        try:
            if output_format == "txt":
                # Create TXT content manually
                content = self.generate_txt_content(session)
                filename = f"analysis_{session.session_id}.txt"
                mime_type = "text/plain"
            else:
                # Create JSON content manually
                import json
                content = self.generate_json_content(session)
                filename = f"analysis_{session.session_id}.json"
                mime_type = "application/json"
            
            st.download_button(
                label=f"📥 Sonuçları İndir ({output_format.upper()})",
                data=content,
                file_name=filename,
                mime=mime_type,
                key=f"manual_download_{session.session_id}_{output_format}"
            )
            
            st.success(f"✅ Sonuçlar hazırlandı: {filename}")
            
        except Exception as e:
            st.error(f"❌ Manuel dosya oluşturulamadı: {e}")
    
    def generate_txt_content(self, session):
        """Generate TXT format content for analysis results"""
        result = session.analysis_result
        content = f"""LyricMood-AI Analiz Sonuçları
================================

Şarkı Bilgileri:
- Başlık: {session.song.metadata.title}
- Sanatçı: {session.song.metadata.artist_name}
- Analiz Tarihi: {session.completed_at.strftime('%Y-%m-%d %H:%M:%S') if session.completed_at else 'Bilinmiyor'}

Duygu Analizi:
- Baskın Duygu: {result.dominant_emotion.value.title()} ({result.dominant_score:.1f}%)
- Genel Güven: {result.overall_confidence:.1%}
- Analiz Kalitesi: {result.analysis_quality}

Duygu Skorları:
"""
        
        emotion_names = {
            "happiness": "Mutluluk",
            "sadness": "Hüzün", 
            "anger": "Öfke",
            "fear": "Korku",
            "love": "Aşk"
        }
        
        for emotion, score in result.emotion_scores.items():
            emotion_tr = emotion_names.get(emotion.value, emotion.value.title())
            content += f"- {emotion_tr}: {score.score:.1f}%\n"
        
        content += f"\nÖzet:\n{result.get_summary_text()}\n"
        
        if session.song.has_lyrics:
            content += f"\nŞarkı Sözleri:\n{session.song.lyrics.content}\n"
        
        return content
    
    def generate_json_content(self, session):
        """Generate JSON format content for analysis results"""
        import json
        
        result = session.analysis_result
        
        data = {
            "session_id": session.session_id,
            "timestamp": session.completed_at.isoformat() if session.completed_at else None,
            "song": {
                "title": session.song.metadata.title,
                "artist": session.song.metadata.artist_name,
                "album": session.song.metadata.album,
                "release_date": session.song.metadata.release_date,
                "lyrics": session.song.lyrics.content if session.song.has_lyrics else None
            },
            "analysis": {
                "dominant_emotion": result.dominant_emotion.value,
                "dominant_score": result.dominant_score,
                "overall_confidence": result.overall_confidence,
                "analysis_quality": result.analysis_quality,
                "processing_time": result.processing_time,
                "emotion_scores": {
                    emotion.value: {
                        "score": score.score,
                        "description": score.description
                    }
                    for emotion, score in result.emotion_scores.items()
                },
                "summary": result.get_summary_text()
            }
        }
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def render_history_page(self):
        """Render the analysis history page"""
        st.header("📊 Analiz Geçmişi")
        
        history = st.session_state.analysis_history
        
        if not history.sessions:
            st.info("📝 Henüz analiz geçmişi yok. Bazı şarkıları analiz ederek burada görebilirsiniz!")
            return
        
        # History statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Toplam Analiz", history.total_sessions)
        with col2:
            st.metric("Başarılı", history.successful_sessions_count)
        with col3:
            st.metric("Başarı Oranı", f"{history.success_rate:.1%}")
        
        # Recent sessions table
        st.subheader("📋 Son Analizler")
        
        sessions_data = []
        for i, session in enumerate(history.get_recent_sessions(20)):
            if session.is_successful and session.analysis_result:
                emotion_names_tr = {
                    "happiness": "Mutluluk",
                    "sadness": "Hüzün", 
                    "anger": "Öfke",
                    "fear": "Korku",
                    "love": "Aşk"
                }
                dominant = emotion_names_tr.get(session.analysis_result.dominant_emotion.value, session.analysis_result.dominant_emotion.value.title())
                confidence = f"{session.analysis_result.overall_confidence:.1%}"
                status = "✅ Başarılı"
            else:
                dominant = "N/A"
                confidence = "N/A"
                status = "❌ Başarısız"
            
            sessions_data.append({
                '#': i + 1,
                'Şarkı': session.song.metadata.title,
                'Sanatçı': session.song.metadata.artist_name,
                'Baskın Duygu': dominant,
                'Güven': confidence,
                'Tarih': session.completed_at.strftime("%Y-%m-%d %H:%M") if session.completed_at else "Beklemede",
                'Durum': status
            })
        
        df = pd.DataFrame(sessions_data)
        st.dataframe(df, use_container_width=True, hide_index=True, key=f"history_dataframe_{len(sessions_data)}")
        
        # Export history
        if st.button("📤 Geçmişi CSV Olarak Dışa Aktar", key="export_history_csv_button"):
            csv_path = self.file_service.save_analysis_csv(history.sessions)
            with open(csv_path, 'rb') as f:
                st.download_button(
                    label="📥 CSV İndir",
                    data=f.read(),
                    file_name=csv_path.name,
                    mime="text/csv",
                    key="download_history_csv"
                )
    
    def render_statistics_page(self):
        """Render the statistics page"""
        st.header("📈 Uygulama İstatistikleri")
        
        # Performance metrics
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Analiz Performansı")
            history = st.session_state.analysis_history
            successful_sessions = history.get_successful_sessions()
            
            if successful_sessions:
                avg_processing_time = sum(
                    s.analysis_result.processing_time for s in successful_sessions 
                    if s.analysis_result.processing_time
                ) / len(successful_sessions)
                
                st.metric("Ortalama İşlem Süresi", f"{avg_processing_time:.2f}s")
                st.metric("Toplam Başarılı Analiz", len(successful_sessions))
                st.metric("Başarı Oranı", f"{history.success_rate:.1%}")
            else:
                st.info("Henüz başarılı analiz yok.")
        
        with col2:
            st.subheader("💾 Depolama Bilgileri")
            storage_stats = self.file_service.get_storage_stats()
            
            st.metric("Çıktı Dosyaları", storage_stats['total_files'])
            st.metric("Toplam Boyut", f"{storage_stats['total_size_mb']:.2f} MB")
            st.text(f"Dizin: {storage_stats['output_directory']}")
        
        # Cache statistics
        st.subheader("🚀 Önbellek Performansı")
        cache_stats = self.analysis_service.get_cache_stats()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Önbellek Etkin", "Evet" if cache_stats['cache_enabled'] else "Hayır")
        with col2:
            st.metric("Önbellekteki Analizler", cache_stats['cached_analyses'])
        with col3:
            st.metric("Önbellek Boyutu", f"{cache_stats['cache_size_mb']:.2f} MB")
    
    def run(self):
        """Run the Streamlit application"""
        self.render_header()
        self.render_sidebar()
        
        # Route to appropriate page
        if st.session_state.page == "Analiz":
            self.render_analyze_page()
        elif st.session_state.page == "Arama":
            self.render_search_page()
        elif st.session_state.page == "Geçmiş":
            self.render_history_page()
        elif st.session_state.page == "İstatistikler":
            self.render_statistics_page()


# Run the application
if __name__ == "__main__":
    app = StreamlitApp()
    app.run()