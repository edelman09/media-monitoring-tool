import streamlit as st
import pandas as pd
import time
import os
import logging
from datetime import datetime
import re

logger = logging.getLogger(__name__)

def standardize_date_format(date_str):
    """
    Convert various date formats to YYYY/MM/DD format.
    
    Args:
        date_str (str): Date string in various formats
        
    Returns:
        str: Standardized date in YYYY/MM/DD format or "N/A" if parsing fails
    """
    if pd.isna(date_str) or date_str == "N/A" or not date_str:
        return "N/A"
    
    date_str = str(date_str).strip()
    
    try:
        # Handle relative dates like "3 days ago", "1 hour ago", etc.
        if "ago" in date_str.lower():
            # Extract number and time unit
            match = re.search(r'(\d+)\s*(minute|hour|day|week|month|year)s?\s*ago', date_str.lower())
            if match:
                number = int(match.group(1))
                unit = match.group(2)
                
                current_date = datetime.now()
                if unit == 'minute':
                    target_date = current_date - pd.Timedelta(minutes=number)
                elif unit == 'hour':
                    target_date = current_date - pd.Timedelta(hours=number)
                elif unit == 'day':
                    target_date = current_date - pd.Timedelta(days=number)
                elif unit == 'week':
                    target_date = current_date - pd.Timedelta(weeks=number)
                elif unit == 'month':
                    target_date = current_date - pd.Timedelta(days=number*30)
                elif unit == 'year':
                    target_date = current_date - pd.Timedelta(days=number*365)
                
                return target_date.strftime("%Y/%m/%d")
        
        # Try to parse various date formats using pandas
        try:
            # Common formats to try
            formats_to_try = [
                "%m/%d/%y %I:%M:%S %p",  # 04/24/25 8:08:11 PM
                "%Y-%m-%dT%H:%M:%S",     # 2025-05-07T23:35:35
                "%Y-%m-%d %H:%M:%S",     # 2025-05-07 23:35:35
                "%m/%d/%Y",              # 04/24/2025
                "%Y-%m-%d",              # 2025-05-07
                "%d/%m/%Y",              # 24/04/2025
                "%B %d, %Y",             # May 7, 2025
                "%b %d, %Y",             # May 7, 2025
                "%d-%m-%Y",              # 07-05-2025
                "%Y/%m/%d",              # Already in target format
            ]
            
            # Try each format
            for fmt in formats_to_try:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    return parsed_date.strftime("%Y/%m/%d")
                except ValueError:
                    continue
            
            # If none of the specific formats work, try pandas' flexible parser
            parsed_date = pd.to_datetime(date_str, errors='coerce')
            if not pd.isna(parsed_date):
                return parsed_date.strftime("%Y/%m/%d")
                
        except Exception:
            pass
        
        # If all parsing fails, return the original string
        return date_str
        
    except Exception as e:
        logger.warning(f"Could not parse date '{date_str}': {e}")
        return "N/A"

