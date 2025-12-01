import cv2
import mediapipe as mp
import numpy as np
import threading
import time
import os
import locale

# Try to fix locale issue for MediaPipe
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except:
    pass

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh

# Eye landmark indices for MediaPipe Face Mesh
LEFT_EYE = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
RIGHT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
LEFT_IRIS = [474, 475, 476, 477]
RIGHT_IRIS = [469, 470, 471, 472]

class EyeTracker:
    def __init__(self, screen_width=1920, screen_height=1080):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        
        self.gaze_x = screen_width // 2
        self.gaze_y = screen_height // 2
        
        # Smoothing
        self.smooth_gaze_x = screen_width // 2
        self.smooth_gaze_y = screen_height // 2
        self.smoothing_factor = 0.1 # Increased slightly for responsiveness

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)

    def get_gaze(self):
        with self.lock:
            return self.smooth_gaze_x, self.smooth_gaze_y

    def _get_iris_center(self, landmarks, iris_indices, frame_width, frame_height):
        x_coords = [landmarks[i].x * frame_width for i in iris_indices]
        y_coords = [landmarks[i].y * frame_height for i in iris_indices]
        center_x = int(sum(x_coords) / len(x_coords))
        center_y = int(sum(y_coords) / len(y_coords))
        return (center_x, center_y)

    def _get_face_center(self, landmarks, frame_width, frame_height):
        nose_tip = landmarks[1]
        center_x = int(nose_tip.x * frame_width)
        center_y = int(nose_tip.y * frame_height)
        return (center_x, center_y)

    def _get_eye_bounds(self, landmarks, eye_indices, frame_width, frame_height):
        x_coords = [landmarks[i].x * frame_width for i in eye_indices]
        y_coords = [landmarks[i].y * frame_height for i in eye_indices]
        return min(x_coords), max(x_coords), min(y_coords), max(y_coords)

    def _map_gaze_to_screen(self, pupil_pos, eye_bounds, face_center, frame_width, frame_height):
        min_x, max_x, min_y, max_y = eye_bounds
        
        eye_width = max_x - min_x
        eye_height = max_y - min_y
        
        if eye_width == 0 or eye_height == 0:
            return self.screen_width // 2, self.screen_height // 2
        
        rel_x = (pupil_pos[0] - min_x) / eye_width
        rel_y = (pupil_pos[1] - min_y) / eye_height
        
        # INVERT Y-AXIS
        rel_y = 1 - rel_y
        
        # Add head position influence
        head_x = face_center[0] / frame_width
        head_y = face_center[1] / frame_height
        
        combined_x = rel_x * 0.4 + head_x * 0.6
        combined_y = rel_y * 0.4 + head_y * 0.6
        
        sensitivity_x = 2.5
        sensitivity_y = 2.5
        
        combined_x = (combined_x - 0.5) * sensitivity_x + 0.5
        combined_y = (combined_y - 0.5) * sensitivity_y + 0.5
        
        combined_x = max(0, min(1, combined_x))
        combined_y = max(0, min(1, combined_y))
        
        screen_x = int(combined_x * self.screen_width)
        screen_y = int(combined_y * self.screen_height)
        
        return screen_x, screen_y

    def _process_loop(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("EyeTracker: Failed to open webcam.")
            return

        try:
            with mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.7
            ) as face_mesh:
                
                while self.running:
                    success, frame = cap.read()
                    if not success:
                        time.sleep(0.1)
                        continue
                    
                    frame = cv2.flip(frame, 1)
                    frame_height, frame_width = frame.shape[:2]
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    results = face_mesh.process(rgb_frame)
                    
                    if results.multi_face_landmarks:
                        for face_landmarks in results.multi_face_landmarks:
                            landmarks = face_landmarks.landmark
                            
                            face_center = self._get_face_center(landmarks, frame_width, frame_height)
                            
                            left_pupil = self._get_iris_center(landmarks, LEFT_IRIS, frame_width, frame_height)
                            right_pupil = self._get_iris_center(landmarks, RIGHT_IRIS, frame_width, frame_height)
                            
                            left_bounds = self._get_eye_bounds(landmarks, LEFT_EYE, frame_width, frame_height)
                            right_bounds = self._get_eye_bounds(landmarks, RIGHT_EYE, frame_width, frame_height)
                            
                            left_gaze = self._map_gaze_to_screen(left_pupil, left_bounds, face_center, frame_width, frame_height)
                            right_gaze = self._map_gaze_to_screen(right_pupil, right_bounds, face_center, frame_width, frame_height)
                            
                            gaze_x = (left_gaze[0] + right_gaze[0]) // 2
                            gaze_y = (left_gaze[1] + right_gaze[1]) // 2
                            
                            with self.lock:
                                self.smooth_gaze_x = int(self.smooth_gaze_x * (1 - self.smoothing_factor) + gaze_x * self.smoothing_factor)
                                self.smooth_gaze_y = int(self.smooth_gaze_y * (1 - self.smoothing_factor) + gaze_y * self.smoothing_factor)
                    
                    # Small sleep to prevent CPU hogging if needed, though MediaPipe is heavy enough
                    # time.sleep(0.01) 
        except Exception as e:
            print(f"EyeTracker: Error initializing or running FaceMesh: {e}")
            print("EyeTracker: Eye tracking will be disabled.")
            self.running = False
        finally:
            cap.release()
