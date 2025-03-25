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
import threading
import time
import heapq
import uuid

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
        self.properties_manager = NetworkPropertiesManager(self)
        # Générer un ID unique pour ce nœud réseau
        self.node_id = str(uuid.uuid4())
        self.object_states = {}  # Pour stocker les états des objets

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
                            "class": b.__class__.__name__,
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
                        
                        # Ajouter le traitement des messages spécifiques
                        if packet.get('type') == "network_message":
                            message_content = packet.get('content')
                            if message_content and packet.get('node_id') != self.node_id:
                                self.properties_manager.process_message(message_content)
                            continue
                            
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

            unit_mapping = {
                    "Villager": Villager,
                    "Swordsman": Swordsman,
                    "Horseman": Horseman,
                    "Archer": Archer,
                    "Unit": Unit
                }
            
            for player in players_state:
                # Utiliser l'IP source comme identifiant unique
                player_key = (source_ip, player.get("id"))
                if player_key in self.remote_players:
                    remote_player = self.remote_players[player_key]
                else:
                    remote_player = RemotePlayer((source_ip, 0), name=f"Remote-{source_ip}-{player.get('id')}")
                    remote_player.id = player.get("id") or remote_player.id
                    self.remote_players[player_key] = remote_player
                
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
                building_mapping = {
                    "TownCenter": TownCenter,
                    "Barracks": Barracks,
                    "Stable": Stable,
                    "ArcheryRange": ArcheryRange,
                    "Farm": Farm,   
                    "House": House,
                    "Keep": Keep,
                    "Camp": Camp
                }

                # Nettoyer les bâtiments qui n'existent plus
                buildings_to_remove = []
                for building in remote_player.buildings if hasattr(remote_player, 'buildings') else []:
                    if not any(b_state.get("position") == building.position for b_state in buildings_state):
                        buildings_to_remove.append(building)
                        # Retirer le bâtiment de sa tile
                        if hasattr(building, "position"):
                            x, y = building.position
                            if 0 <= y < len(self.local_map.grid) and 0 <= x < len(self.local_map.grid[y]):
                                tile = self.local_map.grid[y][x]
                                if hasattr(tile, 'building'):
                                    tile.building = None

                # Supprimer les bâtiments qui n'existent plus
                for building in buildings_to_remove:
                    if hasattr(remote_player, 'buildings'):
                        remote_player.buildings.remove(building)

                # Initialiser la liste des bâtiments si elle n'existe pas
                if not hasattr(remote_player, 'buildings'):
                    remote_player.buildings = []

                # Mettre à jour ou créer les bâtiments
                for building_state in buildings_state:
                    building_name = building_state.get("name")
                    position = building_state.get("position")
                    hp = building_state.get("hp")
                    is_attacked = building_state.get("is_attacked", False)

                    if not building_name or not position:
                        continue

                    x, y = position
                    # Vérifier si le bâtiment existe déjà à cette position
                    existing_building = None
                    for building in remote_player.buildings:
                        if building.position == position:
                            existing_building = building
                            break

                    if existing_building:
                        # Mettre à jour le bâtiment existant
                        existing_building.hp = hp
                        existing_building.is_attacked = is_attacked
                    else:
                        # Créer un nouveau bâtiment
                        building_cls = building_mapping.get(building_name)
                        if building_cls:
                            new_building = building_cls(player=remote_player)
                            new_building.position = position
                            new_building.hp = hp
                            new_building.is_attacked = is_attacked

                            # Placer le bâtiment sur toutes les tuiles qu'il occupe
                            size = new_building.size
                            can_place = True
                            
                            # Vérifier que toutes les tuiles sont disponibles
                            for dy in range(size):
                                for dx in range(size):
                                    check_y = y + dy
                                    check_x = x + dx
                                    if not (0 <= check_y < len(self.local_map.grid) and 
                                          0 <= check_x < len(self.local_map.grid[0])):
                                        can_place = False
                                        break
                                    if hasattr(self.local_map.grid[check_y][check_x], 'building') and \
                                       self.local_map.grid[check_y][check_x].building is not None:
                                        can_place = False
                                        break

                            if can_place:
                                # Placer le bâtiment sur toutes les tuiles
                                for dy in range(size):
                                    for dx in range(size):
                                        tile = self.local_map.grid[y + dy][x + dx]
                                        tile.building = new_building
                                remote_player.buildings.append(new_building)
                                #debug_print(f"New building {building_name} added at ({x}, {y}) with size {size}x{size}")

    def close(self):
        """Ferme les sockets réseau."""
        self.send_socket.close()
        self.recv_socket.close()

    def send_network_message(self, message):
        """Envoie un message réseau spécifique (différent de l'état complet)"""
        try:
            packet = {
                "type": "network_message",
                "content": message,
                "source_ip": self.local_ip,
                "node_id": self.node_id
            }
            
            # Sérialiser et compresser
            pickle_payload = pickle.dumps(packet)
            compressed_payload = zlib.compress(pickle_payload)
            
            # Envoi direct si petit paquet
            network_packet = {
                'fragment': False,
                'data': compressed_payload
            }
            self.send_socket.sendto(pickle.dumps(network_packet), ("127.0.0.1", PY_TO_C_PORT))
        except socket.error as e:
            debug_print(f"Erreur lors de l'envoi du message réseau: {e}")

    def get_object_state(self, obj_id):
        """Récupère l'état actuel d'un objet"""
        # Implémenter la logique pour récupérer l'état à partir de l'ID
        # Exemple simple: chercher dans les objets du jeu
        if obj_id in self.object_states:
            return self.object_states[obj_id]
        
        # Sinon, chercher dans les unités et bâtiments
        if hasattr(self, 'game_engine'):
            for player in self.game_engine.players:
                # Chercher dans les unités
                for unit_id, unit in player.units.items():
                    if unit.network_id == obj_id:
                        return unit.get_network_state()
                
                # Chercher dans les bâtiments
                for building in player.buildings:
                    if hasattr(building, 'network_id') and building.network_id == obj_id:
                        return building.get_network_state()
        
        return None

    def apply_object_state(self, obj_id, state):
        """Applique l'état reçu à l'objet correspondant"""
        # Résoudre les références entre objets avant d'appliquer l'état
        resolved_state = self.resolve_object_references(state)
        
        # Stocker l'état résolu
        self.object_states[obj_id] = resolved_state
        
        # Chercher l'objet et appliquer l'état
        if hasattr(self, 'game_engine'):
            for player in self.game_engine.players:
                # Chercher dans les unités
                for unit_id, unit in player.units.items():
                    if hasattr(unit, 'network_id') and unit.network_id == obj_id:
                        unit.apply_network_state(resolved_state)
                        return True
                
                # Chercher dans les bâtiments
                for building in player.buildings:
                    if hasattr(building, 'network_id') and building.network_id == obj_id:
                        building.apply_network_state(resolved_state)
                        return True
        
        return False

    def resolve_object_references(self, state):
        """Résout les références d'objets à partir de leurs IDs"""
        if not hasattr(self, 'object_references'):
            self.object_references = {}
        
        if not isinstance(state, dict):
            return state
        
        # Copier l'état pour éviter de modifier l'original
        resolved_state = state.copy()
        
        # Parcourir les attributs qui sont des objets
        for key, value in state.items():
            if isinstance(value, dict):
                # Si c'est un dictionnaire avec network_id, c'est une référence
                if 'network_id' in value:
                    obj_id = value['network_id']
                    ref_obj = self.find_object_by_id(obj_id)
                    if ref_obj:
                        resolved_state[key] = ref_obj
                        self.object_references[obj_id] = ref_obj
                    else:
                        # Résoudre récursivement ce sous-objet
                        resolved_state[key] = self.resolve_object_references(value)
                else:
                    # C'est un dictionnaire ordinaire, résoudre récursivement
                    resolved_state[key] = self.resolve_object_references(value)
            elif isinstance(value, list):
                # Si c'est une liste, résoudre chaque élément
                resolved_state[key] = [self.resolve_object_references(item) for item in value]
        
        return resolved_state

    def find_object_by_id(self, obj_id):
        """Trouve un objet à partir de son ID réseau"""
        # Chercher dans les objets déjà référencés
        if hasattr(self, 'object_references') and obj_id in self.object_references:
            return self.object_references[obj_id]
        
        # Chercher dans tous les objets du jeu
        if hasattr(self, 'game_engine'):
            for player in self.game_engine.players:
                # Chercher dans les unités
                for unit_id, unit in player.units.items():
                    if hasattr(unit, 'network_id') and unit.network_id == obj_id:
                        return unit
                
                # Chercher dans les bâtiments
                for building in player.buildings:
                    if hasattr(building, 'network_id') and building.network_id == obj_id:
                        return building
        
        return None

