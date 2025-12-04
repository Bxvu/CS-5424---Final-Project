#!/usr/bin/env python3
"""
Rock-Paper-Scissors Game with Brain-Computer Interface
Uses eye tracking + attention level for selection
Controls robot arm to display gestures
"""

import tkinter as tk
import sys
import os
import time
import random
import threading

# Add parent directory to path to import from servo_gui
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'servo_gui'))

from headset_input import HeadsetClient

# Try to import eye tracker
try:
    from eye_tracker import EyeTracker
    HAS_EYE_TRACKER = True
except ImportError:
    print("WARNING: EyeTracker dependencies not found. Eye tracking disabled.")
    HAS_EYE_TRACKER = False

# Try to import pi_servo_hat
try:
    import pi_servo_hat
    HAS_HARDWARE = True
except ImportError:
    print("WARNING: pi_servo_hat not found. Running in simulation mode.")
    HAS_HARDWARE = False


# =============================================================================
# SERVO CONFIGURATION
# =============================================================================

# Servo Channel Mapping (same as original servo_app)
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

# Arm positions for Rock, Paper, Scissors
# Each gesture is a dict of {joint: angle}
GESTURES = {
    "rock": {
        "Base": 90,
        "Shoulder": 60,
        "Elbow": 120,
        "Wrist": 90,
        "Gripper": 180  # Closed fist
    },
    "paper": {
        "Base": 90,
        "Shoulder": 90,
        "Elbow": 90,
        "Wrist": 90,
        "Gripper": 0  # Open hand
    },
    "scissors": {
        "Base": 90,
        "Shoulder": 75,
        "Elbow": 100,
        "Wrist": 70,
        "Gripper": 90  # Half open (two fingers)
    }
}

# Neutral position (starting position)
NEUTRAL_POSITION = {
    "Base": 90,
    "Shoulder": 90,
    "Elbow": 90,
    "Wrist": 90,
    "Gripper": 90
}


# =============================================================================
# CHOICE WIDGET - Similar to ServoWidget but for RPS selection
# =============================================================================

class ChoiceWidget(tk.Frame):
    """A widget representing one choice (Rock/Paper/Scissors)"""
    
    def __init__(self, parent, choice_name, emoji, color, dwell_time=1.5, callback=None):
        super().__init__(parent, borderwidth=3, relief="raised")
        self.choice_name = choice_name
        self.dwell_time = dwell_time
        self.callback = callback
        self.color = color
        self.default_bg = "#f0f0f0"
        
        self.is_hovering = False
        self.hover_start_time = 0
        self.selected = False
        self.enabled = True
        
        # Configure frame
        self.config(bg=self.default_bg)
        
        # Emoji label (large)
        self.emoji_label = tk.Label(self, text=emoji, font=("Arial", 72), bg=self.default_bg)
        self.emoji_label.pack(pady=20)
        
        # Text label
        self.text_label = tk.Label(self, text=choice_name.upper(), font=("Arial", 24, "bold"), bg=self.default_bg)
        self.text_label.pack(pady=10)
        
        # Progress bar canvas
        self.progress_canvas = tk.Canvas(self, width=200, height=20, bg="white", highlightthickness=1)
        self.progress_canvas.pack(pady=10)
        self.progress_bar = self.progress_canvas.create_rectangle(0, 0, 0, 20, fill=color, outline="")
        
        # Bind mouse events (fallback if no eye tracker)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        for child in [self.emoji_label, self.text_label, self.progress_canvas]:
            child.bind("<Enter>", self.on_enter)
            child.bind("<Leave>", self.on_leave)
    
    def on_enter(self, event=None):
        if self.enabled and not self.selected:
            self.is_hovering = True
            self.hover_start_time = time.time()
            self.config(bg=self.color)
            self.emoji_label.config(bg=self.color)
            self.text_label.config(bg=self.color)
    
    def on_leave(self, event=None):
        if not self.selected:
            self.is_hovering = False
            self.config(bg=self.default_bg)
            self.emoji_label.config(bg=self.default_bg)
            self.text_label.config(bg=self.default_bg)
            self.progress_canvas.coords(self.progress_bar, 0, 0, 0, 20)
    
    def update_gaze(self, is_inside):
        """Update from eye tracker"""
        if not self.enabled or self.selected:
            return
            
        if is_inside and not self.is_hovering:
            self.on_enter()
        elif not is_inside and self.is_hovering:
            self.on_leave()
    
    def process_frame(self, attention_level):
        """Process frame - check for dwell time and attention threshold"""
        if not self.enabled or self.selected:
            return False
            
        if self.is_hovering:
            elapsed = time.time() - self.hover_start_time
            
            # Update progress bar
            progress = min(1.0, elapsed / self.dwell_time)
            bar_width = int(200 * progress)
            self.progress_canvas.coords(self.progress_bar, 0, 0, bar_width, 20)
            
            # Check if dwell time met and attention threshold reached
            ATTENTION_THRESHOLD = 30
            if elapsed >= self.dwell_time and attention_level >= ATTENTION_THRESHOLD:
                self.select()
                return True
        
        return False
    
    def select(self):
        """Mark this choice as selected"""
        self.selected = True
        self.config(bg=self.color, relief="sunken", borderwidth=5)
        self.emoji_label.config(bg=self.color)
        self.text_label.config(bg=self.color)
        self.progress_canvas.coords(self.progress_bar, 0, 0, 200, 20)
        
        if self.callback:
            self.callback(self.choice_name)
    
    def reset(self):
        """Reset the widget state"""
        self.selected = False
        self.is_hovering = False
        self.enabled = True
        self.config(bg=self.default_bg, relief="raised", borderwidth=3)
        self.emoji_label.config(bg=self.default_bg)
        self.text_label.config(bg=self.default_bg)
        self.progress_canvas.coords(self.progress_bar, 0, 0, 0, 20)
    
    def disable(self):
        """Disable the widget"""
        self.enabled = False
        self.config(bg="#cccccc")
        self.emoji_label.config(bg="#cccccc")
        self.text_label.config(bg="#cccccc")


# =============================================================================
# MAIN GAME CLASS
# =============================================================================

class RockPaperScissorsGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Rock Paper Scissors - Brain Control")
        self.root.attributes('-fullscreen', True)
        self.root.bind("<Escape>", lambda e: self.root.attributes("-fullscreen", False))
        self.root.configure(bg="#1a1a2e")
        
        # Game state
        self.human_choice = None
        self.computer_choice = None
        self.game_over = False
        
        # Initialize hardware
        self.servo = None
        if HAS_HARDWARE:
            try:
                self.servo = pi_servo_hat.PiServoHat()
                self.servo.restart()
                print("Servo Hat Initialized.")
                self._set_arm_position("LeftArm", NEUTRAL_POSITION)
                self._set_arm_position("RightArm", NEUTRAL_POSITION)
            except Exception as e:
                print(f"Error initializing Servo Hat: {e}")
                self.servo = None
        
        # Initialize headset
        self.headset = HeadsetClient()
        self.headset.start()
        
        # Initialize eye tracker
        self.eye_tracker = None
        self.cursor_window = None
        if HAS_EYE_TRACKER:
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            self.eye_tracker = EyeTracker(screen_width, screen_height)
            self.eye_tracker.start()
            
            # Visual cursor
            self.cursor_window = tk.Toplevel(self.root)
            self.cursor_window.overrideredirect(True)
            self.cursor_window.attributes('-topmost', True)
            self.cursor_window.geometry("20x20+0+0")
            cursor_canvas = tk.Canvas(self.cursor_window, width=20, height=20, bg='black', highlightthickness=0)
            cursor_canvas.pack()
            cursor_canvas.create_oval(0, 0, 20, 20, fill='red', outline='white')
            try:
                self.cursor_window.attributes('-transparentcolor', 'black')
            except:
                pass
        
        # Build UI
        self._build_ui()
        
        # Start update loop
        self.update_loop()
    
    def _build_ui(self):
        """Build the game UI"""
        # Main container
        self.main_frame = tk.Frame(self.root, bg="#1a1a2e")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        self.title_label = tk.Label(
            self.main_frame, 
            text="🎮 ROCK PAPER SCISSORS 🎮",
            font=("Arial", 36, "bold"),
            bg="#1a1a2e",
            fg="#eee"
        )
        self.title_label.pack(pady=20)
        
        # Status / Instruction label
        self.status_label = tk.Label(
            self.main_frame,
            text="Look at your choice and focus to select!",
            font=("Arial", 20),
            bg="#1a1a2e",
            fg="#aaa"
        )
        self.status_label.pack(pady=10)
        
        # Info frame (attention display)
        self.info_frame = tk.Frame(self.main_frame, bg="#1a1a2e")
        self.info_frame.pack(pady=10)
        
        self.attention_label = tk.Label(
            self.info_frame,
            text="Attention: 0",
            font=("Arial", 16),
            bg="#1a1a2e",
            fg="#4ecca3"
        )
        self.attention_label.pack(side="left", padx=20)
        
        self.signal_label = tk.Label(
            self.info_frame,
            text="Signal: --",
            font=("Arial", 16),
            bg="#1a1a2e",
            fg="#4ecca3"
        )
        self.signal_label.pack(side="left", padx=20)
        
        # Choices frame
        self.choices_frame = tk.Frame(self.main_frame, bg="#1a1a2e")
        self.choices_frame.pack(pady=30, fill="both", expand=True)
        
        # Create choice widgets
        self.choice_widgets = {}
        
        choices = [
            ("rock", "🪨", "#e74c3c"),      # Red
            ("paper", "📄", "#3498db"),     # Blue
            ("scissors", "✂️", "#f39c12")   # Orange
        ]
        
        for choice_name, emoji, color in choices:
            widget = ChoiceWidget(
                self.choices_frame,
                choice_name,
                emoji,
                color,
                dwell_time=1.5,
                callback=self.on_human_choice
            )
            widget.pack(side="left", padx=20, fill="both", expand=True)
            self.choice_widgets[choice_name] = widget
        
        # Result frame (hidden initially)
        self.result_frame = tk.Frame(self.main_frame, bg="#1a1a2e")
        
        self.result_label = tk.Label(
            self.result_frame,
            text="",
            font=("Arial", 48, "bold"),
            bg="#1a1a2e",
            fg="#fff"
        )
        self.result_label.pack(pady=20)
        
        self.matchup_label = tk.Label(
            self.result_frame,
            text="",
            font=("Arial", 24),
            bg="#1a1a2e",
            fg="#aaa"
        )
        self.matchup_label.pack(pady=10)
        
        self.countdown_label = tk.Label(
            self.result_frame,
            text="",
            font=("Arial", 16),
            bg="#1a1a2e",
            fg="#666"
        )
        self.countdown_label.pack(pady=10)
    
    def _set_arm_position(self, arm_name, positions):
        """Set an arm to a specific gesture position"""
        if not self.servo:
            print(f"[SIM] Setting {arm_name} to: {positions}")
            return
        
        for joint, angle in positions.items():
            try:
                channel = SERVO_MAP[arm_name][joint]
                self.servo.move_servo_position(channel, angle)
            except Exception as e:
                print(f"Error moving {arm_name} {joint}: {e}")
    
    def on_human_choice(self, choice):
        """Called when human makes a selection"""
        if self.game_over:
            return
        
        self.human_choice = choice
        print(f"Human chose: {choice}")
        
        # Disable all widgets
        for widget in self.choice_widgets.values():
            widget.disable()
        
        # Update status
        self.status_label.config(text=f"You chose {choice.upper()}! Computer is choosing...")
        
        # Move human's arm (LeftArm shows human choice)
        self._set_arm_position("LeftArm", GESTURES[choice])
        
        # Delay before computer choice for suspense
        self.root.after(1500, self._computer_turn)
    
    def _computer_turn(self):
        """Computer makes its random choice"""
        self.computer_choice = random.choice(["rock", "paper", "scissors"])
        print(f"Computer chose: {self.computer_choice}")
        
        # Move computer's arm (RightArm shows computer choice)
        self._set_arm_position("RightArm", GESTURES[self.computer_choice])
        
        # Update status
        self.status_label.config(text=f"Computer chose {self.computer_choice.upper()}!")
        
        # Determine winner after brief pause
        self.root.after(1000, self._determine_winner)
    
    def _determine_winner(self):
        """Determine the winner and show result"""
        self.game_over = True
        
        human = self.human_choice
        computer = self.computer_choice
        
        # Get emoji for display
        emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
        
        # Determine result
        if human == computer:
            result = "TIE"
            result_text = "🤝 IT'S A TIE! 🤝"
            result_color = "#f39c12"
            human_wins = None
        elif (human == "rock" and computer == "scissors") or \
             (human == "paper" and computer == "rock") or \
             (human == "scissors" and computer == "paper"):
            result = "WIN"
            result_text = "🎉 YOU WIN! 🎉"
            result_color = "#2ecc71"
            human_wins = True
        else:
            result = "LOSE"
            result_text = "😢 YOU LOSE 😢"
            result_color = "#e74c3c"
            human_wins = False
        
        # Show result
        self.choices_frame.pack_forget()
        self.result_frame.pack(pady=30, fill="both", expand=True)
        
        self.result_label.config(text=result_text, fg=result_color)
        self.matchup_label.config(text=f"You: {emojis[human]} {human.upper()}  vs  Computer: {emojis[computer]} {computer.upper()}")
        
        # If human wins, start countdown and exit
        if human_wins:
            self._start_exit_countdown(10)
        else:
            # Show play again option (or just display result)
            self.countdown_label.config(text="Press ESC to exit or close window")
    
    def _start_exit_countdown(self, seconds):
        """Start countdown to exit"""
        if seconds <= 0:
            self._cleanup_and_exit()
            return
        
        self.countdown_label.config(text=f"Exiting in {seconds} seconds...")
        self.root.after(1000, lambda: self._start_exit_countdown(seconds - 1))
    
    def _cleanup_and_exit(self):
        """Clean up resources and exit"""
        print("Cleaning up and exiting...")
        
        # Return arms to neutral
        if self.servo:
            self._set_arm_position("LeftArm", NEUTRAL_POSITION)
            self._set_arm_position("RightArm", NEUTRAL_POSITION)
        
        # Stop headset
        if self.headset:
            self.headset.stop()
        
        # Stop eye tracker
        if self.eye_tracker:
            self.eye_tracker.stop()
        
        self.root.quit()
        self.root.destroy()
    
    def update_loop(self):
        """Main update loop"""
        if self.game_over:
            self.root.after(100, self.update_loop)
            return
        
        # Get attention level
        attention = self.headset.get_attention()
        self.attention_label.config(text=f"Attention: {attention}")
        
        # Update eye tracker cursor and check widget hover
        if self.eye_tracker and self.eye_tracker.running:
            gaze_x, gaze_y = self.eye_tracker.get_gaze()
            
            # Move cursor
            if self.cursor_window:
                try:
                    self.cursor_window.geometry(f"+{gaze_x-10}+{gaze_y-10}")
                except:
                    pass
            
            # Check which widget the gaze is over
            for widget in self.choice_widgets.values():
                wx = widget.winfo_rootx()
                wy = widget.winfo_rooty()
                ww = widget.winfo_width()
                wh = widget.winfo_height()
                
                is_inside = wx <= gaze_x <= wx + ww and wy <= gaze_y <= wy + wh
                widget.update_gaze(is_inside)
        
        # Process each widget
        for widget in self.choice_widgets.values():
            if widget.process_frame(attention):
                break  # Selection made, stop processing
        
        # Schedule next update
        self.root.after(50, self.update_loop)
    
    def __del__(self):
        if hasattr(self, 'headset') and self.headset:
            self.headset.stop()
        if hasattr(self, 'eye_tracker') and self.eye_tracker:
            self.eye_tracker.stop()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    root = tk.Tk()
    game = RockPaperScissorsGame(root)
    root.mainloop()

