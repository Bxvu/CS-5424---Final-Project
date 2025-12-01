import cv2
import mediapipe as mp
import numpy as np
import screeninfo

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh

# Eye landmark indices for MediaPipe Face Mesh
LEFT_EYE = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
RIGHT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
LEFT_IRIS = [474, 475, 476, 477]
RIGHT_IRIS = [469, 470, 471, 472]

def get_iris_center(landmarks, iris_indices, frame_width, frame_height):
    """Calculate the center point of an iris (pupil position)."""
    x_coords = [landmarks[i].x * frame_width for i in iris_indices]
    y_coords = [landmarks[i].y * frame_height for i in iris_indices]
    center_x = int(sum(x_coords) / len(x_coords))
    center_y = int(sum(y_coords) / len(y_coords))
    return (center_x, center_y)

def get_face_center(landmarks, frame_width, frame_height):
    """Calculate the center point of the face."""
    # Use nose tip as face center reference
    nose_tip = landmarks[1]
    center_x = int(nose_tip.x * frame_width)
    center_y = int(nose_tip.y * frame_height)
    return (center_x, center_y)

def get_eye_bounds(landmarks, eye_indices, frame_width, frame_height):
    """Get the bounding box of an eye."""
    x_coords = [landmarks[i].x * frame_width for i in eye_indices]
    y_coords = [landmarks[i].y * frame_height for i in eye_indices]
    return min(x_coords), max(x_coords), min(y_coords), max(y_coords)

def map_gaze_to_screen(pupil_pos, eye_bounds, face_center, screen_width, screen_height, frame_width, frame_height):
    """Map pupil position and head position to screen coordinates."""
    min_x, max_x, min_y, max_y = eye_bounds
    
    # Calculate relative position within eye (0 to 1)
    eye_width = max_x - min_x
    eye_height = max_y - min_y
    
    if eye_width == 0 or eye_height == 0:
        return screen_width // 2, screen_height // 2
    
    rel_x = (pupil_pos[0] - min_x) / eye_width
    rel_y = (pupil_pos[1] - min_y) / eye_height
    
    # INVERT Y-AXIS
    rel_y = 1 - rel_y
    
    # Add head position influence
    # Normalize face center to 0-1 range
    head_x = face_center[0] / frame_width
    head_y = face_center[1] / frame_height
    
    # Combine eye gaze and head position
    # Head movement has significant influence
    combined_x = rel_x * 0.4 + head_x * 0.6
    combined_y = rel_y * 0.4 + head_y * 0.6
    
    # Add sensitivity multiplier
    sensitivity_x = 2.5
    sensitivity_y = 2.5
    
    # Center and scale with extended range
    combined_x = (combined_x - 0.5) * sensitivity_x + 0.5
    combined_y = (combined_y - 0.5) * sensitivity_y + 0.5
    
    # Clamp to valid range
    combined_x = max(0, min(1, combined_x))
    combined_y = max(0, min(1, combined_y))
    
    # Map to screen coordinates
    screen_x = int(combined_x * screen_width)
    screen_y = int(combined_y * screen_height)
    
    return screen_x, screen_y

