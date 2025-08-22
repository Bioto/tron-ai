# Android Agent

The Android Agent is a sophisticated AI assistant specialized in Android mobile automation and testing through Appium. It provides comprehensive device control, UI interaction, screenshot capture, and app state monitoring capabilities.

## Features

- **Device Management**: Connect/disconnect from Android devices via Appium
- **UI Automation**: Tap, swipe, type, and interact with mobile app elements
- **Screenshot Capture**: Take full-screen screenshots with customizable filenames
- **Text Extraction**: Extract visible text content from app screens
- **Element Analysis**: Get detailed information about UI elements
- **Activity Navigation**: Switch between different app activities
- **Hardware Control**: Simulate key presses and system navigation
- **Dynamic App Connection**: Connect to any running app without pre-configuration
- **System Information**: Get device and system-level information
- **Flexible Configuration**: Work with or without specifying target app package
- **Natural Language Commands**: Execute conversational commands like "click search and type hello"
- **Multi-Step Workflows**: Execute complex sequences of UI interactions
- **Intelligent Element Finding**: Find UI elements by text content and fuzzy matching

## Environment Variables

The Android Agent supports flexible configuration with both required and optional environment variables.

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `APPIUM_SERVER_URL` | URL of the Appium server | `http://localhost:4723/wd/hub` |
| `ANDROID_DEVICE_NAME` | Name or ID of the Android device | `emulator-5554` or `R58N123ABCD` |
| `ANDROID_PLATFORM_VERSION` | Android OS version | `11.0` |

### Optional Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `ANDROID_APP_PACKAGE` | Target app package name | None | `com.example.myapp` |
| `ANDROID_APP_ACTIVITY` | Target app main activity | None | `com.example.myapp.MainActivity` |
| `APPIUM_WAIT_TIMEOUT` | Wait timeout for element detection (seconds) | `10` | `15` |
| `APPIUM_LOG_LEVEL` | Appium server log level | `info` | `debug` |

## Usage Modes

### Mode 1: Target Specific App (Traditional)
Set `ANDROID_APP_PACKAGE` and `ANDROID_APP_ACTIVITY` to automatically launch and interact with a specific app.

```bash
export ANDROID_APP_PACKAGE="com.android.settings"
export ANDROID_APP_ACTIVITY="com.android.settings.Settings"
```

### Mode 2: Device-Only Connection (New)
**No app package required!** Connect to the device and interact with whatever app is currently running.

```bash
# Only set the required variables
export APPIUM_SERVER_URL="http://localhost:4723/wd/hub"
export ANDROID_DEVICE_NAME="emulator-5554"
export ANDROID_PLATFORM_VERSION="11.0"
```

This mode is perfect for:
- Testing any app that's already running
- System-level interactions
- Connecting to games or apps without known package names
- Exploring the device UI

## Setup Instructions

### 1. Install Appium Server

```bash
npm install -g appium
npm install -g appium-uiautomator2-driver
```

### 2. Start Appium Server

```bash
appium --address 127.0.0.1 --port 4723
```

### 3. Set Environment Variables

Create a `.env` file or set environment variables:

```bash
export APPIUM_SERVER_URL="http://localhost:4723/wd/hub"
export ANDROID_DEVICE_NAME="emulator-5554"
export ANDROID_PLATFORM_VERSION="11.0"
export ANDROID_APP_PACKAGE="com.android.settings"
export ANDROID_APP_ACTIVITY="com.android.settings.Settings"
```

### 4. Connect Android Device

### 5. Set Environment Variables

```bash
export APPIUM_SERVER_URL="http://localhost:4723/wd/hub"
export ANDROID_DEVICE_NAME="emulator-5554"
export ANDROID_PLATFORM_VERSION="11.0"
# Optional - only set if targeting specific app
# export ANDROID_APP_PACKAGE="com.android.settings"
# export ANDROID_APP_ACTIVITY="com.android.settings.Settings"
```

#### Using Android Emulator:
1. Start Android Studio
2. Open AVD Manager
3. Create or start an Android Virtual Device
4. Note the device name (e.g., `emulator-5554`)

#### Using Physical Device:
1. Enable Developer Options on your Android device
2. Enable USB Debugging
3. Connect device via USB
4. Run `adb devices` to get device ID

## Usage Examples

### Basic Device Connection
```python
# Connect to Android device
AndroidTools.connect_device()

# Get device information
AndroidTools.get_device_info()

# Take a screenshot
AndroidTools.take_screenshot(filename="home_screen.png")

# Disconnect
AndroidTools.disconnect_device()
```

