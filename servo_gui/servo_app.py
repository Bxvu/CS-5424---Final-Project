#!/usr/bin/env python3
import tkinter as tk
from servo_widget import ServoWidget
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
        "Shoulder": 0,
        "Elbow": 1,
        "Wrist": 2,
        "Gripper": 3
    },
    "RightArm": {
        "Shoulder": 4,
        "Elbow": 5,
        "Wrist": 6,
        "Gripper": 7
    }
}

class ServoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Robot Arm Servo Control")
        self.root.geometry("600x600")
        
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

        # State tracking for servo angles (default 90)
        self.servo_angles = {}
        for arm in ["LeftArm", "RightArm"]:
            self.servo_angles[arm] = {}
            for joint in ["Shoulder", "Elbow", "Wrist", "Gripper"]:
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
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Split into two sides
        self.left_frame = tk.Frame(self.main_frame, borderwidth=2, relief="sunken")
        self.left_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        self.right_frame = tk.Frame(self.main_frame, borderwidth=2, relief="sunken")
        self.right_frame.pack(side="right", fill="both", expand=True, padx=5)
        
        # Headers
        tk.Label(self.left_frame, text="Left Arm", font=("Arial", 14, "bold")).pack(pady=10)
        tk.Label(self.right_frame, text="Right Arm", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Servo Widgets Storage
        self.widgets = []
        
        # Create Widgets
        self.create_arm_widgets(self.left_frame, "LeftArm", ["Shoulder", "Elbow", "Wrist", "Gripper"])
        self.create_arm_widgets(self.right_frame, "RightArm", ["Shoulder", "Elbow", "Wrist", "Gripper"])
        
        # Start Dwell Check Loop
        self.check_dwell_loop()
        
    def create_arm_widgets(self, parent, arm_name, servo_names):
        for name in servo_names:
            widget = ServoWidget(parent, arm_name, name, callback=self.on_servo_action)
            widget.pack(pady=5)
            self.widgets.append(widget)
            
    def on_servo_action(self, arm, servo_name, action):
        # Determine direction
        change = 2 if action == 'right' else -2
        
        # Update angle
        current_angle = self.servo_angles[arm][servo_name]
        new_angle = current_angle + change
        
        # Clamp between 0 and 180
        new_angle = max(0, min(180, new_angle))
        
        if new_angle != current_angle:
            self.servo_angles[arm][servo_name] = new_angle
            print(f"Moving {arm} {servo_name} to {new_angle} degrees")
            
            # Send to hardware
            if self.servo:
                try:
                    channel = SERVO_MAP[arm][servo_name]
                    self.servo.move_servo_position(channel, new_angle)
                except Exception as e:
                    print(f"Error moving servo: {e}")
        
    def check_dwell_loop(self):
        for widget in self.widgets:
            widget.check_dwell()
        self.root.after(50, self.check_dwell_loop) # Check every 50ms for smoother response

if __name__ == "__main__":
    root = tk.Tk()
    app = ServoGUI(root)
    root.mainloop()
