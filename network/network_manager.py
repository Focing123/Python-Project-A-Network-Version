import socket
import json
from backend.logger import debug_print

class NetworkManager:
    def __init__(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.broadcast_address = ("<broadcast>", 12345)

    def send_game_state(self, game_state):
        """Envoie l'état du jeu via UDP"""
        try:
            map_state = game_state.map.get_state()
        except AttributeError:
            map_state = "Etat de la map non défini"

        players_state = []
        for player in game_state.players:
            try:
                p_state = player.get_state()
            except AttributeError:
                p_state = {
                    "name": getattr(player, "name", "inconnu"),
                    "units": [{"position": unit.position} for unit in getattr(player, "units", [])],
                    "buildings": [{"position": b.position} for b in getattr(player, "buildings", [])],
                    "resources": getattr(player, "owned_resources", {})
                }
            players_state.append(p_state)

        state = {
            "turn": game_state.turn,
            "map": map_state,
            "players": players_state,
            "actions": []
        }

        json_payload = json.dumps(state)
        try:
            self.udp_socket.sendto(json_payload.encode("utf-8"), self.broadcast_address)
            debug_print("Etat multijoueur envoyé via UDP.")
        except Exception as e:
            debug_print(f"Erreur lors de l'envoi UDP: {e}")

    def close(self):
        """Ferme la connexion réseau"""
        self.udp_socket.close()
