import socket
import json

def main():
    udp_port = 1234  # Doit correspondre au port utilisé pour l'envoi
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', udp_port))
    print(f"Écoute UDP sur le port {udp_port}...")

    while True:
        data, addr = sock.recvfrom(65535)  # Taille maximale des données
        try:
            game_state = json.loads(data.decode('utf-8'))
            print(f"\nÉtat reçu de {addr}:")
            print(json.dumps(game_state, indent=4))
        except json.JSONDecodeError as e:
            print("Erreur de décodage JSON:", e)

if __name__ == "__main__":
    main()