import os
import time
import base64
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple
from selenium.webdriver.common.by import By
from tron_ai.agents.productivity.android.utils import  AppiumClient
from datetime import datetime

logger = logging.getLogger(__name__)

# Shared client instance
_shared_client: Optional[AppiumClient] = None
_client_lock = threading.Lock()


class AndroidTools:
    """Tools for Android mobile automation using Appium."""
    
    @staticmethod
    def _get_shared_client() -> AppiumClient:
        """Get or create a shared client instance."""
        global _shared_client
        
        with _client_lock:
            if _shared_client is None:
                _shared_client = AppiumClient()
                logger.info("Created new shared AppiumClient instance")
            
            # Ensure client is connected
            if not _shared_client.is_connected():
                success = _shared_client.connect()
                if not success:
                    raise Exception("Failed to connect shared client to Android device")
                logger.info("Connected shared client to Android device")
            
            return _shared_client
    
    @staticmethod
    def disconnect_shared_client() -> Dict[str, Any]:
        """Disconnect and clean up the shared client."""
        global _shared_client
        
        with _client_lock:
            if _shared_client is not None:
                try:
                    _shared_client.disconnect()
                    _shared_client = None
                    logger.info("Disconnected and cleaned up shared client")
                    return {
                        "success": True,
                        "message": "Successfully disconnected shared client"
                    }
                except Exception as e:
                    logger.error(f"Error disconnecting shared client: {str(e)}")
                    return {
                        "success": False,
                        "message": f"Error disconnecting shared client: {str(e)}"
                    }
            else:
                return {
                    "success": True,
                    "message": "No shared client to disconnect"
                }

    @staticmethod
    def connect_device() -> Dict[str, Any]:
        """Connect to Android device via Appium."""
        try:
            client = AndroidTools._get_shared_client()
            device_info = client.get_device_info()
            return {
                "success": True,
                "message": "Successfully connected to Android device",
                "device_info": device_info
            }
        except Exception as e:
            logger.error(f"Error connecting to device: {str(e)}")
            return {
                "success": False,
                "message": f"Error connecting to device: {str(e)}"
            }

    @staticmethod
    def disconnect_device() -> Dict[str, Any]:
        """Disconnect from Android device."""
        return AndroidTools.disconnect_shared_client()

    @staticmethod
    def take_screenshot(filename: str = None, save_path: str = "/tmp") -> Dict[str, Any]:
        """Take a screenshot of the current screen."""
        try:
            client = AndroidTools._get_shared_client()

            if not filename:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"

            filepath = os.path.join(save_path, filename)

            # Ensure directory exists
            os.makedirs(save_path, exist_ok=True)

            # Take screenshot
            screenshot_data = client.driver.get_screenshot_as_png()

            # Save to file
            with open(filepath, "wb") as f:
                f.write(screenshot_data)

            return {
                "success": True,
                "message": f"Screenshot saved to {filepath}",
                "filepath": filepath,
                "filename": filename
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error taking screenshot: {str(e)}"
            }

    @staticmethod
    def press_key(key_code: str) -> Dict[str, Any]:
        """Press a hardware key on the device."""
        def _key_action():
            try:
                client = AndroidTools._get_shared_client()

                # Map common key names to Android key codes
                key_mapping = {
                    "home": 3,
                    "back": 4,
                    "menu": 82,
                    "search": 84,
                    "enter": 66,
                    "volume_up": 24,
                    "volume_down": 25,
                    "power": 26
                }

                key_code_lower = key_code.lower()
                if key_code_lower in key_mapping:
                    android_key_code = key_mapping[key_code_lower]
                else:
                    # Try to parse as integer
                    try:
                        android_key_code = int(key_code)
                    except ValueError:
                        return {
                            "success": False,
                            "message": f"Invalid key code: {key_code}. Use key name or numeric code."
                        }

                client.driver.press_keycode(android_key_code)

                return {
                    "success": True,
                    "message": f"Successfully pressed key: {key_code} ({android_key_code})"
                }

            except Exception as e:
                return {
                    "success": False,
                    "message": f"Error pressing key: {str(e)}"
                }
        
        return AndroidTools._execute_with_screen_analysis(_key_action)

    @staticmethod
    def analyze_current_screen() -> Dict[str, Any]:
        """Perform a comprehensive analysis of the current screen UI elements."""
        try:
            client = AndroidTools._get_shared_client()

            # Get page source (XML representation of UI hierarchy)
            page_source = client.driver.page_source

            open("page_source.xml", "w").write(page_source)

            return {
                "success": True,
                "raw_page_source": page_source
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error analyzing screen: {str(e)}"
            }

    @staticmethod
    def wait_for_element(locator_strategy: str, locator_value: str, timeout: int = 10) -> Dict[str, Any]:
        """Wait for an element to appear on screen."""
        try:
            client = AndroidTools._get_shared_client()

            element = client.wait_for_element(locator_strategy, locator_value, timeout)
            if element:
                return {
                    "success": True,
                    "message": f"Element found: {locator_strategy}={locator_value}",
                    "element_info": {
                        "text": element.get_attribute("text"),
                        "resource_id": element.get_attribute("resource-id"),
                        "class": element.get_attribute("class"),
                        "clickable": element.get_attribute("clickable") == "true",
                        "enabled": element.get_attribute("enabled") == "true"
                    }
                }
            else:
                return {
                    "success": False,
                    "message": f"Element not found within {timeout} seconds: {locator_strategy}={locator_value}"
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error waiting for element: {str(e)}"
            }
            
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Get Android system information and device details."""
        try:
            client = AndroidTools._get_shared_client()

            # Get various device information
            device_info = {
                "current_package": client.driver.current_package,
                "current_activity": client.driver.current_activity,
                "device_screen_size": client.driver.get_window_size(),
                "device_pixel_ratio": client.driver.execute_script("return window.devicePixelRatio"),
                "device_time": client.driver.get_device_time(),
                "is_keyboard_shown": client.driver.is_keyboard_shown(),
                "is_locked": client.driver.is_locked()
            }

            return {
                "success": True,
                "message": "Successfully retrieved system information",
                "system_info": device_info
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error getting system info: {str(e)}"
            }

    @staticmethod
    def _execute_click_action(client, element_description: str) -> Dict[str, Any]:
        """Execute a click action based on element description."""
        # Try different strategies to find and click the element - ID first, then XPath
        strategies = [
            # Try ID strategies first (fastest and most reliable)
            ('id', element_description),
            ('id', f"*:id/{element_description}"),
            # Fall back to XPath strategies
            ('xpath', f"//*[@resource-id='{element_description}']"),
            ('xpath', f"//*[contains(@resource-id, '{element_description}')]"),
            ('xpath', f"//*[contains(@text, '{element_description}')]"),
            ('xpath', f"//*[@content-desc='{element_description}']"),
            ('xpath', f"//*[@text='{element_description}']"),
            ('xpath', f"//android.widget.Button[contains(@text, '{element_description}')]"),
            ('xpath', f"//android.widget.TextView[contains(@text, '{element_description}')]"),
            ('class_name', 'android.widget.EditText'),
            ('class_name', 'android.widget.Button')
        ]

        for strategy, value in strategies:
            try:
                element = client.wait_for_element(strategy, value, timeout=5)
                if element:
                    element.click()
                    return {
                        "success": True,
                        "message": f"Successfully clicked element using {strategy}='{value}'"
                    }
            except:
                continue

        return {
            "success": False,
            "message": f"Could not find clickable element for '{element_description}'"
        }

    @staticmethod
    def _execute_type_action(client, text: str) -> Dict[str, Any]:
        """Execute a typing action."""
        # Try to find input field and type text - check for common IDs first, then XPath
        strategies = [
            # Try common input field IDs first
            ('id', 'search'),
            ('id', 'search_bar'),
            ('id', 'input'),
            ('id', 'edit_text'),
            ('id', 'text_input'),
            # Fall back to XPath strategies
            ('xpath', "//android.widget.EditText"),
            ('xpath', "//android.widget.AutoCompleteTextView"),
            ('xpath', "//android.widget.EditText[@enabled='true']"),
            ('xpath', "//android.widget.EditText[@clickable='true']"),
            ('xpath', "//*[@class='android.widget.EditText']"),
            ('class_name', 'android.widget.EditText'),
            ('class_name', 'android.widget.AutoCompleteTextView')
        ]

        for strategy, value in strategies:
            try:
                element = client.wait_for_element(strategy, value, timeout=5)
                if element:
                    element.clear()
                    element.send_keys(text)
                    return {
                        "success": True,
                        "message": f"Successfully typed '{text}' into element"
                    }
            except:
                continue

        return {
            "success": False,
            "message": f"Could not find input field to type '{text}'"
        }

    @staticmethod
    def _execute_with_screen_analysis(action_func, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute an action and automatically perform screen analysis afterward.
        This ensures the agent always has current screen state information.
        """
        try:
            # Execute the original action
            result = action_func(*args, **kwargs)
            
            # If the action was successful, perform screen analysis
            if result.get("success", False):
                try:
                    # Get current screen information
                    screen_analysis = AndroidTools.analyze_current_screen()
                    current_activity = AndroidTools.get_current_activity()
                    
                    # Add screen analysis to the result
                    result["screen_analysis"] = {
                        "timestamp": datetime.now().isoformat(),
                        "screen_state": screen_analysis,
                        "current_activity": current_activity,
                        "message": "Screen analyzed after action execution"
                    }
                    
                except Exception as analysis_error:
                    # If screen analysis fails, add error info but don't fail the main action
                    result["screen_analysis"] = {
                        "timestamp": datetime.now().isoformat(),
                        "error": f"Screen analysis failed: {str(analysis_error)}",
                        "message": "Action completed but screen analysis failed"
                    }
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error in action execution: {str(e)}",
                "screen_analysis": {
                    "timestamp": datetime.now().isoformat(),
                    "error": "Screen analysis not performed due to action failure",
                    "message": "Action failed before screen analysis could be performed"
                }
            }

    @staticmethod
    def type_text(locator_strategy: str, locator_value: str, text: str, clear_first: bool = True) -> Dict[str, Any]:
        """Type text into an input field."""
        def _type_action():
            try:
                client = AndroidTools._get_shared_client()

                element = client.wait_for_element(locator_strategy, locator_value)
                if element:
                    if clear_first:
                        element.clear()
                    element.send_keys(text)
                    return {
                        "success": True,
                        "message": f"Successfully typed text into element: {locator_strategy}={locator_value}"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Element not found: {locator_strategy}={locator_value}"
                    }

            except Exception as e:
                return {
                    "success": False,
                    "message": f"Error typing text: {str(e)}"
                }
        
        return AndroidTools._execute_with_screen_analysis(_type_action)

    @staticmethod
    def get_current_activity() -> Dict[str, Any]:
        """Get the current activity of the app."""
        client = AndroidTools._get_shared_client()
        return {
            "success": True,
            "activity": client.driver.current_activity
        }

    @staticmethod
    def swipe_screen(direction: str, duration: int = 1000) -> Dict[str, Any]:
        """Swipe the screen in a specified direction."""
        def _swipe_action():
            try:
                client = AndroidTools._get_shared_client()

                # Get screen dimensions
                screen_size = client.driver.get_window_size()
                width = screen_size['width']
                height = screen_size['height']

                # Define swipe coordinates based on direction
                if direction.lower() == "up":
                    start_x, start_y = width // 2, height * 3 // 4
                    end_x, end_y = width // 2, height // 4
                elif direction.lower() == "down":
                    start_x, start_y = width // 2, height // 4
                    end_x, end_y = width // 2, height * 3 // 4
                elif direction.lower() == "left":
                    start_x, start_y = width * 3 // 4, height // 2
                    end_x, end_y = width // 4, height // 2
                elif direction.lower() == "right":
                    start_x, start_y = width // 4, height // 2
                    end_x, end_y = width * 3 // 4, height // 2
                else:
                    return {
                        "success": False,
                        "message": "Invalid direction. Use: up, down, left, or right"
                    }

                # Perform swipe
                client.driver.swipe(start_x, start_y, end_x, end_y, duration)

                return {
                    "success": True,
                    "message": f"Successfully swiped {direction}"
                }

            except Exception as e:
                return {
                    "success": False,
                    "message": f"Error swiping screen: {str(e)}"
                }
        
        return AndroidTools._execute_with_screen_analysis(_swipe_action)

    @staticmethod
    def get_page_source() -> Dict[str, Any]:
        """Get the page source of the current screen."""
        client = AndroidTools._get_shared_client()
        return {
            "success": True,
            "page_source": client.driver.page_source
        }
        
    @staticmethod
    def click_element_by_text(text: str) -> Dict[str, Any]:
        """Click an element by its text content."""
        try:
            client = AndroidTools._get_shared_client()

            # Try different text-based strategies
            strategies = [
                (By.XPATH, f"//*[@text='{text}']"),
                (By.XPATH, f"//*[contains(@text, '{text}')]"),
                (By.XPATH, f"//*[@content-desc='{text}']"),
                (By.XPATH, f"//*[contains(@content-desc, '{text}')]"),
                (By.XPATH, f"//android.widget.TextView[@text='{text}']"),
                (By.XPATH, f"//android.widget.Button[@text='{text}']")
            ]
            
            for strategy, value in strategies:
                try:
                    element = client.wait_for_element(strategy, value, timeout=5)
                    if element:
                        element.click()
                        return {
                            "success": True,
                            "message": f"Successfully clicked element with text: '{text}'"
                        }
                    else:
                        continue
                except:
                    continue

            return {
                "success": False,
                "message": f"Could not find element with text: '{text}'"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error clicking element by text: {str(e)}"
            }
            
    @staticmethod
    def click_element_by_id(element_id: str) -> Dict[str, Any]:
        """Click an element by its resource ID."""
        try:
            client = AndroidTools._get_shared_client()

            # Try different ID strategies - prefer exact ID match first, then fall back to XPath
            strategies = [
                # Primary ID strategies (fastest and most reliable)
                (By.ID, element_id),
                (By.ID, f"*:id/{element_id}"),
                # Fall back to XPath if ID locator fails
                (By.XPATH, f"//*[@resource-id='{element_id}']"),
                (By.XPATH, f"//*[contains(@resource-id, '{element_id}')]")
            ]

            for strategy, value in strategies:
                try:
                    element = client.wait_for_element(strategy, value, timeout=5)
                    if element:
                        element.click()
                        return {
                            "success": True,
                            "message": f"Successfully clicked element with ID: '{element_id}'"
                        }
                except:
                    continue

            return {
                "success": False,
                "message": f"Could not find element with ID: '{element_id}'"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error clicking element by ID: {str(e)}"
            }