def render_aggregation_tab():
    """Render the Data Aggregation tab"""
    
    # st.subheader("Aggregate Data from Multiple Sources")
    
    # File upload section
    uploaded_files = st.file_uploader("Upload files", accept_multiple_files=True, type=["csv", "xlsx"])
    
    if uploaded_files:
        
        # Process and show preview of uploaded files
        all_dataframes = []
        with st.expander("Uploaded Files"):
            st.write(f"Uploaded {len(uploaded_files)} files")
            for uploaded_file in uploaded_files:
                # Extract platform from filename
                file_name = uploaded_file.name
                platform = "Unknown"
                
                if file_name.lower().startswith("talkwalker") or file_name.lower().startswith("export"):
                    platform = "Talkwalker"
                elif file_name.lower().startswith("googlenews"):
                    platform = "Google News"
                else:
                    platform = "Newswhip"  # Default to Newswhip for other files
                
                # Read file based on its extension
                try:
                    if file_name.endswith('.csv'):
                        df = pd.read_csv(uploaded_file)
                    elif file_name.endswith('.xlsx'):
                        df = pd.read_excel(uploaded_file)
                    
                    # Extract necessary columns based on platform
                    standardized_df = pd.DataFrame()
                    
                    if platform == "Talkwalker":
                        # Extract relevant columns from Talkwalker export
                        if 'title' in df.columns:
                            standardized_df['Title'] = df['title']
                        elif 'title_snippet' in df.columns:
                            standardized_df['Title'] = df['title_snippet']
                        else:
                            standardized_df['Title'] = "N/A"
                        
                        if 'url' in df.columns:
                            standardized_df['URL'] = df['url']
                        else:
                            standardized_df['URL'] = "N/A"
                        
                        standardized_df['Platform'] = "Talkwalker"
                        
                        if 'domain_url' in df.columns:
                            standardized_df['Source'] = df['domain_url']
                        else:
                            standardized_df['Source'] = "Talkwalker"
                        
                        # Additional Talkwalker-specific columns
                        if 'sentiment' in df.columns:
                            standardized_df['Sentiment'] = df['sentiment']
                        else:
                            standardized_df['Sentiment'] = "N/A"
                        
                        if 'lang' in df.columns:
                            standardized_df['Language'] = df['lang']
                        else:
                            standardized_df['Language'] = "N/A"
                        
                        if 'extra_source_attributes.world_data.country' in df.columns:
                            standardized_df['Country'] = df['extra_source_attributes.world_data.country']
                        elif 'extra_author_attributes.world_data.country' in df.columns:
                            standardized_df['Country'] = df['extra_author_attributes.world_data.country']
                        elif 'extra_article_attributes.world_data.country' in df.columns:
                            standardized_df['Country'] = df['extra_article_attributes.world_data.country']
                        else:
                            standardized_df['Country'] = "N/A"
                        
                        if 'source_type' in df.columns:
                            standardized_df['Source_Type'] = df['source_type']
                        else:
                            standardized_df['Source_Type'] = "N/A"
                        
                        if 'published' in df.columns:
                            standardized_df['Published_Date'] = df['published'].apply(standardize_date_format)
                        elif 'indexed' in df.columns:
                            standardized_df['Published_Date'] = df['indexed'].apply(standardize_date_format)
                        else:
                            standardized_df['Published_Date'] = "N/A"
                    
                    elif platform == "Newswhip":
                        # Extract relevant columns from Newswhip export
                        if 'Headline' in df.columns:
                            standardized_df['Title'] = df['Headline']
                        else:
                            standardized_df['Title'] = "N/A"
                        
                        if 'Link' in df.columns:
                            standardized_df['URL'] = df['Link']
                        else:
                            standardized_df['URL'] = "N/A"
                        
                        standardized_df['Platform'] = "Newswhip"
                        
                        if 'Domain' in df.columns:
                            standardized_df['Source'] = df['Domain']
                        else:
                            standardized_df['Source'] = "Newswhip"
                        
                        # Additional Newswhip-specific columns
                        standardized_df['Sentiment'] = "N/A"  # Not available in Newswhip
                        standardized_df['Language'] = "N/A"  # Not available in Newswhip
                        
                        if 'Country' in df.columns:
                            standardized_df['Country'] = df['Country']
                        else:
                            standardized_df['Country'] = "N/A"
                        
                        standardized_df['Source_Type'] = "News"  # Default for Newswhip
                        
                        if 'Published' in df.columns:
                            standardized_df['Published_Date'] = df['Published'].apply(standardize_date_format)
                        else:
                            standardized_df['Published_Date'] = "N/A"
                    
                    elif platform == "Google News":
                        # Extract relevant columns from Google News export
                        if 'title' in df.columns:
                            standardized_df['Title'] = df['title']
                        else:
                            standardized_df['Title'] = "N/A"
                        
                        if 'link' in df.columns:
                            standardized_df['URL'] = df['link']
                        else:
                            standardized_df['URL'] = "N/A"
                        
                        standardized_df['Platform'] = "Google News"
                        
                        if 'source' in df.columns:
                            standardized_df['Source'] = df['source']
                        else:
                            standardized_df['Source'] = "Google News"
                        
                        # Additional Google News-specific columns
                        standardized_df['Sentiment'] = "N/A"  # Not available in Google News
                        standardized_df['Language'] = "N/A"  # Not directly available
                        standardized_df['Country'] = "N/A"   # Not available in Google News
                        standardized_df['Source_Type'] = "News"  # Default for Google News
                        
                        if 'date' in df.columns:
                            standardized_df['Published_Date'] = df['date'].apply(standardize_date_format)
                        else:
                            standardized_df['Published_Date'] = "N/A"
                        
                        # Add search keyword information if available
                        if 'search_keyword' in df.columns:
                            standardized_df['Search_Keyword'] = df['search_keyword']
                        else:
                            standardized_df['Search_Keyword'] = "N/A"
                    
                    # Add to list of dataframes
                    if not standardized_df.empty:
                        all_dataframes.append(standardized_df)
                        st.success(f"Successfully processed: {file_name}")
                        
                except Exception as e:
                    st.error(f"Error processing {file_name}: {str(e)}")
        
        # Combine all dataframes
        if all_dataframes:
            combined_df = pd.concat(all_dataframes, ignore_index=True)
            
            # Store the combined dataframe in session state for intelligent search
            st.session_state['aggregated_data'] = combined_df
            
            # Preview the standardized data
            st.subheader("Preview of Standardized Data")
            st.dataframe(combined_df)
            
            # Add button to use aggregated data in intelligent search
            st.subheader("Quick Actions")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔍 Use in Intelligent Search", use_container_width=True):
                    # Set flag to indicate data should be used in intelligent search
                    st.session_state['use_aggregated_in_search'] = True
                    st.success("✅ Aggregated data is ready for Intelligent Search!")
                    st.info("👉 Go to the 'Intelligent Search' tab to start searching through your aggregated data.")
            
            with col2:
                # Keep the existing export functionality
                st.write("")  # Placeholder for alignment
            
            # Export the combined data
            st.subheader("Export Combined Data")
            
            export_format = st.radio(
                "Export Format",
                ["CSV", "Excel"],
                horizontal=True
            )
            
            if st.button("Generate Combined File"):
                downloads_dir = os.path.join(os.getcwd(), "downloads")
                os.makedirs(downloads_dir, exist_ok=True)
                
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                
                if export_format == "CSV":
                    export_file_path = os.path.join(downloads_dir, f"combined_news_data_{timestamp}.csv")
                    combined_df.to_csv(export_file_path, index=False)
                    mime_type = "text/csv"
                    file_extension = "csv"
                else:  # Excel
                    export_file_path = os.path.join(downloads_dir, f"combined_news_data_{timestamp}.xlsx")
                    combined_df.to_excel(export_file_path, index=False)
                    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    file_extension = "xlsx"
                
                # Create a download button for the exported file
                with open(export_file_path, "rb") as file:
                    st.download_button(
                        label=f"Download Combined {export_format} File",
                        data=file,
                        file_name=f"combined_news_data_{timestamp}.{file_extension}",
                        mime=mime_type
                    )
                
                st.success(f"Combined file generated successfully!")
        
        else:
            st.warning("No data could be processed from the uploaded files.")
    """Render the Data Aggregation tab"""