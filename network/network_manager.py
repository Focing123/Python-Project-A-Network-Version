import socket
import json
import pickle  # Ajout de l'import pickle
import select
import time
import zlib  # Ajoutez cet import en haut du fichier
from backend.logger import debug_print
from frontend.Terrain import Gold, Wood  # Assurez-vous que le chemin d'import est correct
from backend.Units import *
from backend.Units import Villager, Swordsman, Horseman, Archer, Unit
from backend.Building import *

# Ports de communication avec le programme C
PY_TO_C_PORT = 6000      # Port où le process C reçoit les données venant du Python
C_TO_PY_PORT = 6002      # Port où le process C envoie les données (forwarded broadcast) au Python

class NetworkManager:
    def __init__(self, peer_to_peer=False):
        self.peer_to_peer = peer_to_peer
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

    def send_game_state(self, game_state, nature='data'):
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
                            'id': getattr(unit, "id", hash(f"{player.name}-{unit.__class__.__name__}-{unit.position}")),
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
            "actions": [],
            "source_ip": self.local_ip  # Ajout de l'IP source
        }
        
        try:
            # Sérialiser et compresser les données
            pickle_payload = pickle.dumps(state)
            compressed_payload = zlib.compress(pickle_payload)
            
            # Fragmenter si nécessaire (max 60000 octets par paquet)
            MAX_CHUNK_SIZE = 60000
            if len(compressed_payload) > MAX_CHUNK_SIZE:
                chunks = [compressed_payload[i:i + MAX_CHUNK_SIZE] 
                         for i in range(0, len(compressed_payload), MAX_CHUNK_SIZE)]
                for i, chunk in enumerate(chunks):
                    packet = {
                        'fragment': True,
                        'fragment_id': i,
                        'total_fragments': len(chunks),
                        'data': chunk
                    }
                    self.send_socket.sendto(pickle.dumps(packet), ("127.0.0.1", PY_TO_C_PORT))
            else:
                # Envoi direct si petit paquet
                packet = {
                    'fragment': False,
                    'data': compressed_payload
                }
                self.send_socket.sendto(pickle.dumps(packet), ("127.0.0.1", PY_TO_C_PORT))
        except socket.error as e:
            debug_print(f"Erreur lors de l'envoi UDP: {e}")

    def receive_game_state(self, timeout=0.1,applystate = True):  # Increase timeout to 100ms
        self.recv_socket.settimeout(timeout)
        fragments = {}
        try:
            while True:  # Loop to process all incoming packets
                try:
                    data, addr = self.recv_socket.recvfrom(65507)
                    packet = pickle.loads(data)
                    
                    if packet.get('fragment', False):
                        # Gestion des fragments
                        frag_id = packet['fragment_id']
                        total_frags = packet['total_fragments']
                        fragments[frag_id] = packet['data']
                        
                        # Vérifier si tous les fragments sont reçus
                        if len(fragments) == total_frags:
                            # Réassembler et décompresser
                            complete_data = b''.join(fragments[i] for i in range(total_frags))
                            decompressed_data = zlib.decompress(complete_data)
                            payload = pickle.loads(decompressed_data)
                            
                            if payload.get("type") == "game_data":
                                if applystate:
                                    self.apply_state_to_game(payload, sender_addr=addr)
                                return payload
                    else:
                        # Paquet unique
                        decompressed_data = zlib.decompress(packet['data'])
                        payload = pickle.loads(decompressed_data)
                        
                        if payload.get("type") == "game_data":
                            if applystate:
                                self.apply_state_to_game(payload, sender_addr=addr)
                            return payload
                            
                except socket.timeout:
                    return None  # Exit after timeout
        except Exception as e:
            debug_print(f"Erreur lors de la réception UDP sur le port {C_TO_PY_PORT}: {e}")
        return None

    def apply_state_to_game(self, payload, sender_addr=None):
        """Met à jour la map locale à partir du payload."""
        source_ip = payload.get("source_ip", sender_addr[0] if sender_addr else "unknown")
        
        # Ne pas appliquer les données reçues de sa propre IP
        if source_ip == self.local_ip:
            debug_print(f"Ignoré les données reçues de l'IP locale: {source_ip}")
            return

        map_state = payload.get("map", {})
        if self.local_map is not None:
            # MàJ des ressources
            resources_state = map_state.get("resources", {})
            # Traiter chaque type de ressource (wood et gold)
            for resource_type, resources in resources_state.items():
                resource_type = resource_type.capitalize()  # Convertir en "Wood" ou "Gold"
                if not isinstance(resources, list):
                    debug_print(f"Structure des resources invalide pour {resource_type}")
                    continue
                for resource_data in resources:
                    if len(resource_data) != 3:
                        continue  
                    x, y, amount = resource_data
                    # Vérifier si la ressource existe déjà à cette position
                    if resource_type not in self.local_map.resources:
                        self.local_map.resources[resource_type] = []
                    if (x, y) not in self.local_map.resources[resource_type]:
                        self.local_map.resources[resource_type].append((x, y))
                        #debug_print(f"Nouvelle ressource ajoutée de type {resource_type} à ({x}, {y}) avec quantité {amount}")
                        # Créer et placer la ressource sur la grille
                        if y < len(self.local_map.grid) and x < len(self.local_map.grid[y]):
                            resource_obj = Gold() if resource_type == "Gold" else Wood() if resource_type == "Wood" else None
                            if resource_obj is not None:
                                resource_obj.amount = amount
                                self.local_map.grid[y][x].resource = resource_obj

            # MàJ des joueurs et de leurs unités
            players_state = payload.get("players", [])
            
            for player in players_state:
                # Utiliser l'IP source comme identifiant unique
                player_key = (source_ip, player.get("id"))
                if player_key in self.remote_players:
                    remote_player = self.remote_players[player_key]
                else:
                    remote_player = RemotePlayer((source_ip, 0), name=f"Remote-{source_ip}-{player.get('id')}")
                    remote_player.id = player.get("id") or remote_player.id
                    self.remote_players[player_key] = remote_player

                unit_mapping = {
                    "Villager": Villager,
                    "Swordsman": Swordsman,
                    "Horseman": Horseman,
                    "Archer": Archer,
                    "Unit": Unit
                }
                units_state = player.get("units", [])
                # Créer un set pour suivre les unités existantes
                existing_unit_ids = set()
                
                # Nettoyer les unités qui n'existent plus
                units_to_remove = []
                for unit_id, unit in remote_player.units.items():
                    if any(u_state.get("id") == unit_id for u_state in units_state):
                        existing_unit_ids.add(unit_id)
                    else:
                        units_to_remove.append(unit_id)
                        # Retirer l'unité de sa tile actuelle
                        if hasattr(unit, "position"):
                            x, y = unit.position
                            if 0 <= y < len(self.local_map.grid) and 0 <= x < len(self.local_map.grid[y]):
                                tile = self.local_map.grid[y][x]
                                if hasattr(tile, "unit") and unit in tile.unit:
                                    tile.unit.remove(unit)

                # Supprimer les unités qui n'existent plus
                for unit_id in units_to_remove:
                    del remote_player.units[unit_id]

                # Mettre à jour ou créer les unités
                for unit_state in units_state:
                    unit_id = unit_state.get("id")
                    if unit_id is None:
                        continue

                    pos = unit_state.get("position")
                    if pos is None:
                        continue

                    x, y = pos
                    # Vérifier si l'unité existe déjà
                    existing_unit = remote_player.units.get(unit_id)
                    
                    if existing_unit:
                        # Mettre à jour l'unité existante
                        old_pos = existing_unit.position
                        if old_pos != tuple(pos):
                            # Retirer l'unité de son ancienne position
                            old_x, old_y = old_pos
                            if 0 <= old_y < len(self.local_map.grid) and 0 <= old_x < len(self.local_map.grid[old_y]):
                                old_tile = self.local_map.grid[old_y][old_x]
                                if hasattr(old_tile, "unit") and existing_unit in old_tile.unit:
                                    old_tile.unit.remove(existing_unit)
                            
                            # Placer l'unité à sa nouvelle position
                            if 0 <= y < len(self.local_map.grid) and 0 <= x < len(self.local_map.grid[y]):
                                new_tile = self.local_map.grid[y][x]
                                if not hasattr(new_tile, "unit") or new_tile.unit is None:
                                    new_tile.unit = []
                                new_tile.unit.append(existing_unit)
                                existing_unit.position = tuple(pos)
                        
                        # Mettre à jour les autres attributs
                        existing_unit.hp = unit_state.get("hp")
                        existing_unit.target_position = unit_state.get("target_position")
                        existing_unit.target_attack = unit_state.get("target_attack")
                        existing_unit.is_attacked_by = unit_state.get("is_attacked_by")
                        existing_unit.direction = unit_state.get("direction")
                        existing_unit.current_frame = unit_state.get("current_frame")
                        existing_unit.frame_counter = unit_state.get("frame_counter")
                        existing_unit.is_moving = unit_state.get("is_moving")
                        existing_unit.task = unit_state.get("task")
                    
                    else:
                        # Créer une nouvelle unité
                        if 0 <= y < len(self.local_map.grid) and 0 <= x < len(self.local_map.grid[y]):
                            tile = self.local_map.grid[y][x]
                            unit_class_name = unit_state.get("class")
                            unit_cls = unit_mapping.get(unit_class_name)
                            if unit_cls is None:
                                debug_print(f"Classe d'unité non reconnue: {unit_class_name}")
                                continue

                            unit = unit_cls(player=remote_player, position=tuple(pos))
                            unit.id = unit_id
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
                            remote_player.units[unit_id] = unit
                            #debug_print(f"Nouvelle unité {unit_id} ajoutée dans la tile ({x}, {y}) pour le joueur {remote_player.name}.")
                        
                # MàJ des bâtiments
                buildings_state = player.get("buildings", [])
                for building_state in buildings_state:
                    building_name = building_state.get("name")
                    position = building_state.get("position")
                    hp = building_state.get("hp")
                    is_attacked = building_state.get("is_attacked", False)

                    if not building_name or not position:
                        continue

                    # Vérifier si le bâtiment existe déjà à cette position
                    x, y = position
                    existing_building = None
                    if 0 <= y < len(self.local_map.grid) and 0 <= x < len(self.local_map.grid[y]):
                        tile = self.local_map.grid[y][x]
                        if hasattr(tile, 'building') and tile.building:
                            existing_building = tile.building

                    if not existing_building:
                        # Créer et placer le nouveau bâtiment
                        building = None
                        if building_name == "TownCenter":
                            building_cls = TownCenter
                        elif building_name == "Barracks":
                            building_cls = Barracks
                        elif building_name == "Stable":
                            building_cls = Stable
                        elif building_name == "ArcheryRange":
                            building_cls = ArcheryRange
                        elif building_name == "Farm":
                            building_cls = Farm
                        elif building_name == "House":
                            building_cls = House
                        elif building_name == "Keep":
                            building_cls = Keep
                        elif building_name == "Camp":
                            building_cls = Camp
                        if building_cls:    
                            building = building_cls()
                        if building:
                            building.position = position
                            building.hp = hp
                            building.is_attacked = is_attacked
                            # Utiliser la méthode place_building de la map
                            self.local_map.place_building(building, position[0], position[1])
                            print(f"Nouvelle construction {building_name} ajoutée dans la tile ({x}, {y}) pour le joueur {remote_player.name}.")
                    else:
                        # Mettre à jour les attributs du bâtiment existant
                        existing_building.hp = hp
                        existing_building.is_attacked = is_attacked

    def close(self):
        """Ferme les sockets réseau."""
        self.send_socket.close()
        self.recv_socket.close()

class RemotePlayer:
    def __init__(self, addr, name=None):
        self.addr = addr
        self.units = {}
        if name is None:
            self.name = f"Remote-{addr[0]}:{addr[1]}"
        else:
            self.name = name
        self.id = abs(hash(self.name)) % 100