import socket
import json
import time
import argparse

def send_event(ip, port, event_id, event_type, message):
    """Send a game event to the specified IP and port."""
    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Create event data
    event_data = {
        "id": event_id,
        "type": event_type,
        "message": message
    }
    
    # Convert to JSON and encode
    json_data = json.dumps(event_data)
    
    # Send the data
    sock.sendto(json_data.encode('utf-8'), (ip, port))
    print(f"Sent event to {ip}:{port}: {json_data}")
    
    # Close socket
    sock.close()

def main():
    parser = argparse.ArgumentParser(description="Send test game events via UDP")
    parser.add_argument("--ip", default="127.0.0.1", help="Destination IP address")
    parser.add_argument("--port", type=int, default=12346, help="Destination port")
    args = parser.parse_args()
    
    # Send a few test events
    for i in range(5):
        event_id = i + 1
        event_type = (i % 3) + 1  # Different types of events
        message = f"Test event {event_id} of type {event_type}"
        
        send_event(args.ip, args.port, event_id, event_type, message)
        time.sleep(1)  # Wait between events

if __name__ == "__main__":
    main()