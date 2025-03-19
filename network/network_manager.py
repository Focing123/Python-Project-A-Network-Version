import socket
import json
import select
import time
from backend.logger import debug_print

class NetworkManager:
    def __init__(self, peer_to_peer=False):
        self.peer_to_peer = peer_to_peer
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.broadcast_address = ("255.255.255.255", 1234)
        self.udp_socket.bind(('', 0)) # Bind to any available port
        self.udp_socket.setblocking(False)
        # Attributs pour le mode peer-to-peer
        self.peer_id = None
        self.is_server = False
        self.peer_table = {}  # Ex: { "('192.168.1.100', 12345)": 1, ... }
        self.last_discovery_broadcast = 0

    def run_peer_discovery(self, timeout=5):
        """Lance la découverte des pairs."""
        if not self.peer_to_peer:
            return

        discovery_message = json.dumps({"type": "discovery_request"})
        self.udp_socket.sendto(discovery_message.encode("utf-8"), self.broadcast_address)
        start_time = time.time()
        response_received = False

        while time.time() - start_time < timeout:
            ready = select.select([self.udp_socket], [], [], 0.5)
            if ready[0]:
                try:
                    data, addr = self.udp_socket.recvfrom(65535)
                    message = json.loads(data.decode("utf-8"))
                    if message.get("type") == "discovery_response":
                        self.peer_id = message.get("assigned_id")
                        self.peer_table = message.get("peer_table", {})
                        response_received = True
                        debug_print(f"Serveur détecté. ID attribué: {self.peer_id}")
                        break
                except Exception as e:
                    debug_print(f"Erreur lors de la découverte des pairs: {e}")

        if not response_received:
            # Aucune réponse : rebind du socket sur le port 1234 et déclaration en tant que serveur.
            self.udp_socket.close()
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                self.udp_socket.bind(('', 1234))  # Le serveur écoute sur le port 1234
            except Exception as e:
                debug_print(f"Erreur lors du bind sur le port 1234 : {e}")
                return False  # Signal que l'initialisation en tant que serveur a échoué
            self.udp_socket.setblocking(False)
            self.peer_id = 1
            self.is_server = True
            # Ajoute soi-même dans la table
            local_addr = socket.gethostbyname(socket.gethostname())
            self.peer_table[f"('{local_addr}', 1234)"] = self.peer_id
            debug_print("Aucun serveur trouvé. Démarrage en tant que serveur avec ID 1.")
        
        return True

    def update(self):
        """Méthode principale à appeler dans la boucle principale du jeu pour gérer le réseau"""
        if not self.peer_to_peer:
            return
            
        # Si serveur, gérer les demandes de découverte
        if self.is_server:
            self.handle_incoming_discovery()
        
        # Tous les 10 secondes, renvoyer une annonce de découverte si serveur
        # ou vérifier si le serveur est toujours disponible si client
        current_time = time.time()
        if current_time - self.last_discovery_broadcast > 10:
            self.last_discovery_broadcast = current_time
            if self.is_server:
                # Annoncer sa présence
                announcement = {
                    "type": "server_announcement",
                    "peer_table": self.peer_table
                }
                self.udp_socket.sendto(json.dumps(announcement).encode("utf-8"), self.broadcast_address)
                debug_print("Annonce serveur envoyée")
            else:
                # Envoyer un ping au serveur
                ping = {
                    "type": "ping",
                    "peer_id": self.peer_id
                }
                self.udp_socket.sendto(json.dumps(ping).encode("utf-8"), self.broadcast_address)
                debug_print(f"Ping envoyé au serveur, ID: {self.peer_id}")

    def handle_incoming_discovery(self):
        """Méthode destinée à être appelée en boucle par le serveur pour traiter
        les demandes de découverte entrantes."""
        ready = select.select([self.udp_socket], [], [], 0)
        if ready[0]:
            try:
                data, addr = self.udp_socket.recvfrom(65535)
                message = json.loads(data.decode("utf-8"))
                
                # Traitement des demandes de découverte
                if message.get("type") == "discovery_request" and self.is_server:
                    # Attribue un nouvel ID en incrémentant le max actuel
                    new_id = max(self.peer_table.values()) + 1 if self.peer_table else 1
                    addr_str = str(addr)
                    self.peer_table[addr_str] = new_id
                    
                    response = {
                        "type": "discovery_response",
                        "assigned_id": new_id,
                        "peer_table": self.peer_table
                    }
                    self.udp_socket.sendto(json.dumps(response).encode("utf-8"), addr)
                    debug_print(f"Nouvelle instance connectée avec ID {new_id} depuis {addr}.")
                    
                # Traitement des pings
                elif message.get("type") == "ping" and self.is_server:
                    peer_id = message.get("peer_id")
                    # Vérifier si ce peer existe dans notre table
                    if peer_id in self.peer_table.values():
                        pong = {
                            "type": "pong",
                            "peer_table": self.peer_table
                        }
                        self.udp_socket.sendto(json.dumps(pong).encode("utf-8"), addr)
                        debug_print(f"Pong envoyé à peer ID {peer_id}")
                
                # Réception d'une annonce serveur ou d'un pong
                elif (message.get("type") == "server_announcement" or 
                      message.get("type") == "pong") and not self.is_server:
                    # Mise à jour de la table des pairs
                    self.peer_table = message.get("peer_table", {})
                    debug_print(f"Table des pairs mise à jour: {self.peer_table}")
                    
            except Exception as e:
                debug_print(f"Erreur lors du traitement de la découverte: {e}")

    def send_game_state(self, game_state):
        """Envoie l'état du jeu via UDP en tenant compte des ports dans la table des pairs"""
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
            "sender_id": self.peer_id,
            "map": map_state,
            "width": game_state.map.width,
            "height": game_state.map.height,
            "players": players_state,
            "actions": []
        }
        json_payload = json.dumps(state)
        try:
            for peer_addr, peer_id in self.peer_table.items():
                if peer_id != self.peer_id:
                    addr_tuple = eval(peer_addr)
                    self.udp_socket.sendto(json_payload.encode("utf-8"), addr_tuple)
                    debug_print(f"Etat multijoueur envoyé à {addr_tuple} (peer ID: {peer_id}).")
        except Exception as e:
            debug_print(f"Erreur lors de l'envoi UDP: {e}")

    def receive_game_state(self, timeout=0.001):
        """Reçoit l'état du jeu via UDP en tenant compte des ports dans la table des pairs"""
        ready = select.select([self.udp_socket], [], [], timeout)
        if ready[0]:
            try:
                data, addr = self.udp_socket.recvfrom(65535)
                payload = json.loads(data.decode('utf-8'))
                
                # Traiter uniquement les messages de type game_data
                if payload.get("type") == "game_data":
                    sender_id = payload.get("sender_id")
                    # Ne pas traiter ses propres messages
                    if sender_id != self.peer_id:
                        debug_print(f"État multijoueur reçu de {addr} (peer ID: {sender_id})")
                        return payload
                # Les autres types de messages sont traités par handle_incoming_discovery
                elif payload.get("type") in ["discovery_request", "discovery_response", 
                                            "server_announcement", "ping", "pong"]:
                    # Appeler handle_incoming_discovery pour traiter ces messages
                    self.handle_incoming_discovery()
                    return None
                
            except Exception as e:
                debug_print(f"Erreur lors de la réception UDP: {e}")
        return None

    def apply_state_to_game(self, game_engine, state):
        """Applique l'état reçu au moteur de jeu"""
        if not state:
            return

        if "turn" in state and state["turn"] > game_engine.turn:
            game_engine.turn = state["turn"]

        for player_state in state.get("players", []):
            for player in game_engine.players:
                if player.name == player_state["name"]:
                    player.owned_resources = player_state["resources"]
                    for unit_state in player_state["units"]:
                        for unit in player.units:
                            if unit.position == unit_state["position"]:
                                unit.hp = unit_state["hp"]
                                unit.target_position = unit_state["target_position"]
                                unit.target_attack = unit_state["target_attack"]
                                unit.is_attacked_by = unit_state["is_attacked_by"]
                                unit.task = unit_state["task"]
                                unit.direction = unit_state["direction"]
                                unit.is_moving = unit_state["is_moving"]
                    for building_state in player_state["buildings"]:
                        for building in player.buildings:
                            if building.position == building_state["position"]:
                                building.hp = building_state["hp"]
                                building.is_attacked = building_state["is_attacked"]

    def close(self):
        """Ferme la connexion réseau"""
        self.udp_socket.close()