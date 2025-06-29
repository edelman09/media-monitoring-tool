import streamlit as st
import logging
import os
from talkwalker_scraper import TalkwalkerScraper
from newswhip_scraper import NewswhipScraper
from google_news_scraper import GoogleNewsScraper

# Import tab modules
from extraction_tab import render_extraction_tab
from aggregation_tab import render_aggregation_tab
from intelligent_search_tab import render_intelligent_search_tab

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app_logs.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create downloads directory
downloads_dir = os.path.join(os.getcwd(), "downloads")
os.makedirs(downloads_dir, exist_ok=True)

st.set_page_config(
    page_title="Web Scraping Automation Tool",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Function to clean up resources when the session ends
def cleanup_resources():
    """Clean up scraper resources"""
    if st.session_state.get('talkwalker_scraper'):
        try:
            st.session_state.talkwalker_scraper.close()
            logger.info("Talkwalker scraper closed successfully")
        except Exception as e:
            logger.error(f"Error closing Talkwalker scraper: {str(e)}")
    
    if st.session_state.get('newswhip_scraper'):
        try:
            st.session_state.newswhip_scraper.close()
            logger.info("Newswhip scraper closed successfully")
        except Exception as e:
            logger.error(f"Error closing Newswhip scraper: {str(e)}")

# Initialize session state variables
def initialize_session_state():
    """Initialize all session state variables"""
    session_vars = {
        'talkwalker_scraper': None,
        'newswhip_scraper': None,
        'google_news_scraper': None,
        'download_url': None,
        'download_path': None,
        'selected_platform': 'Talkwalker'
    }
    
    for var, default_value in session_vars.items():
        if var not in st.session_state:
            st.session_state[var] = default_value

# Initialize session state
initialize_session_state()

# Header
st.title("🛠️ Edelman DEAT")

# Sidebar for platform selection and authentication
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Platform selection
    platform = st.radio(
        "Supported Platform",
        ["Talkwalker", "Newswhip", "Google News"],
        index=0,
    )
    
    # Store selected platform in session state
    st.session_state.selected_platform = platform
    
    # Authentication section (only shown for platforms requiring login)
    if platform in ["Talkwalker", "Newswhip"]:
        st.subheader("Authentication")
        email = st.text_input(f"{platform} Email")
        password = st.text_input(f"{platform} Password", type="password")
        
        if platform == "Talkwalker" and email and password and st.button("Login to Talkwalker"):
            with st.spinner("Logging in to Talkwalker..."):
                try:
                    st.session_state.talkwalker_scraper = TalkwalkerScraper(email, password)
                    # Test the login by fetching projects
                    projects = st.session_state.talkwalker_scraper.get_projects()
                    st.success(f"Successfully logged in to Talkwalker! Found {len(projects)} projects.")
                except Exception as e:
                    st.error(f"Failed to login: {str(e)}")
                    st.session_state.talkwalker_scraper = None
        
        elif platform == "Newswhip" and email and password and st.button("Login to Newswhip"):
            with st.spinner("Logging in to Newswhip..."):
                try:
                    st.session_state.newswhip_scraper = NewswhipScraper(email, password)
                    # Test the login by fetching folders
                    folders = st.session_state.newswhip_scraper.get_folders()
                    st.success("Successfully logged in to Newswhip!")
                except Exception as e:
                    st.error(f"Failed to login: {str(e)}")
                    st.session_state.newswhip_scraper = None

# Create tabs
tab1, tab2, tab3 = st.tabs(["Data Extraction", "Data Aggregation", "Intelligent Search"])

with tab1:  # Data Extraction Tab
    render_extraction_tab()

with tab2:  # Data Aggregation Tab
    render_aggregation_tab()

with tab3:  # Intelligent Search Tab
    render_intelligent_search_tab()

# Footer
st.markdown("---")
st.caption("© 2025 Edelman Automation Tool  | Version 1.0")

# Register cleanup callback
if "session_clean_up_initialized" not in st.session_state:
    st.session_state.session_clean_up_initialized = True
    # Streamlit doesn’t natively support session end detection, so cleanup relies on manual calls or app restart