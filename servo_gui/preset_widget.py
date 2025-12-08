#!/usr/bin/env python3
import tkinter as tk
import time

class PresetWidget(tk.Frame):
    """A gaze-selectable preset button widget."""
    def __init__(self, parent, preset_name, dwell_time=1.5, callback=None, repeat=False):
        super().__init__(parent, borderwidth=2, relief="groove")
        self.preset_name = preset_name
        self.dwell_time = dwell_time
        self.callback = callback
        self.repeat = repeat # internal flag for scrolling
        
        self.is_hovering = False
        self.progress_seconds = 0.0 # Accumulated active time
        self.last_update_time = time.time()
        self.triggered = False  # Prevent multiple triggers
        
        # UI Setup
        self.height = 100 # Increased height
        self.canvas = tk.Canvas(self, bg="white", width=200, height=self.height)
        self.canvas.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Draw rectangle background
        self.rect = self.canvas.create_rectangle(0, 0, 200, self.height, fill="white", outline="black")
        
        # Add text label
        self.text = self.canvas.create_text(100, self.height/2, text=preset_name, font=("Arial", 12, "bold"))
        
        # Progress bar (hidden initially)
        self.progress_bar = self.canvas.create_rectangle(0, self.height-5, 0, self.height, fill="#4CAF50", outline="")
        
        # Bind events
        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<Enter>", self.on_enter)
        self.canvas.bind("<Leave>", self.on_leave)

    def on_resize(self, event):
        w, h = event.width, event.height
        self.canvas.coords(self.rect, 0, 0, w, h)
        self.canvas.coords(self.text, w/2, h/2)
        self.canvas.coords(self.progress_bar, 0, h - 5, 0, h)
        
    def on_enter(self, event):
        self.is_hovering = True
        self.last_update_time = time.time()
        self.update_visuals()
        
    def on_leave(self, event):
        self.is_hovering = False
        self.triggered = False
        self.last_update_time = time.time()
        # Do NOT reset progress_seconds here, let it decay
        self.reset_visuals()

    def update_gaze(self):
        """Manual update from eye tracker - called when gaze is on this widget."""
        if not self.is_hovering:
            self.is_hovering = True
            self.last_update_time = time.time()
            self.triggered = False
        self.update_visuals()

    def clear_hover(self):
        """Manual clear hover state."""
        if self.is_hovering:
            self.is_hovering = False
            # self.triggered = False # Don't untrigger immediately if we want to latch? Standard behavior is fine.
            self.triggered = False 
            self.last_update_time = time.time()
            self.reset_visuals()
            
    def update_visuals(self):
        self.canvas.itemconfig(self.rect, fill="#e3f2fd")  # Light blue highlight
        
    def reset_visuals(self):
        self.canvas.itemconfig(self.rect, fill="white")
        # Don't reset progress bar width here visually if we want to show decay, 
        # but usually we hide it or show it shrinking. 
        # For now, let process_frame handle the bar coords.
        
    def process_frame(self, attention_level):
        """Called every frame to check dwell time and trigger action."""
        current_time = time.time()
        dt = current_time - self.last_update_time
        self.last_update_time = current_time
        
        # Decay rate (seconds lost per second)
        DECAY_RATE = 2.0
        
        if self.is_hovering and (not self.triggered or self.repeat):
            self.progress_seconds += dt
        else:
            # Decay if not hovering OR if already triggered (resetting)
            if self.progress_seconds > 0:
                self.progress_seconds -= dt * DECAY_RATE
        
        # Clamp
        self.progress_seconds = max(0.0, min(self.progress_seconds, self.dwell_time))
        
        # Update progress bar
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        
        if self.progress_seconds > 0:
            progress_width = (self.progress_seconds / self.dwell_time) * w
            self.canvas.coords(self.progress_bar, 0, h - 5, progress_width, h)
        else:
            self.canvas.coords(self.progress_bar, 0, h - 5, 0, h)
            
        # Check trigger
        if self.is_hovering:
            if not self.triggered or self.repeat:
                if self.progress_seconds >= self.dwell_time:
                    # Threshold check
                    THRESHOLD = 35
                    if attention_level > THRESHOLD:
                        self.triggered = True
                        self.perform_trigger()

    def perform_trigger(self):
        self.canvas.itemconfig(self.rect, fill="#4CAF50")
        if self.callback:
            self.callback(self.preset_name)
        
        if self.repeat:
            # Faster repeat: Reset progress to allow quick re-trigger
            # e.g., if dwell is 0.8, set to 0.6 so it fires again in 0.2s
            repeat_delay = 0.2
            self.progress_seconds = max(0, self.dwell_time - repeat_delay)
            self.triggered = False # Allow re-trigger
            self.after(50, self.reset_visuals) # Short flash
        else:
            # Reset progress after trigger so it can decay/reset
            self.progress_seconds = 0
            self.after(300, self.reset_visuals)


