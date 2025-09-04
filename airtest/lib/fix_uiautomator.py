#!/usr/bin/env python3
"""
UiAutomator2 Accessibility Service Fix Utility

This script helps resolve the common "AccessibilityServiceAlreadyRegisteredError" 
that occurs when UiAutomator2 tries to connect to an Android device.
"""

import subprocess
import time
import sys

def run_adb_command(command):
    """Run an adb command and return the result"""
    try:
        result = subprocess.run(['adb'] + command, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except FileNotFoundError:
        print("Error: adb command not found. Please install Android SDK Platform Tools.")
        return False, "", "adb not found"

def check_device_connection():
    """Check if any Android devices are connected"""
    print("Checking device connection...")
    success, stdout, stderr = run_adb_command(['devices'])
    
    if not success:
        print(f"Failed to check devices: {stderr}")
        return False
    
    print(f"ADB devices output:\n{stdout}")
    
    # Check if any devices are connected
    lines = stdout.strip().split('\n')[1:]  # Skip header
    devices = [line for line in lines if '\tdevice' in line]
    
    if not devices:
        print("No devices connected. Please connect your Android device and enable USB debugging.")
        return False
    
    print(f"Found {len(devices)} connected device(s)")
    return True

def kill_uiautomator_processes():
    """Kill all uiautomator related processes on the device"""
    print("Killing uiautomator processes...")
    
    commands = [
        ['shell', 'pkill', '-f', 'uiautomator'],
        ['shell', 'pkill', '-f', 'com.github.uiautomator'],
        ['shell', 'pkill', '-f', 'ATX'],
        ['shell', 'am', 'force-stop', 'com.github.uiautomator'],
    ]
    
    for cmd in commands:
        success, stdout, stderr = run_adb_command(cmd)
        if success:
            print(f"✓ Successfully ran: adb {' '.join(cmd)}")
        else:
            print(f"✗ Failed to run: adb {' '.join(cmd)} - {stderr}")
    
    time.sleep(2)
    print("Process cleanup completed")

def restart_adb_server():
    """Restart the ADB server"""
    print("Restarting ADB server...")
    
    # Kill server
    success, stdout, stderr = run_adb_command(['kill-server'])
    if success:
        print("✓ ADB server stopped")
    else:
        print(f"✗ Failed to stop ADB server: {stderr}")
    
    time.sleep(1)
    
    # Start server
    success, stdout, stderr = run_adb_command(['start-server'])
    if success:
        print("✓ ADB server started")
    else:
        print(f"✗ Failed to start ADB server: {stderr}")

def clear_uiautomator_data():
    """Clear UiAutomator app data and cache"""
    print("Clearing UiAutomator app data...")
    
    commands = [
        ['shell', 'pm', 'clear', 'com.github.uiautomator'],
        ['shell', 'pm', 'clear', 'com.github.uiautomator.test'],
    ]
    
    for cmd in commands:
        success, stdout, stderr = run_adb_command(cmd)
        if success:
            print(f"✓ Cleared data for package")
        else:
            print(f"Package not found or already cleared: {' '.join(cmd[2:])}")

def disable_enable_accessibility():
    """Guide user to disable and re-enable accessibility services"""
    print("\n" + "="*60)
    print("MANUAL STEP REQUIRED:")
    print("Please follow these steps on your Android device:")
    print("1. Go to Settings > Accessibility")
    print("2. Find any UiAutomator or testing-related services")
    print("3. Disable them temporarily")
    print("4. Wait 5 seconds")
    print("5. Re-enable them")
    print("6. Press Enter here when done...")
    print("="*60)
    input("Press Enter when you've completed the accessibility settings...")

def main():
    """Main function to fix UiAutomator2 issues"""
    print("UiAutomator2 Accessibility Service Fix Utility")
    print("=" * 50)
    
    # Step 1: Check device connection
    if not check_device_connection():
        return False
    
    # Step 2: Kill existing processes
    kill_uiautomator_processes()
    
    # Step 3: Clear app data
    clear_uiautomator_data()
    
    # Step 4: Restart ADB server
    restart_adb_server()
    
    # Step 5: Check connection again
    if not check_device_connection():
        print("Device connection lost after restart. Please reconnect.")
        return False
    
    # Step 6: Manual accessibility step (if needed)
    print("\nIf the issue persists, you may need to manually manage accessibility services:")
    response = input("Do you want guidance for manual accessibility settings? (y/n): ")
    if response.lower().startswith('y'):
        disable_enable_accessibility()
    
    print("\n✓ Fix utility completed!")
    print("Now try running your UiAutomator2 script again.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

