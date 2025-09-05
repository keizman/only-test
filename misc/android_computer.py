import base64
import time
from enum import StrEnum
from typing import Literal, TypedDict

from PIL import Image

from anthropic.types.beta import BetaToolComputerUse20241022Param

from .base import BaseAnthropicTool, ToolError, ToolResult

import requests
import re

OUTPUT_DIR = "./tmp/outputs"

TYPING_DELAY_MS = 12
TYPING_GROUP_SIZE = 50

# Android-specific actions (removed hover as Android doesn't support it)
Action = Literal[
    "key",
    "type",
    "tap",           # Single tap (replaces left_click)
    "long_press",    # Long press (replaces right_click)
    "double_tap",    # Double tap (replaces double_click)
    "swipe",         # Swipe gesture (replaces left_click_drag)
    "scroll_up",     # Scroll up
    "scroll_down",   # Scroll down
    "screenshot",
    "get_position",  # Get current touch position
    "back",          # Android back button
    "home",          # Android home button
    "recent_apps",   # Android recent apps button
    "wait"
]


class Resolution(TypedDict):
    width: int
    height: int


# Common Android screen resolutions
MAX_SCALING_TARGETS: dict[str, Resolution] = {
    "HD": Resolution(width=720, height=1280),      # 9:16
    "FHD": Resolution(width=1080, height=1920),    # 9:16
    "QHD": Resolution(width=1440, height=2560),    # 9:16
    "TABLET": Resolution(width=1200, height=1920), # 10:16
}


class ScalingSource(StrEnum):
    ANDROID = "android"
    API = "api"


class AndroidComputerToolOptions(TypedDict):
    display_height_px: int
    display_width_px: int
    display_number: int | None


def chunks(s: str, chunk_size: int) -> list[str]:
    return [s[i : i + chunk_size] for i in range(0, len(s), chunk_size)]

