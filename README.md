# Brain-Controlled Robot Arm System

**CS-5424 Interactive Device Design - Final Project**

A Brain-Computer Interface (BCI) system that enables hands-free control of dual robot arms using **brain waves (EEG)**, **eye tracking**, and **head position**.

---

## Overview

This project creates an accessible human-robot interaction system where users can control robot arm movements without using their hands. The system combines three input modalities:

| Input | Source | Purpose |
|-------|--------|---------|
| **Attention Level** | NeuroSky MindWave EEG Headset | Confirms intent (higher focus = action trigger) |
| **Gaze Position** | Webcam + MediaPipe | Selects which control to activate |
| **Head Position** | Webcam + MediaPipe | Coarse pointing for gaze targeting |

---

## System Architecture

```
┌─────────────────────┐
│  NeuroSky Headset   │──Bluetooth──┐
│  (EEG Brain Waves)  │             │
└─────────────────────┘             │
                                    ▼
┌─────────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│      Webcam         │─────▶│   Main App      │─────▶│  Servo Hat      │
│  (Eye + Head Track) │      │  (servo_app.py) │      │  (PCA9685)      │
└─────────────────────┘      └─────────────────┘      └────────┬────────┘
                                    │                          │
                                    ▼                          ▼
                             ┌─────────────────┐      ┌─────────────────┐
                             │  LED Stick      │      │   Robot Arms    │
                             │  (Attention)    │      │  (10 Servos)    │
                             └─────────────────┘      └─────────────────┘
```

---

## Project Structure

```
CS-5424---Final-Project/
├── servo_gui/                 # Main control application
│   ├── servo_app.py          # Tkinter GUI with full arm control
│   ├── servo_widget.py       # Individual servo +/- control widget
│   ├── preset_widget.py      # Preset pose buttons & toggle
│   ├── headset_input.py      # Threaded NeuroSky client class
│   └── eye_tracker.py        # Threaded eye tracking class
│
├── rsp_game/                  # Demo application
│   └── rsp.py                # Rock-Paper-Scissors game
│
├── pi_headset.py             # Standalone headset data viewer
├── eye_tracking.py           # Standalone eye tracking demo
├── sudodata.py               # Mock headset data generator
│
├── setup_guide.md            # Hardware setup instructions
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

---

## Components

### 1. NeuroSky Headset Integration

**Files:** `pi_headset.py`, `servo_gui/headset_input.py`

Connects to a NeuroSky MindWave headset via Bluetooth RFCOMM and parses the ThinkGear protocol:

| Data Code | Meaning | Range |
|-----------|---------|-------|
| `0x02` | Signal Quality | 0 (best) - 200 |
| `0x04` | **Attention** | 0 - 100 |
| `0x05` | Meditation | 0 - 100 |
| `0x83` | EEG Power Bands | 8 frequency bands |

**Key Insight:** The **Attention** value (0-100) is used as a confirmation mechanism. The system only triggers actions when attention exceeds a threshold (default: 35), ensuring intentional control.

### 2. Eye & Head Tracking

**Files:** `eye_tracking.py`, `servo_gui/eye_tracker.py`

Uses MediaPipe Face Mesh to track:
- **Iris position** within each eye (pupil tracking)
- **Head position** via nose tip landmark

The final gaze position combines:
- 40% eye gaze direction
- 60% head position

This hybrid approach is more robust than pure eye tracking while remaining responsive.

### 3. Main Control Application

**File:** `servo_gui/servo_app.py`

A windowed Tkinter application (80% screen size) with multiple control modes:

#### Preset Mode (Default)
- Pre-defined arm poses organized into categories
- Scrollable list with gaze-controlled scroll buttons
- Categories include: **Throw**, **Kick**, **Pass Object (L to R)**
- Each category has its own submenu with step-by-step actions

#### Manual Mode
- Fine-grained control of each servo
- Descriptive labels (e.g., "Forwards/Backwards" instead of "+/-")
- Visual feedback when at joint limits

#### Features
- **Mock Hardware Mode**: `USE_MOCK_HARDWARE = True` for testing without servos
- **LED Attention Meter**: 10-LED strip showing attention level (Red → Yellow → Green)
- **Startup Pose**: Configurable initial arm position
- **Smooth Interpolation**: Servo movements interpolated over time for fluid motion
- **Safe Exit**: Returns to startup pose before shutting down

#### Servo Mapping

| Arm | Joint | Channel | Labels |
|-----|-------|---------|--------|
| Left | Base | 0 | Right / Left |
| Left | Shoulder | 1 | Backwards / Forwards |
| Left | Elbow | 2 | Forwards / Backwards |
| Left | Wrist | 3 | Right / Left |
| Left | Gripper | 4 | Open / Close |
| Right | Base | 15 | Right / Left |
| Right | Shoulder | 14 | Backwards / Forwards |
| Right | Elbow | 13 | Forwards / Backwards |
| Right | Wrist | 12 | Right / Left |
| Right | Gripper | 11 | Open / Close |

#### Servo Limits

Two arm configurations are supported with different servo limits:

| Type | Used For | Shoulder Range | Gripper Range |
|------|----------|----------------|---------------|
| Orange | Left Arm | 10° - 100° | -20° - 73° |
| Black | Right Arm | 20° - 150° | -50° - 50° |

### 4. Rock-Paper-Scissors Demo

**File:** `rsp_game/rsp.py`

A demonstration game showing the system's capabilities:

1. User looks at Rock (R), Paper (P), or Scissors (S)
2. Dwell + focus triggers selection
3. Left arm displays user's choice
4. Right arm displays random computer choice
5. Winner determined and displayed
6. Auto-exits after 10 seconds if user wins

**Servo Gestures:**
| Gesture | Gripper Angle | Description |
|---------|---------------|-------------|
| Rock | 180° | Closed fist |
| Paper | 0° | Open hand |
| Scissors | 90° | Half open |

### 5. LED Attention Meter

**Integrated in:** `servo_gui/servo_app.py`

Uses a Qwiic LED Stick (10 LEDs) to display attention level in real-time:

| LEDs Lit | Attention Level | Color |
|----------|-----------------|-------|
| 1-3 | Low (0-30) | Red |
| 4-6 | Medium (30-60) | Yellow |
| 7-10 | High (60-100) | Green |

Runs a test pattern on startup to verify functionality.

---

## Hardware Requirements

- **Raspberry Pi** (tested on Pi 4)
- **SparkFun Pi Servo Hat** (PCA9685-based)
- **NeuroSky MindWave Mobile** EEG headset
- **USB Webcam** (for eye tracking)
- **2x Robot Arms** with 5 servos each
- **Qwiic LED Stick** (optional, for attention visualization)

---

## Software Dependencies

```bash
pip install -r requirements.txt
```

Key dependencies:
- `mediapipe` - Face mesh and iris detection
- `opencv-python` - Video capture and processing
- `sparkfun-pi-servo-hat` - Servo control
- `qwiic-led-stick` - LED attention meter
- `screeninfo` - Screen dimension detection

---

## Usage

### Main Servo Control App
```bash
cd servo_gui
python3 servo_app.py
```

### Rock-Paper-Scissors Game
```bash
cd rsp_game
python3 rsp.py
```

### Standalone Eye Tracking Demo
```bash
python3 eye_tracking.py
```

### Standalone Headset Data Viewer
```bash
python3 pi_headset.py
```

### Mock Headset Data (for testing without hardware)
```bash
python3 sudodata.py --att_mean 60 --att_var 15 --interval 0.5
```

---

## Controls

| Action | Method |
|--------|--------|
| Select control | Look at it (gaze + head position) |
| Confirm action | Focus/concentrate (attention > 35) |
| Toggle mode | Look at "Switch to Manual/Presets" button |
| Scroll lists | Look at Scroll Up/Down buttons |
| Exit application | Press `ESC` |

---

## Interaction Flow

```
1. LOOK    → Gaze determines which widget is targeted
             (progress bar starts filling)

