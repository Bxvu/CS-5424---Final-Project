#!/usr/bin/env python3
import tkinter as tk
import time

class ServoWidget(tk.Frame):
    def __init__(self, parent, arm_name, servo_name, dwell_time=1.0, callback=None):
        super().__init__(parent, borderwidth=2, relief="groove")
        self.arm_name = arm_name
        self.servo_name = servo_name
        self.dwell_time = dwell_time
        self.callback = callback
        
        self.is_hovering = False
        self.hover_start_time = 0
        self.hover_side = None # 'left' or 'right'
        self.last_trigger_time = 0
        
        # UI Setup
        self.label = tk.Label(self, text=f"{servo_name}", font=("Arial", 10, "bold"))
        self.label.pack(pady=2)
        
        self.canvas = tk.Canvas(self, width=200, height=50, bg="lightgray")
        self.canvas.pack(padx=5, pady=5)
        
        # Draw split rectangle
        self.rect_left = self.canvas.create_rectangle(0, 0, 100, 50, fill="white", outline="black", tags="left")
        self.rect_right = self.canvas.create_rectangle(100, 0, 200, 50, fill="white", outline="black", tags="right")
        
        # Add text labels
        self.canvas.create_text(50, 25, text="-", font=("Arial", 20))
        self.canvas.create_text(150, 25, text="+", font=("Arial", 20))
        
        # Bind events
        self.canvas.bind("<Enter>", self.on_enter)
        self.canvas.bind("<Leave>", self.on_leave)
        self.canvas.bind("<Motion>", self.on_motion)
        
    def on_enter(self, event):
        self.is_hovering = True
        self.check_side(event.x)
        self.hover_start_time = time.time()
        
    def on_leave(self, event):
        self.is_hovering = False
        self.hover_side = None
        self.reset_visuals()
        
    def on_motion(self, event):
        new_side = 'left' if event.x < 100 else 'right'
        if new_side != self.hover_side:
            self.hover_side = new_side
            self.hover_start_time = time.time() # Reset timer on side switch
            self.update_visuals()
            
    def check_side(self, x):
        self.hover_side = 'left' if x < 100 else 'right'
        self.update_visuals()
        
    def update_visuals(self):
        if self.hover_side == 'left':
            self.canvas.itemconfig(self.rect_left, fill="#ffcccc") # Light red
            self.canvas.itemconfig(self.rect_right, fill="white")
        else:
            self.canvas.itemconfig(self.rect_left, fill="white")
            self.canvas.itemconfig(self.rect_right, fill="#ccffcc") # Light green
            
    def reset_visuals(self):
        self.canvas.itemconfig(self.rect_left, fill="white")
        self.canvas.itemconfig(self.rect_right, fill="white")
        
    def check_dwell(self):
        if self.is_hovering and self.hover_side:
            elapsed = time.time() - self.hover_start_time
            if elapsed >= self.dwell_time:
                # Trigger action
                if self.callback:
                    self.callback(self.arm_name, self.servo_name, self.hover_side)
                
                # Reset timer to prevent rapid firing, or keep firing?
                # For now, let's reset to allow continuous activation if user keeps staring
                # But maybe add a small delay so it doesn't flood
                self.hover_start_time = time.time() 