class AndroidComputerTool(BaseAnthropicTool):
    """
    A tool that allows the agent to interact with Android devices through ADB.
    Android-specific implementation that removes hover actions and adapts for touch interface.
    """

    name: Literal["android_computer"] = "android_computer"
    api_type: Literal["computer_20241022"] = "computer_20241022"
    width: int
    height: int
    display_num: int | None
    device_id: str | None  # ADB device ID

    _screenshot_delay = 1.0  # Faster for Android
    _scaling_enabled = True

    @property
    def options(self) -> AndroidComputerToolOptions:
        width, height = self.scale_coordinates(
            ScalingSource.ANDROID, self.width, self.height
        )
        return {
            "display_width_px": width,
            "display_height_px": height,
            "display_number": self.display_num,
        }

    def to_params(self) -> BetaToolComputerUse20241022Param:
        return {"name": self.name, "type": self.api_type, **self.options}

    def __init__(self, device_id: str | None = None, is_scaling: bool = False):
        super().__init__()

        self.device_id = device_id or ""  # Empty string uses first available device
        self.display_num = None
        self.offset_x = 0
        self.offset_y = 0
        self.is_scaling = is_scaling
        self.width, self.height = self.get_screen_size()
        print(f"Android screen size: {self.width}, {self.height}")

        # Android-specific key mappings
        self.key_conversion = {
            "Page_Down": "KEYCODE_PAGE_DOWN",
            "Page_Up": "KEYCODE_PAGE_UP",
            "Escape": "KEYCODE_ESCAPE",
            "Enter": "KEYCODE_ENTER",
            "Back": "KEYCODE_BACK",
            "Home": "KEYCODE_HOME",
            "Menu": "KEYCODE_MENU",
            "Volume_Up": "KEYCODE_VOLUME_UP",
            "Volume_Down": "KEYCODE_VOLUME_DOWN",
            "Power": "KEYCODE_POWER",
        }


    async def __call__(
        self,
        *,
        action: Action,
        text: str | None = None,
        coordinate: tuple[int, int] | None = None,
        end_coordinate: tuple[int, int] | None = None,  # For swipe gestures
        **kwargs,
    ):
        print(f"Android action: {action}, text: {text}, coordinate: {coordinate}, is_scaling: {self.is_scaling}")
        
        # Handle touch actions that require coordinates
        if action in ("tap", "long_press", "double_tap"):
            if coordinate is None:
                raise ToolError(f"coordinate is required for {action}")
            if text is not None:
                raise ToolError(f"text is not accepted for {action}")
            if not isinstance(coordinate, (list, tuple)) or len(coordinate) != 2:
                raise ToolError(f"{coordinate} must be a tuple of length 2")
            if not all(isinstance(i, int) for i in coordinate):
                raise ToolError(f"{coordinate} must be a tuple of integers")
            
            if self.is_scaling:
                x, y = self.scale_coordinates(
                    ScalingSource.API, coordinate[0], coordinate[1]
                )
            else:
                x, y = coordinate

            print(f"Touch action at {x}, {y}")
            
            if action == "tap":
                self.send_adb_command(f"shell input tap {x} {y}")
                return ToolResult(output=f"Tapped at ({x}, {y})")
            elif action == "long_press":
                # Long press is implemented as tap with duration
                self.send_adb_command(f"shell input swipe {x} {y} {x} {y} 1000")
                return ToolResult(output=f"Long pressed at ({x}, {y})")
            elif action == "double_tap":
                self.send_adb_command(f"shell input tap {x} {y}")
                time.sleep(0.1)
                self.send_adb_command(f"shell input tap {x} {y}")
                return ToolResult(output=f"Double tapped at ({x}, {y})")

        # Handle swipe gesture
        if action == "swipe":
            if coordinate is None or end_coordinate is None:
                raise ToolError(f"both coordinate and end_coordinate are required for swipe")
            if text is not None:
                raise ToolError(f"text is not accepted for swipe")
            
            if self.is_scaling:
                x1, y1 = self.scale_coordinates(ScalingSource.API, coordinate[0], coordinate[1])
                x2, y2 = self.scale_coordinates(ScalingSource.API, end_coordinate[0], end_coordinate[1])
            else:
                x1, y1 = coordinate
                x2, y2 = end_coordinate

            # Duration in milliseconds (default 300ms for smooth swipe)
            duration = kwargs.get('duration', 300)
            self.send_adb_command(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")
            return ToolResult(output=f"Swiped from ({x1}, {y1}) to ({x2}, {y2})")

        # Handle key and text input
        if action in ("key", "type"):
            if text is None:
                raise ToolError(f"text is required for {action}")
            if coordinate is not None:
                raise ToolError(f"coordinate is not accepted for {action}")
            if not isinstance(text, str):
                raise ToolError(output=f"{text} must be a string")

            if action == "key":
                # Handle Android key codes
                key_code = self.key_conversion.get(text, text)
                if key_code.startswith("KEYCODE_"):
                    self.send_adb_command(f"shell input keyevent {key_code}")
                else:
                    # Handle special key combinations or single keys
                    self.send_adb_command(f"shell input keyevent {key_code}")
                return ToolResult(output=f"Pressed key: {text}")
            
            elif action == "type":
                # Android text input - escape special characters
                escaped_text = text.replace(' ', '%s').replace("'", "\\'")
                self.send_adb_command(f"shell input text '{escaped_text}'")
                screenshot_base64 = (await self.screenshot()).base64_image
                return ToolResult(output=text, base64_image=screenshot_base64)

        # Handle Android navigation buttons
        if action in ("back", "home", "recent_apps"):
            if text is not None:
                raise ToolError(f"text is not accepted for {action}")
            if coordinate is not None:
                raise ToolError(f"coordinate is not accepted for {action}")

            if action == "back":
                self.send_adb_command("shell input keyevent KEYCODE_BACK")
            elif action == "home":
                self.send_adb_command("shell input keyevent KEYCODE_HOME")
            elif action == "recent_apps":
                self.send_adb_command("shell input keyevent KEYCODE_APP_SWITCH")
            
            return ToolResult(output=f"Performed {action}")

        # Handle scrolling
        if action in ("scroll_up", "scroll_down"):
            if text is not None:
                raise ToolError(f"text is not accepted for {action}")
            
            # Default scroll in center of screen
            center_x = self.width // 2
            center_y = self.height // 2
            scroll_distance = 500  # pixels
            
            if action == "scroll_up":
                # Swipe down to scroll up (content moves up)
                start_y = center_y + scroll_distance // 2
                end_y = center_y - scroll_distance // 2
                self.send_adb_command(f"shell input swipe {center_x} {start_y} {center_x} {end_y} 300")
            elif action == "scroll_down":
                # Swipe up to scroll down (content moves down)
                start_y = center_y - scroll_distance // 2
                end_y = center_y + scroll_distance // 2
                self.send_adb_command(f"shell input swipe {center_x} {start_y} {center_x} {end_y} 300")
            
            return ToolResult(output=f"Performed {action}")

        # Handle utility actions
        if action in ("screenshot", "get_position"):
            if text is not None:
                raise ToolError(f"text is not accepted for {action}")
            if coordinate is not None:
                raise ToolError(f"coordinate is not accepted for {action}")

            if action == "screenshot":
                return await self.screenshot()
            elif action == "get_position":
                # Android doesn't have a direct equivalent to cursor position
                # Return center of screen as default
                x, y = self.width // 2, self.height // 2
                if self.is_scaling:
                    x, y = self.scale_coordinates(ScalingSource.ANDROID, x, y)
                return ToolResult(output=f"X={x},Y={y}")

        if action == "wait":
            duration = kwargs.get('duration', 1.0)
            time.sleep(duration)
            return ToolResult(output=f"Waited for {duration} seconds")

        raise ToolError(f"Invalid action: {action}")

    def send_adb_command(self, command: str):
        """
        Executes an ADB command on the Android device via HTTP server.
        """
        device_prefix = f"-s {self.device_id} " if self.device_id else ""
        full_command = ["adb", device_prefix + command] if device_prefix else ["adb"] + command.split()
        
        try:
            print(f"Sending ADB command: {full_command}")
            response = requests.post(
                f"http://localhost:5000/execute", 
                headers={'Content-Type': 'application/json'},
                json={"command": full_command},
                timeout=30
            )
            time.sleep(0.3)  # Short delay for Android actions
            print(f"ADB command executed")
            if response.status_code != 200:
                raise ToolError(f"Failed to execute ADB command. Status code: {response.status_code}")
            return response.json().get('output', '')
        except requests.exceptions.RequestException as e:
            raise ToolError(f"An error occurred while trying to execute ADB command: {str(e)}")

    async def screenshot(self):
        """Take screenshot using ADB and return as base64."""
        if not hasattr(self, 'target_dimension'):
            self.target_dimension = MAX_SCALING_TARGETS["FHD"]  # Default to FHD for Android
        
        # Use ADB to take screenshot
        self.send_adb_command("shell screencap -p /sdcard/screenshot.png")
        # Pull screenshot from device
        self.send_adb_command("pull /sdcard/screenshot.png ./tmp/android_screenshot.png")
        # Clean up device storage
        # self.send_adb_command("shell rm /sdcard/screenshot.png")
        
        width, height = self.target_dimension["width"], self.target_dimension["height"]
        
        try:
            # Read and process the screenshot
            with open("./tmp/android_screenshot.png", "rb") as f:
                screenshot_data = f.read()
            
            # Optional: resize if needed
            if width != self.width or height != self.height:
                image = Image.open("./tmp/android_screenshot.png")
                image = image.resize((width, height), Image.Resampling.LANCZOS)
                image.save("./tmp/android_screenshot_resized.png")
                with open("./tmp/android_screenshot_resized.png", "rb") as f:
                    screenshot_data = f.read()
            
            time.sleep(0.3)  # Short delay for Android
            return ToolResult(base64_image=base64.b64encode(screenshot_data).decode())
        except Exception as e:
            raise ToolError(f"Failed to capture or process screenshot: {str(e)}")

    def scale_coordinates(self, source: ScalingSource, x: int, y: int):
        """Scale coordinates for Android screen resolution."""
        if not self._scaling_enabled:
            return x, y
        
        ratio = self.width / self.height
        target_dimension = None

        # Find best matching Android resolution
        for target_name, dimension in MAX_SCALING_TARGETS.items():
            target_ratio = dimension["width"] / dimension["height"]
            if abs(target_ratio - ratio) < 0.05:  # Allow for aspect ratio variations
                if dimension["width"] <= self.width:
                    target_dimension = dimension
                    self.target_dimension = target_dimension
                break

        if target_dimension is None:
            # Default to FHD if no match found
            target_dimension = MAX_SCALING_TARGETS["FHD"]
            self.target_dimension = target_dimension

        x_scaling_factor = target_dimension["width"] / self.width
        y_scaling_factor = target_dimension["height"] / self.height
        
        if source == ScalingSource.API:
            if x > target_dimension["width"] or y > target_dimension["height"]:
                raise ToolError(f"Coordinates {x}, {y} are out of bounds for target resolution")
            # Scale up to device resolution
            return round(x / x_scaling_factor), round(y / y_scaling_factor)
        
        # Scale down to target resolution
        return round(x * x_scaling_factor), round(y * y_scaling_factor)

    def get_screen_size(self):
        """Get Android device screen size using ADB."""
        try:
            # Get screen size using ADB
            response = requests.post(
                f"http://localhost:5000/execute",
                headers={'Content-Type': 'application/json'},
                json={"command": ["adb", "shell", "wm", "size"]},
                timeout=30
            )
            if response.status_code != 200:
                raise ToolError(f"Failed to get Android screen size. Status code: {response.status_code}")
            
            output = response.json()['output'].strip()
            # Expected output: "Physical size: 1080x1920" or "Override size: 1080x1920"
            match = re.search(r'(\d+)x(\d+)', output)
            if not match:
                raise ToolError(f"Could not parse Android screen size from output: {output}")
            width, height = map(int, match.groups())
            return width, height
        except requests.exceptions.RequestException as e:
            raise ToolError(f"An error occurred while trying to get Android screen size: {str(e)}")