### UI Interaction
```python
# Tap on an element by ID
AndroidTools.tap_element(locator_strategy="id", locator_value="com.example:id/login_button")

# Type text into an input field
AndroidTools.type_text(locator_strategy="id", locator_value="com.example:id/username", text="testuser")

# Wait for an element to appear
AndroidTools.wait_for_element(locator_strategy="xpath", locator_value="//android.widget.TextView[@text='Welcome']")
```

### Screen Navigation
```python
# Swipe up on the screen
AndroidTools.swipe_screen(direction="up")

# Navigate to a specific activity
AndroidTools.navigate_to_activity(app_package="com.android.settings", app_activity="com.android.settings.WifiSettings")

# Get current activity information
AndroidTools.get_current_activity()
```

### Data Extraction
```python
# Extract all visible text
AndroidTools.get_screen_text()

# Get information about interactive elements
AndroidTools.get_app_elements()

# Take a screenshot for documentation
AndroidTools.take_screenshot(filename="app_state.png", save_path="/tmp/screenshots")
```

### Device-Only Mode (No App Package)
```python
# Connect to device without targeting a specific app
AndroidTools.connect_device()

# Get info about currently running app
AndroidTools.get_running_apps()

# Connect to a running app dynamically
AndroidTools.connect_to_running_app(app_package="com.android.chrome")

# Get system information
AndroidTools.get_system_info()

# Launch any app on-demand
AndroidTools.launch_app_manually(app_package="com.android.camera", app_activity="com.android.camera.Camera")
```

### Natural Language Commands
```python
# Execute conversational commands
AndroidTools.execute_natural_command("click on search and type 'hello world'")
AndroidTools.execute_natural_command("take a screenshot")
AndroidTools.execute_natural_command("swipe down and tap menu")

# Find and interact with elements by text
AndroidTools.find_element_by_text("Login")
AndroidTools.click_element_by_text("Search")
```

### Multi-Step Workflows
```python
# Execute complex workflows
workflow_steps = [
    {"action": "click", "text": "Search"},
    {"action": "type", "text": "hello world", "target": "search bar"},
    {"action": "wait", "seconds": 2},
    {"action": "screenshot", "filename": "search_results.png"},
    {"action": "swipe", "direction": "up"}
]

AndroidTools.execute_workflow(workflow_steps)
```

## Conversational Usage Examples

### Interactive Commands
The Android agent now understands natural language commands for common mobile interactions:

**Search Operations:**
- "Click on search and type 'Python programming'" → Finds search element and types text
- "Tap the search bar and enter 'restaurants near me'" → Clicks search field and enters query
- "Search for 'weather forecast'" → Automatically finds and uses search functionality

**Navigation Commands:**
- "Swipe up" or "Scroll down" → Performs screen swipes
- "Go back" or "Press back button" → Simulates hardware back button
- "Take a screenshot" → Captures current screen

**App Interaction:**
- "Click menu button" → Finds and clicks menu elements
- "Tap settings" → Locates and clicks settings options
- "Open notifications" → Interacts with notification elements

### Multi-Step Automation
The agent can execute complex workflows that combine multiple actions:

**Example: Social Media Post**
```python
workflow = [
    {"action": "click", "text": "New Post"},
    {"action": "type", "text": "Hello from AI!", "target": "text field"},
    {"action": "click", "text": "Post"},
    {"action": "wait", "seconds": 2},
    {"action": "screenshot", "filename": "post_confirmation.png"}
]
AndroidTools.execute_workflow(workflow)
```

**Example: Shopping Search**
```python
shopping_workflow = [
    {"action": "click", "text": "Search"},
    {"action": "type", "text": "wireless headphones", "target": "search"},
    {"action": "click", "text": "Search"},
    {"action": "wait", "seconds": 3},
    {"action": "screenshot", "filename": "search_results.png"},
    {"action": "swipe", "direction": "up"}
]
AndroidTools.execute_workflow(shopping_workflow)
```

### Smart Element Detection
The agent uses intelligent strategies to find UI elements:

1. **Text-Based Finding**: Searches for elements by their displayed text
2. **Content Description**: Uses accessibility labels and hints
3. **Resource IDs**: Matches Android resource identifiers
4. **Class Names**: Falls back to element types (Button, EditText, etc.)
5. **XPath Matching**: Uses flexible XML path expressions

### UI Analysis Tools
```python
# Get comprehensive screen analysis
AndroidTools.analyze_current_screen()

# Understand how element detection works
AndroidTools.explain_element_detection()

# Get detailed element information
AndroidTools.get_app_elements(max_elements=50)
```

