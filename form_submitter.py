import json
import logging
import sys
import os
import time

from form_interaction import FormInteraction

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("form_submission.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_browser():
    """
    Set up Chrome WebDriver with advanced configuration
    
    :return: Configured Selenium WebDriver
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager

        # Chrome options for stability and stealth
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--log-level=3")  # Minimal logging
        
        # Anti-bot detection options
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Optional: Run in headless mode (uncomment if needed)
        # chrome_options.add_argument("--headless")
        
        # Use WebDriver Manager to handle driver installation
        service = Service(ChromeDriverManager().install())
        
        # Create driver with service and options
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Additional anti-detection script
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    except Exception as e:
        logger.error(f"Error setting up browser: {e}")
        raise

def load_form_data(file_path):
    """
    Load form data from JSON file
    
    :param file_path: Path to the JSON file
    :return: Parsed JSON data
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading form data: {e}")
        return []

def process_forms(json_data, user_data):
    """
    Process forms from JSON data
    
    :param json_data: List of form entries
    :param user_data: User data dictionary
    """
    # Setup browser
    driver = None
    try:
        driver = setup_browser()
        
        # Form interaction instance
        form_interaction = FormInteraction(driver)
        
        # Process each form entry
        for index, form_entry in enumerate(json_data, 1):
            try:
                # Skip forms with errors or no fields
                if form_entry.get('error') or not form_entry.get('fields'):
                    logger.warning(f"Skipping form {index} due to error or no fields")
                    continue
                
                # Get URL
                url = form_entry.get('url')
                if not url:
                    logger.warning(f"No URL found for form {index}")
                    continue
                
                # Log current processing
                logger.info(f"Processing form {index}/{len(json_data)}: {url}")
                
                # Navigate to URL
                driver.get(url)
                
                # Wait for page to load
                time.sleep(3)
                
                # Process the form
                success = form_interaction.process_form(form_entry, user_data)
                
                # Log result
                if success:
                    logger.info(f"Successfully processed form: {url}")
                else:
                    logger.warning(f"Failed to process form: {url}")
                
                # Optional: Add delay between form submissions
                time.sleep(8)
            
            except Exception as e:
                logger.error(f"Error processing form {index}: {e}")
                continue
    
    except Exception as e:
        logger.critical(f"Critical error in form processing: {e}")
    
    finally:
        # Ensure driver is closed
        if driver:
            try:
                driver.quit()
            except:
                pass

def main():
    """
    Main entry point for the script
    """
    # User data dictionary
    user_data = {
        "FirstName": "John",
        "LastName": "Doe",
        "Email": "johndoe@example.com",
        "Phone": "5551234567"
    }
    
    # Path to input JSON file
    input_file = "form_fields.json"
    
    # Validate input file exists
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)
    
    # Load form data
    json_data = load_form_data(input_file)
    
    # Process forms
    process_forms(json_data, user_data)

if __name__ == "__main__":
    main()