import streamlit as st
import pandas as pd
import logging
import re
import math
from collections import Counter
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
except:
    pass

def preprocess_text(text):
    """
    Preprocess text for better matching.
    
    Args:
        text (str): Input text
        
    Returns:
        str: Preprocessed text
    """
    if pd.isna(text) or not text:
        return ""
    
    # Convert to lowercase and remove special characters
    text = str(text).lower()
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def keyword_search_score(query, title, content="", source=""):
    """
    Calculate keyword-based relevance score.
    
    Args:
        query (str): Search query
        title (str): Article title
        content (str): Article content/snippet
        source (str): Article source
        
    Returns:
        float: Keyword relevance score (0-100)
    """
    if not query:
        return 0
    
    query_processed = preprocess_text(query)
    title_processed = preprocess_text(title)
    content_processed = preprocess_text(content)
    source_processed = preprocess_text(source)
    
    query_words = set(query_processed.split())
    title_words = set(title_processed.split())
    content_words = set(content_processed.split())
    source_words = set(source_processed.split())
    
    if not query_words:
        return 0
    
    # Calculate matches with different weights
    title_matches = len(query_words.intersection(title_words))
    content_matches = len(query_words.intersection(content_words))
    source_matches = len(query_words.intersection(source_words))
    
    # Weight: title=50%, content=40%, source=10%
    title_score = (title_matches / len(query_words)) * 50
    content_score = (content_matches / len(query_words)) * 40
    source_score = (source_matches / len(query_words)) * 10
    
    total_score = title_score + content_score + source_score
    
    # Bonus for exact phrase matches
    if query_processed in title_processed:
        total_score += 20
    elif query_processed in content_processed:
        total_score += 10
    
    return min(total_score, 100)

def semantic_search_score(query, articles_df):
    """
    Calculate semantic similarity scores using TF-IDF and cosine similarity.
    
    Args:
        query (str): Search query
        articles_df (pd.DataFrame): DataFrame with articles
        
    Returns:
        np.array: Array of semantic similarity scores (0-100)
    """
    try:
        # Combine title and content for better semantic understanding
        articles_text = []
        for _, row in articles_df.iterrows():
            title = str(row.get('Title', ''))
            snippet = str(row.get('snippet', '')) if 'snippet' in row else ""
            combined_text = f"{title} {snippet}".strip()
            articles_text.append(preprocess_text(combined_text) if combined_text else "")
        
        # Add query to the corpus
        query_processed = preprocess_text(query)
        corpus = [query_processed] + articles_text
        
        # Create TF-IDF vectors
        vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2),  # Include bigrams for better context
            min_df=1,
            max_df=0.95
        )
        
        tfidf_matrix = vectorizer.fit_transform(corpus)
        
        # Calculate cosine similarity between query and articles
        query_vector = tfidf_matrix[0:1]  # First row is the query
        article_vectors = tfidf_matrix[1:]  # Rest are articles
        
        similarities = cosine_similarity(query_vector, article_vectors)[0]
        
        # Convert to 0-100 scale
        semantic_scores = similarities * 100
        
        return semantic_scores
        
    except Exception as e:
        logger.warning(f"Error in semantic search: {e}")
        # Return zeros if semantic search fails
        return np.zeros(len(articles_df))

def calculate_combined_relevance_score(query, articles_df):
    """
    Calculate combined relevance score using both keyword and semantic search.
    
    Args:
        query (str): Search query
        articles_df (pd.DataFrame): DataFrame with articles
        
    Returns:
        pd.DataFrame: DataFrame with relevance scores added
    """
    if articles_df.empty:
        return articles_df
    
    logger.info(f"Calculating relevance scores for {len(articles_df)} articles")
    
    # Calculate keyword scores
    keyword_scores = []
    for _, row in articles_df.iterrows():
        title = row.get('Title', '')
        snippet = row.get('snippet', '') if 'snippet' in articles_df.columns else ""
        source = row.get('Source', '')
        
        score = keyword_search_score(query, title, snippet, source)
        keyword_scores.append(score)
    
    # Calculate semantic scores
    semantic_scores = semantic_search_score(query, articles_df)
    
    # Combine scores (60% keyword, 40% semantic for balanced approach)
    combined_scores = []
    for i in range(len(articles_df)):
        keyword_weight = 0.6
        semantic_weight = 0.4
        
        combined_score = (keyword_scores[i] * keyword_weight) + (semantic_scores[i] * semantic_weight)
        combined_scores.append(round(combined_score, 2))
    
    # Add scores to dataframe
    result_df = articles_df.copy()
    result_df['Keyword_Score'] = keyword_scores
    result_df['Semantic_Score'] = [round(score, 2) for score in semantic_scores]
    result_df['Relevance_Score'] = combined_scores
    
    # Sort by relevance score (descending)
    result_df = result_df.sort_values('Relevance_Score', ascending=False).reset_index(drop=True)
    
    logger.info(f"Relevance calculation completed. Top score: {max(combined_scores):.2f}")
    
    return result_df

