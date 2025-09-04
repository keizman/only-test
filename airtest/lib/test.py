import uiautomator2 as u2
import time
import subprocess
import sys

def restart_uiautomator_service():
    """Restart uiautomator service to clear any conflicts"""
    try:
        print("Attempting to restart uiautomator service...")
        # Kill existing uiautomator processes
        subprocess.run(['adb', 'shell', 'pkill', '-f', 'uiautomator'], capture_output=True)
        time.sleep(2)
        print("Uiautomator service restarted")
        return True
    except Exception as e:
        print(f"Failed to restart uiautomator service: {e}")
        return False

def connect_with_retry():
    """Try multiple connection methods to handle accessibility service conflicts"""
    
    # Method 1: Try normal connection first
    try:
        print("Attempting normal connection...")
        device = u2.connect()
        print("✓ Normal connection successful")
        return device
    except u2.exceptions.AccessibilityServiceAlreadyRegisteredError:
        print("✗ Accessibility service already registered, trying alternatives...")
    except Exception as e:
        print(f"✗ Normal connection failed: {e}")
    
    # Method 2: Restart service and retry
    if restart_uiautomator_service():
        try:
            print("Attempting connection after service restart...")
            device = u2.connect()
            print("✓ Connection successful after restart")
            return device
        except Exception as e:
            print(f"✗ Connection failed after restart: {e}")
    
    # Method 3: Try connecting with init=False to skip service initialization
    try:
        print("Attempting connection with init=False...")
        device = u2.connect(init=False)
        print("✓ Connection successful with init=False")
        return device
    except Exception as e:
        print(f"✗ Connection with init=False failed: {e}")
    
    # Method 4: Try connecting to a specific device if multiple devices
    try:
        print("Checking for available devices...")
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        print(f"ADB devices output:\n{result.stdout}")
        
        # Extract device serial numbers
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        devices = [line.split('\t')[0] for line in lines if '\tdevice' in line]
        
        if devices:
            serial = devices[0]
            print(f"Attempting connection to specific device: {serial}")
            device = u2.connect(serial)
            print(f"✓ Connection successful to device {serial}")
            return device
    except Exception as e:
        print(f"✗ Specific device connection failed: {e}")
    
    print("✗ All connection methods failed")
    return None

def test_device_functionality(device):
    """Test basic device functionality"""
    if not device:
        print("No device connected")
        return False
    
    try:
        # Test basic device info
        print(f"Device info: {device.info}")
        
        # Test screenshot capability
        print("Testing screenshot...")
        device.screenshot("test_screenshot.png")
        print("✓ Screenshot test successful")
        
        # Test hierarchy dump (uncomment the lines you had commented)
        print("Testing hierarchy dump...")
        xml = device.dump_hierarchy()
        print("✓ Hierarchy dump successful")
        
        # Save XML to file
        with open('screen_dump.xml', 'w', encoding='utf-8') as f:
            f.write(xml)
        print("✓ XML saved to screen_dump.xml")
        
        return True
        
    except Exception as e:
        print(f"Device functionality test failed: {e}")
        return False

if __name__ == "__main__":
    print("Starting UiAutomator2 connection test...")
    
    # Connect to device with retry logic
    device = connect_with_retry()
    
    if device:
        print("Device connected successfully!")
        
        # Test device functionality
        if test_device_functionality(device):
            print("✓ All tests passed successfully!")
        else:
            print("✗ Some tests failed")
    else:
        print("Failed to connect to device")
        print("\nTroubleshooting suggestions:")
        print("1. Make sure USB debugging is enabled")
        print("2. Check if device is properly connected: adb devices")
        print("3. Try manually stopping uiautomator: adb shell pkill -f uiautomator")
        print("4. Restart adb server: adb kill-server && adb start-server")
        print("5. Disable and re-enable USB debugging on device")
        sys.exit(1)

