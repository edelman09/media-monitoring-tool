from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging
import os

logger = logging.getLogger(__name__)

class TalkwalkerScraper:
    """
    A class to handle Talkwalker data scraping operations.
    """
    
    def __init__(self, email, password):
        """
        Initialize the TalkwalkerScraper with credentials.
        
        Args:
            email (str): Talkwalker account email
            password (str): Talkwalker account password
        """
        self.email = email
        self.password = password
        self.driver = None
        self.wait = None
        self.actions = None
        self.is_logged_in = False
        self.current_project = None
        
    def _setup_driver(self):
        """
        Set up the Chrome driver with proper options if it's not already set up.
        
        Returns:
            str: Path to download directory
        """
        # Only setup the driver if it doesn't exist or has been quit
        if self.driver is None:
            options = Options()
            options.add_argument("--start-maximized")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            # options.add_argument("--headless")
            
            # Set download preferences
            download_path = os.path.join(os.getcwd(), "downloads")
            os.makedirs(download_path, exist_ok=True)
            
            prefs = {
                "download.default_directory": download_path,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False
            }
            options.add_experimental_option("prefs", prefs)
            
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            self.wait = WebDriverWait(self.driver, 20)
            self.actions = ActionChains(self.driver)
            logger.info("Chrome driver has been set up")
            
            return download_path
        else:
            # Driver already exists, just return the download path
            download_path = os.path.join(os.getcwd(), "downloads")
            return download_path
    
    def close(self):
        """Close the browser and clean up resources."""
        if self.driver:
            logger.info("Closing browser session")
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Error closing driver: {str(e)}")
            finally:
                self.driver = None
                self.wait = None
                self.actions = None
                self.is_logged_in = False
                self.current_project = None
    
    def _login(self):
        """
        Log in to the Talkwalker platform if not already logged in.
        
        Returns:
            bool: True if login successful or already logged in, False otherwise
        """
        try:
            # Setup driver if it doesn't exist
            self._setup_driver()
            
            if self.is_logged_in:
                # Try to verify if still logged in by checking for project button
                try:
                    self.driver.find_element(By.XPATH, "//button[contains(@class,'p-navbar-project-selection')]")
                    logger.info("Already logged in to Talkwalker.")
                    return True
                except:
                    # Element not found, we need to login again
                    logger.info("Session expired, logging in again.")
                    self.is_logged_in = False
            
            # Navigate to login page
            logger.info("Navigating to Talkwalker login page...")
            self.driver.get("https://app.talkwalker.com/app/login")
            
            # Enter email
            logger.info("Entering email...")
            self.wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(self.email)
            self.wait.until(EC.element_to_be_clickable((By.ID, "next-button"))).click()
            
            # Enter password
            logger.info("Entering password...")
            self.wait.until(EC.visibility_of_element_located((By.NAME, "password"))).send_keys(self.password)
            self.wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
            
            # Wait for login to complete by checking for the project button
            self.wait.until(EC.presence_of_element_located((
                By.XPATH, "//button[contains(@class,'p-navbar-project-selection')]"
            )))
            
            self.is_logged_in = True
            logger.info("Successfully logged into Talkwalker.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to login to Talkwalker: {str(e)}")
            self.is_logged_in = False
            return False
    
    def get_projects(self):
        """
        Fetch all available projects.
        
        Returns:
            list: List of project dictionaries with 'id' and 'name' keys
        """
        try:
            # Setup driver and login
            self._setup_driver()
            if not self._login():
                raise Exception("Failed to login to Talkwalker.")
            
            # Click on the project dropdown
            logger.info("Opening project dropdown...")
            project_dropdown_button = self.wait.until(EC.element_to_be_clickable((
                By.XPATH, "//button[contains(@class,'p-navbar-project-selection')]"
            )))
            project_dropdown_button.click()
            
            # Fetch all projects
            logger.info("Fetching project elements...")
            project_elements = self.wait.until(EC.presence_of_all_elements_located((
                By.XPATH, "//div[contains(@class,'nav-menu-body-content')]//div[contains(@class,'navbar-project') and contains(@class,'p-menu-item')]//div[contains(@class,'menu-label')]"
            )))
            
            projects = []
            for idx, elem in enumerate(project_elements, start=1):
                project_name = elem.text.strip()
                projects.append({
                    "id": idx,
                    "name": project_name
                })
            
            logger.info(f"Found {len(projects)} projects.")
            # Click on the project dropdown again to close it
            project_dropdown_button.click()
            return projects
            
        except Exception as e:
            logger.error(f"Error fetching projects: {str(e)}")
            raise
    
    def select_project_and_navigate_to_topic_analytics(self, project_id):
        """
        Select project and navigate to Topic Analytics.
        
        Args:
            project_id (int): The ID of the project to select (1-based index)
        """
        try:
            if not self.is_logged_in:
                if not self._login():
                    raise Exception("Login failed")
            
            # Find the selected project
            projects = self.get_projects()
            project = None
            for p in projects:
                if p["id"] == project_id:
                    project = p
                    break
                    
            if project is None:
                raise ValueError(f"Project with ID {project_id} not found")
            
            # Click on the project dropdown
            project_dropdown_button = self.wait.until(EC.element_to_be_clickable((
                By.XPATH, "//button[contains(@class,'p-navbar-project-selection')]"
            )))
            project_dropdown_button.click()
            
            # Click on the selected project
            logger.info(f"Selecting project: {project['name']}")
            project_elements = self.wait.until(EC.presence_of_all_elements_located((
                By.XPATH, "//div[contains(@class,'nav-menu-body-content')]//div[contains(@class,'navbar-project') and contains(@class,'p-menu-item')]//div[contains(@class,'menu-label')]"
            )))
            
            if project_id > len(project_elements) or project_id < 1:
                raise ValueError(f"Project ID {project_id} is out of range")
                
            selected_project_element = project_elements[project_id - 1]
            self.driver.execute_script("arguments[0].click();", selected_project_element)
            
            # Wait for project switching
            time.sleep(3)
            
            # Navigate to Topic Analytics
            logger.info("Navigating to Topic Analytics...")
            topic_analytics_card = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH, 
                    "//div[contains(@class, 'descriptive-card-title')]//span[contains(text(), 'Topic Analytics')]/ancestor::div[contains(@class, 'descriptive-card')]"
                ))
            )
            topic_analytics_card.click()
            
            # Wait for the view container
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "view-container")))
            time.sleep(2)
            
            self.current_project = project
            logger.info(f"Successfully navigated to project {project['name']} and Topic Analytics")
            
        except Exception as e:
            logger.error(f"Error selecting project and navigating: {str(e)}")
            raise
    
    def get_categories(self):
        """
        Get all available categories for the current project.
        
        Returns:
            list: List of category dictionaries with 'id' and 'name' keys
        """
        try:
            if not self.is_logged_in:
                if not self._login():
                    raise Exception("Login failed")
                    
            logger.info("Fetching available categories...")
            
            # Get all category containers
            category_containers = self.wait.until(EC.presence_of_all_elements_located(
                (By.XPATH, "//div[contains(@class,'p-sbtm-item') and contains(@class, 'group')]")
            ))
            
            categories = []
            for idx, category in enumerate(category_containers, start=1):
                try:
                    category_name = category.find_element(By.XPATH, ".//span[contains(@class, 'item-label')]").text.strip()
                    categories.append({
                        "id": idx,
                        "name": category_name
                    })
                except Exception as e:
                    logger.warning(f"Skipping category due to error: {str(e)}")
                    continue
            
            logger.info(f"Found {len(categories)} categories")
            return categories
            
        except Exception as e:
            logger.error(f"Error fetching categories: {str(e)}")
            raise
    
    def get_topics_for_category(self, category_id):
        """
        Get topics for a specific category.
        
        Args:
            category_id (int): The ID of the category (1-based index)
            
        Returns:
            list: List of topic dictionaries with 'id' and 'name' keys
        """
        try:
            if not self.is_logged_in:
                if not self._login():
                    raise Exception("Login failed")
            
            # Get categories
            categories = self.get_categories()
            
            if category_id > len(categories) or category_id < 1:
                raise ValueError(f"Category ID {category_id} is out of range")
            
            selected_category = categories[category_id - 1]
            logger.info(f"Getting topics for category: {selected_category['name']}")
            
            # Find the selected category element
            category_containers = self.wait.until(EC.presence_of_all_elements_located(
                (By.XPATH, "//div[contains(@class,'p-sbtm-item') and contains(@class, 'group')]")
            ))
            
            selected_category_element = category_containers[category_id - 1]
            
            # Expand selected category if not expanded
            try:
                # Check if category is collapsed
                if len(selected_category_element.find_elements(By.XPATH, "following-sibling::div[contains(@class, 'child')]")) == 0:
                    # Try to find the toggle button and click it
                    toggle_button = selected_category_element.find_element(By.XPATH, ".//button[contains(@class,'action-icon')]")
                    toggle_button.click()
                    time.sleep(1)  # Wait for animation
                    logger.info(f"Expanded category '{selected_category['name']}' to show topics")
            except Exception as e:
                logger.warning(f"Error while expanding category: {str(e)}")
            
            # Get topics inside the selected category
            topics_in_category = selected_category_element.find_elements(By.XPATH, "following-sibling::div[contains(@class, 'child')]")
            
            topics = []
            for idx, topic in enumerate(topics_in_category, start=1):
                try:
                    topic_name = topic.find_element(By.XPATH, ".//span[contains(@class, 'item-label')]").text.strip()
                    topics.append({
                        "id": idx,
                        "name": topic_name
                    })
                except Exception:
                    continue
            
            logger.info(f"Found {len(topics)} topics in category '{selected_category['name']}'")
            return topics
            
        except Exception as e:
            logger.error(f"Error fetching topics: {str(e)}")
            raise
    
    def export_data(self, project_id, category_id, topic_id, time_choice):
        """
        Complete export workflow - combines all steps.
        
        Args:
            project_id (int): Project ID (1-based index)
            category_id (int): Category ID (1-based index) 
            topic_id (int): Topic ID (1-based index)
            time_choice (str): Time period choice ("1" to "6")
            
        Returns:
            str: Path to the downloaded CSV file
        """
        download_path = None
        try:
            # Setup driver and ensure we're logged in
            download_path = self._setup_driver()
            if not self._login():
                raise Exception("Login failed")
            
            # If we need to navigate to the project
            if self.current_project is None or self.current_project["id"] != project_id:
                self.select_project_and_navigate_to_topic_analytics(project_id)
            
            # Get the projects to get the project name
            projects = self.get_projects()
            project = next((p for p in projects if p["id"] == project_id), None)
            if not project:
                raise ValueError(f"Project with ID {project_id} not found")
            
            # Select time period
            logger.info(f"Selecting time period: {time_choice}")
            time_period_mapping = {
                "1": {"id": "d1", "label": "1D"},
                "2": {"id": "d7", "label": "7D"},
                "3": {"id": "d30", "label": "30D"},
                "4": {"id": "m3", "label": "3M"},
                "5": {"id": "m6", "label": "6M"},
                "6": {"id": "y1", "label": "1Y"},
            }
            
            selected_option = time_period_mapping.get(time_choice)
            if not selected_option:
                raise ValueError(f"Invalid time choice: {time_choice}")
                
            data_id = selected_option["id"]
            label = selected_option["label"]
            
            # Detect which UI pattern is present
            ui_pattern = self._detect_time_selection_pattern()
            logger.info(f"Detected time selection UI pattern: {ui_pattern}")
            
            if ui_pattern == "direct":
                # Try direct selection first - all time periods are directly visible
                try:
                    xpath = f"//div[@data-id='{data_id}']"
                    element = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    element.click()
                    logger.info(f"Selected time period using direct selection: {label}")
                except Exception as e:
                    logger.warning(f"Direct time period selection failed: {str(e)}, trying dropdown method...")
                    # Fallback to dropdown method
                    self._select_time_period_from_dropdown(data_id, label)
                    
            elif ui_pattern == "dropdown":
                # Some time periods might be in a "More" dropdown
                if time_choice in ["1", "2"] and self._check_time_period_visible(data_id):
                    # These might be directly visible in some projects
                    xpath = f"//div[@data-id='{data_id}']"
                    element = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    element.click()
                    logger.info(f"Selected time period using direct selection: {label}")
                else:
                    # Use dropdown method
                    self._select_time_period_from_dropdown(data_id, label)
            
            elif ui_pattern == "unknown":
                # Try all methods in sequence
                logger.info("Using fallback method for time period selection")
                try:
                    # Try direct selection first
                    xpath = f"//div[@data-id='{data_id}']"
                    element = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    element.click()
                    logger.info(f"Selected time period using direct selection: {label}")
                except Exception as e:
                    logger.warning(f"Direct time period selection failed: {str(e)}, trying dropdown method...")
                    # Fallback to dropdown method
                    try:
                        self._select_time_period_from_dropdown(data_id, label)
                    except Exception as e:
                        logger.error(f"All time period selection methods failed: {str(e)}")
                        raise
            
            time.sleep(2)
            
            # Get categories
            categories = self.get_categories()
            if category_id > len(categories) or category_id < 1:
                raise ValueError(f"Category ID {category_id} is out of range")
            
            selected_category = categories[category_id - 1]
            
            # Get topics for the selected category
            topics = self.get_topics_for_category(category_id)
            if topic_id > len(topics) or topic_id < 1:
                raise ValueError(f"Topic ID {topic_id} is out of range")
            
            selected_topic = topics[topic_id - 1]
            
            # Get the topic element and click it
            category_containers = self.driver.find_elements(By.XPATH, "//div[contains(@class,'p-sbtm-item') and contains(@class, 'group')]")
            selected_category_element = category_containers[category_id - 1]
            topics_in_category = selected_category_element.find_elements(By.XPATH, "following-sibling::div[contains(@class, 'child')]")
            
            if topic_id > len(topics_in_category):
                raise ValueError(f"Topic ID {topic_id} is out of range")
                
            selected_topic_element = topics_in_category[topic_id - 1]
            logger.info(f"Clicking on topic: {selected_topic['name']}")
            
            # Click the topic using the clickable part (a tag)
            topic_clickable_part = selected_topic_element.find_element(By.XPATH, ".//a[contains(@class, 'item-container')]")
            self.driver.execute_script("arguments[0].click();", topic_clickable_part)
            time.sleep(2)
            
            # Navigate to Results tab
            logger.info("Navigating to Results tab...")
            results_icon = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//i[contains(@class,'tw3-icon-results-list')]"))
            )
            results_icon.click()
            time.sleep(5)
            
            # Find the results widget and hover over it
            logger.info("Finding results widget...")
            results_widget = self.wait.until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//div[contains(@class,'widget-card-section') and .//div[contains(text(),'Group') and contains(@class,'bar-dd-menu-header')] and .//div[contains(text(),'Sort by') and contains(@class,'bar-dd-menu-header')]]"
                ))
            )
            self.actions.move_to_element(results_widget).perform()
            
            # Find and click three-dot button
            logger.info("Opening export menu...")
            three_dot_button = results_widget.find_element(
                By.XPATH,
                ".//div[contains(@class,'item-header-action-icon')]//button[i[contains(@class,'tw3-icon-three-dots')]]"
            )
            three_dot_button.click()
            
            # Click Export
            export_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//div[@id='EXPORT_ALL' and contains(@class,'clickable')]"))
            )
            export_button.click()
            
            # Wait for export modal and select CSV
            logger.info("Selecting CSV export format...")
            export_modal = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='dialog' and contains(@class,'modal-bubble')]"))
            )
            
            csv_button = export_modal.find_element(
                By.XPATH,
                ".//div[contains(@class,'custom-button-tab-label') and text()='CSV']/parent::div[@tabindex='0']"
            )
            csv_button.click()
            
            # Click Export button
            export_confirm_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "model-confirm-button"))
            )
            export_confirm_button.click()
            logger.info("Export initiated...")
            
            # Wait for download link
            logger.info("Waiting for download link...")
            download_link = self.wait.until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//div[contains(@class,'notification-renderer-item')]//div[contains(@class,'info-title')]//a[contains(@href,'.csv') and contains(text(),'here')]"
                ))
            )
            download_url = download_link.get_attribute("href")
            logger.info(f"Download URL obtained: {download_url}")
            
            # Navigate to URL to download file
            self.driver.get(download_url)
            logger.info("Downloading CSV file...")
            time.sleep(10)
            
            # Find the latest CSV file
            csv_files = [f for f in os.listdir(download_path) if f.endswith('.csv')]
            if not csv_files:
                raise Exception("No CSV file was downloaded")
                
            latest_file = max([os.path.join(download_path, f) for f in csv_files], key=os.path.getctime)
            
            # Create new filename with descriptive naming
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            sanitized_project = project["name"].replace(' ', '_').replace('/', '_')
            sanitized_category = selected_category["name"].replace(' ', '_').replace('/', '_')
            sanitized_topic = selected_topic["name"].replace(' ', '_').replace('/', '_')
            
            new_filename = f"talkwalker_{sanitized_project}_{sanitized_category}_{sanitized_topic}_{data_id}_{timestamp}.csv"
            new_file_path = os.path.join(download_path, new_filename)
            
            # Rename the file
            os.rename(latest_file, new_file_path)
            logger.info(f"CSV file saved as: {new_file_path}")
            
            return new_file_path
            
        except Exception as e:
            logger.error(f"Error in export workflow: {str(e)}")
            raise
    
    def _detect_time_selection_pattern(self):
        """
        Detect which UI pattern is used for time selection.
        
        Returns:
            str: "direct" if all time periods are directly accessible,
                 "dropdown" if a dropdown is needed for some time periods,
                 "unknown" if the pattern could not be determined
        """
        try:
            # Check if the "More" dropdown exists
            more_elements = self.driver.find_elements(By.XPATH, 
                "//div[contains(@class,'p-time-filter-header-event-more-label-wrapper')]")
            
            if more_elements and len(more_elements) > 0:
                # Check if some time periods are directly visible
                d1_elements = self.driver.find_elements(By.XPATH, "//div[@data-id='d1']")
                d7_elements = self.driver.find_elements(By.XPATH, "//div[@data-id='d7']")
                
                if (d1_elements and len(d1_elements) > 0) or (d7_elements and len(d7_elements) > 0):
                    return "dropdown"  # Some items direct, some in dropdown
                else:
                    return "direct"  # All might be in the dropdown
            else:
                # Check if time periods are directly visible without dropdown
                time_elements = self.driver.find_elements(By.XPATH, 
                    "//div[contains(@class, 'p-time-filter-header-event-button')]")
                if time_elements and len(time_elements) > 0:
                    return "direct"
            
            return "unknown"  # Could not determine pattern
        except Exception as e:
            logger.warning(f"Error detecting time selection pattern: {str(e)}")
            return "unknown"
            
    def _check_time_period_visible(self, data_id):
        """
        Check if a specific time period element is directly visible.
        
        Args:
            data_id (str): The data-id attribute value of the time period element
            
        Returns:
            bool: True if the element is visible, False otherwise
        """
        try:
            elements = self.driver.find_elements(By.XPATH, f"//div[@data-id='{data_id}']")
            return elements and len(elements) > 0
        except:
            return False
            
    def _select_time_period_from_dropdown(self, data_id, label):
        """
        Select time period using the dropdown method.
        
        Args:
            data_id (str): The data-id attribute value of the time period element
            label (str): The label of the time period (for logging)
        """
        # First click the "More" dropdown
        more_button = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//div[contains(@class,'p-time-filter-header-event-more-label-wrapper')]")
        ))
        more_button.click()
        time.sleep(1)
        
        # Then select the time period
        xpath = f"//div[@data-id='{data_id}']"
        element = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        element.click()
        
        logger.info(f"Selected time period from dropdown: {label}")