def filter_top_results(df, selection_method, selection_value):
    """
    Filter top results based on user selection.
    
    Args:
        df (pd.DataFrame): DataFrame with relevance scores
        selection_method (str): "Number" or "Percentage"
        selection_value (int/float): Number of articles or percentage
        
    Returns:
        pd.DataFrame: Filtered DataFrame
    """
    if df.empty:
        return df
    
    if selection_method == "Number":
        top_n = min(int(selection_value), len(df))
        return df.head(top_n)
    else:  # Percentage
        percentage = float(selection_value) / 100
        top_n = max(1, int(len(df) * percentage))
        return df.head(top_n)

def render_intelligent_search_tab():
    """Render the Intelligent Search tab"""
    
    # st.subheader("Intelligent News Search")
    # st.write("Find the most relevant news articles using advanced keyword and semantic search algorithms.")
    
    # Check if there's aggregated data available
    has_aggregated_data = 'aggregated_data' in st.session_state and st.session_state['aggregated_data'] is not None
    use_aggregated_suggested = st.session_state.get('use_aggregated_in_search', False)
    
    # Show option to use aggregated data if available
    data_source_option = "Upload File"  # Default
    
    if has_aggregated_data:
        st.markdown("### 📊 Data Source")
        data_source_option = st.radio(
            "Choose data source:",
            ["Use Aggregated Data", "Upload New File"],
            index=0 if use_aggregated_suggested else 1,
            horizontal=True,
            help="Use data from the Aggregation tab or upload a new file"
        )
        
        if data_source_option == "Use Aggregated Data":
            aggregated_df = st.session_state['aggregated_data']
            st.success(f"✅ Using aggregated data with {len(aggregated_df)} articles")
            
            # Show preview of aggregated data
            with st.expander("Preview Aggregated Data", expanded=False):
                st.dataframe(aggregated_df.head(50))
            
            # Reset the flag
            if 'use_aggregated_in_search' in st.session_state:
                del st.session_state['use_aggregated_in_search']
    
    col1, col2 = st.columns([1, 0.4])
    
    with col1:
        # Search query input
        with st.expander("How our search works?", expanded=False):
            st.markdown(
                """
                <small>ℹ️ **How our search works:** We use a hybrid algorithm combining:
                <ul>
                    <li><b>Keyword Matching (60% weight):</b> Scores based on keyword presence in title, content, and source, with bonuses for exact phrase matches.</li>
                    <li><b>Semantic Similarity (40% weight):</b> Utilizes TF-IDF and cosine similarity to understand contextual meaning and find related articles.</li>
                </ul>
                </small>
                """,
                unsafe_allow_html=True
            )
        search_query = st.text_area(
            "Enter keywords, sentences, or description:",
            height=100,
            help="Describe the topic, situation, or keywords you're looking for. The more specific, the better the results."
        )
        
        # File upload (only show if not using aggregated data)
        uploaded_file = None
        if data_source_option == "Upload New File" or not has_aggregated_data:
            st.markdown("### Upload News Data")
            uploaded_file = st.file_uploader(
                "Upload CSV/Excel file with news articles",
                type=['csv', 'xlsx'],
                help="Upload a file in the same format as the aggregation tab (with Title, URL, Platform, Source, etc.)"
            )
    
    with col2:
        # Search parameters
        with st.expander("Search Parameters", expanded=True):
            st.markdown("#### Result Selection")
            
            selection_method = st.radio(
                "Select top results by:",
                ["Number", "Percentage"],
                horizontal=True,
                help="Choose whether to get a specific number of articles or a percentage of total articles"
            )
            
            if selection_method == "Number":
                selection_value = st.number_input(
                    "Number of top articles:",
                    min_value=1,
                    max_value=1000,
                    value=10,
                    help="How many top relevant articles to show"
                )
            else:
                selection_value = st.slider(
                    "Percentage of articles:",
                    min_value=1,
                    max_value=100,
                    value=10,
                    help="What percentage of articles to show (most relevant ones)"
                )
    
    # Determine which data to use
    data_to_process = None
    data_source_info = ""
    
    if has_aggregated_data and data_source_option == "Use Aggregated Data":
        data_to_process = st.session_state['aggregated_data']
        data_source_info = f"aggregated data ({len(data_to_process)} articles)"
    elif uploaded_file:
        data_source_info = f"uploaded file ({uploaded_file.name})"
    
    # Process the search
    if search_query and (data_to_process is not None or uploaded_file):
        if st.button("🔍 Search Relevant Articles", use_container_width=True):
            try:
                with st.spinner("🔍 Analyzing articles and calculating relevance scores..."):
                    # Load the data
                    if data_to_process is not None:
                        df = data_to_process.copy()
                    else:
                        # Load the uploaded file
                        if uploaded_file.name.endswith('.csv'):
                            df = pd.read_csv(uploaded_file)
                        else:
                            df = pd.read_excel(uploaded_file)
                    
                    if df.empty:
                        st.error("The data source is empty.")
                        return
                    
                    st.info(f"📊 Loaded {len(df)} articles from {data_source_info}")
                    
                    # Calculate relevance scores
                    with st.spinner("🧮 Computing relevance scores using hybrid algorithm..."):
                        scored_df = calculate_combined_relevance_score(search_query, df)
                    
                    # Filter top results
                    top_results = filter_top_results(scored_df, selection_method, selection_value)
                    
                    if top_results.empty:
                        st.warning("No relevant articles found for your query.")
                        return
                    
                    # Display results
                    st.success(f"✅ Found {len(top_results)} most relevant articles!")
                    
                    # Show search summary
                    st.markdown("### 📈 Search Results Summary")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Articles", len(df))
                    with col2:
                        st.metric("Relevant Articles", len(top_results))
                    with col3:
                        avg_score = top_results['Relevance_Score'].mean()
                        st.metric("Avg. Relevance", f"{avg_score:.1f}%")
                    with col4:
                        max_score = top_results['Relevance_Score'].max()
                        st.metric("Top Score", f"{max_score:.1f}%")
                    
                    # Display results table
                    st.markdown("### 📋 Top Relevant Articles")
                    
                    # Prepare display dataframe
                    display_df = top_results.copy()
                    
                    # Reorder columns for better display
                    column_order = ['Relevance_Score', 'Title', 'Platform', 'Source', 'Published_Date', 'URL']
                    
                    # Add optional columns if they exist
                    optional_cols = ['Country', 'Language', 'Sentiment', 'Source_Type', 'Search_Keyword']
                    for col in optional_cols:
                        if col in display_df.columns:
                            column_order.append(col)
                    
                    # Add score breakdown columns at the end
                    column_order.extend(['Keyword_Score', 'Semantic_Score'])
                    
                    # Filter to existing columns
                    column_order = [col for col in column_order if col in display_df.columns]
                    display_df = display_df[column_order]
                    
                    # Style the dataframe
                    styled_df = display_df.style.format({
                        'Relevance_Score': '{:.1f}%',
                        'Keyword_Score': '{:.1f}%',
                        'Semantic_Score': '{:.1f}%'
                    }).background_gradient(
                        subset=['Relevance_Score'], 
                        cmap='RdYlGn', 
                        vmin=0, 
                        vmax=100
                    )
                    
                    st.dataframe(styled_df, use_container_width=True)
                    
                    # Export functionality
                    st.markdown("### 💾 Export Results")
                    
                    export_format = st.radio(
                        "Export Format:",
                        ["CSV", "Excel"],
                        horizontal=True,
                        key="export_format_radio"
                    )
                    
                    # Create safe query name for filename
                    import time
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    safe_query = re.sub(r'[^a-zA-Z0-9\s]', '', search_query)
                    safe_query = re.sub(r'\s+', '_', safe_query)[:50]  # Limit length
                    
                    if export_format == "CSV":
                        filename = f"intelligent_search_{safe_query}_{timestamp}.csv"
                        csv_data = display_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download CSV File",
                            data=csv_data,
                            file_name=filename,
                            mime="text/csv",
                            key="download_csv_button"
                        )
                    else:  # Excel
                        filename = f"intelligent_search_{safe_query}_{timestamp}.xlsx"
                        
                        # Create Excel file in memory
                        from io import BytesIO
                        output = BytesIO()
                        
                        # Use pandas ExcelWriter with xlsxwriter engine
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            display_df.to_excel(writer, sheet_name='Search Results', index=False)
                        
                        # Get the binary data
                        excel_data = output.getvalue()
                        
                        st.download_button(
                            label="📥 Download Excel File",
                            data=excel_data,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_excel_button"
                        )
            
            except Exception as e:
                st.error(f"Error processing search: {str(e)}")
                logger.error(f"Search processing error: {e}")
    
    elif not search_query:
        st.info("👆 Please enter a search query to begin")
    elif not has_aggregated_data and not uploaded_file:
        st.info("👆 Please upload a news data file or use aggregated data to search through")
    else:
        st.info("👆 Please provide both a search query and select a data source to start searching")