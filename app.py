import streamlit as st
import logging
import os
import sys

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

def detect_environment():
    """
    Detect if running on Streamlit Community Cloud or local environment
    
    Returns:
        str: 'streamlit_cloud' or 'local'
    """
    # Check for Streamlit Cloud environment indicators
    if (os.getenv('STREAMLIT_SHARING_MODE') or 
        'streamlit' in os.getenv('HOME', '').lower() or
        '/mount/src' in os.getcwd() or
        'appuser' in os.getenv('HOME', '')):
        return 'streamlit_cloud'
    return 'local'

# Detect environment
ENVIRONMENT = detect_environment()
SELENIUM_AVAILABLE = ENVIRONMENT == 'local'

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
        'selected_platform': 'Google News' if not SELENIUM_AVAILABLE else 'Talkwalker',
        'environment': ENVIRONMENT,
        'selenium_available': SELENIUM_AVAILABLE
    }
    
    for var, default_value in session_vars.items():
        if var not in st.session_state:
            st.session_state[var] = default_value

# Initialize session state
initialize_session_state()

# Header
st.title("🛠️ Edelman DEAT")

# Show environment warning if on Streamlit Cloud
if not SELENIUM_AVAILABLE:
    st.warning(
        "⚠️ **Running on Streamlit Community Cloud**: Browser automation (Talkwalker & Newswhip) is not supported. "
        "Google News scraping, data aggregation, and intelligent search are fully functional."
    )

# Sidebar for platform selection and authentication
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Platform selection - adjust options based on environment
    if SELENIUM_AVAILABLE:
        platform_options = ["Talkwalker", "Newswhip", "Google News"]
        default_index = 0
    else:
        platform_options = ["Google News"]
        default_index = 0
        
        # Show disabled options with explanation
        st.info("🔒 **Disabled on Streamlit Cloud:**")
        st.markdown("- Talkwalker (requires browser automation)")
        st.markdown("- Newswhip (requires browser automation)")
        st.markdown("")
        st.success("✅ **Available:**")
        st.markdown("- Google News (API-based)")
        st.markdown("- Data Aggregation")
        st.markdown("- Intelligent Search")
    
    platform = st.radio(
        "Supported Platform",
        platform_options,
        index=default_index,
    )
    
    # Store selected platform in session state
    st.session_state.selected_platform = platform
    
    # Authentication section (only shown for platforms requiring login and available)
    if platform in ["Talkwalker", "Newswhip"] and SELENIUM_AVAILABLE:
        st.subheader("Authentication")
        email = st.text_input(f"{platform} Email")
        password = st.text_input(f"{platform} Password", type="password")
        
        if platform == "Talkwalker" and email and password and st.button("Login to Talkwalker"):
            with st.spinner("Logging in to Talkwalker..."):
                try:
                    # Import here to avoid issues if selenium not available
                    from talkwalker_scraper import TalkwalkerScraper
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
                    # Import here to avoid issues if selenium not available
                    from newswhip_scraper import NewswhipScraper
                    st.session_state.newswhip_scraper = NewswhipScraper(email, password)
                    # Test the login by fetching folders
                    folders = st.session_state.newswhip_scraper.get_folders()
                    st.success("Successfully logged in to Newswhip!")
                except Exception as e:
                    st.error(f"Failed to login: {str(e)}")
                    st.session_state.newswhip_scraper = None
    
    elif platform in ["Talkwalker", "Newswhip"] and not SELENIUM_AVAILABLE:
        st.info(f"💡 **{platform} requires local setup**")
        st.markdown(
            "To use browser automation features:\n"
            "1. Run this app locally\n"
            "2. Install Chrome/Chromium\n"
            "3. Install selenium dependencies"
        )

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
    # Streamlit doesn't natively support session end detection, so cleanup relies on manual calls or app restart