## How UI Elements Are Discovered

### The UI Discovery Process

The Android agent uses a multi-layered approach to discover and interact with UI elements:

#### 1. **XML Page Source Analysis**
- Appium provides the complete UI hierarchy as XML
- Every screen is represented as a structured XML document
- Elements are organized in a tree hierarchy with parent-child relationships

```xml
<hierarchy>
  <android.widget.LinearLayout>
    <android.widget.Button text="Login" resource-id="com.example:id/login_btn"/>
    <android.widget.EditText hint="Enter username"/>
  </android.widget.LinearLayout>
</hierarchy>
```

#### 2. **Element Attribute Extraction**
Each UI element has multiple attributes that can be used for identification:

- **text**: The visible text content
- **resource-id**: Android's unique resource identifier
- **class**: The widget class (Button, EditText, TextView, etc.)
- **content-desc**: Accessibility description
- **bounds**: Screen coordinates [left,top,right,bottom]
- **clickable/enabled/focused**: Interaction states

#### 3. **Intelligent Matching Strategy**

When you say "click on search", the agent tries multiple approaches:

**First Pass - Text Matching:**
```xpath
//*[@text='search']                    // Exact match
//*[contains(@text, 'search')]         // Partial match
//*[@content-desc='search']           // Accessibility label
```

**Second Pass - ID Patterns:**
```xpath
//*[@resource-id='*search*']          // IDs containing 'search'
//*[@resource-id='*btn*']             // Common button patterns
```

**Third Pass - Class Fallback:**
```xpath
//android.widget.Button               // All buttons
//android.widget.EditText             // Input fields
//android.widget.TextView             // Text elements
```

#### 4. **Fallback Chain Strategy**
The agent uses a sophisticated fallback system:

1. **Exact Text Match** → `//*[@text='Login']`
2. **Partial Text Match** → `//*[contains(@text, 'Login')]`
3. **Content Description** → `//*[@content-desc='Login']`
4. **Resource ID Pattern** → `//*[@resource-id='*login*']`
5. **Class Name Match** → `//android.widget.Button`
6. **Accessibility ID** → `//*[@accessibility-id='login']`

#### 5. **Real-time Element Analysis**
```python
# Get live analysis of current screen
screen_info = AndroidTools.analyze_current_screen()
print(f"Current app: {screen_info['screen_analysis']['current_package']}")
print(f"UI elements found: {screen_info['screen_analysis']['total_elements']}")

# See the actual XML structure
print(screen_info['raw_page_source'])
```

### Element Interaction Process

When executing an action like "click search":

1. **Parse Command**: Extract action type and target
2. **Element Discovery**: Try multiple locator strategies
3. **Validation**: Check if element is clickable/enabled
4. **Action Execution**: Perform the requested interaction
5. **Result Verification**: Confirm action was successful

## Locator Strategies

The Android Agent supports multiple locator strategies for finding UI elements:

| Strategy | Description | Example |
|----------|-------------|---------|
| `id` | Find by Android resource ID | `com.example:id/button` |
| `xpath` | Find by XPath expression | `//android.widget.Button[@text='Login']` |
| `class_name` | Find by Android class name | `android.widget.EditText` |
| `accessibility_id` | Find by accessibility ID | `login_button` |

## Hardware Key Codes

The agent can simulate hardware key presses using these key names:

| Key Name | Description |
|----------|-------------|
| `home` | Home button |
| `back` | Back button |
| `menu` | Menu button |
| `search` | Search button |
| `enter` | Enter key |
| `volume_up` | Volume up |
| `volume_down` | Volume down |
| `power` | Power button |

```python
# Press the back button
AndroidTools.press_key(key_code="back")

# Press the home button
AndroidTools.press_key(key_code="home")
```

## Error Handling

The Android Agent includes comprehensive error handling:

- **Connection Errors**: Automatic retry logic for device connections
- **Element Not Found**: Timeout handling with detailed error messages
- **App Crashes**: Detection and recovery from app crashes
- **Network Issues**: Connection timeout and recovery mechanisms

## Best Practices

1. **Always Connect First**: Establish device connection before performing actions
2. **Use Appropriate Timeouts**: Adjust wait timeouts based on app performance
3. **Handle Element Loading**: Use wait_for_element for dynamic content
4. **Take Screenshots**: Capture visual evidence of app states
5. **Clean Up Connections**: Always disconnect when finished
6. **Use Specific Locators**: Prefer IDs over XPath when possible for better performance

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Ensure Appium server is running
   - Check device connectivity with `adb devices`
   - Verify environment variables are set correctly