class RemotePlayer:
    def __init__(self, addr, name=None):
        self.addr = addr
        self.units = {}
        if name is None:
            self.name = f"Remote-{addr[0]}:{addr[1]}"
        else:
            self.name = name
        self.id = abs(hash(self.name)) % 100

class NetworkPropertiesManager:
    """Gère les propriétés réseau des objets du jeu"""
    
    def __init__(self, network_manager):
        self.network_manager = network_manager
        self.locks = {}  # ID objet -> verrou
        self.owners = {}  # ID objet -> propriétaire réseau
        self.message_queue = []  # File prioritaire pour les messages
        self.local_player_id = None  # ID du joueur local
        self.last_sync_time = time.time()
        self.sync_interval = 5.0  # Synchronisation complète toutes les 5 secondes
        
    def register_object(self, obj_id, initial_owner_id):
        """Enregistre un nouvel objet dans le système avec son propriétaire initial"""
        if obj_id not in self.locks:
            self.locks[obj_id] = threading.Lock()
            self.owners[obj_id] = initial_owner_id
            return True
        return False
        
    def request_ownership(self, obj_id, requester_id):
        """Demande la propriété d'un objet"""
        if obj_id not in self.owners:
            return False
            
        # Si l'objet nous appartient déjà, pas besoin de demander
        if self.owners[obj_id] == self.local_player_id:
            return True
            
        # Envoyer une demande de propriété via le réseau
        message = {
            "type": "ownership_request",
            "object_id": obj_id,
            "requester_id": requester_id,
            "timestamp": time.time()
        }
        
        # Ajouter à la file de messages prioritaires (priorité 0 = élevée)
        heapq.heappush(self.message_queue, (0, message))
        
        # Attendre une réponse (avec timeout)
        timeout = time.time() + 2.0  # 2 secondes de timeout
        while time.time() < timeout:
            if self.owners.get(obj_id) == requester_id:
                return True
            time.sleep(0.05)
        
        return False
        
    def transfer_ownership(self, obj_id, new_owner_id):
        """Transfère la propriété d'un objet"""
        if obj_id not in self.owners:
            return False
            
        # Vérifier que nous sommes bien le propriétaire actuel
        if self.owners[obj_id] != self.local_player_id:
            return False
            
        # Acquérir le verrou avant de modifier la propriété
        with self.locks[obj_id]:
            self.owners[obj_id] = new_owner_id
            
            # Annoncer le changement de propriété via le réseau
            message = {
                "type": "ownership_transfer",
                "object_id": obj_id,
                "new_owner_id": new_owner_id,
                "timestamp": time.time()
            }
            
            # Priorité moyenne (1)
            heapq.heappush(self.message_queue, (1, message))
            
        return True
        
    def process_message(self, message):
        """Traite un message réseau reçu"""
        if message["type"] == "ownership_request":
            obj_id = message["object_id"]
            requester_id = message["requester_id"]
            
            # Si nous sommes le propriétaire, nous pouvons répondre
            if obj_id in self.owners and self.owners[obj_id] == self.local_player_id:
                self.transfer_ownership(obj_id, requester_id)
                
        elif message["type"] == "ownership_transfer":
            obj_id = message["object_id"]
            new_owner_id = message["new_owner_id"]
            
            # Mettre à jour notre copie locale de la propriété
            if obj_id in self.owners:
                with self.locks[obj_id]:
                    self.owners[obj_id] = new_owner_id
                    
        elif message["type"] == "state_update":
            # Mise à jour de l'état d'un objet
            obj_id = message["object_id"]
            state = message["state"]
            
            # Résoudre les références avant d'appliquer l'état
            resolved_state = self.network_manager.resolve_object_references(state)
            
            # Appliquer la mise à jour si nous ne sommes pas le propriétaire
            if obj_id in self.owners and self.owners[obj_id] != self.local_player_id:
                self.network_manager.apply_object_state(obj_id, resolved_state)
                
        elif message["type"] == "full_sync":
            # Synchronisation complète
            objects = message.get("objects", {})
            for obj_id, state in objects.items():
                # Résoudre les références pour chaque objet
                resolved_state = self.network_manager.resolve_object_references(state)
                # Appliquer si nous ne sommes pas propriétaire
                if obj_id in self.owners and self.owners[obj_id] != self.local_player_id:
                    self.network_manager.apply_object_state(obj_id, resolved_state)
                
    def send_state_update(self, obj_id, state):
        """Envoie une mise à jour d'état d'un objet"""
        # Vérifier que nous sommes bien le propriétaire
        if obj_id not in self.owners or self.owners[obj_id] != self.local_player_id:
            return False
            
        message = {
            "type": "state_update",
            "object_id": obj_id,
            "state": state,
            "timestamp": time.time()
        }
        
        # Priorité normale (2)
        heapq.heappush(self.message_queue, (2, message))
        return True
        
    def process_message_queue(self):
        """Traite la file de messages prioritaires"""
        current_time = time.time()
        
        # Traiter les messages en attente (max 10 par frame pour éviter les blocages)
        for _ in range(min(10, len(self.message_queue))):
            if self.message_queue:
                _, message = heapq.heappop(self.message_queue)
                self.network_manager.send_network_message(message)
                
        # Synchronisation périodique complète
        if current_time - self.last_sync_time > self.sync_interval:
            self.perform_full_sync()
            self.last_sync_time = current_time
            
    def perform_full_sync(self):
        """Effectue une synchronisation complète des objets dont nous sommes propriétaires"""
        owned_objects = [obj_id for obj_id, owner in self.owners.items() if owner == self.local_player_id]
        
        if owned_objects:
            sync_message = {
                "type": "full_sync",
                "objects": {
                    obj_id: self.network_manager.get_object_state(obj_id)
                    for obj_id in owned_objects
                },
                "timestamp": time.time()
            }
            
            # Priorité basse (3) pour la synchronisation complète
            heapq.heappush(self.message_queue, (3, sync_message))