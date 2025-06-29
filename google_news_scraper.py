import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import urllib.parse
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logger = logging.getLogger(__name__)

class GoogleNewsScraper:
    
    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/101.0.4951.54 Safari/537.36"
            )
        }
        self.download_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(self.download_dir, exist_ok=True)
        # Create a subdirectory for saving HTML debug files
        self.html_debug_dir = os.path.join(self.download_dir, "html_debug")
        os.makedirs(self.html_debug_dir, exist_ok=True)
        self._lock = threading.Lock()
    
    def _fetch_full_title(self, url):
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status() 
            if response.status_code == 200:
                article_soup = BeautifulSoup(response.content, "html.parser")
                if article_soup.title:
                    return article_soup.title.get_text().strip()
        except requests.exceptions.RequestException as e: 
            with self._lock:
                logger.error(f"Request error fetching full title for {url}: {e}")
        except Exception as e:
            with self._lock:
                logger.error(f"Error fetching full title for {url}: {e}")
        return ""
    
    def _build_search_url(self, keyword, languages, geos, time_period, sort_by="Relevance", start=0):
        base_url = "https://www.google.com/search"
        tbs_params = []

        if time_period:
            tbs_params.append(f"qdr:{time_period}")
        
        if sort_by.lower() == "recency":
            tbs_params.append("sbd:1")

        params = {
            "q": keyword, "tbm": "nws", "start": start, "hl": "en",
        }

        if tbs_params:
            params["tbs"] = ",".join(tbs_params)
            
        if languages:
            params["lr"] = "|".join(languages) 
        
        if geos:
            params["gl"] = geos[0] if geos else "" 

        query_string = urllib.parse.urlencode(params, safe='|')
        return f"{base_url}?{query_string}"
    
    def _scrape_page(self, url, keyword, page_num):
        """
        Scrapes a single page of Google News results.
        Saves HTML to a debug file if no results are found on the page.
        """
        page_results = []
        try:
            logger.info(f"Scraping URL for '{keyword}' page {page_num}: {url}")
            response = requests.get(url, headers=self.headers, timeout=10) 
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            
            # --- YOU WILL LIKELY NEED TO UPDATE THESE SELECTORS ---
            # Inspect the HTML of Google News search results to find the correct ones.
            # The current selectors are: div.gG0TJc, div.SoaBEf, div.Gx5Zad
            # These were examples and might be outdated.
            articles_elements = soup.select("div.SoaBEf") # Example selector, **NEEDS VERIFICATION**
            # If the above doesn't work, try more general ones or inspect HTML for new ones:
            # articles_elements = soup.select("div[role='main'] div[jscontroller] div > div") # Highly generic example

            if not articles_elements:
                with self._lock:
                    logger.warning(f"No article elements found on page {page_num} for '{keyword}' using current selectors. HTML content will be saved for debugging.")
                    # Save HTML for debugging
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    safe_keyword = "".join(c if c.isalnum() else "_" for c in keyword[:30])
                    debug_filename = os.path.join(self.html_debug_dir, f"debug_{safe_keyword}_page{page_num}_{timestamp}.html")
                    with open(debug_filename, "w", encoding="utf-8") as f:
                        f.write(soup.prettify())
                    logger.info(f"Saved HTML for '{keyword}' page {page_num} to {debug_filename}")
                return [] # Return empty list as no articles found with current selectors

            for el in articles_elements:
                link_el = el.find("a", href=True)
                if not link_el:
                    continue
                
                link = link_el["href"]
                
                title_el = el.select_one("h3, div[role='heading'], div.MBeuO, div.n0jPhd") # Example, NEEDS VERIFICATION
                truncated_title = title_el.get_text().strip() if title_el else ""
                
                full_title = ""
                if link and link.startswith("http"):
                    full_title = self._fetch_full_title(link)
                
                final_title = full_title if full_title else truncated_title

                snippet_el = el.select_one(".GI74Re, .st, .dbsr") # Example, NEEDS VERIFICATION
                snippet = snippet_el.get_text().strip() if snippet_el else ""
                
                date_el = el.select_one(".LfVVr, .slp span") # Example, NEEDS VERIFICATION (added span)
                date = date_el.get_text().strip() if date_el else ""
                
                source_el = el.select_one(".NUnG9d span, .MgUUmf span") # Example, NEEDS VERIFICATION (changed second selector)
                source = source_el.get_text().strip() if source_el else ""

                if final_title and link:
                    page_results.append({
                        "link": link, "title": final_title, "snippet": snippet,
                        "date": date, "source": source
                    })
            
            with self._lock:
                logger.info(f"Page {page_num} for '{keyword}': Found {len(page_results)} results using URL: {url}")
            
            return page_results
            
        except requests.exceptions.RequestException as e:
            with self._lock:
                logger.error(f"Request error scraping page {page_num} for '{keyword}' ({url}): {e}")
            return []
        except Exception as e:
            with self._lock:
                logger.error(f"Error scraping page {page_num} for '{keyword}' ({url}): {e}")
                 # Save HTML on other exceptions too, as it might be a parsing issue or unexpected HTML
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                safe_keyword = "".join(c if c.isalnum() else "_" for c in keyword[:30])
                debug_filename = os.path.join(self.html_debug_dir, f"debug_EXCEPTION_{safe_keyword}_page{page_num}_{timestamp}.html")
                if 'response' in locals() and response: # Check if response object exists
                    try:
                        with open(debug_filename, "w", encoding="utf-8") as f:
                            f.write(response.text) # Save raw text which might be useful
                        logger.info(f"Saved HTML on EXCEPTION for '{keyword}' page {page_num} to {debug_filename}")
                    except Exception as ex_save:
                        logger.error(f"Could not save debug HTML on exception: {ex_save}")
            return []

    def _get_multiple_pages_parallel(self, keyword, languages, geos, time_period, sort_by, max_pages=5):
        all_results = []
        urls_and_pages = []
        for page in range(max_pages):
            start_index = page * 10 
            url = self._build_search_url(keyword, languages, geos, time_period, sort_by, start_index)
            urls_and_pages.append((url, keyword, page + 1))
        
        with ThreadPoolExecutor(max_workers=min(5, max_pages)) as executor: 
            future_to_page = {
                executor.submit(self._scrape_page, url, kw, page_num): (url, kw, page_num)
                for url, kw, page_num in urls_and_pages
            }
            
            for future in as_completed(future_to_page):
                _url, kw, page_num = future_to_page[future]
                try:
                    page_results = future.result()
                    if page_results:
                        all_results.extend(page_results)
                except Exception as exc:
                    with self._lock:
                        logger.error(f"Page {page_num} for '{kw}' (sort: {sort_by}) generated an exception in future processing: {exc}")
        return all_results
    
    def _process_keyword_parallel(self, keyword, languages, geos, time_period, sort_by, max_pages):
        with self._lock:
            logger.info(f"Processing keyword: '{keyword}' with {max_pages} pages, sorted by {sort_by}")
        
        keyword_results = self._get_multiple_pages_parallel(keyword, languages, geos, time_period, sort_by, max_pages)
        
        for result in keyword_results:
            result['search_keyword'] = keyword
        
        with self._lock:
            logger.info(f"Completed keyword '{keyword}' (sort: {sort_by}): Found {len(keyword_results)} results")
        return keyword_results
    
    def get_news_data(self, keyword, languages=None, geos=None, time_period=None, sort_by="Relevance", max_pages=5):
        try:
            keywords = [kw.strip() for kw in keyword.split(',') if kw.strip()]
            if not keywords:
                logger.error("No valid keywords provided.")
                raise ValueError("No valid keywords provided")
            
            logger.info(f"Searching for news about {len(keywords)} keyword(s): {keywords}, sorted by {sort_by}")
            
            all_results = []
            max_keyword_workers = min(3, len(keywords))  
            
            with ThreadPoolExecutor(max_workers=max_keyword_workers) as executor:
                future_to_keyword = {
                    executor.submit(
                        self._process_keyword_parallel, 
                        kw, languages, geos, time_period, sort_by, max_pages
                    ): kw for kw in keywords
                }
                
                for future in as_completed(future_to_keyword):
                    kw = future_to_keyword[future]
                    try:
                        keyword_results = future.result()
                        all_results.extend(keyword_results)
                        logger.info(f"Completed processing keyword: '{kw}' (sort: {sort_by})")
                    except Exception as exc:
                        logger.error(f"Keyword '{kw}' (sort: {sort_by}) generated an exception during future result retrieval: {exc}")
            
            seen_urls = set()
            unique_results = []
            for result in all_results:
                if result.get('link') and result['link'] not in seen_urls:
                    seen_urls.add(result['link'])
                    unique_results.append(result)
            
            logger.info(f"Total unique results after deduplication: {len(unique_results)} (sorted by {sort_by})")
            
            if not unique_results:
                logger.info(f"No results found for keywords: {keywords} with sort_by: {sort_by}. No file will be generated.")
                return None 

            df = pd.DataFrame(unique_results)
            time_period_names = {
                "h": "past_hour", "d": "past_day", "w": "past_week",
                "m": "past_month", "y": "past_year"
            }
            time_period_name = time_period_names.get(time_period, "custom_time")
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            username = "anonymous" 

            sanitized_keywords = '_'.join([
                kw.replace(' ', '_').replace('/', '_').replace('\\', '_') for kw in keywords[:2] 
            ])
            if len(keywords) > 2:
                sanitized_keywords += f"_etc"
            sort_by_suffix = "_recency" if sort_by.lower() == "recency" else "_relevance"
            output_filename = os.path.join(
                self.download_dir, 
                f"googlenews_{username}_{time_period_name}_{sanitized_keywords}{sort_by_suffix}_{timestamp}.xlsx"
            )
            
            column_order = ['search_keyword', 'title', 'link', 'source', 'date', 'snippet']
            for col in column_order:
                if col not in df.columns:
                    df[col] = None 
            df = df.reindex(columns=column_order)
            
            df.to_excel(output_filename, index=False)
            logger.info(f"{len(unique_results)} unique results exported to {output_filename}")
            return output_filename
        except ValueError as ve: 
            logger.error(f"ValueError in get_news_data: {str(ve)}")
            raise 
        except Exception as e:
            logger.error(f"General error fetching news data: {str(e)}")
            raise