2. **Element Not Found**
   - Wait for elements to load using `wait_for_element`
   - Check locator strategy and value
   - Take screenshot to verify current screen state

3. **App Not Responding**
   - Increase timeout values
   - Check if app is in foreground
   - Verify app package and activity names

### Debug Commands

```bash
# Check connected devices
adb devices

# Check Appium server status
curl http://localhost:4723/wd/hub/status

# Get device logs
adb logcat

# Take device screenshot manually
adb shell screencap /sdcard/screen.png
adb pull /sdcard/screen.png
```

## Troubleshooting

### Common Issues

#### 1. Connection Failed: "UnknownCommandError"
**Symptoms:**
```
ERROR Failed to connect to Appium: Message: The requested resource could not be found
```

**Solutions:**
1. **Check Appium Server:**
   ```bash
   # Kill existing server
   pkill -f appium

   # Start with proper configuration
   appium --address 127.0.0.1 --port 4723 --base-path /wd/hub --log-level info
   ```

2. **Verify UiAutomator2 Driver:**
   ```bash
   appium driver list
   appium driver install uiautomator2
   ```

3. **Check Environment Variables:**
   ```bash
   echo $APPIUM_SERVER_URL
   echo $ANDROID_DEVICE_NAME
   echo $ANDROID_PLATFORM_VERSION
   ```

#### 2. Device Connection Issues
**Check Device Status:**
```bash
# List connected devices
adb devices

# Check device properties
adb shell getprop ro.build.version.release

# Restart ADB server
adb kill-server && adb start-server
```

**Emulator Issues:**
```bash
# List running emulators
adb devices | grep emulator

# Start emulator with specific port
emulator -avd <emulator_name> -port 5554
```

#### 3. Element Not Found Errors
**Common Causes:**
- App UI not fully loaded
- Element locator incorrect
- App in different state than expected

**Solutions:**
1. **Increase wait timeout:**
   ```bash
   export APPIUM_WAIT_TIMEOUT="20"
   ```

2. **Take screenshot to debug:**
   ```python
   AndroidTools.take_screenshot(filename="debug_state.png")
   ```

3. **Get current app elements:**
   ```python
   AndroidTools.get_app_elements()
   ```

#### 4. App Installation Issues
**If targeting specific app:**
```bash
# Install app on device
adb install path/to/your/app.apk

# Check if app is installed
adb shell pm list packages | grep your.package.name
```

### Debug Commands

```bash
# Check Appium server status
curl http://localhost:4723/wd/hub/status

# Check device screen (screenshots)
adb shell screencap /sdcard/screen.png
adb pull /sdcard/screen.png

# Get device logs
adb logcat | grep -i appium

# Check Appium server logs
appium --log-level debug
```

### Environment Setup Verification

**1. Check Python Dependencies:**
```bash
python -c "import appium; print('Appium Python client:', appium.__version__)"
python -c "from selenium import webdriver; print('Selenium installed')"
```

**2. Check Android SDK:**
```bash
echo $ANDROID_HOME
ls $ANDROID_HOME/platform-tools/adb
```

**3. Check Appium Installation:**
```bash
appium --version
appium driver list | grep uiautomator2
```

### Network Issues

**If connecting to remote Appium server:**
```bash
# Test network connectivity
telnet <remote_host> 4723

# Check firewall settings
sudo ufw status
```

### Performance Optimization

**For better performance:**
1. **Use specific element locators** (ID > XPath > Class Name)
2. **Increase wait timeouts** for slower devices
3. **Use `no_reset=true`** to avoid app restart overhead
4. **Batch operations** when possible

### Getting Help

**Debug Information to Provide:**
1. Appium server logs
2. Agent error messages
3. Device type (emulator/physical)
4. Android version
5. Appium and Python versions

**Log Collection:**
```bash
# Collect comprehensive logs
APPIUM_LOG_LEVEL=debug appium --log-timestamp > appium.log 2>&1 &
python your_script.py 2>&1 | tee agent.log
adb logcat > device.log &
```

## Architecture

The Android Agent follows a modular architecture:

- **`agent.py`**: Main agent class with prompts and tool management
- **`tools.py`**: Core automation methods and Appium interactions
- **`utils.py`**: Appium client setup, connection management, and utilities
- **`__init__.py`**: Module initialization

This structure ensures clean separation of concerns and easy maintenance.