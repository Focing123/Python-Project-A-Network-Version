import socket

class NetworkManager:
    def __init__(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.broadcast_address = ("<broadcast>", 12345)

    def _serialize_unit(self, unit):
        """Sérialise une unité en chaîne de caractères avec ses attributs."""
        keys = ['player', 'hp', 'position', 'target_position', 'target_attack',
                'is_attacked_by', 'spawn_building', 'spawn_position', 'direction',
                'current_frame', 'frame_counter', 'is_moving']
        # Pour chaque clé, on récupère la valeur ou "None" si absente.
        return ",".join(f"{k}:{unit.get(k, 'None')}" for k in keys)

    def _serialize_building(self, building):
        """Sérialise un bâtiment en chaîne de caractères avec ses attributs."""
        keys = ['name', 'hp', 'built', 'position', 'is_attacked']
        return ",".join(f"{k}:{building.get(k, 'None')}" for k in keys)

    def _serialize_state(self, state_dict):
        """Convertit un dictionnaire en chaîne de caractères."""
        parts = []
        parts.append(f"map={state_dict['map']}")
        
        for player in state_dict['players']:
            player_str = f"player:name={player['name']}"
            units_str = ";".join(self._serialize_unit(u) for u in player['units'])
            buildings_str = ";".join(self._serialize_building(b) for b in player['buildings'])
            resources_str = ",".join(f"{k}:{v}" for k, v in player['resources'].items())
            player_str += f"|units={units_str}|buildings={buildings_str}|resources={resources_str}"
            parts.append(player_str)
        
        return "||".join(parts)

    def send_game_state(self, game_state):
        """Envoie l'état du jeu via UDP."""
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
                    "units": [
                        {
                            "player": getattr(unit, "player", None),
                            "hp": getattr(unit, "hp", None),
                            "position": getattr(unit, "position", None),
                            "target_position": getattr(unit, "target_position", None),
                            "target_attack": getattr(unit, "target_attack", None),
                            "is_attacked_by": getattr(unit, "is_attacked_by", None),
                            "spawn_building": getattr(unit, "spawn_building", None),
                            "spawn_position": getattr(unit, "spawn_position", None),
                            "direction": getattr(unit, "direction", "south"),
                            "current_frame": getattr(unit, "current_frame", 0),
                            "frame_counter": getattr(unit, "frame_counter", 0),
                            "is_moving": getattr(unit, "is_moving", False)
                        }
                        for unit in getattr(player, "units", [])
                    ],
                    "buildings": [
                        {
                            "name": getattr(b, "name", "Unknown"),
                            "hp": getattr(b, "hp", None),
                            "built": getattr(b, "built", False),
                            "position": getattr(b, "position", None),
                            "is_attacked": getattr(b, "is_attacked", False)
                        }
                        for b in getattr(player, "buildings", [])
                    ],
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
        """Ferme la connexion réseau."""
        self.udp_socket.close()