2. DWELL   → Keep looking for 1.5 seconds
             (progress bar fills up)
             Progress decays if you look away

3. FOCUS   → Concentrate to trigger action
             (attention level must exceed threshold)

4. ACTION  → Servo moves smoothly to target position
             (interpolated over configurable duration)
```

---

## Configuration Options

### Mock Hardware Mode
In `servo_gui/servo_app.py`:
```python
USE_MOCK_HARDWARE = True  # Set to False for real hardware
```

### Startup Pose
```python
STARTUP_POSE = {
    "LeftArm": {"Base": 60, "Shoulder": 30, "Elbow": 70, "Wrist": 55, "Gripper": 0},
    "RightArm": {"Base": 10, "Shoulder": 50, "Elbow": 70, "Wrist": 90, "Gripper": 0}
}
```

### Attention Threshold
```python
THRESHOLD = 35  # Minimum attention level to trigger actions
```

### Dwell Time
```python
dwell_time = 1.5  # Seconds of sustained gaze required
```

---

## Accessibility Features

This system was designed with accessibility in mind:

- **Hands-free operation** - No physical buttons or touch required
- **Adjustable thresholds** - Attention threshold can be tuned per user
- **Fallback controls** - Mouse hover works if eye tracking unavailable
- **Visual feedback** - Progress bars, color changes, and LED meter show system state
- **Progress decay** - Looking away doesn't reset progress immediately
- **Graceful degradation** - Works in simulation mode without hardware
- **Safe shutdown** - Returns arms to known position on exit

---

## Preset Actions

### Main Menu Presets
- Home Position
- Left/Right Gripper Open/Closed
- Left/Right Elbow Bent/Extended
- Wave Animation (single and both arms)
- Reach Forward (Both)
- Pass Object (L to R)

### Category: Throw
1. **Prepare** - Position arm for loading
2. **Load** - Close gripper on object
3. **Launch** - Animated throwing motion with release

### Category: Kick
1. **Load** - Wind up position
2. **Strike** - Animated kick motion

### Category: Pass Object (L to R)
Step-by-step sequence for passing an object between arms with manual fine-tuning controls.

---

## Setup

See `setup_guide.md` for detailed hardware setup instructions including:
- Bluetooth pairing with NeuroSky headset
- Servo hat wiring
- Raspberry Pi configuration

---

## Authors

CS-5424 Interactive Device Design - Fall 2025
