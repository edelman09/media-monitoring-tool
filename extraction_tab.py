import streamlit as st
import logging
import os
import pandas as pd

logger = logging.getLogger(__name__)

def render_extraction_tab():
    """Render the Data Extraction tab"""
    
    # Get platform from sidebar (passed from main app)
    platform = st.session_state.get('selected_platform', 'Talkwalker')
    
    # Initialize status placeholder for showing operation progress
    status_placeholder = st.empty()

    if platform == "Talkwalker":
        render_talkwalker_extraction(status_placeholder)
    elif platform == "Newswhip":
        render_newswhip_extraction(status_placeholder)
    else:  # Google News
        render_google_news_extraction(status_placeholder)

def initialize_talkwalker_session_state():
    """Initializes Talkwalker specific session state variables if they don't exist."""
    defaults = {
        'tw_projects': [],
        'tw_categories': [],
        'tw_topics': [],
        'tw_selected_project_id': None,
        'tw_selected_project_name': None,
        'tw_selected_category_id': None,
        'tw_selected_category_name': None,
        'tw_selected_topic_id': None,
        'tw_selected_topic_name': None,
        'tw_time_period': '2',  # Default to "7D"
        'tw_download_url': None,
        'tw_download_path': None
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def render_talkwalker_extraction(status_placeholder):
    """Render Talkwalker extraction interface"""
    
    # Initialize Talkwalker session state variables
    initialize_talkwalker_session_state()
    
    col1, col2 = st.columns([1, 0.4])
    
    with col1:
        # Time period selection radio buttons
        time_options = {
            "1 Day": "1",
            "7 Days": "2", 
            "30 Days": "3",
            "3 Months": "4",
            "6 Months": "5",
            "1 Year": "6"
        }
        
        time_period = st.radio(
            "Select Time Period",
            list(time_options.keys()),
            index=1,  # Default to 7 Days
            horizontal=True
        )
        
        # Update session state with the selected time period
        st.session_state.tw_time_period = time_options[time_period]
    
    with col2:
        with st.expander("Select Parameters", expanded=False):
            if st.session_state.talkwalker_scraper is None:
                st.info("Please login first.")
            else:
                # Step 1: Project Selection
                if not st.session_state.tw_projects:
                    if st.button("Fetch Available Projects"):
                        with status_placeholder.container():
                            st.info("Fetching available projects... Please wait.")
                        
                        try:
                            projects = st.session_state.talkwalker_scraper.get_projects()
                            st.session_state.tw_projects = projects
                            logger.info(f"Retrieved {len(projects)} Talkwalker projects")
                            status_placeholder.success("Projects retrieved successfully!")
                        except Exception as e:
                            logger.error(f"Error fetching Talkwalker projects: {str(e)}")
                            status_placeholder.error(f"Error: {str(e)}")
                
                if st.session_state.tw_projects:
                    # Format projects for selectbox: "1. Project Name"
                    project_options = [f"{p['id']}. {p['name']}" for p in st.session_state.tw_projects]
                    
                    # Find index of currently selected project
                    selected_index = 0
                    if st.session_state.tw_selected_project_id:
                        for i, p in enumerate(st.session_state.tw_projects):
                            if p['id'] == st.session_state.tw_selected_project_id:
                                selected_index = i
                                break
                    
                    selected_project = st.selectbox(
                        "Select Project", 
                        project_options,
                        index=selected_index
                    )
                    
                    # Extract project ID and name from selection
                    selected_project_id = int(selected_project.split('.')[0])
                    selected_project_name = selected_project[selected_project.find('.')+2:]
                    
                    # If project selection changed, reset categories and topics
                    if selected_project_id != st.session_state.tw_selected_project_id:
                        st.session_state.tw_selected_project_id = selected_project_id
                        st.session_state.tw_selected_project_name = selected_project_name
                        st.session_state.tw_categories = []
                        st.session_state.tw_topics = []
                        st.session_state.tw_selected_category_id = None
                        st.session_state.tw_selected_category_name = None
                        st.session_state.tw_selected_topic_id = None
                        st.session_state.tw_selected_topic_name = None
                
                # Step 2: Fetch Categories if project is selected
                if st.session_state.tw_selected_project_id and not st.session_state.tw_categories:
                    if st.button("Fetch Categories"):
                        with status_placeholder.container():
                            st.info(f"Fetching categories for project '{st.session_state.tw_selected_project_name}'... Please wait.")
                        
                        try:
                            # First navigate to project and topic analytics
                            st.session_state.talkwalker_scraper.select_project_and_navigate_to_topic_analytics(
                                st.session_state.tw_selected_project_id
                            )
                            
                            # Then get categories
                            categories = st.session_state.talkwalker_scraper.get_categories()
                            st.session_state.tw_categories = categories
                            logger.info(f"Retrieved {len(categories)} categories for project {st.session_state.tw_selected_project_name}")
                            status_placeholder.success("Categories retrieved successfully!")
                        except Exception as e:
                            logger.error(f"Error fetching categories: {str(e)}")
                            status_placeholder.error(f"Error: {str(e)}")
                
                # Step 3: Show Categories dropdown if they're available
                if st.session_state.tw_categories:
                    # Format categories for selectbox: "1. Category Name"
                    category_options = [f"{c['id']}. {c['name']}" for c in st.session_state.tw_categories]
                    
                    # Find index of currently selected category
                    selected_index = 0
                    if st.session_state.tw_selected_category_id:
                        for i, c in enumerate(st.session_state.tw_categories):
                            if c['id'] == st.session_state.tw_selected_category_id:
                                selected_index = i
                                break
                    
                    selected_category = st.selectbox(
                        "Select Category", 
                        category_options,
                        index=selected_index
                    )
                    
                    # Extract category ID and name from selection
                    selected_category_id = int(selected_category.split('.')[0])
                    selected_category_name = selected_category[selected_category.find('.')+2:]
                    
                    # If category selection changed, reset topics
                    if selected_category_id != st.session_state.tw_selected_category_id:
                        st.session_state.tw_selected_category_id = selected_category_id
                        st.session_state.tw_selected_category_name = selected_category_name
                        st.session_state.tw_topics = []
                        st.session_state.tw_selected_topic_id = None
                        st.session_state.tw_selected_topic_name = None
                
                # Step 4: Fetch Topics for selected category
                if st.session_state.tw_selected_category_id and not st.session_state.tw_topics:
                    if st.button("Fetch Topics"):
                        with status_placeholder.container():
                            st.info(f"Fetching topics for category '{st.session_state.tw_selected_category_name}'... Please wait.")
                        
                        try:
                            topics = st.session_state.talkwalker_scraper.get_topics_for_category(
                                st.session_state.tw_selected_category_id
                            )
                            st.session_state.tw_topics = topics
                            logger.info(f"Retrieved {len(topics)} topics for category {st.session_state.tw_selected_category_name}")
                            status_placeholder.success("Topics retrieved successfully!")
                        except Exception as e:
                            logger.error(f"Error fetching topics: {str(e)}")
                            status_placeholder.error(f"Error: {str(e)}")
                
                # Step 5: Show Topics dropdown if they're available
                if st.session_state.tw_topics:
                    # Format topics for selectbox: "1. Topic Name"
                    topic_options = [f"{t['id']}. {t['name']}" for t in st.session_state.tw_topics]
                    
                    # Find index of currently selected topic
                    selected_index = 0
                    if st.session_state.tw_selected_topic_id:
                        for i, t in enumerate(st.session_state.tw_topics):
                            if t['id'] == st.session_state.tw_selected_topic_id:
                                selected_index = i
                                break
                    
                    selected_topic = st.selectbox(
                        "Select Topic", 
                        topic_options,
                        index=selected_index
                    )
                    
                    # Extract topic ID and name from selection
                    selected_topic_id = int(selected_topic.split('.')[0])
                    selected_topic_name = selected_topic[selected_topic.find('.')+2:]
                    
                    if selected_topic_id != st.session_state.tw_selected_topic_id:
                        st.session_state.tw_selected_topic_id = selected_topic_id
                        st.session_state.tw_selected_topic_name = selected_topic_name
    
    # Export data button
    if (st.session_state.tw_selected_project_id and 
        st.session_state.tw_selected_category_id and 
        st.session_state.tw_selected_topic_id):
        
        if st.button("Export Data", use_container_width=True, type="primary"):
            with status_placeholder.container():
                st.info("Exporting data... This may take a few minutes.")
            
            try:
                download_url = st.session_state.talkwalker_scraper.export_data(
                    st.session_state.tw_selected_project_id,
                    st.session_state.tw_selected_category_id,
                    st.session_state.tw_selected_topic_id,
                    st.session_state.tw_time_period
                )
                
                st.session_state.tw_download_url = download_url
                
                # Find the downloaded file in the downloads directory
                downloads_dir = os.path.join(os.getcwd(), "downloads")
                csv_files = [f for f in os.listdir(downloads_dir) if f.endswith('.csv')]
                if csv_files:
                    latest_file = max([os.path.join(downloads_dir, f) for f in csv_files], key=os.path.getctime)
                    st.session_state.tw_download_path = latest_file
                    st.session_state.download_path = latest_file  # Global download path
                
                logger.info(f"Exported data for topic {st.session_state.tw_selected_topic_name}")
                status_placeholder.success(f"Data exported successfully!")
            except Exception as e:
                logger.error(f"Error exporting data: {str(e)}")
                status_placeholder.error(f"Error: {str(e)}")
    
    # Display download section if file is available
    if st.session_state.tw_download_path:
        st.markdown("### Download")
        st.success(f"CSV file saved to: {st.session_state.tw_download_path}")
        
        try:
            with open(st.session_state.tw_download_path, "rb") as file:
                st.download_button(
                    label="Download CSV File",
                    data=file,
                    file_name=os.path.basename(st.session_state.tw_download_path),
                    mime="text/csv"
                )
        except Exception as e:
            st.error(f"Could not load file for download: {str(e)}")

def render_newswhip_extraction(status_placeholder):
    """Render Newswhip extraction interface"""
    
    if 'nw_folders' not in st.session_state:
        st.session_state.nw_folders = []
    if 'nw_selected_folder' not in st.session_state:
        st.session_state.nw_selected_folder = None
    
    col1, col2 = st.columns([1, 0.4])
    
    with col1:
        time_period = st.radio(
            "Select Time Period",
            ["Last 24 hours", "Last 7 days", "Last 1 month", "Full Year"],
            index=1,
            horizontal=True
        )
        
        time_mapping = {
            "Last 24 hours": "1",
            "Last 7 days": "2",
            "Last 1 month": "3",
            "Full Year": "4"
        }
    
    with col2:
        with st.expander("Select Parameters", expanded=False):
            if st.session_state.newswhip_scraper is None:
                st.info("Please login first.")
            else:
                if not st.session_state.nw_folders:
                    if st.button("Fetch Available Folders"):
                        with status_placeholder.container():
                            st.info("Fetching available folders... Please wait.")
                        
                        try:
                            folders = st.session_state.newswhip_scraper.get_folders()
                            st.session_state.nw_folders = folders
                            logger.info(f"Retrieved {len(folders)} Newswhip folders")
                            status_placeholder.success("Folders retrieved successfully!")
                        except Exception as e:
                            logger.error(f"Error fetching Newswhip folders: {str(e)}")
                            status_placeholder.error(f"Error: {str(e)}")
                
                if st.session_state.nw_folders:
                    folder_index = 0
                    
                    if st.session_state.nw_selected_folder and st.session_state.nw_selected_folder in st.session_state.nw_folders:
                        folder_index = st.session_state.nw_folders.index(st.session_state.nw_selected_folder)
                    
                    selected_folder = st.selectbox("Select Folder", st.session_state.nw_folders, index=folder_index)
                    st.session_state.nw_selected_folder = selected_folder
    
    if st.session_state.nw_folders:
        if st.button("Export Data", use_container_width=True, type="primary"):
            with status_placeholder.container():
                st.info("Exporting data... This may take a few minutes.")
            
            try:
                download_path = st.session_state.newswhip_scraper.export_data(
                    st.session_state.nw_selected_folder, 
                    time_mapping[time_period]
                )
                
                st.session_state.download_path = download_path
                logger.info(f"Exported data for folder {st.session_state.nw_selected_folder}")
                
                status_placeholder.success(f"Data exported successfully!")
            except Exception as e:
                logger.error(f"Error exporting data: {str(e)}")
                status_placeholder.error(f"Error: {str(e)}")
    
    if st.session_state.download_path:
        st.markdown("### Download")
        st.success(f"CSV file saved to: {st.session_state.download_path}")
        
        with open(st.session_state.download_path, "rb") as file:
            st.download_button(
                label="Download CSV File",
                data=file,
                file_name=os.path.basename(st.session_state.download_path),
                mime="text/csv"
            )

def render_google_news_extraction(status_placeholder):
    """Render Google News extraction interface"""
    
    if 'gn_output_file' not in st.session_state:
        st.session_state.gn_output_file = None
    
    col1, col2 = st.columns([1, 0.4])
    
    with col1:
        time_options = {
            "Past hour": "h",
            "Past day": "d",
            "Past week": "w",
            "Past month": "m",
            "Past year": "y"
        }
        
        time_period = st.radio(
            "Select Time Period",
            list(time_options.keys()),
            index=1,
            horizontal=True
        )
    
    with col2:
        with st.expander("Select Parameters", expanded=False):
            st.subheader("Keyword Input Options")
            
            keyword_input_method = st.radio(
                "Choose how to input keywords:",
                ["Manual Input", "Upload CSV File"],
                horizontal=True
            )
            
            keywords_list = []
            
            if keyword_input_method == "Manual Input":
                keyword = st.text_input("Search Keywords", "Virat Kohli", help="Enter multiple keywords separated by commas (e.g., 'Virat Kohli, Indian Cricket, IPL 2025')")
                if keyword:
                    keywords_list = [kw.strip() for kw in keyword.split(',') if kw.strip()]
            
            else:
                uploaded_csv = st.file_uploader(
                    "Upload CSV file with keywords", 
                    type=['csv'],
                    help="Upload a CSV file with keywords. The first column should contain the keywords, one per row."
                )
                
                if uploaded_csv is not None:
                    try:
                        keywords_df = pd.read_csv(uploaded_csv)
                        first_column = keywords_df.columns[0]
                        keywords_list = keywords_df[first_column].dropna().astype(str).str.strip().tolist()
                        keywords_list = [kw for kw in keywords_list if kw]
                        
                        if keywords_list:
                            st.success(f"Loaded {len(keywords_list)} keywords from CSV file")
                            with st.expander("Preview Keywords", expanded=False):
                                st.write(keywords_list[:10] if len(keywords_list) > 10 else keywords_list)
                                if len(keywords_list) > 10:
                                    st.write(f"... and {len(keywords_list) - 10} more keywords")
                        else:
                            st.error("No valid keywords found in the CSV file")
                    except Exception as e:
                        st.error(f"Error reading CSV file: {str(e)}")
            
            if keywords_list:
                st.info(f"Total keywords to process: {len(keywords_list)}")
            
            max_pages = st.slider(
                "Maximum Pages per Keyword",
                min_value=1,
                max_value=10,
                value=5,
                help="Number of pages to scrape per keyword (10 results per page)"
            )
            
            language_options = {
                "English": "lang_en",
                "Hindi": "lang_hi",
                "French": "lang_fr",
                "German": "lang_de",
                "Spanish": "lang_es"
            }
            
            languages = st.multiselect(
                "Select Languages",
                list(language_options.keys()),
                default=["English"]
            )
            
            geo_options = {
                "India": "IN",
                "United States": "US",
                "United Kingdom": "GB",
                "Australia": "AU",
                "Canada": "CA"
            }
            
            geos = st.multiselect(
                "Select Regions",
                list(geo_options.keys()),
                default=["India"]
            )
    
    if keywords_list:
        if st.button("Fetch News", use_container_width=True):
            with status_placeholder.container():
                estimated_time = len(keywords_list) * max_pages * 0.5
                st.info(f"Fetching news articles for {len(keywords_list)} keywords with {max_pages} pages each...")
            
            try:
                if not st.session_state.google_news_scraper:
                    from google_news_scraper import GoogleNewsScraper
                    st.session_state.google_news_scraper = GoogleNewsScraper()
                
                selected_languages = [language_options[lang] for lang in languages]
                selected_geos = [geo_options[geo] for geo in geos]
                selected_time = time_options[time_period]
                
                keywords_string = ', '.join(keywords_list)
                
                output_file = st.session_state.google_news_scraper.get_news_data(
                    keyword=keywords_string,
                    languages=selected_languages,
                    geos=selected_geos,
                    time_period=selected_time,
                    max_pages=max_pages
                )
                
                st.session_state.gn_output_file = output_file
                logger.info(f"Fetched news articles for {len(keywords_list)} keywords")
                status_placeholder.success(f"News data exported successfully! Processed {len(keywords_list)} keywords.")
            except Exception as e:
                logger.error(f"Error fetching news data: {str(e)}")
                status_placeholder.error(f"Error: {str(e)}")
    else:
        st.info("Please enter keywords manually or upload a CSV file with keywords to start scraping.")
    
    if st.session_state.gn_output_file:
        st.markdown("### Download")
        
        with open(st.session_state.gn_output_file, "rb") as file:
            st.download_button(
                label="Download Excel File",
                data=file,
                file_name=os.path.basename(st.session_state.gn_output_file),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )