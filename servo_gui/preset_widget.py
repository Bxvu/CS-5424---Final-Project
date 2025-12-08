#!/usr/bin/env python3
import tkinter as tk
import time

class PresetWidget(tk.Frame):
    """A gaze-selectable preset button widget."""
    def __init__(self, parent, preset_name, dwell_time=1.5, callback=None):
        super().__init__(parent, borderwidth=2, relief="groove")
        self.preset_name = preset_name
        self.dwell_time = dwell_time
        self.callback = callback
        
        self.is_hovering = False
        self.progress_seconds = 0.0
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
        self.update_visuals()
        
    def on_leave(self, event):
        self.is_hovering = False
        self.reset_visuals(partial=True)

    def update_gaze(self):
        """Manual update from eye tracker - called when gaze is on this widget."""
        if not self.is_hovering:
            self.is_hovering = True
        self.update_visuals()

    def clear_hover(self):
        """Manual clear hover state."""
        if self.is_hovering:
            self.is_hovering = False
            self.reset_visuals(partial=True)
            
    def update_visuals(self):
        self.canvas.itemconfig(self.rect, fill="#e3f2fd")  # Light blue highlight
        
    def reset_visuals(self, partial=False):
        """
        Reset visuals.
        partial=True means we just lost hover (don't clear progress bar instantly).
        partial=False means full reset (clear everything).
        """
        self.canvas.itemconfig(self.rect, fill="white")
        if not partial:
            # Reset progress bar only on full reset (e.g. after trigger)
            w = self.canvas.winfo_width()
            h = self.canvas.winfo_height()
            self.canvas.coords(self.progress_bar, 0, h - 5, 0, h)
        
    def process_frame(self, attention_level):
        """Called every frame to check dwell time and trigger action."""
        current_time = time.time()
        dt = current_time - self.last_update_time
        self.last_update_time = current_time
        
        if self.triggered:
            # Wait for user to look away before resetting trigger state completely?
            # Or just reset progress
            if not self.is_hovering:
                self.triggered = False
                self.progress_seconds = 0
            return

        if self.is_hovering:
            # Accumulate time
            self.progress_seconds += dt
        else:
            # Decay time (e.g. 2x speed decay)
            decay_rate = 2.0
            self.progress_seconds -= dt * decay_rate
        
        # Clamp bounds
        self.progress_seconds = max(0.0, min(self.progress_seconds, self.dwell_time))
        
        # Update progress bar
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w > 1: # Avoid div by zero or weirdness if not packed yet
            progress_width = (self.progress_seconds / self.dwell_time) * w
            self.canvas.coords(self.progress_bar, 0, h - 5, progress_width, h)
        
        # Check trigger
        if self.progress_seconds >= self.dwell_time:
            # Threshold check
            THRESHOLD = 1 # Lower threshold for now as people found it hard
            if attention_level > THRESHOLD:
                self.triggered = True
                self.canvas.itemconfig(self.rect, fill="#4CAF50")
                if self.callback:
                    self.callback(self.preset_name)
                    
                # Reset progress after trigger
                self.progress_seconds = 0
                self.after(300, lambda: self.reset_visuals(partial=False))


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
        self.update_visuals()
        
    def on_leave(self, event):
        self.is_hovering = False
        self.reset_visuals(partial=True)

    def update_gaze(self):
        """Manual update from eye tracker."""
        if not self.is_hovering:
            self.is_hovering = True
        self.update_visuals()

    def clear_hover(self):
        """Manual clear hover state."""
        if self.is_hovering:
            self.is_hovering = False
            self.reset_visuals(partial=True)
            
    def update_visuals(self):
        self.canvas.itemconfig(self.rect, fill="#bbdefb")  # Light blue
        
    def reset_visuals(self, partial=False):
        self.canvas.itemconfig(self.rect, fill="#e0e0e0")
        if not partial:
            w = self.canvas.winfo_width()
            h = self.canvas.winfo_height()
            self.canvas.coords(self.progress_bar, 0, h - 5, 0, h)
        
    def process_frame(self, attention_level=0):
        current_time = time.time()
        dt = current_time - self.last_update_time
        self.last_update_time = current_time
        
        if self.triggered:
            if not self.is_hovering:
                self.triggered = False
                self.progress_seconds = 0
            return

        if self.is_hovering:
            self.progress_seconds += dt
        else:
            decay_rate = 2.0
            self.progress_seconds -= dt * decay_rate
            
        self.progress_seconds = max(0.0, min(self.progress_seconds, self.dwell_time))
        
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w > 1:
            progress_width = (self.progress_seconds / self.dwell_time) * w
            self.canvas.coords(self.progress_bar, 0, h - 5, progress_width, h)
            
        if self.progress_seconds >= self.dwell_time:
            THRESHOLD = 1
            if attention_level > THRESHOLD:
                self.triggered = True
                self.canvas.itemconfig(self.rect, fill="#4CAF50")
                if self.callback:
                    self.callback()
                self.progress_seconds = 0
                self.after(300, lambda: self.reset_visuals(partial=False))
