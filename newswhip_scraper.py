from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging
import os

logger = logging.getLogger(__name__)

class NewswhipScraper:
    """
    A class to handle Newswhip data scraping operations.
    """
    
    def __init__(self, email, password):
        """
        Initialize the NewswhipScraper with credentials.
        
        Args:
            email (str): Newswhip account email
            password (str): Newswhip account password
        """
        self.email = email
        self.password = password
        self.driver = None
        self.wait = None
        self.actions = None
        
    def _setup_driver(self):
        """Set up the Chrome driver with proper options."""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--start-maximized")
        
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
        
        return download_path
        
    def _login(self):
        """Log in to the Newswhip platform."""
        logger.info("Logging into Newswhip")
        self.driver.get("https://spike.newswhip.com/login")
        
        # Enter email and password
        self.wait.until(EC.presence_of_element_located((By.ID, "email"))).send_keys(self.email)
        self.wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(self.password)
        
        # Click login button
        self.wait.until(EC.element_to_be_clickable((By.ID, "loginFormSubmit"))).click()
        
        # Wait for login to complete
        self.wait.until(EC.presence_of_all_elements_located((
            By.XPATH, "//div[contains(@class, 'dashboard-list-item-container')]//span[contains(@class, 'single-search-dashboard-name')]"
        )))
        
        logger.info("Successfully logged into Newswhip")
    
    def get_folders(self):
        """
        Fetch all available folders.
        
        Returns:
            list: List of folder names
        """
        try:
            self._setup_driver()
            self._login()
            
            # Get all folder elements
            folder_elements = self.driver.find_elements(
                By.XPATH, 
                "//div[contains(@class, 'dashboard-list-item-container')]//span[contains(@class, 'single-search-dashboard-name')]"
            )
            
            folders = [folder.text.strip() for folder in folder_elements]
            logger.info(f"Found {len(folders)} folders")
            
            return folders
            
        except Exception as e:
            logger.error(f"Error fetching folders: {str(e)}")
            raise
        finally:
            if self.driver:
                self.driver.quit()
    
    def export_data(self, folder_name, time_choice):
        """
        Export data from a selected folder with specified time period.
        
        Args:
            folder_name (str): The name of the folder to export from
            time_choice (str): The time period choice (1-4)
            
        Returns:
            str: Path to the downloaded CSV file
        """
        download_path = None
        try:
            download_path = self._setup_driver()
            self._login()
            
            # Click on the selected folder
            folder_button = self.wait.until(EC.element_to_be_clickable((
                By.XPATH, f"//span[contains(text(), '{folder_name}')]/ancestor::button"
            )))
            folder_button.click()
            logger.info(f"Folder '{folder_name}' selected successfully.")
            try:
                # Wait for the tooltip's close button to be clickable
                tooltip_close_button = wait.until(EC.element_to_be_clickable((
                    By.XPATH, "//div[contains(@class, 'cdk-overlay-pane')]//button[contains(@class, 'btn-close') and contains(@class, 'close-button')]"
                )))
                tooltip_close_button.click()
                print("ℹ️ Closed the 'Top Themes Highlight' tooltip.")
                time.sleep(1) # Brief pause after closing
            except Exception as e:
                print(f"ℹ️ 'Top Themes Highlight' tooltip not found or already closed: {e}")
            # Wait for content to load and refresh
            # time.sleep(2)

            # Open Date Selection Dropdown
            date_selection_button = self.wait.until(EC.element_to_be_clickable((
                By.XPATH, "//div[contains(@class, 'header-bottom')]//button[contains(@class, 'date-picker-dropdown-toggle')]"
            )))
            date_selection_button.click()
            logger.info("Date selection dropdown opened.")
            
            # Wait for date panel to appear
            self.wait.until(EC.presence_of_element_located((
                By.XPATH, "//div[contains(@class, 'custom-datetime-container')]"
            )))
            
            # Select time range based on choice
            if time_choice == "1":
                label_xpath_prefix = "relative-time-hours-"
                label_description = "Last 24 hours"
                
                # Find the label by the prefix of its 'for' attribute
                label = self.wait.until(EC.element_to_be_clickable((
                    By.XPATH, f"//label[starts-with(@for, '{label_xpath_prefix}')]"
                )))
                label.click()
                
                # Find the closest ancestor div that acts as a container for this radio option
                # This container typically has a class like 'radio' or a similar grouping class.
                # We assume the input type="number" is within this container.
                parent_container = label.find_element(By.XPATH, "./ancestor::div[contains(@class, 'radio')][1]")
                
                # Find the number input field within this specific parent container
                input_field = parent_container.find_element(By.XPATH, ".//input[@type='number']")
                # Optional: If you also want to ensure min/max attributes match, you can use:
                # input_field = parent_container.find_element(By.XPATH, ".//input[@type='number' and @min='1' and @max='24']")
                
                input_field.clear()
                # input_field.send_keys("24") # Uncomment if you want to programmatically set the value
                print(f"✅ Selected {label_description}.")

            elif time_choice == "2":
                label_xpath_prefix = "relative-time-days-"
                label_description = "Last 7 days"
                
                label = self.wait.until(EC.element_to_be_clickable((
                    By.XPATH, f"//label[starts-with(@for, '{label_xpath_prefix}')]"
                )))
                label.click()
                
                parent_container = label.find_element(By.XPATH, "./ancestor::div[contains(@class, 'radio')][1]")
                input_field = parent_container.find_element(By.XPATH, ".//input[@type='number']")
                # Optional: For more specificity:
                # input_field = parent_container.find_element(By.XPATH, ".//input[@type='number' and @min='1' and @max='365']")
                
                input_field.clear()
                # input_field.send_keys("7")
                print(f"✅ Selected {label_description}.")

            elif time_choice == "3":
                label_xpath_prefix = "relative-time-months-"
                label_description = "Last 1 month"
                
                label = self.wait.until(EC.element_to_be_clickable((
                    By.XPATH, f"//label[starts-with(@for, '{label_xpath_prefix}')]"
                )))
                label.click()
                
                parent_container = label.find_element(By.XPATH, "./ancestor::div[contains(@class, 'radio')][1]")
                input_field = parent_container.find_element(By.XPATH, ".//input[@type='number']")
                # Optional: For more specificity:
                # input_field = parent_container.find_element(By.XPATH, ".//input[@type='number' and @min='1' and @max='12']")
                
                input_field.clear()
                # input_field.send_keys("1")
                print(f"✅ Selected {label_description}.")

            elif time_choice == "4":
                label_xpath_prefix = "full-year-"
                label_description = "Full Year"
                
                # For "Full Year", there's typically no separate number input field to interact with via script.
                # We just click the label identified by its 'for' attribute prefix.
                label = self.wait.until(EC.element_to_be_clickable((
                    By.XPATH, f"//label[starts-with(@for, '{label_xpath_prefix}')]"
                )))
                label.click()
                print(f"✅ Selected {label_description}.")
    
            # Click Apply Button
            apply_button = self.wait.until(EC.element_to_be_clickable((
                By.XPATH, "//button[contains(@class, 'btn-primary') and text()='Apply']"
            )))
            apply_button.click()
            logger.info("Date range applied successfully.")

            # Wait for date filter to apply
            time.sleep(2)
            
            # Click 3-dot menu under All Articles
            all_articles_menu = self.wait.until(EC.element_to_be_clickable((
                By.XPATH, "//span[contains(text(), 'All Articles')]/ancestor::div[contains(@class, 'header-top')]//button[contains(@class, 'widget-action') and .//i[contains(@class, 'fa-ellipsis-v')]]"
            )))
            all_articles_menu.click()
            
            # Hover on Export and Click CSV
            export_button = self.wait.until(EC.visibility_of_element_located((
                By.XPATH, "//span[text()='Export']/parent::a"
            )))
            self.actions.move_to_element(export_button).perform()
            time.sleep(2)
            
            csv_button = self.wait.until(EC.presence_of_element_located((
                By.XPATH, "//spike-export-panel-dropdown-menu//span[text()='CSV']"
            )))
            self.driver.execute_script("arguments[0].click();", csv_button)
            
            logger.info("CSV Export triggered successfully.")
            
            # Wait for download to complete
            time.sleep(3)
            
            # Find the latest CSV file in the download directory
            csv_files = [f for f in os.listdir(download_path) if f.endswith('.csv')]
            if not csv_files:
                raise Exception("No CSV file was downloaded")
                
            latest_file = max([os.path.join(download_path, f) for f in csv_files], key=os.path.getctime)
            
            # Time period mapping for filename
            time_period_names = {
                "1": "24hours",
                "2": "7days",
                "3": "1month",
                "4": "fullyear"
            }
            
            time_period_name = time_period_names[time_choice]
            
            # Format timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            # Create a sanitized filename
            sanitized_username = self.email.split('@')[0]
            sanitized_folder = folder_name.replace(' ', '_').replace('/', '_')
            
            new_filename = f"newswhip_{sanitized_username}_{time_period_name}_{sanitized_folder}_{timestamp}.csv"
            new_file_path = os.path.join(download_path, new_filename)
            
            # Rename the file
            os.rename(latest_file, new_file_path)
            
            logger.info(f"CSV file renamed and saved to: {new_file_path}")
            
            return new_file_path
            
        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            raise
        finally:
            if self.driver:
                self.driver.quit()