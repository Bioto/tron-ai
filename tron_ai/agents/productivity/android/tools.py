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
                # Element not found - automatically refresh page source for current state analysis
                try:
                    page_source_result = AndroidTools.get_page_source()
                    current_activity = AndroidTools._get_current_activity()
                    
                    # Analyze page source for intermediate actions and current state
                    page_source = page_source_result.get("page_source", "") if page_source_result.get("success") else ""
                    intermediate_analysis = AndroidTools.analyze_page_source_for_intermediate_actions(page_source)
                    
                    return {
                        "success": False,
                        "message": f"Element not found within {timeout} seconds: {locator_strategy}={locator_value}",
                        "page_source_refreshed": True,
                        "current_activity": current_activity.get("activity", "unknown"),
                        "intermediate_actions": intermediate_analysis.get("intermediate_actions", []),
                        "warnings": intermediate_analysis.get("warnings", []),
                        "recommendations": intermediate_analysis.get("recommendations", []),
                        "analysis_summary": f"Page source refreshed after element search failure. Found {len(intermediate_analysis.get('intermediate_actions', []))} intermediate actions that may need attention."
                    }
                except Exception as refresh_error:
                    return {
                        "success": False,
                        "message": f"Element not found within {timeout} seconds: {locator_strategy}={locator_value}",
                        "page_source_refreshed": False,
                        "refresh_error": f"Failed to refresh page source: {str(refresh_error)}"
                    }

        except Exception as e:
            # Exception occurred - also try to refresh page source for context
            try:
                page_source_result = AndroidTools.get_page_source()
                current_activity = AndroidTools._get_current_activity()
                
                return {
                    "success": False,
                    "message": f"Error waiting for element: {str(e)}",
                    "page_source_refreshed": True,
                    "current_activity": current_activity.get("activity", "unknown"),
                    "page_source_available": page_source_result.get("success", False),
                    "analysis_summary": "Page source refreshed after element search exception for context analysis"
                }
            except Exception as refresh_error:
                return {
                    "success": False,
                    "message": f"Error waiting for element: {str(e)}",
                    "page_source_refreshed": False,
                    "refresh_error": f"Failed to refresh page source: {str(refresh_error)}"
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
    def analyze_page_source_for_intermediate_actions(page_source: str) -> Dict[str, Any]:
        """
        Analyze page source to identify intermediate actions that might be needed.
        This helps detect dialogs, popups, permission requests, or other UI states
        that require user interaction before proceeding.
        """
        try:
            intermediate_actions = []
            warnings = []
            recommendations = []
            
            # Check for common intermediate UI states that need attention
            
            # 1. Permission dialogs
            if "permission" in page_source.lower():
                if "allow" in page_source.lower() or "deny" in page_source.lower():
                    intermediate_actions.append({
                        "type": "permission_dialog",
                        "description": "Permission request dialog detected",
                        "action_needed": "Click 'Allow' or 'Deny' button",
                        "priority": "high"
                    })
            
            # 2. Error dialogs or messages
            if "error" in page_source.lower() or "failed" in page_source.lower():
                intermediate_actions.append({
                    "type": "error_dialog",
                    "description": "Error message or dialog detected",
                    "action_needed": "Review error and take appropriate action",
                    "priority": "high"
                })
            
            # 3. Confirmation dialogs
            if "confirm" in page_source.lower() or "ok" in page_source.lower():
                if "cancel" in page_source.lower():
                    intermediate_actions.append({
                        "type": "confirmation_dialog",
                        "description": "Confirmation dialog detected",
                        "action_needed": "Click 'OK' or 'Confirm' button",
                        "priority": "medium"
                    })
            
            # 4. Loading states
            if "loading" in page_source.lower() or "progress" in page_source.lower():
                intermediate_actions.append({
                    "type": "loading_state",
                    "description": "Loading or progress indicator detected",
                    "action_needed": "Wait for loading to complete",
                    "priority": "medium"
                })
            
            # 5. Keyboard presence
            if "keyboard" in page_source.lower() or "input" in page_source.lower():
                if "done" in page_source.lower() or "next" in page_source.lower():
                    intermediate_actions.append({
                        "type": "keyboard_action",
                        "description": "Keyboard action buttons detected",
                        "action_needed": "Click 'Done', 'Next', or similar button",
                        "priority": "medium"
                    })
            
            # 6. Dropdown lists and suggestions (CRITICAL for search results)
            if any(indicator in page_source.lower() for indicator in ["dropdown", "suggestion", "autocomplete", "list_item", "search_result"]):
                intermediate_actions.append({
                    "type": "dropdown_suggestions",
                    "description": "Dropdown list or search suggestions detected",
                    "action_needed": "Review available options and select appropriate item",
                    "priority": "high",
                    "note": "This may contain search results, autocomplete suggestions, or navigation options"
                })
            
            # 7. Search results and video suggestions (YouTube specific)
            if "video" in page_source.lower() and ("suggestion" in page_source.lower() or "result" in page_source.lower()):
                intermediate_actions.append({
                    "type": "search_results",
                    "description": "Search results or video suggestions detected",
                    "action_needed": "Review available video options and select desired result",
                    "priority": "high",
                    "note": "Multiple video options available - user must choose which to navigate to"
                })
            
            # 8. Autocomplete and search suggestions
            if any(indicator in page_source.lower() for indicator in ["autocomplete", "suggestion", "search_suggestion"]):
                intermediate_actions.append({
                    "type": "search_suggestions",
                    "description": "Search suggestions or autocomplete options detected",
                    "action_needed": "Review available suggestions and select appropriate option",
                    "priority": "medium",
                    "note": "Multiple search suggestions available - user must choose which to select"
                })
            
            # 9. Navigation elements that might need attention
            if "back" in page_source.lower() and "button" in page_source.lower():
                if "enabled='false'" in page_source.lower():
                    warnings.append("Back button is disabled - may indicate navigation issue")
            
            # 10. Check for unexpected activity changes
            if "activity" in page_source.lower() and "android.intent" in page_source.lower():
                warnings.append("Intent-based activity detected - may need special handling")
            
            # Generate recommendations based on findings
            if intermediate_actions:
                recommendations.append("Review and handle intermediate actions before proceeding")
                recommendations.append("Consider waiting for UI to stabilize if loading states detected")
                
                # Add specific recommendations for dropdowns and suggestions
                dropdown_actions = [action for action in intermediate_actions if action.get("type") in ["dropdown_suggestions", "search_results", "search_suggestions"]]
                if dropdown_actions:
                    recommendations.append("⚠️ CRITICAL: Dropdown/suggestions detected - page source should be refreshed to capture full list")
                    recommendations.append("Multiple options available - user must specify which item to select")
                    recommendations.append("Consider calling refresh_and_analyze_page_source() to get complete dropdown content")
            
            if warnings:
                recommendations.append("Pay attention to warnings - may indicate UI state issues")
            
            return {
                "success": True,
                "intermediate_actions": intermediate_actions,
                "warnings": warnings,
                "recommendations": recommendations,
                "analysis_summary": f"Found {len(intermediate_actions)} intermediate actions, {len(warnings)} warnings",
                "requires_attention": len(intermediate_actions) > 0 or len(warnings) > 0
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error analyzing page source for intermediate actions: {str(e)}",
                "intermediate_actions": [],
                "warnings": [],
                "recommendations": []
            }

    @staticmethod
    def analyze_current_page_source_for_intermediate_actions() -> Dict[str, Any]:
        """
        Analyze the current page source to identify intermediate actions needed.
        This is a standalone method that can be called independently to check
        the current UI state for any required intermediate actions.
        """
        try:
            # Get current page source
            page_source_result = AndroidTools.get_page_source()
            if not page_source_result.get("success"):
                return {
                    "success": False,
                    "message": "Failed to get page source for analysis"
                }
            
            page_source = page_source_result.get("page_source", "")
            
            # Analyze for intermediate actions
            analysis_result = AndroidTools.analyze_page_source_for_intermediate_actions(page_source)
            
            # Add current context information
            try:
                current_activity = AndroidTools._get_current_activity()
                analysis_result["current_context"] = {
                    "activity": current_activity.get("activity", "unknown"),
                    "timestamp": datetime.now().isoformat()
                }
            except:
                analysis_result["current_context"] = {
                    "activity": "unknown",
                    "timestamp": datetime.now().isoformat()
                }
            
            return analysis_result
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error analyzing current page source: {str(e)}",
                "intermediate_actions": [],
                "warnings": [],
                "recommendations": []
            }

    @staticmethod
    def _execute_with_screen_analysis(action_func, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute an action and automatically perform comprehensive screen analysis afterward.
        This ensures the agent always has current screen state information and identifies
        any intermediate actions needed before proceeding.
        """
        try:
            # Execute the original action
            result = action_func(*args, **kwargs)
            
            # If the action was successful, perform comprehensive screen analysis
            if result.get("success", False):
                try:
                    # Get current screen information
                    screen_analysis = AndroidTools.analyze_current_screen()
                    current_activity = AndroidTools._get_current_activity()
                    
                    # Get page source for intelligent analysis
                    page_source_result = AndroidTools.get_page_source()
                    page_source = page_source_result.get("page_source", "") if page_source_result.get("success") else ""
                    
                    # Analyze page source for intermediate actions
                    intermediate_analysis = AndroidTools.analyze_page_source_for_intermediate_actions(page_source)
                    
                    # Add comprehensive screen analysis to the result
                    result["screen_analysis"] = {
                        "timestamp": datetime.now().isoformat(),
                        "screen_state": screen_analysis,
                        "current_activity": current_activity,
                        "page_source_analysis": intermediate_analysis,
                        "message": "Comprehensive screen analysis completed after action execution"
                    }
                    
                    # Add high-priority alerts if immediate attention is needed
                    if intermediate_analysis.get("requires_attention", False):
                        high_priority_actions = [action for action in intermediate_analysis.get("intermediate_actions", []) 
                                               if action.get("priority") == "high"]
                        if high_priority_actions:
                            result["requires_immediate_attention"] = True
                            result["immediate_actions"] = high_priority_actions
                            result["alert_message"] = f"⚠️ IMMEDIATE ATTENTION REQUIRED: {len(high_priority_actions)} high-priority intermediate actions detected"
                    
                    # CRITICAL: If ANY intermediate actions are detected, automatically refresh page source
                    # to capture dynamic UI elements like dropdowns, suggestions, and other context
                    if intermediate_analysis.get("intermediate_actions"):
                        try:
                            # Force a fresh page source refresh to capture current state
                            fresh_page_source_result = AndroidTools.get_page_source()
                            if fresh_page_source_result.get("success"):
                                fresh_page_source = fresh_page_source_result.get("page_source", "")
                                
                                # Analyze the fresh page source for additional context
                                fresh_analysis = AndroidTools.analyze_page_source_for_intermediate_actions(fresh_page_source)
                                
                                # Add the fresh analysis to the result
                                result["fresh_page_source_analysis"] = {
                                    "timestamp": datetime.now().isoformat(),
                                    "message": "Page source automatically refreshed due to intermediate actions detected",
                                    "intermediate_actions": fresh_analysis.get("intermediate_actions", []),
                                    "warnings": fresh_analysis.get("warnings", []),
                                    "recommendations": fresh_analysis.get("recommendations", []),
                                    "requires_attention": fresh_analysis.get("requires_attention", False),
                                    "analysis_summary": f"Fresh analysis found {len(fresh_analysis.get('intermediate_actions', []))} intermediate actions"
                                }
                                
                                # Check if fresh analysis reveals additional context (like dropdowns)
                                if fresh_analysis.get("intermediate_actions"):
                                    result["dynamic_ui_detected"] = True
                                    result["ui_context_message"] = "Dynamic UI elements detected - page source refreshed to capture current state"
                                
                        except Exception as fresh_analysis_error:
                            result["fresh_page_source_analysis"] = {
                                "timestamp": datetime.now().isoformat(),
                                "error": f"Failed to refresh page source for intermediate actions: {str(fresh_analysis_error)}",
                                "message": "Could not capture fresh page source for dynamic UI analysis"
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
                    # Element not found - get current page source for analysis
                    try:
                        page_source_result = AndroidTools.get_page_source()
                        current_activity = AndroidTools._get_current_activity()
                        
                        # Analyze page source for intermediate actions and current state
                        page_source = page_source_result.get("page_source", "") if page_source_result.get("success") else ""
                        intermediate_analysis = AndroidTools.analyze_page_source_for_intermediate_actions(page_source)
                        
                        return {
                            "success": False,
                            "message": f"Element not found: {locator_strategy}={locator_value}",
                            "page_source_refreshed": True,
                            "current_activity": current_activity.get("activity", "unknown"),
                            "intermediate_actions": intermediate_analysis.get("intermediate_actions", []),
                            "warnings": intermediate_analysis.get("warnings", []),
                            "recommendations": intermediate_analysis.get("recommendations", []),
                            "analysis_summary": f"Page source refreshed after element search failure. Found {len(intermediate_analysis.get('intermediate_actions', []))} intermediate actions that may need attention.",
                            "suggested_actions": [
                                "Check if the app has navigated to a different screen",
                                "Look for permission dialogs or error messages",
                                "Verify if the input field is visible and accessible",
                                "Check for loading states that may need to complete",
                                "Consider if the keyboard needs to be dismissed first"
                            ]
                        }
                    except Exception as refresh_error:
                        return {
                            "success": False,
                            "message": f"Element not found: {locator_strategy}={locator_value}",
                            "page_source_refreshed": False,
                            "refresh_error": f"Failed to refresh page source: {str(refresh_error)}"
                        }

            except Exception as e:
                return {
                    "success": False,
                    "message": f"Error typing text: {str(e)}"
                }
        
        return AndroidTools._execute_with_screen_analysis(_type_action)

    @staticmethod
    def _get_current_activity() -> Dict[str, Any]:
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
    def refresh_and_analyze_page_source() -> Dict[str, Any]:
        """
        Refresh the page source and perform comprehensive analysis.
        This is useful when the agent needs to understand the current state
        after element searches fail or when checking for intermediate actions.
        """
        try:
            # Get current page source
            page_source_result = AndroidTools.get_page_source()
            if not page_source_result.get("success"):
                return {
                    "success": False,
                    "message": "Failed to get page source"
                }
            
            page_source = page_source_result.get("page_source", "")
            
            # Get current activity
            current_activity = AndroidTools._get_current_activity()
            
            # Analyze page source for intermediate actions
            intermediate_analysis = AndroidTools.analyze_page_source_for_intermediate_actions(page_source)
            
            # Get system info for additional context
            system_info = AndroidTools.get_system_info()
            
            return {
                "success": True,
                "message": "Page source refreshed and analyzed successfully",
                "timestamp": datetime.now().isoformat(),
                "current_activity": current_activity.get("activity", "unknown"),
                "page_source": page_source,
                "intermediate_actions": intermediate_analysis.get("intermediate_actions", []),
                "warnings": intermediate_analysis.get("warnings", []),
                "recommendations": intermediate_analysis.get("recommendations", []),
                "system_info": system_info.get("system_info", {}),
                "analysis_summary": f"Found {len(intermediate_analysis.get('intermediate_actions', []))} intermediate actions, {len(intermediate_analysis.get('warnings', []))} warnings",
                "requires_attention": intermediate_analysis.get("requires_attention", False),
                "suggested_next_steps": [
                    "Review intermediate actions if any detected",
                    "Check current activity matches expected state",
                    "Look for any error messages or dialogs",
                    "Verify if the app is in the expected screen"
                ]
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error refreshing and analyzing page source: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            
    @staticmethod
    def analyze_dropdown_and_suggestions() -> Dict[str, Any]:
        """
        Specifically analyze the current page source for dropdown lists, search suggestions,
        and other dynamic UI elements that require user selection.
        This is critical for handling search results, autocomplete, and navigation options.
        """
        try:
            # Get fresh page source for dropdown analysis
            page_source_result = AndroidTools.get_page_source()
            if not page_source_result.get("success"):
                return {
                    "success": False,
                    "message": "Failed to get page source for dropdown analysis"
                }
            
            page_source = page_source_result.get("page_source", "")
            
            # Look for specific dropdown and suggestion patterns
            dropdown_indicators = []
            suggestion_indicators = []
            
            # Check for dropdown patterns
            if "dropdown" in page_source.lower():
                dropdown_indicators.append("dropdown")
            if "list_item" in page_source.lower():
                dropdown_indicators.append("list_item")
            if "spinner" in page_source.lower():
                dropdown_indicators.append("spinner")
            
            # Check for suggestion patterns
            if "suggestion" in page_source.lower():
                suggestion_indicators.append("suggestion")
            if "autocomplete" in page_source.lower():
                suggestion_indicators.append("autocomplete")
            if "search_result" in page_source.lower():
                suggestion_indicators.append("search_result")
            
            # Check for video-specific patterns (YouTube)
            video_suggestions = []
            if "video" in page_source.lower():
                # Look for video titles or descriptions
                lines = page_source.split('\n')
                for line in lines:
                    if "video" in line.lower() and len(line.strip()) > 10:
                        video_suggestions.append(line.strip())
            
            # Check for search result patterns
            search_results = []
            if any(indicator in page_source.lower() for indicator in ["result", "option", "choice"]):
                lines = page_source.split('\n')
                for line in lines:
                    if any(indicator in line.lower() for indicator in ["result", "option", "choice"]) and len(line.strip()) > 5:
                        search_results.append(line.strip())
            
            return {
                "success": True,
                "message": "Dropdown and suggestions analysis completed",
                "timestamp": datetime.now().isoformat(),
                "dropdown_detected": len(dropdown_indicators) > 0,
                "suggestions_detected": len(suggestion_indicators) > 0,
                "dropdown_indicators": dropdown_indicators,
                "suggestion_indicators": suggestion_indicators,
                "video_suggestions": video_suggestions[:10],  # Limit to first 10
                "search_results": search_results[:10],  # Limit to first 10
                "total_video_suggestions": len(video_suggestions),
                "total_search_results": len(search_results),
                "requires_user_selection": len(video_suggestions) > 0 or len(search_results) > 0,
                "recommendations": [
                    "Multiple options available - user must specify which to select",
                    "Consider the available suggestions before proceeding",
                    "If video suggestions found, user must choose specific video",
                    "If search results found, user must select desired option"
                ] if (len(video_suggestions) > 0 or len(search_results) > 0) else ["No dropdown or suggestions detected"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error analyzing dropdowns and suggestions: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    @staticmethod
    def click_element_by_text(text: str) -> Dict[str, Any]:
        """Click an element by its text content."""
        def _click_text_action():
            try:
                client = AndroidTools._get_shared_client()

                # Try different XPath-based text strategies
                strategies = [
                    (By.XPATH, f"//*[@text='{text}']"),
                    (By.XPATH, f"//*[contains(@text, '{text}')]"),
                    (By.XPATH, f"//*[@content-desc='{text}']"),
                    (By.XPATH, f"//*[contains(@content-desc, '{text}')]"),
                    (By.XPATH, f"//android.widget.TextView[@text='{text}']"),
                    (By.XPATH, f"//android.widget.Button[@text='{text}']"),
                    (By.XPATH, f"//android.widget.TextView[contains(@text, '{text}')]"),
                    (By.XPATH, f"//android.widget.Button[contains(@text, '{text}')]"),
                    (By.XPATH, f"//android.widget.EditText[@text='{text}']"),
                    (By.XPATH, f"//android.widget.EditText[contains(@text, '{text}')]")
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

                # Element not found - get current page source for analysis
                try:
                    page_source_result = AndroidTools.get_page_source()
                    current_activity = AndroidTools._get_current_activity()
                    
                    # Analyze page source for intermediate actions and current state
                    page_source = page_source_result.get("page_source", "") if page_source_result.get("success") else ""
                    intermediate_analysis = AndroidTools.analyze_page_source_for_intermediate_actions(page_source)
                    
                    return {
                        "success": False,
                        "message": f"Could not find element with text: '{text}'",
                        "page_source_refreshed": True,
                        "current_activity": current_activity.get("activity", "unknown"),
                        "intermediate_actions": intermediate_analysis.get("intermediate_actions", []),
                        "warnings": intermediate_analysis.get("warnings", []),
                        "recommendations": intermediate_analysis.get("recommendations", []),
                        "analysis_summary": f"Page source refreshed after element search failure. Found {len(intermediate_analysis.get('intermediate_actions', []))} intermediate actions that may need attention.",
                        "suggested_actions": [
                            "Check if the app has navigated to a different screen",
                            "Look for permission dialogs or error messages",
                            "Verify if the element text has changed",
                            "Check for loading states that may need to complete"
                        ]
                    }
                except Exception as refresh_error:
                    return {
                        "success": False,
                        "message": f"Could not find element with text: '{text}'",
                        "page_source_refreshed": False,
                        "refresh_error": f"Failed to refresh page source: {str(refresh_error)}"
                    }

            except Exception as e:
                return {
                    "success": False,
                    "message": f"Error clicking element by text: {str(e)}"
                }
        
        return AndroidTools._execute_with_screen_analysis(_click_text_action)
    
    @staticmethod
    def click_element_by_id(element_id: str) -> Dict[str, Any]:
        """Click an element by its resource ID."""
        def _click_id_action():
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

                # Element not found - get current page source for analysis
                try:
                    page_source_result = AndroidTools.get_page_source()
                    current_activity = AndroidTools._get_current_activity()
                    
                    # Analyze page source for intermediate actions and current state
                    page_source = page_source_result.get("page_source", "") if page_source_result.get("success") else ""
                    intermediate_analysis = AndroidTools.analyze_page_source_for_intermediate_actions(page_source)
                    
                    return {
                        "success": False,
                        "message": f"Could not find element with ID: '{element_id}'",
                        "page_source_refreshed": True,
                        "current_activity": current_activity.get("activity", "unknown"),
                        "intermediate_actions": intermediate_analysis.get("intermediate_actions", []),
                        "warnings": intermediate_analysis.get("warnings", []),
                        "recommendations": intermediate_analysis.get("recommendations", []),
                        "analysis_summary": f"Page source refreshed after element search failure. Found {len(intermediate_analysis.get('intermediate_actions', []))} intermediate actions that may need attention.",
                        "suggested_actions": [
                            "Check if the app has navigated to a different screen",
                            "Look for permission dialogs or error messages",
                            "Verify if the element ID has changed or is no longer available",
                            "Check for loading states that may need to complete",
                            "Consider if the app version or UI structure has changed"
                        ]
                    }
                except Exception as refresh_error:
                    return {
                        "success": False,
                        "message": f"Could not find element with ID: '{element_id}'",
                        "page_source_refreshed": False,
                        "refresh_error": f"Failed to refresh page source: {str(refresh_error)}"
                    }

            except Exception as e:
                return {
                    "success": False,
                    "message": f"Error clicking element by ID: {str(e)}"
                }
        
        return AndroidTools._execute_with_screen_analysis(_click_id_action)

    @staticmethod
    def wait_for_loading_completion(timeout: int = 30, check_interval: float = 0.5) -> Dict[str, Any]:
        """
        Wait for loading states to complete by monitoring the page source.
        This is useful for handling intermediate actions that involve loading states.
        """
        try:
            client = AndroidTools._get_shared_client()
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                # Get current page source
                page_source = client.driver.page_source
                
                # Check if loading indicators are still present
                loading_indicators = [
                    "loading", "progress", "spinner", "wait", "please wait",
                    "processing", "saving", "uploading", "downloading"
                ]
                
                loading_detected = False
                for indicator in loading_indicators:
                    if indicator in page_source.lower():
                        loading_detected = True
                        break
                
                if not loading_detected:
                    # No loading indicators found, loading is complete
                    return {
                        "success": True,
                        "message": "Loading completed successfully",
                        "wait_time": round(time.time() - start_time, 2),
                        "final_page_source": page_source
                    }
                
                # Wait before next check
                time.sleep(check_interval)
            
            # Timeout reached
            return {
                "success": False,
                "message": f"Loading timeout reached after {timeout} seconds",
                "wait_time": timeout,
                "final_page_source": client.driver.page_source
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error waiting for loading completion: {str(e)}"
            }