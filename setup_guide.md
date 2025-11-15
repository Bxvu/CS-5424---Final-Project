# Star Wars Force Trainer II - Raspberry Pi 5 Setup Guide
Prerequisites:
- Raspberry Pi 5
- Star Wars Force Trainer II Headset
- Python 3

## Step 1: Enable Bluetooth Legacy Mode 
### (CRITICAL) The Pi 5 uses modern Bluetooth (BLE), but the headset uses an older standard. We must force the Pi to speak the old language.

Open the Bluetooth configuration file:

```bash
sudo nano /etc/bluetooth/main.conf
```

Scroll down the [General] section. Look for ControllerMode.

Change (or add) this line to set it to bredr (Basic Rate/Enhanced Data Rate):

```toml
# ControllerMode = dual  <-- Change this
ControllerMode = bredr
```

Save and Exit: Press Ctrl+O, Enter, then Ctrl+X.

Restart Bluetooth:

```bash
sudo systemctl restart bluetooth
```

## Step 2: Pair the Headset

Turn on the Force Trainer II headset (LED should be blinking).

Open the Bluetooth CLI:

```bash
sudo bluetoothctl
```

Run the following sequence:

```bash
# 1. Enable scanning
scan on

# Wait for "Force Trainer II" or "NeuroSky" to appear.
# Copy the MAC ADDRESS (e.g., 9C:54:1C:00:A7:15)

# 2. Pair (Replace with your MAC address)
pair 9C:54:1C:00:A7:15
# If asked for a PIN, enter 0000

# 3. Trust (Essential for auto-reconnect)
trust 9C:54:1C:00:A7:15

# 4. Exit
exit
```

# Step 3: Set Up Python Virtual Environment

Creating a virtual environment isolates the project dependencies and prevents conflicts with system packages.

Navigate to the project directory:

```bash
cd /home/pi/CS-5424---Final-Project/
```

Create a virtual environment:

```bash
python3 -m venv venv
```

Activate the virtual environment:

```bash
source venv/bin/activate
```

You should see `(venv)` appear at the beginning of your terminal prompt, indicating the virtual environment is active.

## Step 4: Install Dependencies

With the virtual environment activated, install the required packages:

```bash
pip install -r requirements.txt
```

**Note**: Always activate the virtual environment before running the project:
```bash
source venv/bin/activate
```

To deactivate the virtual environment when done:
```bash
deactivate
```

## Step 5: Run the Program

Turn on the headset, then run

```bash
python pi_headset.py
```
