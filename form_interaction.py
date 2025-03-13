from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementNotInteractableException,
    StaleElementReferenceException,
    NoSuchElementException
)
from selenium.webdriver.common.action_chains import ActionChains
import logging
import re
import time

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
            
            # Field name mapping for alternate field names
            field_mappings = {
                'Street': ['Street', 'StreetAddress', 'Address', 'AddressLine1', 'addr1'],
                'StreetAddress': ['Street', 'StreetAddress', 'Address', 'AddressLine1', 'addr1'],
                'Address': ['Street', 'StreetAddress', 'Address', 'AddressLine1', 'addr1'],
                'Email': ['Email', 'EmailAddress', 'email_address'],
                'ConfirmEmail': ['ConfirmEmail', 'EmailConfirm', 'email_confirm', 'verify_email'],
                'Phone': ['Phone', 'Telephone', 'PhoneNumber', 'phone_number', 'Mobile'],
                'City': ['City', 'Town', 'city_name'],
                'Zipcode': ['Zipcode', 'ZipCode', 'PostalCode', 'Zip', 'postal_code', 'zip_code'],
                'State': ['State', 'Province', 'Region', 'state_province'],
                'Country': ['Country', 'Nation', 'country_name']
            }
            
            for field_name, field_info in entry.get('fields', {}).items():
                # Skip Submit button
                if field_name == 'Submit':
                    # Log submit button location
                    submit_xpath = field_info.get('xpath', '')
                    if submit_xpath:
                        logger.info(f"Submit button found at XPath: {submit_xpath}")
                        continue
                    else:
                        logger.info("Submit button NOT found")

                
                
                # Check if this field is in our user data
                user_value = None
                
                # Direct match
                if field_name in user_data:
                    user_value = user_data[field_name]
                else:
                    # Try alternate field names
                    for user_key, possible_fields in field_mappings.items():
                        if field_name in possible_fields and user_key in user_data:
                            user_value = user_data[user_key]
                            logger.info(f"Using {user_key} value for field {field_name}")
                            break
                
                if user_value is None:
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
                    
                    # Handle different input types
                    element_type = field_info.get('type', '').lower()
                    
                    if element_type == 'select' or element.tag_name.lower() == 'select':
                        self.handle_dropdown(element, user_value)
                    elif element_type == 'checkbox' and isinstance(user_value, bool):
                        # Handle boolean checkbox values
                        is_checked = element.is_selected()
                        if (user_value and not is_checked) or (not user_value and is_checked):
                            element.click()
                    else:
                        # Clear existing value and input new value
                        element.clear()
                        element.send_keys(str(user_value))
                    
                    filled_fields.append(field_name)
                    logger.info(f"Filled {field_name} with value: {user_value}")
                
                except (TimeoutException, NoSuchElementException):
                    logger.warning(f"Could not find element for {field_name}")
                except Exception as e:
                    logger.error(f"Error filling {field_name}: {str(e)}")
            
            # Process additional required fields
            for additional_field in entry.get('additional_fields', []):
                try:
                    field_name = additional_field.get('field_name', '').lower()
                    xpath = additional_field.get('xpath', '')
                    element_type = additional_field.get('element_type', '').lower()
                    
                    # Skip if no xpath
                    if not xpath:
                        continue
                    
                    # Check if the additional field name matches any of our keys using more flexible matching
                    matching_key = None
                    matching_value = None
                    
                    # Try direct user data keys first
                    for key, value in user_data.items():
                        key_lower = key.lower()
                        if key_lower in field_name or field_name in key_lower:
                            matching_key = key
                            matching_value = value
                            break
                    
                    # If no direct match, try the alternate field names
                    if not matching_key:
                        for user_key, possible_fields in field_mappings.items():
                            if user_key in user_data:
                                for possible_field in possible_fields:
                                    if possible_field.lower() in field_name or field_name in possible_field.lower():
                                        matching_key = user_key
                                        matching_value = user_data[user_key]
                                        break
                                if matching_key:
                                    break
                    
                    if not matching_key:
                        continue
                    
                    # Find element
                    element = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    
                    # Handle based on element type
                    if element_type == 'select' or element.tag_name.lower() == 'select':
                        self.handle_dropdown(element, matching_value)
                    elif element_type == 'checkbox' and isinstance(matching_value, bool):
                        # Handle boolean checkbox values
                        is_checked = element.is_selected()
                        if (matching_value and not is_checked) or (not matching_value and is_checked):
                            element.click()
                    else:
                        # Clear and input value
                        element.clear()
                        element.send_keys(str(matching_value))
                    
                    filled_fields.append(field_name)
                    logger.info(f"Filled additional field {field_name} with value: {matching_value}")
                
                except (TimeoutException, NoSuchElementException):
                    logger.warning(f"Could not find additional field: {additional_field}")
                except Exception as e:
                    logger.error(f"Error filling additional field: {str(e)}")
            
            # Handle privacy checkboxes if needed
            self.handle_privacy_field(entry)
            
            # Return True if any fields were filled
            return len(filled_fields) > 0
        
        except Exception as e:
            logger.error(f"Unexpected error processing form: {e}")
            return False
    
    def handle_dropdown(self, element, value):
        """
        Enhanced dropdown handling with multiple selection strategies
        
        :param element: The dropdown element
        :param value: The value to select
        """
        try:
            # Standard Select approach
            select = Select(element)
            
            # Strategy 1: Try to select by visible text
            try:
                select.select_by_visible_text(str(value))
                logger.info(f"Selected dropdown option by visible text: {value}")
                return
            except Exception:
                pass
            
            # Strategy 2: Try to select by value
            try:
                select.select_by_value(str(value))
                logger.info(f"Selected dropdown option by value: {value}")
                return
            except Exception:
                pass
            
            # Strategy 3: Find partial text match
            try:
                options = select.options
                for option in options:
                    option_text = option.text.lower()
                    if str(value).lower() in option_text:
                        select.select_by_visible_text(option.text)
                        logger.info(f"Selected dropdown option by partial text match: {option.text}")
                        return
            except Exception:
                pass
            
            # Strategy 4: Select first non-empty option as fallback
            try:
                options = select.options
                for option in options:
                    if option.text.strip() and not option.text.lower() in ['select', 'choose', 'pick', '---']:
                        select.select_by_visible_text(option.text)
                        logger.info(f"Selected first valid dropdown option as fallback: {option.text}")
                        return
            except Exception:
                pass
                
            # Strategy 5: Select by index as last resort
            try:
                select.select_by_index(1)  # Usually index 0 is the placeholder
                logger.info("Selected dropdown option by index 1")
                return
            except Exception:
                pass
                
        except Exception as e:
            logger.warning(f"Standard dropdown selection failed: {e}")
            
            # Handle non-standard dropdowns (custom dropdowns using divs/spans)
            try:
                # Click to open the dropdown
                ActionChains(self.driver).move_to_element(element).click().perform()
                time.sleep(0.5)
                
                # Find dropdown items
                dropdown_items = None
                
                # Try various common patterns for custom dropdowns
                selectors = [
                    f"//ul[contains(@class, 'dropdown')]/li",
                    f"//div[contains(@class, 'dropdown')]/div",
                    f"//div[contains(@class, 'select')]/div",
                    f"//div[contains(@class, 'option')]",
                    f"//li[contains(@class, 'option')]",
                    f"//div[contains(@role, 'option')]"
                ]
                
                for selector in selectors:
                    try:
                        dropdown_items = WebDriverWait(self.driver, 2).until(
                            EC.presence_of_all_elements_located((By.XPATH, selector))
                        )
                        if dropdown_items:
                            break
                    except:
                        continue
                
                if dropdown_items:
                    # Strategy 1: Try to find exact text match
                    for item in dropdown_items:
                        if str(value).lower() == item.text.lower():
                            item.click()
                            logger.info(f"Selected custom dropdown option by exact match: {item.text}")
                            return
                    
                    # Strategy 2: Try to find partial text match
                    for item in dropdown_items:
                        if str(value).lower() in item.text.lower():
                            item.click()
                            logger.info(f"Selected custom dropdown option by partial match: {item.text}")
                            return
                    
                    # Strategy 3: Select first item as fallback
                    if len(dropdown_items) > 0:
                        dropdown_items[0].click()
                        logger.info(f"Selected first custom dropdown option as fallback: {dropdown_items[0].text}")
                        return
            except Exception as e:
                logger.warning(f"Custom dropdown selection failed: {e}")
    
    def handle_privacy_field(self, entry):
        """
        Handle privacy checkboxes/consent fields
        
        :param entry: Dictionary containing form entry data
        """
        try:
            # Try to find privacy field
            privacy_info = entry.get('fields', {}).get('Privacy', {})
            
            if privacy_info and privacy_info.get('found', False):
                xpath = privacy_info.get('xpath', '')
                if not xpath:
                    return
                
                try:
                    # Find element
                    element = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    
                    # Check if it's already selected
                    if element.get_attribute('type') == 'checkbox' and element.is_selected():
                        logger.info("Privacy checkbox already selected")
                        return
                    
                    # Try different approaches to interact with the checkbox
                    try:
                        # First approach: Try to click the label instead of the checkbox
                        # This often works better for styled checkboxes
                        try:
                            # First try to find an associated label
                            checkbox_id = element.get_attribute('id')
                            if checkbox_id:
                                label = self.driver.find_element(By.XPATH, f"//label[@for='{checkbox_id}']")
                                label.click()
                                logger.info("Clicked label associated with privacy checkbox")
                                return
                        except Exception as label_error:
                            logger.debug(f"Label click failed: {label_error}")
                        
                        # Second approach: standard click
                        element.click()
                        logger.info("Clicked privacy checkbox/consent")
                    except Exception as click_error:
                        logger.warning(f"Standard click failed: {click_error}")
                        try:
                            # Third approach: JavaScript click
                            self.driver.execute_script("arguments[0].click();", element)
                            logger.info("Clicked privacy checkbox via JavaScript")
                        except Exception as js_error:
                            logger.warning(f"JavaScript click failed: {js_error}")
                            try:
                                # Fourth approach: Set attribute directly if it's a checkbox
                                if element.get_attribute('type') == 'checkbox':
                                    self.driver.execute_script(
                                        "arguments[0].setAttribute('checked', 'checked'); "
                                        "arguments[0].checked = true; "
                                        "arguments[0].dispatchEvent(new Event('change', { bubbles: true }))",
                                        element
                                    )
                                    logger.info("Set privacy checkbox checked state via JavaScript")
                            except Exception as attr_error:
                                # Fifth approach: Special handling for React/styled components
                                try:
                                    # Try to find span next to input as a click target
                                    self.driver.execute_script(
                                        "arguments[0].parentNode.querySelector('span').click();",
                                        element
                                    )
                                    logger.info("Clicked span element next to privacy checkbox")
                                except Exception as span_error:
                                    logger.error(f"All privacy checkbox interaction methods failed: {span_error}")
                except Exception as e:
                    logger.warning(f"Error interacting with privacy field: {e}")
        except Exception as e:
            logger.warning(f"Error in privacy field handling: {e}")