import socket
import time
import threading

class HeadsetClient:
    def __init__(self, mac_address="9C:54:1C:00:A7:15", channel=2):
        self.mac_address = mac_address
        self.channel = channel
        self.attention = 0
        self.meditation = 0
        self.signal_quality = 0
        self.connected = False
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)

    def get_attention(self):
        with self.lock:
            return self.attention

    def _read_loop(self):
        sock = None
        print(f"HeadsetClient: Connecting to {self.mac_address} on channel {self.channel}...")
        
        while self.running:
            # Try to connect if not connected
            if sock is None:
                try:
                    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
                    sock.connect((self.mac_address, self.channel))
                    sock.settimeout(2.0)
                    self.connected = True
                    print("HeadsetClient: Connected!")
                except Exception as e:
                    # print(f"HeadsetClient: Connection failed ({e}). Retrying...")
                    if sock:
                        sock.close()
                    sock = None
                    time.sleep(2)
                    continue

            # Read data
            try:
                data = sock.recv(1024)
                if not data:
                    print("HeadsetClient: Socket closed.")
                    sock.close()
                    sock = None
                    self.connected = False
                    continue
                
                self._parse_data(data)
                
            except socket.timeout:
                continue
            except Exception as e:
                print(f"HeadsetClient: Error reading data: {e}")
                sock.close()
                sock = None
                self.connected = False
                time.sleep(1)

    def _parse_data(self, data):
        # Simple parser based on the provided example
        # We are looking for the sync bytes AA AA and then the payload
        # This is a simplified stream parser that might miss packets split across reads, 
        # but sufficient for this context if packets are small.
        
        # In a robust implementation, we would buffer data. 
        # For now, let's scan the chunk for the codes we care about.
        
        i = 0
        while i < len(data) - 1:
            # Look for sync bytes? Or just scan for codes if we trust the stream alignment?
            # The original code parsed payloads after AA AA.
            # Let's try to find AA AA
            if data[i] == 0xAA and data[i+1] == 0xAA:
                if i + 2 < len(data):
                    payload_len = data[i+2]
                    if i + 3 + payload_len <= len(data):
                        payload = data[i+3 : i+3+payload_len]
                        self._parse_payload(payload)
                        i += 3 + payload_len
                        continue
            i += 1

    def _parse_payload(self, payload):
        i = 0
        while i < len(payload):
            code = payload[i]
            if code == 0x02: # Signal Quality
                if i+1 < len(payload):
                    with self.lock:
                        self.signal_quality = payload[i+1]
                i += 2
            elif code == 0x04: # Attention
                if i+1 < len(payload):
                    with self.lock:
                        self.attention = payload[i+1]
                    # print(f"Attention: {self.attention}")
                i += 2
            elif code == 0x05: # Meditation
                if i+1 < len(payload):
                    with self.lock:
                        self.meditation = payload[i+1]
                i += 2
            elif code == 0x83: # EEG Power
                i += 25
            elif code == 0x80: # Raw Wave
                i += 3
            else:
                i += 1
