import pi_servo_hat
import time

# Configuration
SERVO_CH = 0      # Channel 0
SERVO_MIN = 0     # Minimum angle
SERVO_MAX = 180   # Maximum angle

def test_servo():
    # Initialize Servo Hat
    print("Initializing PiServoHat...")
    servo = pi_servo_hat.PiServoHat()
    servo.restart()
    
    print(f"Testing Servo on Channel {SERVO_CH}")
    print(f"Sweeping from {SERVO_MIN} to {SERVO_MAX} degrees...")

    try:
        while True:
            # Sweep up
            print("Moving to MAX...")
            for angle in range(SERVO_MIN, SERVO_MAX + 1, 5):
                servo.move_servo_position(SERVO_CH, angle)
                time.sleep(0.05)
            
            time.sleep(0.5)

            # Sweep down
            print("Moving to MIN...")
            for angle in range(SERVO_MAX, SERVO_MIN - 1, -5):
                servo.move_servo_position(SERVO_CH, angle)
                time.sleep(0.05)
            
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nTest stopped by user.")

if __name__ == "__main__":
    test_servo()
