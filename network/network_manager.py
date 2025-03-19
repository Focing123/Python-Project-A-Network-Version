import socket
import json
import select
import time
from backend.logger import debug_print
from frontend.Terrain import Gold, Wood  # Assurez-vous que le chemin d'import est correct

class NetworkManager:
    def __init__(self, peer_to_peer=False):
        self.peer_to_peer = peer_to_peer
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.broadcast_address = ("255.255.255.255", 1234)
        # Bind to any available port
        self.udp_socket.bind(('', 0))
        self.udp_socket.setblocking(False)
        # Stocke l'adresse locale (IP, port)
        self.local_addr = self.udp_socket.getsockname()
        # Pour identifier les pairs uniquement par leur adresse (IP, port)
        self.peers = set()
        # Indique si l'instance fonctionne en mode serveur (c'est-à-dire si le socket est bind sur le port 1234)
        self.is_server = False
        # Optionnel : adresse du serveur détecté (pour les clients)
        self.server_address = None
        # Référence à la map locale (à affecter depuis GameEngine)
        self.local_map = None


    def validate_peers(self):
        """Valide les pairs existants et supprime ceux qui ne sont plus valides."""
        invalid_peers = set()
        for peer in self.peers:
            if peer != self.local_addr:
                try:
                    # Envoyer un message ping pour vérifier si le pair est toujours accessible
                    ping_message = json.dumps({"type": "ping"})
                    self.udp_socket.sendto(ping_message.encode("utf-8"), peer)
                except socket.error:
                    invalid_peers.add(peer)
        
        # Supprimer les pairs invalides
        for invalid_peer in invalid_peers:
            self.peers.remove(invalid_peer)
            debug_print(f"Pair supprimé (validation): {invalid_peer}")
            
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
                        # Vérifier que l'adresse est valide avant de l'ajouter
                        if addr[0] != '' and addr[1] != 0:
                            # Pour le client, on stocke l'adresse du serveur
                            self.server_address = addr
                            # On traite la liste des pairs reçue
                            peers = message.get("peers", [])
                            for p in peers:
                                if isinstance(p, list) and len(p) == 2 and p[0] != '' and p[1] != 0:
                                    self.peers.add(tuple(p))
                            response_received = True
                            debug_print(f"Serveur détecté depuis {addr}.")
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
                return False  # Échec de l'initialisation en tant que serveur
            self.udp_socket.setblocking(False)
            self.is_server = True
            # Met à jour l'adresse locale après le rebind
            self.local_addr = self.udp_socket.getsockname()
            # Vérifie que l'adresse locale est valide avant de l'ajouter
            if self.local_addr[0] != '' and self.local_addr[1] != 0:
                # Ajoute soi-même dans la liste de pairs
                self.peers.add(self.local_addr)
                debug_print(f"Aucun serveur trouvé. Démarrage en tant que serveur sur {self.local_addr}.")
            else:
                debug_print("Adresse locale invalide, impossible de démarrer en tant que serveur.")
                return False
        
        return True

    def handle_incoming_discovery(self):
        """Traite en boucle les demandes de découverte entrantes (pour le serveur)."""
        ready = select.select([self.udp_socket], [], [], 0)
        if ready[0]:
            try:
                data, addr = self.udp_socket.recvfrom(65535)
                message = json.loads(data.decode("utf-8"))
                
                if message.get("type") == "discovery_request" and self.is_server:
                    # Ajoute le pair à la liste, mais vérifie s'il est valide
                    if addr[0] != '':  # Vérifier que l'adresse IP n'est pas vide
                        self.peers.add(addr)
                        response = {
                            "type": "discovery_response",
                            "peers": [list(peer) for peer in self.peers if peer[0] != '']
                        }
                        self.udp_socket.sendto(json.dumps(response).encode("utf-8"), addr)
                        debug_print(f"Réponse envoyée à la demande de découverte de {addr}.")
                    
                elif message.get("type") == ["server_announcement"] and not self.is_server:
                    peers = message.get("peers", [])
                    for p in peers:
                        self.peers.add(tuple(p))
                    debug_print(f"Mise à jour des pairs: {self.peers}")
                    
            except Exception as e:
                debug_print(f"Erreur lors du traitement de la découverte: {e}")

    def send_game_state(self, game_state, nature='data'):
        """Envoie l'état du jeu via UDP en utilisant la liste des pairs."""
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

        if nature == 'data':
            state = {
                "type": "game_data",
                "map": map_state,
                "width": game_state.map.width,
                "height": game_state.map.height,
            }
        elif nature == 'discovery':
                state = {
                "type": "game_data",
                "map": map_state,
                "players": players_state,
                "actions": []
            }
        json_payload = json.dumps(state)
        invalid_peers = set()
        
        # Envoi vers tous les pairs connus sauf soi-même
        for peer in self.peers:
            if peer != self.local_addr:
                try:
                    self.udp_socket.sendto(json_payload.encode("utf-8"), peer)
                    debug_print(f"Etat multijoueur envoyé à {peer}.")
                except socket.error as e:
                    debug_print(f"Erreur lors de l'envoi UDP à {peer}: {e}")
                    if e.errno == 10049:  # Si c'est une erreur d'adresse invalide
                        invalid_peers.add(peer)
        
        # Supprimer les pairs invalides
        for invalid_peer in invalid_peers:
            self.peers.remove(invalid_peer)
            debug_print(f"Pair supprimé: {invalid_peer}")

    def receive_game_state(self, timeout=0.001):
        """Reçoit l'état du jeu via UDP, applique les changements de ressources sur la map locale et retourne le payload."""
        try:
            ready = select.select([self.udp_socket], [], [], timeout)
            if ready[0]:
                try:
                    # Utilisez 65507 pour la taille de buffer (charge utile max UDP)
                    data, addr = self.udp_socket.recvfrom(65507)
                    payload = json.loads(data.decode('utf-8'))
                    
                    if payload.get("type") == "game_data":
                        # Ignore le message si il provient de soi-même
                        if addr != self.local_addr:
                            debug_print(f"État multijoueur reçu de {addr}.")
                            # Appliquer les changements de ressources dans la map locale
                            self.apply_state_to_game(payload)
                        return payload
                    elif payload.get("type") in ["discovery_request", "discovery_response", "server_announcement"]:
                        self.handle_incoming_discovery()
                        return None
                except Exception as e:
                    debug_print(f"Erreur lors de la réception UDP: {e}")
            return None
        except Exception as e:
            debug_print(f"Erreur dans receive_game_state: {e}")
            return None

    def apply_state_to_game(self, payload):
        """Pour chaque ressource reçue dans le payload, si elle n'existe pas dans la map locale,
        on l'ajoute dans self.local_map.resources et on met à jour la case correspondante de la grille.
        La map locale possède une structure : {"Gold": [], "Wood": []}."""
        map_state = payload.get("map", {})
        if "resources" in map_state and self.local_map is not None:
            remote_resources = map_state["resources"]
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
                            if res_type == "Gold":
                                resource_obj = Gold()
                            elif res_type == "Wood":
                                resource_obj = Wood()
                            else:
                                resource_obj = None
                            if resource_obj is not None:
                                resource_obj.amount = amount
                                self.local_map.grid[y][x].resource = resource_obj

    def close(self):
        """Ferme la connexion réseau."""
        self.udp_socket.close()