import socket
import json
import select
import time
from backend.logger import debug_print
from frontend.Terrain import Gold, Wood  # Assurez-vous que le chemin d'import est correct
from backend.Units import *
from backend.Units import Villager, Swordsman, Horseman, Archer, Unit

# Ports de communication avec le programme C
PY_TO_C_PORT = 6000      # Port où le process C reçoit les données venant du Python
C_TO_PY_PORT = 6002      # Port où le process C envoie les données (forwarded broadcast) au Python

class NetworkManager:
    def __init__(self, peer_to_peer=False, is_server=True):
        self.peer_to_peer = peer_to_peer
        self.is_server = is_server  # Définition de l'attribut is_server
        # Socket pour envoyer les données vers le programme C
        self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Socket pour recevoir les messages du programme C
        self.recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.recv_socket.bind(('', C_TO_PY_PORT))
        except Exception as e:
            debug_print(f"Erreur lors du bind du socket de réception sur le port {C_TO_PY_PORT}: {e}")
        # Récupérer l'IP réelle
        self.local_ip = self.get_local_ip()
        # les autres parties du code restent inchangées
        self.local_map = None
        self.remote_players = {}  # Dictionnaire: { addr: RemotePlayer }

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    def validate_peers(self):
        """Validation des pairs désactivée en mode relais C."""
        debug_print("Validation des pairs désactivée en mode relais C.")
            
    def run_peer_discovery(self, timeout=5):
        """La découverte des pairs est désactivée en mode relais C."""
        debug_print("La découverte des pairs est désactivée en mode relais C.")
        return True

    def handle_incoming_discovery(self):
        """Traite en boucle les demandes de découverte entrantes.
        La découverte des pairs est désactivée en mode relais C."""
        debug_print("handle_incoming_discovery: découverte des pairs désactivée en mode relais C.")

    def send_game_state(self, game_state, nature='data'):
        """Envoie l'état du jeu vers le programme C via UDP (port non-broadcast)."""
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
                            'player': getattr(player, "name", None),
                            "class": unit.__class__.__name__,
                            "hp": getattr(unit, "hp", None),
                            "position": getattr(unit, "position", None),
                            "target_position": getattr(unit, "target_position", None),
                            "target_attack": getattr(unit, "target_attack", None),
                            "is_attacked_by": getattr(unit, "is_attacked_by", None),
                            "direction": getattr(unit, "direction", "south"),
                            "current_frame": getattr(unit, "current_frame", 0),
                            "frame_counter": getattr(unit, "frame_counter", 0),
                            "is_moving": getattr(unit, "is_moving", False),
                            "task": getattr(unit, "task", None)
                        }
                        for unit in getattr(player, "units", [])
                    ],
                    "buildings": [
                        {
                            "name": getattr(b, "name", None),
                            "hp": getattr(b, "hp", None),
                            "position": getattr(b, "position", None),
                            "is_attacked": getattr(b, "is_attacked", False)
                        }
                        for b in getattr(player, "buildings", [])
                    ],
                    "resources": getattr(player, "owned_resources", {})
                }
            players_state.append(p_state)

        state = {
            "type": "game_data",
            "map": map_state,
            "width": getattr(game_state.map, "width", 0),
            "height": getattr(game_state.map, "height", 0),
            "players": players_state,
            "actions": []
        }
        json_payload = json.dumps(state)
        try:
            # Envoie vers le programme C en local (pas de broadcast ici)
            self.send_socket.sendto(json_payload.encode("utf-8"), ("127.0.0.1", PY_TO_C_PORT))
            debug_print("État du jeu envoyé au programme C.")
        except socket.error as e:
            debug_print(f"Erreur lors de l'envoi UDP vers le programme C: {e}")

    def receive_game_state(self, timeout=0.001):
        """Reçoit l'état du jeu envoyé par le programme C via UDP (données broadcast forwardées)."""
        self.recv_socket.settimeout(timeout)
        try:
            data, addr = self.recv_socket.recvfrom(65507)
            payload = json.loads(data.decode('utf-8'))
            if payload.get("type") == "game_data":
                debug_print(f"État multijoueur reçu via le programme C depuis {addr}.")
                self.apply_state_to_game(payload, sender_addr=addr)
                return payload
        except socket.timeout:
            return None
        except Exception as e:
            debug_print(f"Erreur lors de la réception UDP sur le port {C_TO_PY_PORT}: {e}")
        return None

    def apply_state_to_game(self, payload, sender_addr=None):
        """Met à jour la map locale à partir du payload.
        Les unités des joueurs distants sont recréées et mises à jour dans la map."""
        map_state = payload.get("map", {})
        if self.local_map is not None:
            # MàJ des ressources
            remote_resources = map_state.get("resources", [])
            if not isinstance(remote_resources, list):
                debug_print("Structure des resources invalide, attendu une liste.")
                return
            for resource in remote_resources:
                res_type = resource.get("type")
                x, y = resource.get("coordinates", (None, None))
                amount = resource.get("amount")
                if res_type and x is not None and y is not None:
                    if res_type not in self.local_map.resources:
                        self.local_map.resources[res_type] = []
                    if (x, y) not in self.local_map.resources[res_type]:
                        self.local_map.resources[res_type].append((x, y))
                        debug_print(f"Nouvelle resource ajoutée de type {res_type} à ({x}, {y}) avec quantité {amount}.")
                        if y < len(self.local_map.grid) and x < len(self.local_map.grid[y]):
                            resource_obj = Gold() if res_type == "Gold" else Wood() if res_type == "Wood" else None
                            if resource_obj is not None:
                                resource_obj.amount = amount
                                self.local_map.grid[y][x].resource = resource_obj

            # MàJ des joueurs et de leurs unités
            players_state = payload.get("players", [])
            if not isinstance(players_state, list):
                debug_print("Structure des joueurs invalide, attendu une liste.")
                return
            unit_mapping = {
                "Villager": Villager,
                "Swordsman": Swordsman,
                "Horseman": Horseman,
                "Archer": Archer,
                "Unit": Unit
            }
            for player in players_state:
                player_key = player.get("id") or sender_addr
                if player_key in self.remote_players:
                    remote_player = self.remote_players[player_key]
                else:
                    remote_player = RemotePlayer(sender_addr)
                    remote_player.id = player.get("id") or remote_player.id
                    self.remote_players[player_key] = remote_player

                units_state = player.get("units", [])
                for unit_state in units_state:
                    pos = unit_state.get("position")
                    if pos is not None:
                        x, y = pos
                        if 0 <= y < len(self.local_map.grid) and 0 <= x < len(self.local_map.grid[y]):
                            tile = self.local_map.grid[y][x]
                            unit_class_name = unit_state.get("class")
                            unit_cls = unit_mapping.get(unit_class_name)
                            if unit_cls is None:
                                debug_print(f"Classe d'unité non reconnue: {unit_class_name}")
                                continue
                            unit = unit_cls(player=remote_player, position=tuple(unit_state.get("position", (0, 0))))
                            unit.hp = unit_state.get("hp")
                            unit.target_position = unit_state.get("target_position")
                            unit.target_attack = unit_state.get("target_attack")
                            unit.is_attacked_by = unit_state.get("is_attacked_by")
                            unit.direction = unit_state.get("direction")
                            unit.current_frame = unit_state.get("current_frame")
                            unit.frame_counter = unit_state.get("frame_counter")
                            unit.is_moving = unit_state.get("is_moving")
                            unit.task = unit_state.get("task")
                            
                            if not hasattr(tile, "unit") or tile.unit is None:
                                tile.unit = []
                            tile.unit.append(unit)
                            debug_print(f"Unité ajoutée dans la tile ({x}, {y}) pour le joueur {remote_player.name}.")

    def close(self):
        """Ferme les sockets réseau."""
        self.send_socket.close()
        self.recv_socket.close()

class RemotePlayer:
    def __init__(self, addr, name=None):
        self.addr = addr
        if name is None:
            self.name = f"Remote-{addr[0]}:{addr[1]}"
        else:
            debug_print("***************************************")
            self.name = name
        self.id = abs(hash(self.name)) % 100