import socket
import json

def deserialize_state(serialized_str):
    """
    Convertit une chaîne de caractères sérialisée en dictionnaire.
    Format attendu:
    "map=<map_state>||player:name=<name>|units=<units_str>|buildings=<buildings_str>|resources=<resources_str>||..."
    """
    state = {}
    try:
        parts = serialized_str.split("||")
        # Traitement de la partie map
        map_part = parts[0]
        key, val = map_part.split("=", 1)
        if key != "map":
            raise ValueError("Format incorrect pour la map")
        state['map'] = val
        
        players = []
        for part in parts[1:]:
            if not part.startswith("player:"):
                continue
            # Supprime le préfixe "player:" et découpe par "|"
            player_data = part[len("player:"):].split("|")
            player_dict = {}
            for data in player_data:
                if "=" in data:
                    k, v = data.split("=", 1)
                    if k in ["units", "buildings"]:
                        player_dict[k] = v.split(",") if v else []
                    elif k == "resources":
                        res = {}
                        if v:
                            for item in v.split(","):
                                if ':' in item:
                                    rk, rv = item.split(":",1)
                                    res[rk] = rv
                        player_dict[k] = res
                    else:
                        player_dict[k] = v
            players.append(player_dict)
        state['players'] = players
    except Exception as e:
        print("Erreur lors de la désérialisation:", e)
        state = None
    return state

def main():
    udp_port = 12345  # Doit correspondre au port utilisé pour l'envoi
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', udp_port))
    print(f"Écoute UDP sur le port {udp_port}...")

    while True:
        data, addr = sock.recvfrom(65535)  # Taille maximale des données
        try:
            serialized_state = data.decode('utf-8')
            game_state = deserialize_state(serialized_state)
            if game_state is None:
                print(f"Erreur de désérialisation de {addr}")
                continue
            print(f"\nÉtat reçu de {addr}:")
            print("Map:", game_state.get("map"))
            for player in game_state.get("players", []):
                print("Player:")
                for key, value in player.items():
                    print(f"  {key}: {value}")
        except Exception as e:
            print("Erreur lors du traitement du message:", e)

if __name__ == "__main__":
    main()