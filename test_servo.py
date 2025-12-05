import pi_servo_hat
import time
import sys
import os
import signal
import atexit

# --- CONFIGURATION ---
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

# Initialize Hat
servo = pi_servo_hat.PiServoHat()

# Ensure clean startup: sleep first, then restart
try:
    servo.sleep()  # Stop any existing PWM
    time.sleep(0.1)  # Brief pause
except:
    pass
servo.restart()  # Re-initialize cleanly
time.sleep(0.2)  # Let PWM stabilize

def cleanup():
    """Stop all servo PWM signals on exit to prevent erratic behavior."""
    print("\nCleaning up servos...")
    try:
        # Put PCA9685 into sleep mode - this stops all PWM outputs
        servo.sleep()
        print("Servos put to sleep (PWM stopped).")
    except Exception as e:
        print(f"Error during cleanup: {e}")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    cleanup()
    sys.exit(0)

# Register cleanup handlers
atexit.register(cleanup)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def move_servo(channel, angle, arm_name, joint_name):
    """Safely move servo to angle with limit checking."""
    name = f"{arm_name} {joint_name}"
    
    # Get limits for this specific servo
    servo_type = ARM_CONFIG.get(arm_name)
    if servo_type and joint_name in SERVO_LIMITS[servo_type]:
        min_limit, max_limit = SERVO_LIMITS[servo_type][joint_name]
    else:
        # Fallback to global safe limits if not found
        min_limit, max_limit = -180, 180
        
    # Clamp angle
    target_angle = angle
    if target_angle < min_limit:
        target_angle = min_limit
        print(f"Warning: {name} requested {angle}°, clamped to MIN {min_limit}°")
    elif target_angle > max_limit:
        target_angle = max_limit
        print(f"Warning: {name} requested {angle}°, clamped to MAX {max_limit}°")
    
    print(f"Moving {name} (Ch {channel}) to {target_angle}°")
    servo.move_servo_position(channel, target_angle)

def print_header():
    clear_screen()
    print("========================================")
    print("      SERVO DIAGNOSTIC CONTROLLER       ")
    print("========================================")

def manual_mode():
    while True:
        print_header()
        print("--- MANUAL FINE-GRAINED CONTROL ---")
        print("Select Arm:")
        print("  1. Left Arm")
        print("  2. Right Arm")
        print("  b. Back to Main Menu")
        print("-----------------------------------")
        
        arm_choice = input("Select Arm > ").strip().lower()
        
        if arm_choice == 'b':
            break
        
        arm = None
        if arm_choice == '1':
            arm = "LeftArm"
        elif arm_choice == '2':
            arm = "RightArm"
        else:
            continue
        
        # Select joint
        while True:
            print_header()
            print(f"--- {arm} - Select Joint ---")
            print("  1. Base")
            print("  2. Shoulder")
            print("  3. Elbow")
            print("  4. Wrist")
            print("  5. Gripper")
            print("  b. Back to Arm Selection")
            print("----------------------------")
            
            joint_choice = input("Select Joint > ").strip().lower()
            
            if joint_choice == 'b':
                break
            
            joint = None
            if joint_choice == '1':
                joint = "Base"
            elif joint_choice == '2':
                joint = "Shoulder"
            elif joint_choice == '3':
                joint = "Elbow"
            elif joint_choice == '4':
                joint = "Wrist"
            elif joint_choice == '5':
                joint = "Gripper"
            else:
                continue
            
            channel = SERVO_MAP[arm][joint]
            name = f"{arm} {joint}"
            
            print(f"\nSelected: {name} (Ch {channel})")
            print("Enter angle (0-180) or 'b' to go back.")
            
            while True:
                val = input(f"{name} Angle > ").strip().lower()
                if val == 'b':
                    break
                
                try:
                    angle = float(val)
                    move_servo(channel, angle, arm, joint)
                except ValueError:
                    print("Invalid number.")

def preset_mode():
    while True:
        print_header()
        print("--- PRESET POSES ---")
        print("1. Home Position (All 90°)")
        print("2. Left Gripper: OPEN (0°)")
        print("3. Left Gripper: CLOSED (180°)")
        print("4. Right Gripper: OPEN (0°)")
        print("5. Right Gripper: CLOSED (180°)")
        print("6. Left Elbow: EXTENDED (0°)")
        print("7. Left Elbow: BENT (90°)")
        print("8. Right Elbow: EXTENDED (0°)")
        print("9. Right Elbow: BENT (90°)")
        print("b. Back to Main Menu")
        print("--------------------")
        
        choice = input("Select Preset > ").strip().lower()
        
        if choice == 'b':
            break
        elif choice == '1':
            # Home position - all servos to 90
            for arm in SERVO_MAP:
                for joint, channel in SERVO_MAP[arm].items():
                    move_servo(channel, 90, arm, joint)
                    time.sleep(0.1)
        elif choice == '2':
            move_servo(SERVO_MAP["LeftArm"]["Gripper"], 0, "LeftArm", "Gripper")
        elif choice == '3':
            move_servo(SERVO_MAP["LeftArm"]["Gripper"], 180, "LeftArm", "Gripper")
        elif choice == '4':
            move_servo(SERVO_MAP["RightArm"]["Gripper"], 0, "RightArm", "Gripper")
        elif choice == '5':
            move_servo(SERVO_MAP["RightArm"]["Gripper"], 180, "RightArm", "Gripper")
        elif choice == '6':
            move_servo(SERVO_MAP["LeftArm"]["Elbow"], 0, "LeftArm", "Elbow")
        elif choice == '7':
            move_servo(SERVO_MAP["LeftArm"]["Elbow"], 90, "LeftArm", "Elbow")
        elif choice == '8':
            move_servo(SERVO_MAP["RightArm"]["Elbow"], 0, "RightArm", "Elbow")
        elif choice == '9':
            move_servo(SERVO_MAP["RightArm"]["Elbow"], 90, "RightArm", "Elbow")
        
        time.sleep(0.3)

def sweep_test():
    print_header()
    print("--- SWEEP TEST ---")
    print("Select Arm:")
    print("  1. Left Arm")
    print("  2. Right Arm")
    print("  b. Back")
    
    arm_choice = input("Select Arm > ").strip().lower()
    
    if arm_choice == 'b':
        return
    
    arm = None
    if arm_choice == '1':
        arm = "LeftArm"
    elif arm_choice == '2':
        arm = "RightArm"
    else:
        return
    
    print(f"\nRunning sweep on {arm} Elbow... Press Ctrl+C to stop.")
    channel = SERVO_MAP[arm]["Elbow"]
    
    try:
        while True:
            for i in range(0, 180, 5):
                move_servo(channel, i, arm, "Elbow")
                time.sleep(0.05)
            for i in range(180, 0, -5):
                move_servo(channel, i, arm, "Elbow")
                time.sleep(0.05)
    except KeyboardInterrupt:
        pass

def main():
    while True:
        print_header()
        print("1. Manual Control (Fine-grained)")
        print("2. Preset Poses")
        print("3. Run Sweep Test")
        print("q. Quit")
        print("--------------------------------")
        
        choice = input("Select Mode > ").strip().lower()
        
        if choice == '1':
            manual_mode()
        elif choice == '2':
            preset_mode()
        elif choice == '3':
            sweep_test()
        elif choice == 'q':
            print("Exiting.")
            cleanup()
            sys.exit(0)

if __name__ == "__main__":
    main()
