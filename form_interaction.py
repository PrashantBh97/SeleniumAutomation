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
                        logger.info(f"--------------->  Submit button found at XPath: {submit_xpath}")
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
                        self.select_checkbox_by_xpath(xpath, field_name)
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
                        self.select_checkbox_by_xpath(xpath, field_name)
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
            
            # # Strategy 4: Select first non-empty option as fallback
            # try:
            #     options = select.options
            #     for option in options:
            #         if option.text.strip() and not option.text.lower() in ['select', 'choose', 'pick', '---']:
            #             select.select_by_visible_text(option.text)
            #             logger.info(f"Selected first valid dropdown option as fallback: {option.text}")
            #             return
            # except Exception:
            #     pass
            
            # Strategy 5: Select last option as fallback
            try:
                options = select.options
                if options:
                    # Select the last non-placeholder option
                    last_valid_option = None
                    for option in reversed(options):
                        if option.text.strip() and not option.text.lower() in ['select', 'choose', 'pick', '---']:
                            last_valid_option = option
                            break
                    
                    if last_valid_option:
                        select.select_by_visible_text(last_valid_option.text)
                        logger.info(f"Selected last valid dropdown option as fallback: {last_valid_option.text}")
                        return
            except Exception:
                pass
                
            # Strategy 6: Select by index as last resort
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
                    
                    # Strategy 3: Select last item as fallback
                    if len(dropdown_items) > 0:
                        last_valid_item = None
                        for item in reversed(dropdown_items):
                            if item.text.strip() and not item.text.lower() in ['select', 'choose', 'pick', '---']:
                                last_valid_item = item
                                break
                        
                        if last_valid_item:
                            last_valid_item.click()
                            logger.info(f"Selected last valid custom dropdown option as fallback: {last_valid_item.text}")
                        else:
                            # If no valid item found, select the last item
                            dropdown_items[-1].click()
                            logger.info(f"Selected last custom dropdown option as fallback: {dropdown_items[-1].text}")
                        return
            except Exception as e:
                logger.warning(f"Custom dropdown selection failed: {e}")
    
    def handle_privacy_field(self, entry):
        """
        Handle privacy checkboxes/consent fields with multiple strategies
        
        :param entry: Dictionary containing form entry data
        """
        try:
            # Vue.js specific detection strategy
            vue_privacy_selectors = [
                "[data-v-41ea0579][type='checkbox'][name='checkbox']",
                "input.label-container__field.custom-checkbox[type='checkbox']"
            ]
            
            element = None
            for selector in vue_privacy_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break  # Stop if element is found
                except NoSuchElementException:
                    continue
            
            # If no Vue.js element found, fall back to original method
            if element is None:
                # Original privacy field finding logic
                privacy_info = entry.get('fields', {}).get('Privacy', {})
                
                if privacy_info and privacy_info.get('found', False):
                    xpath = privacy_info.get('xpath', '')
                    if not xpath:
                        return
                    
                    # Extract the ID from xpath if possible
                    checkbox_id = None
                    if 'id=' in xpath:
                        id_match = re.search(r'id=[\'"]([^\'"]+)[\'"]', xpath)
                        if id_match:
                            checkbox_id = id_match.group(1)
                    
                    # First try to find by xpath
                    try:
                        element = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, xpath))
                        )
                    except Exception as xpath_error:
                        # If xpath fails and we have ID, try finding by ID directly
                        try:
                            if checkbox_id:
                                element = self.driver.find_element(By.ID, checkbox_id)
                            else:
                                logger.warning("Element not found by XPath and no ID available")
                                return
                        except Exception as id_error:
                            logger.warning(f"Error finding privacy checkbox: {id_error}")
                            return
            
            # If still no element found, return
            if element is None:
                logger.warning("No privacy checkbox found")
                return
            
            # Check if it's already selected
            if element.get_attribute('type') == 'checkbox' and element.is_selected():
                logger.info("Privacy checkbox already selected")
                return
            
            # Make sure element is in view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)  # Brief pause for scrolling
            
            # Multiple strategies to click the checkbox
            strategies = [
                # Strategy 1: Direct click on checkbox
                lambda: element.click(),
                
                # Strategy 2: JavaScript click on checkbox
                lambda: self.driver.execute_script("arguments[0].click();", element),
                
                # Strategy 3: Find and click the label if ID is available
                lambda: (self.driver.find_element(By.XPATH, f"//label[@for='{checkbox_id}']").click()) 
                        if 'checkbox_id' in locals() and checkbox_id else None,
                
                # Strategy 4: Click the frame/styled element nearby
                lambda: self.driver.find_element(By.CSS_SELECTOR, 
                                                f"#{checkbox_id} + .checkbox-frame, #{checkbox_id} ~ .nb-checkbox-frame, "
                                                f"#{checkbox_id} + span, #{checkbox_id} ~ span.checkbox-frame").click() 
                        if 'checkbox_id' in locals() and checkbox_id else None,
                
                # Strategy 5: Set checked property via JavaScript
                lambda: self.driver.execute_script(
                    f"document.getElementById('{checkbox_id}').checked = true;"
                    f"document.getElementById('{checkbox_id}').dispatchEvent(new Event('change', {{bubbles: true}}));"
                ) if 'checkbox_id' in locals() and checkbox_id else self.driver.execute_script(
                    "arguments[0].checked = true; arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", 
                    element
                ),
                
                # Strategy 6: Use parent node to click
                lambda: self.driver.execute_script(
                    "arguments[0].parentNode.click();", element
                ),
                
                # Strategy 7: Find nearby span to click (for custom checkboxes)
                lambda: self.driver.execute_script(
                    "var spans = arguments[0].parentNode.querySelectorAll('span');"
                    "if(spans.length > 0) spans[0].click();",
                    element
                )
            ]
            
            # Try each strategy until one works
            for i, strategy in enumerate(strategies):
                try:
                    strategy()
                    logger.info(f"Privacy checkbox clicked with strategy {i+1}")
                    return
                except Exception as strategy_error:
                    logger.debug(f"Strategy {i+1} failed: {strategy_error}")
                    continue
            
            logger.warning("All privacy checkbox interaction strategies failed")
        
        except Exception as e:
            logger.warning(f"Error in privacy field handling: {e}")

    def select_checkbox_by_xpath(self, xpath, field_name='Checkbox'):
        """
        Select a checkbox by its xpath with multiple interaction strategies
        
        :param xpath: XPath of the checkbox element
        :param field_name: Name of the field for logging purposes
        """
        try:
            logger.info(f"Attempting to find checkbox for {field_name}")
            logger.info(f"XPath: {xpath}")
            
            # Detailed element search
            element = None
            try:
                # 1. Standard WebDriverWait
                element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                logger.info("Found element via presence method")
            except Exception as e1:
                logger.warning(f"Presence method failed: {e1}")
                
                try:
                    # 2. Visibility method
                    element = WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located((By.XPATH, xpath))
                    )
                    logger.info("Found element via visibility method")
                except Exception as e2:
                    logger.warning(f"Visibility method failed: {e2}")
                    
                    try:
                        # 3. JavaScript method
                        element = self.driver.execute_script(
                            "return document.evaluate(arguments[0], document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;", 
                            xpath
                        )
                        if element:
                            logger.info("Found element via JavaScript")
                        else:
                            logger.warning("JavaScript method could not find the element")
                    except Exception as e3:
                        logger.error(f"JavaScript method failed: {e3}")
                        return False
            
            # Interaction strategies
            if element:
                try:
                    # 1. Try clicking the element directly
                    if hasattr(element, 'click'):
                        element.click()
                        logger.info(f"Clicked {field_name} checkbox directly")
                        return True
                    elif element:
                        # If element was found via JavaScript
                        self.driver.execute_script("arguments[0].click();", element)
                        logger.info(f"Clicked {field_name} checkbox via JavaScript")
                        return True
                except Exception as click_error:
                    logger.warning(f"Direct click failed: {click_error}")
                
                try:
                    # 2. Try finding and clicking the associated label
                    checkbox_id = element.get_attribute('id') if hasattr(element, 'get_attribute') else element.id
                    label = self.driver.find_element(By.XPATH, f"//label[@for='{checkbox_id}']")
                    label.click()
                    logger.info(f"Clicked label for {field_name} checkbox")
                    return True
                except Exception as label_error:
                    logger.warning(f"Label click failed: {label_error}")
                
                try:
                    # 3. JavaScript attribute setting
                    self.driver.execute_script("""
                        var elem = arguments[0];
                        elem.checked = true;
                        elem.dispatchEvent(new Event('change', { bubbles: true }));
                    """, element)
                    logger.info(f"Set checkbox state via JavaScript for {field_name}")
                    return True
                except Exception as js_error:
                    logger.error(f"JavaScript checkbox setting failed: {js_error}")
            
            return False
        
        except Exception as e:
            logger.error(f"Comprehensive error in finding {field_name} checkbox: {e}")
            return False