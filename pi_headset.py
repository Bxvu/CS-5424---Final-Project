import socket
import time
import sys

# CONFIGURATION
MAC_ADDRESS = "9C:54:1C:00:A7:15"  # Your Device
CHANNEL = 2  # <--- CHANGE THIS if sdptool showed a different channel (e.g. 2, 3)

def parse_payload(payload):
    i = 0
    while i < len(payload):
        code = payload[i]
        if code == 0x02: # Signal Quality
            if i+1 < len(payload):
                print(f"Signal Quality: {payload[i+1]} (0 is Best)")
            i += 2
        elif code == 0x04: # Attention
            if i+1 < len(payload):
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
