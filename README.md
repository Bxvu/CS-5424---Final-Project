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
                                                               │
                                                               ▼
                                                      ┌─────────────────┐
                                                      │   Robot Arms    │
                                                      │  (10 Servos)    │
                                                      └─────────────────┘
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
├── guesture_servo.py         # Finger-count servo selection
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

A fullscreen Tkinter application with two control modes:

**Preset Mode (Default):**
- Pre-defined arm poses (Home, Wave, Throw, Kick, etc.)
- Look at a preset button → dwell for 1.5s → focus to activate

**Manual Mode:**
- Fine-grained control of each servo
- Each joint has +/- buttons for increment/decrement
- Supports both arms (10 servos total)

**Servo Mapping:**
| Arm | Joint | Channel |
|-----|-------|---------|
| Left | Base | 0 |
| Left | Shoulder | 1 |
| Left | Elbow | 2 |
| Left | Wrist | 3 |
| Left | Gripper | 4 |
| Right | Base | 15 |
| Right | Shoulder | 14 |
| Right | Elbow | 13 |
| Right | Wrist | 12 |
| Right | Gripper | 11 |

### 4. Rock-Paper-Scissors Demo

**File:** `rsp_game/rsp.py`

A demonstration game showing the system's capabilities:

1. User looks at Rock, Paper, or Scissors
2. Dwell + focus triggers selection
3. Left arm displays user's choice
4. Right arm displays random computer choice
5. Winner determined and displayed

**Servo Gestures:**
| Gesture | Gripper Angle | Description |
|---------|---------------|-------------|
| Rock | 180° | Closed fist |
| Paper | 0° | Open hand |
| Scissors | 90° | Half open |

---

## Hardware Requirements

- **Raspberry Pi** (tested on Pi 4)
- **SparkFun Pi Servo Hat** (PCA9685-based)
- **NeuroSky MindWave Mobile** EEG headset
- **USB Webcam** (for eye tracking)
- **2x Robot Arms** with 5 servos each

---

## Software Dependencies

```bash
pip install -r requirements.txt
```

Key dependencies:
- `mediapipe` - Face mesh and iris detection
- `opencv-python` - Video capture and processing
- `sparkfun-pi-servo-hat` - Servo control
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
| Exit fullscreen | Press `ESC` |
| Quit application | Press `ESC` or close window |

---

## Interaction Flow

```
1. LOOK → Gaze determines which widget is targeted
           (progress bar starts filling)

2. DWELL → Keep looking for 1.5 seconds
           (progress bar fills up)

3. FOCUS → Concentrate to trigger action
           (attention level must exceed threshold)

4. ACTION → Servo moves / preset activates / selection confirmed
```

---

## Accessibility Features

This system was designed with accessibility in mind:

- **Hands-free operation** - No physical buttons or touch required
- **Adjustable thresholds** - Attention threshold can be tuned per user
- **Fallback controls** - Mouse hover works if eye tracking unavailable
- **Visual feedback** - Progress bars and color changes show system state
- **Graceful degradation** - Works in simulation mode without hardware

---

## Setup

See `setup_guide.md` for detailed hardware setup instructions including:
- Bluetooth pairing with NeuroSky headset
- Servo hat wiring
- Raspberry Pi configuration

---

## Authors

CS-5424 Interactive Device Design - Fall 2025
