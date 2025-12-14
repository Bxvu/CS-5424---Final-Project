import socket
import time
import sys
import pi_servo_hat
import time
import re
import threading

# CONFIGURATION
MAC_ADDRESS = "9C:54:1C:00:A7:15"  # Your Device
CHANNEL = 2  # <--- CHANGE THIS if sdptool showed a different channel (e.g. 2, 3)
SERVO_MIN = 0
SERVO_MAX = 180
SERVO_CH = 0  # Channel 0 by default
SERVO_CH2 = 1  # Channel 0 by default
SERVO_CH3 = 0  # Channel 0 by default

servo = pi_servo_hat.PiServoHat()
servo.restart()
global angle
angle = 0
print(f"Sweeping servo on channel {SERVO_CH} from {SERVO_MIN} to {SERVO_MAX} degrees...")

def servo_worker():
    global angle
    current_angle = angle
    while True:
        diff = angle - current_angle
        # Only move if difference is significant
        if abs(diff) > 0.5:
            # Smooth easing: move 10% of the distance each step
            # Adjust 0.1 to change speed (lower = slower/smoother, higher = faster)
            current_angle += diff * 0.1
            servo.move_servo_position(SERVO_CH, current_angle)
        time.sleep(0.02) # 50Hz update rate

def parse_payload(payload):
    global angle
    i = 0
    while i < len(payload):
        code = payload[i]
        if code == 0x02: # Signal Quality
            if i+1 < len(payload):
                print(f"Signal Quality: {payload[i+1]} (0 is Best)")
            i += 2
        elif code == 0x04: # Attention
            if i+1 < len(payload):
                if payload[i+1] >= 55:
                    if angle < SERVO_MAX:
                        angle += 10
                    # Clamp to valid range
                    if angle < SERVO_MIN:
                        angle = SERVO_MIN
                    if angle > SERVO_MAX:
                        angle = SERVO_MAX
                    print(f"angle:{angle}")
                    # servo.move_servo_position(SERVO_CH, angle)
                    # time.sleep(0.01)
                elif payload[i+1] <= 30:
                    if angle > SERVO_MIN:
                        angle -= 5
                    # Clamp to valid range
                    if angle < SERVO_MIN:
                        angle = SERVO_MIN
                    if angle > SERVO_MAX:
                        angle = SERVO_MAX
                    print(f"angle:{angle}")
                    # servo.move_servo_position(SERVO_CH, angle)
                    # time.sleep(0.01)
                print(f"--> ATTENTION: {payload[i+1]}")
            i += 2
        elif code == 0x05: # Meditation
            if i+1 < len(payload):
                print(f"--> MEDITATION: {payload[i+1]}")
            i += 2
        elif code == 0x83: # EEG Power
            i += 25
        elif code == 0x80: # Raw Wave
            i += 3
        else:
            i += 1


def main():
    print(f"--- NEUROSKY SOCKET CLIENT ---")
    print(f"Target: {MAC_ADDRESS} on Channel {CHANNEL}")
    print("1. Ensure headset is BLINKING (not connected to anything else).")
    print("------------------------------")

    # Start smoothing thread
    t = threading.Thread(target=servo_worker)
    t.daemon = True
    t.start()

    sock = None
    
    # 1. CONNECT
    while True:
        try:
            print(f"Attempting connection to Channel {CHANNEL}...", end='')
            sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            sock.connect((MAC_ADDRESS, CHANNEL))
            print("\n>>> SUCCESS! Socket Connected <<<")
            break
        except OSError as e:
            print(f"\nError: {e}")
            print("Retrying in 2 seconds...")
            time.sleep(2)
            if sock: sock.close()
        except KeyboardInterrupt:
            print("\nStopping.")
            return

    # 2. READ LOOP
    print("Waiting for data stream...")
    buffer = b''
    last_data_time = time.time()
    
    try:
        while True:
            # Set a timeout so we can detect silence
            sock.settimeout(2.0) 
            
            try:
                data = sock.recv(1024)
                if not data:
                    print("Socket closed by remote device.")
                    break
                
                # Reset silence timer
                last_data_time = time.time()
                
                # Visualize raw bytes if we are stuck
                # print(f"{data.hex().upper()} ", end='', flush=True) 
                
                buffer += data
                
                # Parse Buffer for Sync Bytes AA AA
                while len(buffer) >= 3:
                    if buffer[0] == 0xAA and buffer[1] == 0xAA:
                        payload_len = buffer[2]
                        if len(buffer) >= 3 + payload_len + 1:
                            payload = buffer[3 : 3+payload_len]
                            parse_payload(payload)
                            buffer = buffer[3+payload_len+1:]
                        else:
                            break
                    else:
                        buffer = buffer[1:]
                        
            except socket.timeout:
                print(".", end='', flush=True)
                # If silent for too long, try sending a "Wake up" byte
                if time.time() - last_data_time > 5:
                    print("\n[!] Silence detected. Sending wake-up trigger...")
                    try:
                        sock.send(b'\x00') # Try null byte
                    except:
                        pass
                    last_data_time = time.time()

    except KeyboardInterrupt:
        print("\nClosing.")
        sock.close()

if __name__ == "__main__":
    main()