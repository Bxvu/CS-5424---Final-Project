#!/usr/bin/env python3
import tkinter as tk
from servo_widget import ServoWidget
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
                self.servo.restart()
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
        
        # Columns Frame
        self.columns_frame = tk.Frame(self.main_frame)
        self.columns_frame.pack(side="top", fill="both", expand=True)

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
        
        # Create Widgets
        self.create_arm_widgets(self.left_frame, "LeftArm", ["Base", "Shoulder", "Elbow", "Wrist", "Gripper"])
        self.create_arm_widgets(self.right_frame, "RightArm", ["Base", "Shoulder", "Elbow", "Wrist", "Gripper"])
        
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
        
        # Clamp between 0 and 180
        new_angle = max(0, min(180, new_angle))
        
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

            # Manual Hit Testing for Widgets
            for widget in self.widgets:
                # Get widget absolute coordinates
                wx = widget.winfo_rootx()
                wy = widget.winfo_rooty()
                ww = widget.winfo_width()
                wh = widget.winfo_height()
                
                # Check intersection
                if wx <= gaze_x <= wx + ww and wy <= gaze_y <= wy + wh:
                    # Calculate relative x
                    rel_x = gaze_x - wx
                    widget.update_gaze(rel_x)
                else:
                    widget.clear_hover()
        
        # If no eye tracker, we rely on mouse events which are handled by widget bindings
        
        for widget in self.widgets:
            widget.process_frame(attention)
        self.root.after(50, self.update_loop) # Check every 50ms

    def __del__(self):
        if hasattr(self, 'headset'):
            self.headset.stop()
        if hasattr(self, 'eye_tracker') and self.eye_tracker:
            self.eye_tracker.stop()

if __name__ == "__main__":
    root = tk.Tk()
    app = ServoGUI(root)
    root.mainloop()
