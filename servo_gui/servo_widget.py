#!/usr/bin/env python3
import tkinter as tk
import time

class ServoWidget(tk.Frame):
    def __init__(self, parent, arm_name, servo_name, left_label="-", right_label="+", dwell_time=1.0, callback=None):
        super().__init__(parent, borderwidth=2, relief="groove")
        self.arm_name = arm_name
        self.servo_name = servo_name
        self.dwell_time = dwell_time
        self.callback = callback
        
        self.is_hovering = False
        self.hover_start_time = 0
        self.hover_side = None # 'left' or 'right'
        self.last_trigger_time = 0
        
        self.min_limit = 0
        self.max_limit = 180
        self.current_angle = 90
        
        # UI Setup
        self.label = tk.Label(self, text=f"{servo_name}", font=("Arial", 10, "bold"))
        self.label.pack(pady=2)
        
        # Set small initial dimensions so it doesn't force the window to be huge
        self.canvas = tk.Canvas(self, bg="lightgray", width=10, height=10)
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Draw split rectangle
        self.rect_left = self.canvas.create_rectangle(0, 0, 0, 0, fill="white", outline="black", tags="left")
        self.rect_right = self.canvas.create_rectangle(0, 0, 0, 0, fill="white", outline="black", tags="right")
        
        # Add text labels
        # Use smaller font if labels are long
        font_size = 20 if len(left_label) < 3 and len(right_label) < 3 else 14
        self.text_left = self.canvas.create_text(0, 0, text=left_label, font=("Arial", font_size))
        self.text_right = self.canvas.create_text(0, 0, text=right_label, font=("Arial", font_size))
        
        # Progress bar
        self.progress_bar = self.canvas.create_rectangle(0, 0, 0, 0, fill="#4CAF50", outline="")
        
        # Bind events
        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<Enter>", self.on_enter)
        self.canvas.bind("<Leave>", self.on_leave)
        self.canvas.bind("<Motion>", self.on_motion)

    def set_limits(self, min_limit, max_limit):
        self.min_limit = min_limit
        self.max_limit = max_limit
        
    def set_angle(self, angle):
        self.current_angle = angle
        # If currently hovering, re-evaluate visuals in case we hit a limit
        if self.is_hovering:
            self.update_visuals()

    def on_resize(self, event):
        w, h = event.width, event.height
        self.canvas.coords(self.rect_left, 0, 0, w/2, h)
        self.canvas.coords(self.rect_right, w/2, 0, w, h)
        self.canvas.coords(self.text_left, w/4, h/2)
        self.canvas.coords(self.text_right, 3*w/4, h/2)
        # Progress bar at bottom
        self.canvas.coords(self.progress_bar, 0, h - 5, 0, h)
        
    def on_enter(self, event):
        self.is_hovering = True
        self.check_side(event.x)
        self.hover_start_time = time.time()
        
    def on_leave(self, event):
        self.is_hovering = False
        self.hover_side = None
        self.reset_visuals()
        
    def on_motion(self, event):
        w = self.canvas.winfo_width()
        new_side = 'left' if event.x < w/2 else 'right'
        if new_side != self.hover_side:
            self.hover_side = new_side
            self.hover_start_time = time.time() # Reset timer on side switch
            self.update_visuals()

    def update_gaze(self, rel_x):
        """Manual update from eye tracker coordinates (relative to widget)"""
        if not self.is_hovering:
            self.is_hovering = True
            self.hover_start_time = time.time()
        
        self.check_side(rel_x)

    def clear_hover(self):
        """Manual clear hover state"""
        if self.is_hovering:
            self.is_hovering = False
            self.hover_side = None
            self.reset_visuals()
            
    def check_side(self, x):
        w = self.canvas.winfo_width()
        new_side = 'left' if x < w/2 else 'right'
        
        if new_side != self.hover_side:
            self.hover_side = new_side
            self.hover_start_time = time.time() # Reset timer on side switch
            self.update_visuals()
        
    def update_visuals(self):
        if self.hover_side == 'left':
            # Check min limit
            if self.current_angle <= self.min_limit:
                self.canvas.itemconfig(self.rect_left, fill="white") # No highlight
            else:
                self.canvas.itemconfig(self.rect_left, fill="#ffcccc") # Light red
            self.canvas.itemconfig(self.rect_right, fill="white")
        elif self.hover_side == 'right':
            self.canvas.itemconfig(self.rect_left, fill="white")
            # Check max limit
            if self.current_angle >= self.max_limit:
                self.canvas.itemconfig(self.rect_right, fill="white") # No highlight
            else:
                self.canvas.itemconfig(self.rect_right, fill="#ccffcc") # Light green
        else:
            self.reset_visuals()
            
    def reset_visuals(self):
        self.canvas.itemconfig(self.rect_left, fill="white")
        self.canvas.itemconfig(self.rect_right, fill="white")
        # Reset progress bar
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        self.canvas.coords(self.progress_bar, 0, h - 5, 0, h)
        
    def process_frame(self, attention_level):
        if self.is_hovering and self.hover_side:
            elapsed = time.time() - self.hover_start_time
            
            # Update progress bar
            w = self.canvas.winfo_width()
            h = self.canvas.winfo_height()
            progress_width = min(w, (elapsed / self.dwell_time) * w)
            self.canvas.coords(self.progress_bar, 0, h - 5, progress_width, h)

            # Buffer check: wait for dwell_time before acting
            if elapsed < self.dwell_time:
                return

            # Threshold check - only move if attention is sufficient
            # You can adjust this threshold (e.g., 40, 50)
            THRESHOLD = 35
            
            if attention_level > THRESHOLD:
                # Calculate step size based on attention
                # Higher attention -> larger steps (faster movement)
                # Map 40-100 to 1-5 degrees
                # step = 1 + int((attention_level - THRESHOLD) / 15)
                
                # nah have constant slow step
                step = 1

                if self.callback:
                    self.callback(self.arm_name, self.servo_name, self.hover_side, step) 
