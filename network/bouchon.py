import socket
import time

BROADCAST_IP = "255.255.255.255"  # Broadcast global (ou 192.168.1.255 selon le réseau)
BROADCAST_PORT = 12347  # LISTEN_PORT du proxy

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Active le mode broadcast

try:
    for i in range(5):  # Envoie 5 événements en broadcast
        message = f"Événement {i+1}"
        print(f"📡 Envoi en broadcast : {message}")
        sock.sendto(message.encode(), (BROADCAST_IP, BROADCAST_PORT))
        time.sleep(1)

finally:
    sock.close()
