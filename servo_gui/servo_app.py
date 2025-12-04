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
try:
    import pi_servo_hat
    HAS_HARDWARE = True
except ImportError:
    print("WARNING: pi_servo_hat not found. Running in simulation mode.")
    HAS_HARDWARE = False

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
        "Shoulder": (20, 110),
        "Elbow": (-50, 130),
        "Wrist": (-50, 130),
        "Gripper": (-50, 45)
    },
    "Orange": {
        "Base": (-50, 130),
        "Shoulder": (10, 60),
        "Elbow": (-50, 130),
        "Wrist": (-50, 130), # 55 middle
        "Gripper": (-20, 73)
    }
}

ARM_CONFIG = {
    "LeftArm": "Orange",
    "RightArm": "Black"
}

class ServoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Robot Arm Servo Control")
        # self.root.geometry("600x600")
        self.root.attributes('-fullscreen', True)
        self.root.bind("<Escape>", lambda e: self.root.attributes("-fullscreen", False)) # Allow exit from fullscreen
        
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
                # Initialize hardware to 90 if possible
                if self.servo:
                    try:
                        channel = SERVO_MAP[arm][joint]
                        self.servo.move_servo_position(channel, 90)
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

        # Attention Display
        self.attention_label = tk.Label(self.info_frame, text="Attention: 0", font=("Arial", 12))
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
        
        # Columns Frame
        self.columns_frame = tk.Frame(self.main_frame)
        # self.columns_frame.pack(side="top", fill="both", expand=True) # Hidden by default

        # Split into two sides
        self.left_frame = tk.Frame(self.columns_frame, borderwidth=0, relief="sunken")
        self.left_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        self.right_frame = tk.Frame(self.columns_frame, borderwidth=0, relief="sunken")
        self.right_frame.pack(side="right", fill="both", expand=True, padx=5)
        
        # Headers
        tk.Label(self.left_frame, text="Left Arm", font=("Arial", 14, "bold")).pack(pady=5)
        tk.Label(self.right_frame, text="Right Arm", font=("Arial", 14, "bold")).pack(pady=5)

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
            widget = ServoWidget(parent, arm_name, name, callback=self.on_servo_action)
            widget.pack(pady=5, fill="both", expand=True)
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
        
    def update_loop(self):
        # Get current attention level
        attention = self.headset.get_attention()
        self.attention_label.config(text=f"Attention: {attention}")
        
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
                # Hit testing for Preset Widgets
                for pw in self.preset_widgets:
                    pwx = pw.winfo_rootx()
                    pwy = pw.winfo_rooty()
                    pww = pw.winfo_width()
                    pwh = pw.winfo_height()
                    
                    if pwx <= gaze_x <= pwx + pww and pwy <= gaze_y <= pwy + pwh:
                        pw.update_gaze()
                    else:
                        pw.clear_hover()
        
        # Process frames for all relevant widgets
        self.toggle_widget.process_frame(attention)
        
        if not self.in_preset_mode:
            for widget in self.widgets:
                widget.process_frame(attention)
        else:
            for pw in self.preset_widgets:
                pw.process_frame(attention)
                
        self.root.after(50, self.update_loop) # Check every 50ms

    def toggle_mode(self):
        """Toggle between fine-grained control and preset poses."""
        if not self.in_preset_mode:
            # Switch to Presets mode
            self.columns_frame.pack_forget()
            self.presets_frame.pack(side="top", fill="both", expand=True)
            self.in_preset_mode = True
            self.toggle_widget.set_state(True)
        else:
            # Switch to Manual mode
            self.presets_frame.pack_forget()
            self.columns_frame.pack(side="top", fill="both", expand=True)
            self.in_preset_mode = False
            self.toggle_widget.set_state(False)

    def create_preset_ui(self):
        """Create the preset poses UI with gaze-selectable widgets."""
        # Header
        tk.Label(self.presets_frame, text="Preset Poses (Look to Select)", font=("Arial", 16, "bold")).pack(pady=10)

        # Preset definitions: name -> {arm: {joint: angle}}
        self.presets = {
            "Home Position": {
                "LeftArm": {"Base": 90, "Shoulder": 90, "Elbow": 90, "Wrist": 90, "Gripper": 90},
                "RightArm": {"Base": 90, "Shoulder": 90, "Elbow": 90, "Wrist": 90, "Gripper": 90},
            },
            "Left Gripper Open": {
                "LeftArm": {"Gripper": 0},
            },
            "Left Gripper Closed": {
                "LeftArm": {"Gripper": 180},
            },
            "Right Gripper Open": {
                "RightArm": {"Gripper": 0},
            },
            "Right Gripper Closed": {
                "RightArm": {"Gripper": 180},
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
            "Wave Position": {
                "RightArm": {"Base": 90, "Shoulder": 45, "Elbow": 135, "Wrist": 90, "Gripper": 90},
            },
            "Reach Forward (Both)": {
                "LeftArm": {"Shoulder": 45, "Elbow": 0},
                "RightArm": {"Shoulder": 45, "Elbow": 0},
            },
        }

        # Create gaze-selectable preset widgets
        btn_frame = tk.Frame(self.presets_frame)
        btn_frame.pack(fill="both", expand=True, padx=20, pady=10)

        row = 0
        col = 0
        for preset_name in self.presets.keys():
            pw = PresetWidget(
                btn_frame,
                preset_name,
                dwell_time=1.5,
                callback=self.apply_preset
            )
            pw.grid(row=row, column=col, padx=10, pady=5, sticky="nsew")
            self.preset_widgets.append(pw)
            col += 1
            if col > 1:  # 2 columns
                col = 0
                row += 1
        
        # Configure grid weights for even spacing
        for i in range(2):
            btn_frame.columnconfigure(i, weight=1)

    def apply_preset(self, preset_name):
        """Apply a preset pose to the servos."""
        preset = self.presets.get(preset_name, {})
        print(f"Applying preset: {preset_name}")

        for arm, joints in preset.items():
            for joint, angle in joints.items():
                # Get limits for this specific servo
                servo_type = ARM_CONFIG.get(arm)
                min_limit, max_limit = 0, 180 # Default
                if servo_type and joint in SERVO_LIMITS[servo_type]:
                    min_limit, max_limit = SERVO_LIMITS[servo_type][joint]

                # Clamp angle
                safe_angle = max(min_limit, min(max_limit, angle))
                if safe_angle != angle:
                    print(f"Warning: Preset {preset_name} for {arm} {joint} requested {angle}, clamped to {safe_angle}")
                
                # Update internal state
                self.servo_angles[arm][joint] = safe_angle

                # Send to hardware
                if self.servo:
                    try:
                        channel = SERVO_MAP[arm][joint]
                        self.servo.move_servo_position(channel, safe_angle)
                    except Exception as e:
                        print(f"Error moving {arm} {joint}: {e}")

    def cleanup_servos(self):
        """Stop all servo PWM signals to prevent erratic behavior."""
        if self.servo:
            print("Cleaning up servos...")
            try:
                self.servo.sleep()  # Put PCA9685 to sleep - stops all PWM
                print("Servos put to sleep (PWM stopped).")
            except Exception as e:
                print(f"Error during cleanup: {e}")
            finally:
                self.servo = None # Prevent multiple cleanups

    def __del__(self):
        self.cleanup_servos()
        if hasattr(self, 'headset'):
            self.headset.stop()
        if hasattr(self, 'eye_tracker') and self.eye_tracker:
            self.eye_tracker.stop()

def on_closing(app, root):
    """Handle window close."""
    app.cleanup_servos()
    if hasattr(app, 'headset'):
        app.headset.stop()
    if hasattr(app, 'eye_tracker') and app.eye_tracker:
        app.eye_tracker.stop()
    root.destroy()

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