def draw_control_panel(canvas, screen_width, screen_height):
    """Draw the control panel with rectangles and +/- buttons."""
    mid_x = screen_width // 2
    
    # Draw center divider line
    cv2.line(canvas, (mid_x, 0), (mid_x, screen_height), (100, 100, 100), 3)
    
    # Labels for the rectangles
    left_labels = ["Shoulder", "Elbow", "Wrist", "Hand", "Fingers"]
    right_labels = ["Shoulder", "Elbow", "Wrist", "Hand", "Fingers"]
    
    # Calculate rectangle dimensions
    rect_height = screen_height // 6
    rect_width = (screen_width // 2) - 80
    margin = 40
    
    for i, (left_label, right_label) in enumerate(zip(left_labels, right_labels)):
        y_pos = margin + i * (rect_height + 20)
        
        # LEFT ARM RECTANGLES
        left_x = margin
        # Draw main rectangle
        cv2.rectangle(canvas, (left_x, y_pos), (left_x + rect_width, y_pos + rect_height), 
                     (80, 80, 80), 2)
        
        # Draw center divider
        left_mid = left_x + rect_width // 2
        cv2.line(canvas, (left_mid, y_pos), (left_mid, y_pos + rect_height), (80, 80, 80), 2)
        
        # Draw minus button (left half)
        cv2.putText(canvas, "-", (left_x + rect_width // 4 - 15, y_pos + rect_height // 2 + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
        
        # Draw plus button (right half)
        cv2.putText(canvas, "+", (left_mid + rect_width // 4 - 15, y_pos + rect_height // 2 + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
        
        # Draw label
        cv2.putText(canvas, f"L {left_label}", (left_x + 10, y_pos - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # RIGHT ARM RECTANGLES
        right_x = mid_x + margin
        # Draw main rectangle
        cv2.rectangle(canvas, (right_x, y_pos), (right_x + rect_width, y_pos + rect_height), 
                     (80, 80, 80), 2)
        
        # Draw center divider
        right_mid = right_x + rect_width // 2
        cv2.line(canvas, (right_mid, y_pos), (right_mid, y_pos + rect_height), (80, 80, 80), 2)
        
        # Draw minus button (left half)
        cv2.putText(canvas, "-", (right_x + rect_width // 4 - 15, y_pos + rect_height // 2 + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
        
        # Draw plus button (right half)
        cv2.putText(canvas, "+", (right_mid + rect_width // 4 - 15, y_pos + rect_height // 2 + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
        
        # Draw label
        cv2.putText(canvas, f"R {right_label}", (right_x + 10, y_pos - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

def main():
    # Get screen dimensions
    try:
        screen = screeninfo.get_monitors()[0]
        screen_width = screen.width
        screen_height = screen.height
    except:
        # Fallback if screeninfo doesn't work
        screen_width = 1920
        screen_height = 1080
    
    print(f"Screen resolution: {screen_width}x{screen_height}")
    
    # Initialize webcam
    cap = cv2.VideoCapture(0)
    
    # Create fullscreen window
    cv2.namedWindow('Eye Control Interface', cv2.WINDOW_NORMAL)
    cv2.setWindowProperty('Eye Control Interface', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    # Smoothing for gaze position
    smooth_gaze_x = screen_width // 2
    smooth_gaze_y = screen_height // 2
    smoothing_factor = 0.05  # Lower = smoother but more lag
    
    # Initialize Face Mesh with better tracking
    with mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    ) as face_mesh:
        
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                print("Failed to grab frame")
                break
            
            # Flip frame horizontally for mirror view
            frame = cv2.flip(frame, 1)
            frame_height, frame_width = frame.shape[:2]
            
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process the frame
            results = face_mesh.process(rgb_frame)
            
            # Create black canvas for fullscreen display
            canvas = np.zeros((screen_height, screen_width, 3), dtype=np.uint8)
            
            # Draw the control panel
            draw_control_panel(canvas, screen_width, screen_height)
            
            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    landmarks = face_landmarks.landmark
                    
                    # Get face center for head position tracking
                    face_center = get_face_center(landmarks, frame_width, frame_height)
                    
                    # Get pupil positions
                    left_pupil = get_iris_center(landmarks, LEFT_IRIS, 
                                                 frame_width, frame_height)
                    right_pupil = get_iris_center(landmarks, RIGHT_IRIS, 
                                                  frame_width, frame_height)
                    
                    # Get eye bounds for mapping
                    left_bounds = get_eye_bounds(landmarks, LEFT_EYE, 
                                                 frame_width, frame_height)
                    right_bounds = get_eye_bounds(landmarks, RIGHT_EYE, 
                                                  frame_width, frame_height)
                    
                    # Map each eye's gaze to screen coordinates (with head position)
                    left_gaze = map_gaze_to_screen(left_pupil, left_bounds, face_center,
                                                   screen_width, screen_height, 
                                                   frame_width, frame_height)
                    right_gaze = map_gaze_to_screen(right_pupil, right_bounds, face_center,
                                                    screen_width, screen_height,
                                                    frame_width, frame_height)
                    
                    # Average both eyes
                    gaze_x = (left_gaze[0] + right_gaze[0]) // 2
                    gaze_y = (left_gaze[1] + right_gaze[1]) // 2
                    
                    # Apply smoothing
                    smooth_gaze_x = int(smooth_gaze_x * (1 - smoothing_factor) + 
                                       gaze_x * smoothing_factor)
                    smooth_gaze_y = int(smooth_gaze_y * (1 - smoothing_factor) + 
                                       gaze_y * smoothing_factor)
                    
                    # Draw gaze point as large white circle
                    cv2.circle(canvas, (smooth_gaze_x, smooth_gaze_y), 30, 
                              (255, 255, 255), -1)
                    cv2.circle(canvas, (smooth_gaze_x, smooth_gaze_y), 35, 
                              (0, 255, 255), 3)
            
            # Display instructions
            cv2.putText(canvas, "Press 'q' to quit | Press 'ESC' to exit fullscreen", 
                       (screen_width // 2 - 300, screen_height - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)
            
            # Show the canvas
            cv2.imshow('Eye Control Interface', canvas)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == 27:  # ESC key
                cv2.setWindowProperty('Eye Control Interface', cv2.WND_PROP_FULLSCREEN, 
                                    cv2.WINDOW_NORMAL)
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()