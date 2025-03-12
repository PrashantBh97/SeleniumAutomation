from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementNotInteractableException,
    StaleElementReferenceException
)
import logging
import re

# Configure logging
logger = logging.getLogger(__name__)

class FormInteraction:
    def __init__(self, driver, timeout=10):
        """
        Initialize FormInteraction with a Selenium WebDriver
        
        :param driver: Selenium WebDriver instance
        :param timeout: Maximum wait time for element interactions
        """
        self.driver = driver
        self.timeout = timeout
    
    def process_form(self, entry, user_data):
        """
        Process form and fill out fields
        
        :param entry: Dictionary containing form entry data
        :param user_data: Dictionary of user data to fill form
        :return: Boolean indicating success
        """
        try:
            # Process standard fields
            filled_fields = []
            
            for field_name, field_info in entry.get('fields', {}).items():
                # Skip Submit button
                if field_name == 'Submit':
                    # Log submit button location
                    submit_xpath = field_info.get('xpath', '')
                    if submit_xpath:
                        logger.info(f"Submit button found at XPath: {submit_xpath}")
                    continue
                
                # Check if this field is in our user data
                if field_name not in user_data:
                    continue
                
                # Get XPath
                xpath = field_info.get('xpath', '')
                if not xpath:
                    logger.warning(f"No XPath found for {field_name}")
                    continue
                
                try:
                    # Find the element
                    element = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    
                    # Get value from user data
                    value = user_data.get(field_name, '')
                    
                    # Handle different input types
                    if field_info.get('type', '').lower() == 'select':
                        try:
                            select = Select(element)
                            select.select_by_visible_text(value)
                        except:
                            # Fallback: try to select by index
                            select.select_by_index(1)
                    else:
                        # Clear existing value and input new value
                        element.clear()
                        element.send_keys(str(value))
                    
                    filled_fields.append(field_name)
                    logger.info(f"Filled {field_name} with value: {value}")
                
                except (TimeoutException, NoSuchElementException):
                    logger.warning(f"Could not find element for {field_name}")
                except Exception as e:
                    logger.error(f"Error filling {field_name}: {str(e)}")
            
            # Process additional required fields
            for additional_field in entry.get('additional_fields', []):
                try:
                    # Check if the additional field name matches any of our keys
                    matching_key = next((key for key in user_data.keys() if key.lower() in additional_field.get('name', '').lower()), None)
                    
                    if not matching_key:
                        continue
                    
                    # Find element
                    element = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, additional_field.get('xpath', '')))
                    )
                    
                    # Get value
                    value = user_data[matching_key]
                    
                    # Clear and input value
                    element.clear()
                    element.send_keys(str(value))
                    
                    filled_fields.append(additional_field.get('name', 'Unknown additional field'))
                    logger.info(f"Filled additional field with value: {value}")
                
                except (TimeoutException, NoSuchElementException):
                    logger.warning(f"Could not find additional field: {additional_field}")
                except Exception as e:
                    logger.error(f"Error filling additional field: {str(e)}")
            
            # Return True if any fields were filled
            return len(filled_fields) > 0
        
        except Exception as e:
            logger.error(f"Unexpected error processing form: {e}")
            return False