class ToggleWidget(tk.Frame):
    """A gaze-selectable toggle button widget."""
    def __init__(self, parent, text_on="Switch to Manual", text_off="Switch to Presets", 
                 dwell_time=1.5, callback=None):
        super().__init__(parent, borderwidth=2, relief="raised")
        self.text_on = text_on
        self.text_off = text_off
        self.dwell_time = dwell_time
        self.callback = callback
        self.state = False  # False = showing text_off (presets mode available)
        
        self.is_hovering = False
        self.progress_seconds = 0.0
        self.last_update_time = time.time()
        self.triggered = False
        
        # UI Setup
        self.canvas = tk.Canvas(self, bg="#e0e0e0", width=250, height=80)
        self.canvas.pack(fill="both", expand=True)
        
        # Draw rectangle background
        self.rect = self.canvas.create_rectangle(0, 0, 250, 80, fill="#e0e0e0", outline="black")
        
        # Add text label
        self.text = self.canvas.create_text(125, 40, text=self.text_off, font=("Arial", 16, "bold"))
        
        # Progress bar
        self.progress_bar = self.canvas.create_rectangle(0, 75, 0, 80, fill="#2196F3", outline="")
        
        # Bind events
        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<Enter>", self.on_enter)
        self.canvas.bind("<Leave>", self.on_leave)

    def on_resize(self, event):
        w, h = event.width, event.height
        self.canvas.coords(self.rect, 0, 0, w, h)
        self.canvas.coords(self.text, w/2, h/2 - 2)
        self.canvas.coords(self.progress_bar, 0, h - 5, 0, h)

    def set_state(self, state):
        """Update the toggle state and text."""
        self.state = state
        text = self.text_on if state else self.text_off
        self.canvas.itemconfig(self.text, text=text)
        
    def on_enter(self, event):
        self.is_hovering = True
        self.last_update_time = time.time()
        self.update_visuals()
        
    def on_leave(self, event):
        self.is_hovering = False
        self.triggered = False
        self.last_update_time = time.time()
        self.reset_visuals()

    def update_gaze(self):
        """Manual update from eye tracker."""
        if not self.is_hovering:
            self.is_hovering = True
            self.last_update_time = time.time()
            self.triggered = False
        self.update_visuals()

    def clear_hover(self):
        """Manual clear hover state."""
        if self.is_hovering:
            self.is_hovering = False
            self.triggered = False
            self.last_update_time = time.time()
            self.reset_visuals()
            
    def update_visuals(self):
        self.canvas.itemconfig(self.rect, fill="#bbdefb")  # Light blue
        
    def reset_visuals(self):
        self.canvas.itemconfig(self.rect, fill="#e0e0e0")
        
    def process_frame(self, attention_level=0):
        """Called every frame to check dwell time and trigger toggle."""
        current_time = time.time()
        dt = current_time - self.last_update_time
        self.last_update_time = current_time
        
        DECAY_RATE = 2.0
        
        if self.is_hovering and not self.triggered:
            self.progress_seconds += dt
        else:
            if self.progress_seconds > 0:
                self.progress_seconds -= dt * DECAY_RATE
                
        self.progress_seconds = max(0.0, min(self.progress_seconds, self.dwell_time))
        
        # Update progress bar
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        
        if self.progress_seconds > 0:
            progress_width = (self.progress_seconds / self.dwell_time) * w
            self.canvas.coords(self.progress_bar, 0, h - 5, progress_width, h)
        else:
            self.canvas.coords(self.progress_bar, 0, h - 5, 0, h)
            
        if self.is_hovering and not self.triggered:
            if self.progress_seconds >= self.dwell_time:
                THRESHOLD = 35
                if attention_level > THRESHOLD:
                    self.triggered = True
                    self.perform_trigger()

    def perform_trigger(self):
        self.canvas.itemconfig(self.rect, fill="#4CAF50")
        if self.callback:
            self.callback()
        self.progress_seconds = 0
        self.after(300, self.reset_visuals)
