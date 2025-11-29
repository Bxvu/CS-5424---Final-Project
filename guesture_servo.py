import cv2
import mediapipe as mp
import json
import time
import os

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

# Servo channel mapping based on finger count
SERVO_CHANNELS = {
    1: {"name": "base", "channel": 0},
    2: {"name": "shoulder", "channel": 1},
    3: {"name": "elbow", "channel": 2},
    4: {"name": "wrist", "channel": 3},
    5: {"name": "gripper", "channel": 4}
}

# File to share active channel with servo_control.py
SHARED_FILE = "active_channel.json"

def count_fingers(hand_landmarks):
    """
    Count the number of extended fingers based on hand landmarks.
    Returns the count of fingers up (0-5).
    """
    # Tip landmarks for each finger
    finger_tips = [
        mp_hands.HandLandmark.THUMB_TIP,
        mp_hands.HandLandmark.INDEX_FINGER_TIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
        mp_hands.HandLandmark.RING_FINGER_TIP,
        mp_hands.HandLandmark.PINKY_TIP
    ]
    
    # PIP (middle joint) landmarks for comparison
    finger_pips = [
        mp_hands.HandLandmark.THUMB_IP,
        mp_hands.HandLandmark.INDEX_FINGER_PIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_PIP,
        mp_hands.HandLandmark.RING_FINGER_PIP,
        mp_hands.HandLandmark.PINKY_PIP
    ]
    
    count = 0
    
    # Check each finger
    for i in range(5):
        tip = hand_landmarks.landmark[finger_tips[i]]
        pip = hand_landmarks.landmark[finger_pips[i]]
        
        # For thumb, check x-coordinate (left/right)
        if i == 0:
            # Get wrist and thumb positions
            wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
            # Thumb is extended if tip is farther from wrist than pip
            if abs(tip.x - wrist.x) > abs(pip.x - wrist.x):
                count += 1
        # For other fingers, check y-coordinate (up/down)
        else:
            # Finger is extended if tip is above pip (lower y value = higher on screen)
            if tip.y < pip.y:
                count += 1
    
    return count

def update_active_channel(finger_count):
    """
    Write the active channel to a shared JSON file.
    """
    if finger_count in SERVO_CHANNELS:
        data = {
            "channel": SERVO_CHANNELS[finger_count]["channel"],
            "name": SERVO_CHANNELS[finger_count]["name"],
            "finger_count": finger_count,
            "timestamp": time.time()
        }
        
        with open(SHARED_FILE, 'w') as f:
            json.dump(data, f)
        
        return SERVO_CHANNELS[finger_count]
    return None

def main():
    print("=== GESTURE SERVO CONTROL ===")
    print("Show fingers to select servo channel:")
    print("  1 finger  = Base (Channel 0)")
    print("  2 fingers = Shoulder (Channel 1)")
    print("  3 fingers = Elbow (Channel 2)")
    print("  4 fingers = Wrist (Channel 3)")
    print("  5 fingers = Gripper (Channel 4)")
    print("Press 'q' to quit")
    print("=" * 30)
    
    # Initialize video capture
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return
    
    current_channel = None
    last_update_time = 0
    UPDATE_INTERVAL = 0.5  # Update channel every 0.5 seconds to avoid rapid switching
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Could not read frame.")
                break
            
            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process the frame
            results = hands.process(rgb_frame)
            
            finger_count = 0
            
            # Draw hand landmarks and count fingers
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Draw landmarks
                    mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS
                    )
                    
                    # Count fingers
                    finger_count = count_fingers(hand_landmarks)
            
            # Update active channel if enough time has passed
            current_time = time.time()
            if current_time - last_update_time > UPDATE_INTERVAL:
                if finger_count > 0:
                    servo_info = update_active_channel(finger_count)
                    if servo_info:
                        current_channel = servo_info
                        last_update_time = current_time
            
            # Display information on frame
            cv2.putText(frame, f"Fingers: {finger_count}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            if current_channel:
                cv2.putText(frame, f"Active: {current_channel['name']} (Ch {current_channel['channel']})",
                           (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            else:
                cv2.putText(frame, "No channel selected", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Show the frame
            cv2.imshow('Gesture Servo Control', frame)
            
            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    except KeyboardInterrupt:
        print("\nStopping gesture control...")
    
    finally:
        # Cleanup
        cap.release()
        cv2.destroyAllWindows()
        hands.close()
        print("Camera released and windows closed.")

if __name__ == "__main__":
    main()

