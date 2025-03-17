import socket

class NetworkManager:
    def __init__(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.broadcast_address = ("<broadcast>", 12345)

    def _serialize_state(self, state_dict):
        """Convertit un dictionnaire en chaîne de caractères"""
        parts = []
        parts.append(f"map={state_dict['map']}")
        
        for player in state_dict['players']:
            player_str = f"player:name={player['name']}"
            units_str = ",".join(f"{u['position']}" for u in player['units'])
            buildings_str = ",".join(f"{b['position']}" for b in player['buildings'])
            resources_str = ",".join(f"{k}:{v}" for k, v in player['resources'].items())
            player_str += f"|units={units_str}|buildings={buildings_str}|resources={resources_str}"
            parts.append(player_str)
        
        return "||".join(parts)

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
            "map": map_state,
            "players": players_state,
        }

        payload = self._serialize_state(state)
        try:
            self.udp_socket.sendto(payload.encode("utf-8"), self.broadcast_address)
            print("Etat multijoueur envoyé via UDP.")
        except Exception as e:
            print(f"Erreur lors de l'envoi UDP: {e}")

    def close(self):
        """Ferme la connexion réseau"""
        self.udp_socket.close()
