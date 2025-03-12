import json
import logging
import sys
import os
import time
import csv
from urllib.parse import urlparse

from form_interaction import FormInteraction

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("form_tester.log"),
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

def save_user_notes_to_csv(data):
    """
    Save user notes to a single, persistent CSV file
    
    :param data: List of dictionaries containing URL and user notes
    """
    # Create 'outputs' directory if it doesn't exist
    os.makedirs('outputs', exist_ok=True)
    
    # Define the persistent CSV filename
    filename = 'outputs/user_notes.csv'
    
    try:
        # Check if file exists to determine if we need headers
        file_exists = os.path.exists(filename)
        
        with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
            # Determine fieldnames dynamically based on the first entry
            if data:
                fieldnames = ['timestamp', 'url', 'domain'] + list(data[0].keys() - {'url', 'domain', 'timestamp'})
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Write headers only if file didn't exist before
                if not file_exists:
                    writer.writeheader()
                
                # Write each entry with a timestamp
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                for entry in data:
                    full_entry = {
                        'timestamp': timestamp,
                        **entry
                    }
                    writer.writerow(full_entry)
        
        logger.info(f"User notes appended to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Error saving user notes to CSV: {e}")
        return None

def test_forms(json_data, user_data):
    """
    Test forms with user interaction and note-taking
    
    :param json_data: List of form entries
    :param user_data: User data dictionary
    :return: List of user notes
    """
    # Setup browser
    driver = None
    user_notes = []
    
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
                
                # Process the form
                form_interaction.process_form(form_entry, user_data)
                
                # Prompt for user input
                print(f"\n--- URL: {url} ---")
                print("Fill out the form and then enter any notes about this website.")
                print("Press Enter when done (leave blank if no notes).")
                
                # Wait for user input
                user_note = input("Your notes: ").strip()
                
                # Parse URL for domain
                parsed_url = urlparse(url)
                
                # Collect user notes
                if user_note or user_note == '':
                    user_notes.append({
                        'url': url,
                        'domain': parsed_url.netloc,
                        'user_note': user_note
                    })
                
            except Exception as e:
                logger.error(f"Error processing form {index}: {e}")
                continue
    
    except Exception as e:
        logger.critical(f"Critical error in form testing: {e}")
    
    finally:
        # Ensure driver is closed
        if driver:
            try:
                driver.quit()
            except:
                pass
        
        # Save user notes to CSV
        if user_notes:
            save_user_notes_to_csv(user_notes)
    
    return user_notes

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
    
    # Test forms with user interaction
    user_notes = test_forms(json_data, user_data)
    
    # Print summary
    print("\n--- Testing Complete ---")
    print(f"Total URLs processed: {len(user_notes)}")
    print(f"Notes collected for {len(user_notes)} websites")
    print("Notes saved in outputs/user_notes.csv")

if __name__ == "__main__":
    main()