#!/usr/bin/env python3
import tkinter as tk
import signal
import atexit
from servo_widget import ServoWidget
from preset_widget import PresetWidget, ToggleWidget
from headset_input import HeadsetClient
try:
    from eye_tracker import EyeTracker
    HAS_EYE_TRACKER = True
except ImportError:
    print("WARNING: EyeTracker dependencies not found. Eye tracking disabled.")
    HAS_EYE_TRACKER = False
import time

# Try to import pi_servo_hat, mock if not available (for testing without hardware)
USE_MOCK_HARDWARE = True  # Set to True to force mock mode (prevent overheating/power surges)

class MockServoHat:
    def __init__(self):
        print("MOCK: Initializing MockServoHat")
    
    def restart(self):
        print("MOCK: Restarting Servo Hat")
        
    def sleep(self):
        print("MOCK: Sleeping Servo Hat")
        
    def move_servo_position(self, channel, angle):
        print(f"MOCK: Moving servo on channel {channel} to {angle} degrees")

try:
    if USE_MOCK_HARDWARE:
        raise ImportError("Forced Mock Mode")
    import pi_servo_hat
    HAS_HARDWARE = True
except ImportError:
    if USE_MOCK_HARDWARE:
        print("NOTE: Running in Forced Mock Mode (Hardware Disabled)")
    else:
        print("WARNING: pi_servo_hat not found. Running in simulation mode.")
    HAS_HARDWARE = False

# Try to import LED Stick
try:
    import qwiic_led_stick
    HAS_LED_STICK = True
except ImportError:
    print("WARNING: qwiic_led_stick not found. LED attention meter disabled.")
    HAS_LED_STICK = False

# Servo Channel Mapping
SERVO_MAP = {
    "LeftArm": {
        "Base": 0,
        "Shoulder": 1,
        "Elbow": 2,
        "Wrist": 3,
        "Gripper": 4
    },
    "RightArm": {
        "Base": 15,
        "Shoulder": 14,
        "Elbow": 13,
        "Wrist": 12,
        "Gripper": 11
    }
}

# Servo Limits Configuration
SERVO_LIMITS = {
    "Black": {
        "Base": (-50, 130),
        "Shoulder": (20, 150),
        "Elbow": (-50, 130),
        "Wrist": (-50, 130), # 90 middle
        "Gripper": (-50, 50)
    },
    "Orange": {
        "Base": (-50, 130),
        "Shoulder": (10, 100),
        "Elbow": (-50, 130),
        "Wrist": (-50, 130), # 55 middle
        "Gripper": (-20, 73)
    }
}

ARM_CONFIG = {
    "LeftArm": "Orange",
    "RightArm": "Black"
}

# Initial Pose Configuration
# If defined, servos will move to these angles on startup.
# If a joint is missing here, it defaults to the midpoint of its limits.
STARTUP_POSE = {
    "LeftArm": {"Base": 60, "Shoulder": 30, "Elbow": 70, "Wrist": 55, "Gripper": 0},
    "RightArm": {"Base": 10, "Shoulder": 50, "Elbow": 70, "Wrist": 90, "Gripper": 0}
}

class AttentionLEDMeter:
    """LED Stick meter for displaying attention/focus levels"""
    def __init__(self):
        self.led_stick = None
        self.enabled = False
        
        if HAS_LED_STICK:
            try:
                self.led_stick = qwiic_led_stick.QwiicLEDStick()
                if self.led_stick.begin():
                    print("LED Attention Meter initialized successfully!")
                    self.led_stick.LED_off()  # Clear all LEDs
                    self.enabled = True
                else:
                    print("WARNING: Could not connect to LED Stick")
            except Exception as e:
                print(f"WARNING: LED Stick initialization failed: {e}")
        
        self.num_leds = 10
        self.max_value = 100  # Attention is 0-100
        self.last_displayed = -1  # Track last value to avoid unnecessary updates
        
    def update(self, attention_value):
        """
        Update LED display based on attention value (0-100)
        
        Args:
            attention_value: Current attention level (0-100)
        """
        if not self.enabled or not self.led_stick:
            return
        
        # Clamp value
        attention_value = max(0, min(100, attention_value))
        
        # Calculate number of LEDs to light (0-10)
        num_leds_lit = int((attention_value / self.max_value) * self.num_leds)
        
        # Ensure at least 1 LED if attention > 0
        if attention_value > 0 and num_leds_lit == 0:
            num_leds_lit = 1
        
        # Only update if value changed significantly
        if num_leds_lit == self.last_displayed:
            return
        
        self.last_displayed = num_leds_lit
        
        try:
            # Clear all LEDs first
            self.led_stick.LED_off()
            
            # Light up LEDs with gradient colors
            for i in range(num_leds_lit):
                # Color gradient: Red (low) -> Yellow (medium) -> Green (high)
                if i < 3:
                    # Red (low attention)
                    red, green, blue = 255, 0, 0
                elif i < 7:
                    # Yellow (medium attention)
                    red, green, blue = 255, 255, 0
                else:
                    # Green (high attention)
                    red, green, blue = 0, 255, 0
                
                # LEDs are indexed 1-10
                self.led_stick.set_single_LED_color(i + 1, red, green, blue)
                
        except Exception as e:
            print(f"Error updating LED Stick: {e}")
    
    def clear(self):
        """Turn off all LEDs"""
        if self.enabled and self.led_stick:
            try:
                self.led_stick.LED_off()
                self.last_displayed = -1
            except Exception as e:
                print(f"Error clearing LED Stick: {e}")
    
    def test_pattern(self):
        """Run a test pattern on the LED stick"""
        if not self.enabled or not self.led_stick:
            return
        
        print("Running LED test pattern...")
        try:
            # Fill up from 0 to 100
            for val in range(0, 101, 10):
                self.update(val)
                time.sleep(0.3)
            
            time.sleep(0.5)
            self.clear()
            print("LED test complete!")
        except Exception as e:
            print(f"Error in test pattern: {e}")

class ServoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Robot Arm Servo Control")
        
        # 80% Screen Size
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        
        # Center the window
        x_pos = int((screen_width - window_width) / 2)
        y_pos = int((screen_height - window_height) / 2)
        
        self.root.geometry(f"{window_width}x{window_height}+{x_pos}+{y_pos}")
        # self.root.attributes('-fullscreen', True) # Disabled fullscreen
        self.root.bind("<Escape>", self.quit_app) # Exit on Escape
        self.running = True
        self._quitting = False
        
        # Initialize LED Attention Meter
        self.led_meter = AttentionLEDMeter()
        if self.led_meter.enabled:
            # Run test pattern on startup
            self.root.after(1000, self.led_meter.test_pattern)
        
        # Initialize Servo Hat
        self.servo = None
        if HAS_HARDWARE:
            try:
                self.servo = pi_servo_hat.PiServoHat()
                # Ensure clean startup: sleep first, then restart
                try:
                    self.servo.sleep()  # Stop any existing PWM
                    time.sleep(0.1)
                except:
                    pass
                self.servo.restart()  # Re-initialize cleanly
                time.sleep(0.2)  # Let PWM stabilize
                print("Servo Hat Initialized.")
            except Exception as e:
                print(f"Error initializing Servo Hat: {e}")
                self.servo = None
        else:
            # Use Mock Servo Hat if hardware is missing or disabled
            print("Using Mock Servo Hat")
            self.servo = MockServoHat()

        # Initialize Headset Client
        self.headset = HeadsetClient()
        self.headset.start()

        # Initialize Eye Tracker
        self.eye_tracker = None
        if HAS_EYE_TRACKER:
            # Get screen dimensions
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            self.eye_tracker = EyeTracker(screen_width, screen_height)
            self.eye_tracker.start()
            
            # Create a visual cursor (red circle)
            self.cursor_window = tk.Toplevel(self.root)
            self.cursor_window.overrideredirect(True) # No window decorations
            self.cursor_window.attributes('-topmost', True) # Always on top
            self.cursor_window.geometry("20x20+0+0")
            # Make background transparent if supported, or just match a color
            # Linux transparency can be tricky. Let's just make a red circle on a canvas.
            self.cursor_canvas = tk.Canvas(self.cursor_window, width=20, height=20, bg='black', highlightthickness=0)
            self.cursor_canvas.pack()
            self.cursor_canvas.create_oval(0, 0, 20, 20, fill='red', outline='white')
            # Try to make black transparent
            try:
                self.cursor_window.attributes('-transparentcolor', 'black') # Windows
            except:
                pass # Linux might need '-alpha' but that affects the whole window

        # State tracking for servo angles (default 90)
        self.servo_angles = {}
        for arm in ["LeftArm", "RightArm"]:
            self.servo_angles[arm] = {}
            for joint in ["Base", "Shoulder", "Elbow", "Wrist", "Gripper"]:
                self.servo_angles[arm][joint] = 90
                # Initialize hardware to midpoint or STARTUP_POSE
                if self.servo:
                    try:
                        # Determine initial angle
                        initial_angle = None
                        
                        # Check STARTUP_POSE first
                        if arm in STARTUP_POSE and joint in STARTUP_POSE[arm]:
                            initial_angle = STARTUP_POSE[arm][joint]
                        
                        # Fallback to midpoint
                        if initial_angle is None:
                            # Get limits
                            servo_type = ARM_CONFIG.get(arm)
                            min_limit, max_limit = 0, 180
                            if servo_type and joint in SERVO_LIMITS[servo_type]:
                                min_limit, max_limit = SERVO_LIMITS[servo_type][joint]
                            
                            # Calculate midpoint
                            initial_angle = int((min_limit + max_limit) / 2)
                        
                        self.servo_angles[arm][joint] = initial_angle
                        
                        channel = SERVO_MAP[arm][joint]
                        self.servo.move_servo_position(channel, initial_angle)
                    except Exception as e:
                        print(f"Failed to set initial position for {arm} {joint}: {e}")

        # Main container
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Top Info Frame
        self.info_frame = tk.Frame(self.main_frame)
        self.info_frame.pack(side="top", fill="x", pady=5)

        # Signal Quality Display
        self.signal_quality_label = tk.Label(self.info_frame, text="Signal Quality: 0", font=("Arial", 12))
        self.signal_quality_label.pack(side="left", expand=True)

        # Attention Display (enhanced with LED indicator)
        attention_text = "Attention: 0"
        if self.led_meter.enabled:
            attention_text += " [LED Meter Active]"
        self.attention_label = tk.Label(self.info_frame, text=attention_text, font=("Arial", 12))
        self.attention_label.pack(side="left", expand=True)

        # Toggle Button (gaze-selectable)
        self.toggle_widget = ToggleWidget(
            self.info_frame,
            text_on="Switch to Manual",
            text_off="Switch to Presets",
            dwell_time=1.5,
            callback=self.toggle_mode
        )
        self.toggle_widget.pack(side="right", padx=10)
        self.toggle_widget.set_state(True) # Start in "On" state (Presets mode)
        
        # Track current mode
        self.in_preset_mode = True
        self.in_category_mode = False # Submenu state for presets
        self.active_category_name = None
        
        # Columns Frame
        self.columns_frame = tk.Frame(self.main_frame)
        # self.columns_frame.pack(side="top", fill="both", expand=True) # Hidden by default

        # Split into two sides
        self.left_frame = tk.Frame(self.columns_frame, borderwidth=0, relief="sunken")
        self.left_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        self.right_frame = tk.Frame(self.columns_frame, borderwidth=0, relief="sunken")
        self.right_frame.pack(side="right", fill="both", expand=True, padx=5)
        
        # Header
        
        # Servo Labels Configuration (Left Label (-), Right Label (+))
        self.servo_labels = {
            "Base": ("Right", "Left"), # Rotates base
            "Shoulder": ("Down", "Up"), # Lifts shoulder
            "Elbow": ("Down", "Up"),    # Lifts elbow
            "Wrist": ("Right", "Left"), # Wrist rotates
            "Gripper": ("Open", "Close") # Open/Close gripper
        }
        
        # Servo Widgets Storage
        self.widgets = []
        
        # Preset Widgets Storage
        self.preset_widgets = []
        
        # Create Widgets
        self.create_arm_widgets(self.left_frame, "LeftArm", ["Base", "Shoulder", "Elbow", "Wrist", "Gripper"])
        self.create_arm_widgets(self.right_frame, "RightArm", ["Base", "Shoulder", "Elbow", "Wrist", "Gripper"])
        
        # Create Presets Frame (Shown by default)
        self.presets_frame = tk.Frame(self.main_frame)
        self.create_preset_ui()
        self.presets_frame.pack(side="top", fill="both", expand=True)
        
        # Start Update Loop
        self.update_loop()
        
    def create_arm_widgets(self, parent, arm_name, servo_names):
        for name in servo_names:
            left_lbl, right_lbl = self.servo_labels.get(name, ("-", "+"))
            widget = ServoWidget(parent, arm_name, name, left_label=left_lbl, right_label=right_lbl, callback=self.on_servo_action)
            widget.pack(pady=5, fill="both", expand=True)
            
            # Set limits and initial angle
            servo_type = ARM_CONFIG.get(arm_name)
            if servo_type and name in SERVO_LIMITS[servo_type]:
                min_limit, max_limit = SERVO_LIMITS[servo_type][name]
                widget.set_limits(min_limit, max_limit)
            
            # Set initial angle from state
            initial_angle = self.servo_angles[arm_name][name]
            widget.set_angle(initial_angle)
            
            self.widgets.append(widget)
            
    def on_servo_action(self, arm, servo_name, action, step=1):
        # Determine direction
        change = step if action == 'right' else -step
        
        # Update angle
        current_angle = self.servo_angles[arm][servo_name]
        new_angle = current_angle + change
        
        # Get limits for this specific servo
        servo_type = ARM_CONFIG.get(arm)
        min_limit, max_limit = 0, 180 # Default
        if servo_type and servo_name in SERVO_LIMITS[servo_type]:
            min_limit, max_limit = SERVO_LIMITS[servo_type][servo_name]
        
        # Clamp between limits
        new_angle = max(min_limit, min(max_limit, new_angle))
        
        if new_angle != current_angle:
            self.servo_angles[arm][servo_name] = new_angle
            # print(f"Moving {arm} {servo_name} to {new_angle} degrees")
            
            # Send to hardware
            if self.servo:
                try:
                    channel = SERVO_MAP[arm][servo_name]
                    self.servo.move_servo_position(channel, new_angle)
                except Exception as e:
                    print(f"Error moving servo: {e}")
            
            # Update widget visual state
            # Find the widget and update its angle
            for widget in self.widgets:
                if widget.arm_name == arm and widget.servo_name == servo_name:
                    widget.set_angle(new_angle)
                    break
        
    def update_loop(self):
        if not self.running:
            return
        
        # Get current attention level
        attention = self.headset.get_attention()
        
        # Update attention label
        attention_text = f"Attention: {attention}"
        if self.led_meter.enabled:
            attention_text += " [LED]"
        self.attention_label.config(text=attention_text)
        
        # Update LED Meter based on attention level
        self.led_meter.update(attention)
        
        # Update Eye Tracking
        if self.eye_tracker and self.eye_tracker.running:
            gaze_x, gaze_y = self.eye_tracker.get_gaze()
            
            # Move visual cursor
            try:
                self.cursor_window.geometry(f"+{gaze_x-10}+{gaze_y-10}")
            except:
                pass

            # Check toggle widget gaze
            tw = self.toggle_widget
            twx = tw.winfo_rootx()
            twy = tw.winfo_rooty()
            tww = tw.winfo_width()
            twh = tw.winfo_height()
            if twx <= gaze_x <= twx + tww and twy <= gaze_y <= twy + twh:
                tw.update_gaze()
            else:
                tw.clear_hover()

            # Manual Hit Testing for Servo Widgets (only if in manual mode)
            if not self.in_preset_mode:
                for widget in self.widgets:
                    wx = widget.winfo_rootx()
                    wy = widget.winfo_rooty()
                    ww = widget.winfo_width()
                    wh = widget.winfo_height()
                    
                    if wx <= gaze_x <= wx + ww and wy <= gaze_y <= wy + wh:
                        rel_x = gaze_x - wx
                        widget.update_gaze(rel_x)
                    else:
                        widget.clear_hover()
            else:
                # Presets Mode
                if self.in_category_mode:
                    # Hit testing for current category widgets (Presets or Manual)
                    for widget in self.category_widgets_list:
                        wx = widget.winfo_rootx()
                        wy = widget.winfo_rooty()
                        ww = widget.winfo_width()
                        wh = widget.winfo_height()
                        
                        if wx <= gaze_x <= wx + ww and wy <= gaze_y <= wy + wh:
                            # Duck typing: Check if it's a ServoWidget (needs rel_x) or PresetWidget (no args)
                            if isinstance(widget, ServoWidget):
                                rel_x = gaze_x - wx
                                widget.update_gaze(rel_x)
                            else:
                                widget.update_gaze()
                        else:
                            widget.clear_hover()
                else:
                    # Hit testing for Main Menu Preset Widgets
                    # Get Canvas bounds for visibility check
                    c_y_min = self.preset_canvas.winfo_rooty()
                    c_y_max = c_y_min + self.preset_canvas.winfo_height()
                    
                    for pw in self.preset_widgets:
                        pwx = pw.winfo_rootx()
                        pwy = pw.winfo_rooty()
                        pww = pw.winfo_width()
                        pwh = pw.winfo_height()
                        
                        # Special check for Scroll Buttons (they are outside the canvas, so always visible)
                        is_scroll_btn = (pw == self.scroll_up_btn or pw == self.scroll_down_btn)
                        
                        # Visibility check for items inside canvas
                        is_visible = True
                        if not is_scroll_btn:
                            # A simple check: is the center of the widget within the canvas Y bounds?
                            center_y = pwy + (pwh / 2)
                            if center_y < c_y_min or center_y > c_y_max:
                                is_visible = False
                        
                        if is_visible and pwx <= gaze_x <= pwx + pww and pwy <= gaze_y <= pwy + pwh:
                            pw.update_gaze()
                        else:
                            pw.clear_hover()
        
        # Process frames for all relevant widgets
        self.toggle_widget.process_frame(attention)
        
        if not self.in_preset_mode:
            # MANUAL MODE
            for widget in self.widgets:
                widget.process_frame(attention)
        else:
            # PRESET MODES
            if self.in_category_mode:
                # SUBMENU MODE
                for widget in self.category_widgets_list:
                     widget.process_frame(attention)
            else:
                # MAIN PRESET MENU
                for pw in self.preset_widgets:
                    pw.process_frame(attention)
                
        self.root.after(50, self.update_loop) # Check every 50ms

    def toggle_mode(self):
        """Toggle between fine-grained control and preset poses."""
        if not self.in_preset_mode:
            # Switch TO Presets mode
            self.columns_frame.pack_forget()
            
            if self.in_category_mode:
                self.category_frame.pack(side="top", fill="both", expand=True)
            else:
                self.presets_frame.pack(side="top", fill="both", expand=True)
                
            self.in_preset_mode = True
            self.toggle_widget.set_state(True)
        else:
            # Switch TO Manual mode
            if self.in_category_mode:
                self.category_frame.pack_forget()
            else:
                self.presets_frame.pack_forget()
                
            self.columns_frame.pack(side="top", fill="both", expand=True)
            self.in_preset_mode = False
            self.toggle_widget.set_state(False)

    def create_preset_ui(self):
        """Create the preset poses UI with gaze-selectable widgets."""
        # Header
        tk.Label(self.presets_frame, text="Preset Poses (Look to Select)", font=("Arial", 16, "bold")).pack(pady=10)

        # Preset definitions: name -> {arm: {joint: angle}}
        # Preset definitions: name -> {arm: {joint: angle}} OR list of (duration_ms, {arm: {joint: angle}})
        self.presets = {
            "Home Position": {
                "LeftArm": {"Base": 90, "Shoulder": 35, "Elbow": 90, "Wrist": 90, "Gripper": 0},
                "RightArm": {"Base": 90, "Shoulder": 65, "Elbow": 90, "Wrist": 90, "Gripper": 0},
            },
            "Left Gripper Open": {
                "LeftArm": {"Gripper": -20},
            },
            "Left Gripper Closed": {
                "LeftArm": {"Gripper": 73},
            },
            "Right Gripper Open": {
                "RightArm": {"Gripper": -50},
            },
            "Right Gripper Closed": {
                "RightArm": {"Gripper": 45},
            },
            "Left Elbow Bent (90°)": {
                "LeftArm": {"Elbow": 90},
            },
            "Left Elbow Extended (0°)": {
                "LeftArm": {"Elbow": 0},
            },
            "Right Elbow Bent (90°)": {
                "RightArm": {"Elbow": 90},
            },
            "Right Elbow Extended (0°)": {
                "RightArm": {"Elbow": 0},
            },
            "Wave Animation": [
                (500, {"RightArm": {"Shoulder": 80, "Elbow": 90, "Wrist": 50}}),  # Start
                (300, {"RightArm": {"Wrist": 130}}), # Wave Left
                (300, {"RightArm": {"Wrist": 50}}),  # Wave Right
                (300, {"RightArm": {"Wrist": 130}}), # Wave Left
                (300, {"RightArm": {"Wrist": 50}}),  # Wave Right
                (500, {"RightArm": {"Shoulder": 65, "Elbow": 90, "Wrist": 90}})   # Return Home
            ],
            "Wave Animation with Both Arms": [
                (500, {"RightArm": {"Shoulder": 80, "Elbow": 90, "Wrist": 50}, "LeftArm": {"Shoulder": 80, "Elbow": 90, "Wrist": 50}}),  # Start
                (300, {"RightArm": {"Wrist": 130}, "LeftArm": {"Wrist": 130}}), # Wave Left
                (300, {"RightArm": {"Wrist": 50}, "LeftArm": {"Wrist": 50}}),  # Wave Right
                (300, {"RightArm": {"Wrist": 130}, "LeftArm": {"Wrist": 130}}), # Wave Left
                (300, {"RightArm": {"Wrist": 50}, "LeftArm": {"Wrist": 50}}),  # Wave Right
                (500, {"RightArm": {"Shoulder": 65, "Elbow": 90, "Wrist": 90}, "LeftArm": {"Shoulder": 65, "Elbow": 90, "Wrist": 90}})   # Return Home
            ],
            "Reach Forward (Both)": [   
                (500, {"RightArm": {"Shoulder": 45, "Elbow": 0}, "LeftArm": {"Shoulder": 45, "Elbow": 0}}),
                (500, {"RightArm": {"Shoulder": 65, "Elbow": 90, "Wrist": 90}, "LeftArm": {"Shoulder": 65, "Elbow": 90, "Wrist": 90}}),
            ],
            "Pass Object (L to R)": [
                (2000, {"LeftArm": {"Base": 60, "Shoulder": 90, "Elbow": -20, "Wrist": 55, "Gripper": -40}}), # Grab pose
                (750, {"LeftArm": {"Gripper": 70}}), # Close gripper
                (200, {"LeftArm": {"Shoulder": 30, "Elbow": 60}}), # Lift
                (500, {"LeftArm": {"Elbow": 70}}), # Lift
                (1500, {"LeftArm": {"Base": -30}}), # Rotate to R
                (450, {"RightArm": {"Base": 75, "Shoulder": 130, "Elbow": 130, "Wrist": 30, "Gripper": 15}}), # R Ready
                # (1000, {"LeftArm": {"Elbow": 80}}), # Lower to R
                (1000, {"LeftArm": {"Shoulder": 45, "Elbow": 20}}), # Lower to R
                (2000, {"LeftArm": {"Gripper": 0}}), # L Release
                (500, {"RightArm": {"Wrist": 90, "Gripper": 50}}), # R Grip
                (1000, {"LeftArm": {"Base": 60, "Elbow": 70}}), # L Retract
                (1500, {"RightArm": {"Base": 10, "Shoulder": 100, "Elbow": 110}}), # R Rotate to Drop
                (1000, {"RightArm": {"Shoulder": 60, "Elbow": 100}}), # R Backwards
                (500, {"RightArm": {"Elbow": -10, "Gripper": -30}}), # R Release
                (1000, {"RightArm": {"Shoulder": 50, "Elbow": -50}}), # R Nudge/Clear
                (1000, {"RightArm": {"Elbow": 80}}), # R Straighten
            ]
        }

        # Category Configuration: Grouping complex animations + Manual Controls
        self.categories = {
            "Throw": {
                "presets": {
                    "Prepare": {
                        "RightArm": {"Shoulder": 30, "Elbow": 120, "Wrist": 90, "Gripper": -50},
                    },
                    "Load": {
                        "RightArm": {"Shoulder": 30, "Elbow": 120, "Wrist": 90, "Gripper": 45},
                    },
                    "Launch": [
                        (100, {"RightArm": {"Shoulder": 80, "Elbow": 80}}),
                        (150, {"RightArm": {"Shoulder": 105, "Elbow": 50, "Gripper": 45}}),
                        (150, {"RightArm": {"Shoulder": 110, "Elbow": 45, "Gripper": -50}}),
                        (500, {"RightArm": {"Shoulder": 65, "Elbow": 90, "Wrist": 90, "Gripper": -50}})
                    ]
                },
                "manual_controls": [
                    ("RightArm", "Base"),
                    ("RightArm", "Shoulder")
                ]
            },
            "Kick": {
                "presets": {
                    "Load": {
                        "RightArm": {"Shoulder": 90, "Elbow": -50, "Wrist": 90, "Gripper": 45},
                    },
                    "Strike": [
                        (200, {"RightArm": {"Shoulder": 70, "Elbow": 30}}),
                        (500, {"RightArm": {"Shoulder": 65, "Elbow": 90, "Wrist": 90, "Gripper": 0}})
                    ]
                },
                "manual_controls": [
                    ("RightArm", "Base")
                ]
            }
        }

        # Create gaze-selectable preset widgets
        # Container for Scroll Controls and List
        self.scroll_container = tk.Frame(self.presets_frame)
        self.scroll_container.pack(fill="both", expand=True, padx=20, pady=5)

        # SCROLL UP BUTTON
        self.scroll_up_btn = PresetWidget(
            self.scroll_container,
            "Scroll Up",
            dwell_time=0.8,
            callback=lambda _: self.scroll_list(-1)
        )
        self.scroll_up_btn.pack(fill="x", pady=2)
        # Manually set height to be smaller
        self.scroll_up_btn.canvas.config(height=50)
        self.scroll_up_btn.rect = self.scroll_up_btn.canvas.find_closest(0, 0)[0] # Hacky re-find or just reuse
        # Actually PresetWidget logic uses self.height, let's just let it be standard or slightly smaller? 
        # The user wanted taller buttons for presets, but scroll buttons might be fine standard.

        # CANVAS AREA
        self.preset_canvas = tk.Canvas(self.scroll_container, bg="gray", highlightthickness=0)
        self.preset_canvas.pack(side="top", fill="both", expand=True, pady=5)
        
        self.scrollbar = tk.Scrollbar(self.scroll_container, orient="vertical", command=self.preset_canvas.yview)
        # self.scrollbar.pack(side="right", fill="y") # Optional: Hide scrollbar if purely gaze driven
        
        self.preset_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.preset_canvas.bind('<Configure>', lambda e: self.preset_canvas.configure(scrollregion=self.preset_canvas.bbox("all")))

        # FRAME INSIDE CANVAS
        self.preset_btn_frame = tk.Frame(self.preset_canvas)
        self.canvas_window_id = self.preset_canvas.create_window((0, 0), window=self.preset_btn_frame, anchor="nw")
        
        self.preset_btn_frame.bind("<Configure>", self.on_frame_configure)
        self.preset_canvas.bind("<Configure>", self.on_canvas_configure)

        # SCROLL DOWN BUTTON
        self.scroll_down_btn = PresetWidget(
            self.scroll_container,
            "Scroll Down",
            dwell_time=0.8,
            callback=lambda _: self.scroll_list(1)
        )
        self.scroll_down_btn.pack(side="bottom", fill="x", pady=2)
        self.scroll_down_btn.canvas.config(height=50)

        # Store widgets for hit testing
        self.category_widgets = [] # For category buttons
        
        row = 0
        col = 0
        
        # 1. Add Categories
        for cat_name in self.categories.keys():
            pw = PresetWidget(
                self.preset_btn_frame,
                cat_name,
                dwell_time=1.5,
                callback=self.show_category_view
            )
            pw.grid(row=row, column=col, padx=10, pady=5, sticky="nsew")
            self.preset_widgets.append(pw) # Add to main hit testing list
            
            col += 1
            if col > 2: # 3 Columns (0, 1, 2)
                col = 0
                row += 1

        # 2. Add Regular Presets
        for preset_name in self.presets.keys():
            pw = PresetWidget(
                self.preset_btn_frame,
                preset_name,
                dwell_time=1.5,
                callback=self.apply_preset
            )
            pw.grid(row=row, column=col, padx=10, pady=5, sticky="nsew")
            self.preset_widgets.append(pw)
            col += 1
            if col > 2:  # 3 columns
                col = 0
                row += 1
        
        # Configure grid weights for even spacing
        for i in range(3):
            self.preset_btn_frame.columnconfigure(i, weight=1)

        # Add scroll buttons to hit testing list?
        # We handle them separately or add to preset_widgets.
        # Adding to preset_widgets means they get checked in the main loop.
        self.preset_widgets.append(self.scroll_up_btn)
        self.preset_widgets.append(self.scroll_down_btn)

        # Pre-create a frame for Category View (Submenu) - Hidden initially
        self.category_frame = tk.Frame(self.main_frame)
        self.category_widgets_list = [] # Store widgets in current category view for hit testing
        self.current_category_presets = {} # Local presets for the active category
        
    def on_frame_configure(self, event):
        """Reset the scroll region to encompass the inner frame"""
        self.preset_canvas.configure(scrollregion=self.preset_canvas.bbox("all"))

    def on_canvas_configure(self, event):
        """Resize the inner frame to match the canvas width"""
        canvas_width = event.width
        self.preset_canvas.itemconfig(self.canvas_window_id, width=canvas_width)

    def scroll_list(self, direction):
        """Scroll manually (1 for down, -1 for up)"""
        self.preset_canvas.yview_scroll(direction, "units")
        
    def show_category_view(self, category_name):
        """Switch to categorical submenu."""
        if category_name not in self.categories:
            return

        print(f"Opening category: {category_name}")
        
        # Hide Main Presets
        self.presets_frame.pack_forget()
        
        # Update State
        self.in_category_mode = True
        self.active_category_name = category_name
        
        # Clear previous category UI
        for widget in self.category_frame.winfo_children():
            widget.destroy()
        self.category_widgets_list = []
        self.current_category_presets = self.categories[category_name]["presets"]
        
        # Show Category Frame
        self.category_frame.pack(side="top", fill="both", expand=True)
        
        # Header
        header_frame = tk.Frame(self.category_frame)
        header_frame.pack(fill="x", pady=5)
        
        tk.Label(header_frame, text=f"Category: {category_name}", font=("Arial", 16, "bold")).pack(side="left", padx=20)
        
        # BACK BUTTON (Gaze Selectable)
        back_btn = PresetWidget(
            header_frame,
            "Back to Main",
            dwell_time=1.0,
            callback=lambda _: self.hide_category_view()
        )
        back_btn.pack(side="right", padx=20)
        self.category_widgets_list.append(back_btn)
        
        # Content Frame (Split: Presets Left, Manual Right)
        content = tk.Frame(self.category_frame)
        content.pack(fill="both", expand=True, padx=10, pady=5)
        
        left_pane = tk.Frame(content)
        left_pane.pack(side="left", fill="both", expand=True)
        
        right_pane = tk.Frame(content)
        right_pane.pack(side="right", fill="both", expand=True)
        
        # 1. Category Presets (Left Side)
        tk.Label(left_pane, text="Actions", font=("Arial", 14)).pack(pady=5)
        for preset_name in self.current_category_presets.keys():
            pw = PresetWidget(
                left_pane,
                preset_name,
                dwell_time=1.5,
                callback=self.apply_category_preset
            )
            pw.pack(fill="x", pady=5, padx=10)
            self.category_widgets_list.append(pw)
            
        # 2. Manual Controls (Right Side)
        tk.Label(right_pane, text="Manual Adjust", font=("Arial", 14)).pack(pady=5)
        manual_actions = self.categories[category_name].get("manual_controls", [])
        
        for arm_name, servo_name in manual_actions:
            # Create a ServoWidget instance
            # We need to find the current angle first
            current_angle = self.servo_angles[arm_name][servo_name]
            
            left_lbl, right_lbl = self.servo_labels.get(servo_name, ("-", "+"))
            sw = ServoWidget(right_pane, arm_name, servo_name, left_label=left_lbl, right_label=right_lbl, callback=self.on_servo_action)
            sw.pack(pady=5, fill="both", expand=True)
            
            # Set limits
            servo_type = ARM_CONFIG.get(arm_name)
            if servo_type and servo_name in SERVO_LIMITS[servo_type]:
                min_limit, max_limit = SERVO_LIMITS[servo_type][servo_name]
                sw.set_limits(min_limit, max_limit)
                
            sw.set_angle(current_angle)
            self.category_widgets_list.append(sw)
            # Note: We append to category_widgets_list, which handles hit testing for both Preset and Servo widgets dynamically
            # because they implement update_gaze/clear_hover similarly?
            # actually ServoWidget has update_gaze(rel_x) and PresetWidget has update_gaze().
            # We need to handle this distinction in update_loop.

    def hide_category_view(self):
        """Return to main preset menu."""
        print("Returning to main menu")
        self.category_frame.pack_forget()
        self.presets_frame.pack(side="top", fill="both", expand=True)
        self.in_category_mode = False
        self.active_category_name = None
        
    def apply_category_preset(self, preset_name):
        """Apply a preset from the current active category."""
        if not self.active_category_name or preset_name not in self.current_category_presets:
            return
            
        preset = self.current_category_presets[preset_name]
        print(f"Applying category preset: {preset_name}")
        
        if isinstance(preset, list):
            self.run_animation(preset, 0)
        else:
            self.interpolate_pose(preset, 1000)

    def apply_preset(self, preset_name):
        """Apply a preset pose or animation to the servos."""
        preset = self.presets.get(preset_name)
        if not preset:
            return

        print(f"Applying preset: {preset_name}")
        
        # Check if it's an animation (list) or static pose (dict)
        if isinstance(preset, list):
            self.run_animation(preset, 0)
        else:
            # For static poses, we can also interpolate for smoothness
            self.interpolate_pose(preset, 1000) # Default 1s for static poses

    def run_animation(self, sequence, step_index):
        """Run a sequence of poses with interpolation."""
        if not self.running or step_index >= len(sequence):
            return
            
        duration, pose = sequence[step_index]
        
        # Use interpolate_pose with a callback for the next step
        self.interpolate_pose(pose, duration, lambda: self.run_animation(sequence, step_index + 1))

    def interpolate_pose(self, target_pose, duration_ms, callback=None):
        """
        Smoothly interpolate from current angles to target_pose over duration_ms.
        
        Args:
            target_pose: dict of {arm: {joint: angle}}
            duration_ms: time in ms to complete the move
            callback: function to call when finished
        """
        if duration_ms <= 0:
            self.apply_pose(target_pose)
            if callback:
                callback()
            return

        # 1. Calculate start and end states for all affected joints
        start_angles = {}
        end_angles = {}
        changes = {}
        
        for arm, joints in target_pose.items():
            for joint, target_angle in joints.items():
                # Get current angle
                current = self.servo_angles[arm][joint]
                
                # Get limits and clamp target
                servo_type = ARM_CONFIG.get(arm)
                min_limit, max_limit = 0, 180
                if servo_type and joint in SERVO_LIMITS[servo_type]:
                    min_limit, max_limit = SERVO_LIMITS[servo_type][joint]
                
                safe_target = max(min_limit, min(max_limit, target_angle))
                
                key = (arm, joint)
                start_angles[key] = current
                end_angles[key] = safe_target
                changes[key] = safe_target - current

        # 2. Setup interpolation loop
        steps = int(duration_ms / 20) # Update every 20ms
        if steps < 1: steps = 1
        
        self._interpolation_step(start_angles, changes, steps, 0, callback)

    def _interpolation_step(self, start_angles, changes, total_steps, current_step, callback):
        """Internal recursive step for interpolation."""
        if not self.running:
            return

        current_step += 1
        progress = current_step / total_steps
        
        # Use Linear Interpolation to avoid "slow down" at the end which causes stiction
        ease = progress 
        
        # Apply intermediate angles
        for key, start_angle in start_angles.items():
            arm, joint = key
            total_change = changes[key]
            
            new_angle = start_angle + (total_change * ease)
            
            int_angle = int(new_angle)
            
            # Only update if changed significantly to reduce bus traffic
            if int_angle != int(self.servo_angles[arm][joint]):
                self.servo_angles[arm][joint] = int_angle
                
                # Send to hardware
                if self.servo:
                    try:
                        channel = SERVO_MAP[arm][joint]
                        self.servo.move_servo_position(channel, int_angle)
                    except Exception as e:
                        print(f"Error moving {arm} {joint}: {e}")
                
                # Update widgets
                for widget in self.widgets:
                    if widget.arm_name == arm and widget.servo_name == joint:
                        widget.set_angle(int_angle)
                        break

        if current_step < total_steps:
            self.root.after(20, lambda: self._interpolation_step(start_angles, changes, total_steps, current_step, callback))
        else:
            # FORCE FINAL UPDATE
            # Ensure final values are set exactly and SENT to hardware
            for key, end_angle in start_angles.items(): # Iterate keys
                arm, joint = key
                target = start_angles[key] + changes[key] # Re-calculate exact target
                int_target = int(target)
                
                self.servo_angles[arm][joint] = int_target
                
                # Force send to hardware to ensure we reach the goal
                if self.servo:
                    try:
                        channel = SERVO_MAP[arm][joint]
                        self.servo.move_servo_position(channel, int_target)
                    except Exception as e:
                        print(f"Error moving {arm} {joint}: {e}")
                
                # Final widget update
                for widget in self.widgets:
                    if widget.arm_name == arm and widget.servo_name == joint:
                        widget.set_angle(int_target)
                        break
            
            if callback:
                callback()

    def apply_pose(self, pose):
        """Apply a single static pose dictionary immediately (no interpolation)."""
        for arm, joints in pose.items():
            for joint, angle in joints.items():
                # Get limits for this specific servo
                servo_type = ARM_CONFIG.get(arm)
                min_limit, max_limit = 0, 180 # Default
                if servo_type and joint in SERVO_LIMITS[servo_type]:
                    min_limit, max_limit = SERVO_LIMITS[servo_type][joint]

                # Clamp angle
                safe_angle = max(min_limit, min(max_limit, angle))
                
                # Update internal state
                self.servo_angles[arm][joint] = safe_angle

                # Send to hardware
                if self.servo:
                    try:
                        channel = SERVO_MAP[arm][joint]
                        self.servo.move_servo_position(channel, safe_angle)
                    except Exception as e:
                        print(f"Error moving {arm} {joint}: {e}")
            
            # Update all widgets to reflect new preset angles
            for widget in self.widgets:
                if widget.arm_name in pose and widget.servo_name in pose[widget.arm_name]:
                    # This widget was affected by the preset
                    new_angle = self.servo_angles[widget.arm_name][widget.servo_name]
                    widget.set_angle(new_angle)

    def quit_app(self, event=None):
        """Cleanly exit the application."""
        if self._quitting:
            return
        self._quitting = True
        
        print("Quitting application...")
        self.running = False # Stop update loops
        
        # Return to startup pose if defined
        if STARTUP_POSE:
            print("Returning to startup pose...")
            try:
                # BLOCKING INTERPOLATION LOOP
                # We need to manually interpolate because the main loop is ending.
                # 1. Calculate start and end states
                start_angles = {}
                changes = {}
                duration_ms = 1500 # 1.5 seconds for smooth return
                steps = int(duration_ms / 20) # 50Hz update
                
                for arm, joints in STARTUP_POSE.items():
                    if arm not in self.servo_angles: continue
                    
                    for joint, target_angle in joints.items():
                        if joint not in self.servo_angles[arm]: continue
                        
                        current = self.servo_angles[arm][joint]
                        start_angles[(arm, joint)] = current
                        
                        # Clamp target
                        servo_type = ARM_CONFIG.get(arm)
                        min_limit, max_limit = 0, 180
                        if servo_type and joint in SERVO_LIMITS[servo_type]:
                            min_limit, max_limit = SERVO_LIMITS[servo_type][joint]
                        safe_target = max(min_limit, min(max_limit, target_angle))
                        
                        changes[(arm, joint)] = safe_target - current

                # 2. Run the loop
                for i in range(steps + 1):
                    progress = i / steps
                    # Ease function (optional, linear is fine for safety)
                    ease = progress
                    
                    for key, start_angle in start_angles.items():
                        arm, joint = key
                        total_change = changes[key]
                        new_angle = int(start_angle + (total_change * ease))
                        
                        # Send to hardware directly
                        if self.servo:
                            try:
                                channel = SERVO_MAP[arm][joint]
                                self.servo.move_servo_position(channel, new_angle)
                            except:
                                pass
                                
                    time.sleep(0.02) # 20ms
                
                print("Return to startup pose complete.")
                
            except Exception as e:
                print(f"Error returning to startup pose: {e}")

        self.cleanup_servos()
        
        # Clear LED meter
        self.led_meter.clear()
        
        if hasattr(self, 'headset'):
            self.headset.stop()
        if hasattr(self, 'eye_tracker') and self.eye_tracker:
            self.eye_tracker.stop()
            
        self.root.quit()
        self.root.destroy()

    def cleanup_servos(self):
        """Stop all servo PWM signals to prevent erratic behavior."""
        if self.servo:
            print("Cleaning up servos...")
            try:
                # 1. Explicitly stop all used channels first (if possible)
                # This is a safeguard in case sleep() misses some
                for arm in SERVO_MAP:
                    for joint, channel in SERVO_MAP[arm].items():
                        try:
                            # Setting pulse to 0 usually stops the PWM
                            # self.servo.move_servo_position(channel, 0) # This moves to 0 degrees, NOT OFF
                            # We need to stop the signal. 
                            # If the library doesn't expose 'stop_channel', we rely on sleep.
                            pass 
                        except:
                            pass
                            
                # 2. Put PCA9685 to sleep - stops all PWM
                self.servo.sleep()  
                time.sleep(0.1) # Wait for I2C to finish
                print("Servos put to sleep (PWM stopped).")
                
            except Exception as e:
                print(f"Error during cleanup: {e}")
            finally:
                self.servo = None # Prevent multiple cleanups

    def __del__(self):
        self.cleanup_servos()
        try:
            self.led_meter.clear()
        except:
            pass
        if hasattr(self, 'headset'):
            try:
                self.headset.stop()
            except:
                pass
        if hasattr(self, 'eye_tracker') and self.eye_tracker:
            try:
                self.eye_tracker.stop()
            except:
                pass

def on_closing(app, root):
    """Handle window close."""
    app.quit_app()

if __name__ == "__main__":
    root = tk.Tk()
    app = ServoGUI(root)
    
    # Register cleanup
    atexit.register(app.cleanup_servos)
    
    # Handle window close button
    root.protocol("WM_DELETE_WINDOW", lambda: on_closing(app, root))
    
    # Handle Ctrl+C and SIGTERM
    def signal_handler(sig, frame):
        on_closing(app, root)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    root.mainloop()