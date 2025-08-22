import os
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from appium import webdriver
from appium.webdriver.webdriver import WebDriver
from appium.options.android import UiAutomator2Options

logger = logging.getLogger(__name__)


class AppiumClient:
    """Appium client for Android device automation and testing."""

    def __init__(self,
                 appium_server_url: str = None,
                 device_name: str = None,
                 platform_version: str = None,
                 app_package: str = None,
                 app_activity: str = None,
                 automation_name: str = "UiAutomator2"):
        """
        Initialize Appium client for Android automation.

        Args:
            appium_server_url: Appium server URL (default: http://localhost:4723/wd/hub)
            device_name: Android device name/ID
            platform_version: Android platform version
            app_package: Target app package name
            app_activity: Target app activity
            automation_name: Automation framework to use
        """

        # Load from environment variables if not provided
        # Ensure URL ends with /wd/hub for proper WebDriver protocol
        default_url = "http://localhost:4723/wd/hub"
        self.appium_server_url = appium_server_url or os.getenv("APPIUM_SERVER_URL", default_url)

        # Ensure URL is properly formatted
        if self.appium_server_url.endswith('/'):
            self.appium_server_url = self.appium_server_url.rstrip('/')
        if not self.appium_server_url.endswith('/wd/hub'):
            self.appium_server_url += '/wd/hub'
        self.device_name = device_name or os.getenv("ANDROID_DEVICE_NAME", "emulator-5554")
        self.platform_version = platform_version or os.getenv("ANDROID_PLATFORM_VERSION", "11.0")
        self.app_package = app_package or os.getenv("ANDROID_APP_PACKAGE")
        self.app_activity = app_activity or os.getenv("ANDROID_APP_ACTIVITY")
        self.automation_name = automation_name

        self.driver: Optional[WebDriver] = None
        self.wait_timeout = int(os.getenv("APPIUM_WAIT_TIMEOUT", "10"))

        # Validate required parameters - app_package and app_activity are now optional
        # If not provided, we'll connect to device without launching a specific app
        if not self.device_name:
            from tron_ai.models.agent import MissingEnvironmentVariable
            raise MissingEnvironmentVariable("ANDROID_DEVICE_NAME")
        if not self.platform_version:
            from tron_ai.models.agent import MissingEnvironmentVariable
            raise MissingEnvironmentVariable("ANDROID_PLATFORM_VERSION")

    def _create_driver_options(self) -> UiAutomator2Options:
        """Create Appium driver options."""
        options = UiAutomator2Options()
        options.platform_name = "Android"
        options.platform_version = self.platform_version
        options.device_name = self.device_name
        options.automation_name = self.automation_name

        # Only set app package and activity if provided
        if self.app_package:
            options.app_package = self.app_package
        if self.app_activity:
            options.app_activity = self.app_activity

        # Configure based on whether we're targeting a specific app or not
        if self.app_package and self.app_activity:
            # Target specific app - don't reset state between sessions
            options.no_reset = True  # Don't reset app state between sessions
            options.full_reset = False  # Don't reinstall app
        else:
            # No specific app - connect to device as-is
            options.no_reset = True
            options.full_reset = False

        # Additional options for better stability
        options.set_capability("newCommandTimeout", 300)
        options.set_capability("deviceReadyTimeout", 30000)

        return options

    def connect(self) -> bool:
        """
        Establish connection to Appium server and Android device.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to Appium server at {self.appium_server_url}")
            logger.info(f"Target device: {self.device_name}, Platform: {self.platform_version}")

            if self.app_package and self.app_activity:
                logger.info(f"Target app: {self.app_package}/{self.app_activity}")
            else:
                logger.info("No specific app targeted - connecting to device as-is")

            options = self._create_driver_options()

            # Try connecting with the current URL first
            try:
                self.driver = webdriver.Remote(self.appium_server_url, options=options)
            except Exception as url_error:
                # If connection fails, try with base URL (without /wd/hub) as fallback
                logger.warning(f"Failed to connect with {self.appium_server_url}, trying base URL...")
                base_url = self.appium_server_url.replace('/wd/hub', '')
                self.driver = webdriver.Remote(base_url, options=options)

            # Wait for connection to establish
            if self.app_package and self.app_activity:
                # Wait for specific app to load
                time.sleep(2)
                logger.info("Successfully connected to Android device and launched target app")
            else:
                # Wait for device connection
                time.sleep(1)
                logger.info("Successfully connected to Android device (no specific app launched)")

            return True

        except Exception as e:
            logger.error(f"Failed to connect to Appium: {str(e)}")
            self.driver = None
            return False

    def disconnect(self):
        """Close the Appium driver connection."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Disconnected from Appium")
            except Exception as e:
                logger.error(f"Error disconnecting from Appium: {str(e)}")
            finally:
                self.driver = None

    def wait_for_element(self, locator_strategy: str, locator_value: str, timeout: int = None) -> Optional[Any]:
        """
        Wait for an element to be present and return it.

        Args:
            locator_strategy: Locator strategy (ID preferred for speed, XPATH for flexibility)
                - 'id': Fastest and most reliable, e.g., "search_bar", "com.example:id/button"
                - 'xpath': Most flexible fallback, e.g., "//*[@text='Search']", "//android.widget.Button[@resource-id='submit']"
                - 'class_name': For Android widget classes, e.g., "android.widget.EditText"
                - 'accessibility_id': For content descriptions
            locator_value: The locator value
            timeout: Wait timeout in seconds

        Returns:
            WebElement if found, None otherwise
        """
        if not self.driver:
            raise RuntimeError("Appium driver not connected")

        timeout = timeout or self.wait_timeout
        wait = WebDriverWait(self.driver, timeout)

        try:
            by_strategy = getattr(By, locator_strategy.upper())
            element = wait.until(EC.presence_of_element_located((by_strategy, locator_value)))
            return element
        except (TimeoutException, NoSuchElementException) as e:
            logger.warning(f"Element not found: {locator_strategy}={locator_value}, Error: {str(e)}")
            return None

    def find_element_safe(self, locator_strategy: str, locator_value: str) -> Optional[Any]:
        """
        Safely find an element without waiting.

        Args:
            locator_strategy: Locator strategy (ID preferred, XPATH as fallback)
                - 'id': Fastest and most reliable, e.g., "search_bar"
                - 'xpath': Flexible fallback, e.g., "//*[@text='Search']"
                - 'class_name': For Android widget classes
                - 'accessibility_id': For content descriptions
            locator_value: The locator value

        Returns:
            WebElement if found, None otherwise
        """
        if not self.driver:
            raise RuntimeError("Appium driver not connected")

        try:
            by_strategy = getattr(By, locator_strategy.upper())
            return self.driver.find_element(by_strategy, locator_value)
        except NoSuchElementException:
            return None

    def get_device_info(self) -> Dict[str, Any]:
        """
        Get information about the connected Android device.

        Returns:
            Dictionary containing device information
        """
        if not self.driver:
            raise RuntimeError("Appium driver not connected")

        try:
            capabilities = self.driver.capabilities
            return {
                "platform_name": capabilities.get("platformName"),
                "platform_version": capabilities.get("platformVersion"),
                "device_name": capabilities.get("deviceName"),
                "device_udid": capabilities.get("deviceUDID"),
                "app_package": capabilities.get("appPackage"),
                "app_activity": capabilities.get("appActivity"),
                "device_screen_size": capabilities.get("deviceScreenSize"),
                "device_screen_density": capabilities.get("deviceScreenDensity")
            }
        except Exception as e:
            logger.error(f"Error getting device info: {str(e)}")
            return {}

    def is_connected(self) -> bool:
        """Check if the Appium driver is connected and functional."""
        return self.driver is not None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


def get_appium_client() -> AppiumClient:
    """
    Get a configured Appium client instance.

    Returns:
        AppiumClient instance
    """
    return AppiumClient()