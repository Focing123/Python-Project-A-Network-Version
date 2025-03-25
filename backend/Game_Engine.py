import curses
import time
import pickle
import os
import tkinter as tk
import socket

from queue import Queue
from frontend.gui import GUI

from logger import debug_print
from Units import *
from Building import *
from Actions import *
from frontend.Terrain import Map
try:
    from frontend import gui
    USE_PYGAME = True
except ImportError:
    USE_PYGAME = False
    debug_print("Pygame not installed; running without Pygame features such as 2.5D map view.")

from html_report import generate_html_report

from IA import IA
from network.network_manager import NetworkManager

# GameEngine Class
class GameEngine:
    def __init__(self, game_mode, map_size, players, sauvegarde=False, network_mode=False):
        self.game_mode = game_mode
        self.network = network_mode
        self.map_size = map_size
        self.players = players
        self.visitors = []
        
        # Initialiser la carte AVANT le NetworkManager
        self.map = Map(*map_size)
        
        # Initialisation du gestionnaire réseau
        if self.network:
            self.network_manager = NetworkManager(peer_to_peer=self.network)
            self.network_manager.local_map = self.map  # Maintenant self.map existe
            self.network_manager.game_engine = self
            
            # Initialiser le gestionnaire de propriétés réseau
            if hasattr(self.network_manager, 'properties_manager'):
                # Définir l'ID du joueur local
                local_player_id = self.players[0].id if self.players else None
                self.network_manager.properties_manager.local_player_id = local_player_id
                
                # Enregistrer les objets initiaux
                for player in self.players:
                    # Vérifier si units est un dictionnaire ou une liste
                    if hasattr(player, 'units'):
                        if isinstance(player.units, dict):
                            for unit_id, unit in player.units.items():
                                if hasattr(unit, 'network_id'):
                                    self.network_manager.properties_manager.register_object(
                                        unit.network_id, player.id)
                        else:
                            # Si units est une liste
                            for unit in player.units:
                                if hasattr(unit, 'network_id'):
                                    self.network_manager.properties_manager.register_object(
                                        unit.network_id, player.id)
                    
                    for building in player.buildings:
                        self.network_manager.properties_manager.register_object(
                            building.network_id, player.id)
        else:
            self.network_manager = None
        
        self.turn = 0
        self.is_paused = False  # Flag pour vérifier si le jeu est en pause
        self.changed_tiles = set()  # Ensemble des tuiles modifiées

        # Attributs relatifs à l'IA
        self.ias = [IA(player, player.ai_profile, self.map, time.time()) for player in self.players]
        for i in range(len(self.players)):
            self.players[i].ai = self.ias[i]
        self.IA_used = False

        # Attributs liés à la sauvegarde
        if not sauvegarde:
            # Récupération des données réseau pour les bâtiments
            network_buildings = []
            if self.network and self.network_manager:
                # Attendre et recevoir l'état initial du jeu
                initial_state = self.network_manager.receive_game_state(timeout=1.0, applystate=False)
                if initial_state:
                    for player_state in initial_state.get("players", []):
                        for building in player_state.get("buildings", []):
                            if building.get("name") == "TownCenter" and building.get("position"):
                                network_buildings.append(
                                    (building["position"], player_state.get("player_id", "unknown"))
                                )
                debug_print(f"Received {len(network_buildings)} Town Center positions from the network")
                
            # Placement des bâtiments avec les informations réseau
            Building.place_starting_buildings(self.map, network_buildings)
            Unit.place_starting_units(self.players, self.map) 
        
        self.debug_print = debug_print
        self.current_time = time.time()
        self.terminalon = True

        # Attributs relatifs au thread GUI
        self.gui_running = False
        self.data_queue = Queue()
        self.gui_thread = None

        self.last_state_update = 0
        self.state_update_interval = 0.1  # Intervalle de mise à jour en secondes

    def start_gui_thread(self):
        """Initialize and start the GUI thread"""
        if not self.gui_thread:
            self.data_queue = Queue()
            self.gui_thread = GUI(self.data_queue)
            self.gui_thread.start()
            self.gui_running = True

    def stop_gui_thread(self):
        """Stop the GUI thread safely"""
        if self.gui_thread:
            #self.gui_thread.stop()
            self.gui_thread = None
            self.gui_running = False

    def update_gui(self):
        """Send current game state to GUI thread"""
        if self.gui_running and not self.data_queue.full():
            self.data_queue.put(self)

    def get_current_time(self):
        """Retourne le temps actuel si le jeu n'est pas en pause"""
        if not self.is_paused:
            return time.time()
        return self.current_time

    def run(self, stdscr):
        # Initialize the starting view position
        top_left_x, top_left_y = 0, 0
        viewport_width, viewport_height = 30, 30
        # Display the initial viewport
        stdscr.clear()  # Clear the screen
        
        if self.terminalon :
            self.map.display_viewport(stdscr, top_left_x, top_left_y, viewport_width, viewport_height, Map_is_paused=self.is_paused)  # Display the initial viewport
        
        try:
            while not self.check_victory():
                # Mettre à jour current_time au début de chaque itération si le jeu n'est pas en pause
                if not self.is_paused:
                    self.current_time = time.time()

                # Gestion du réseau
                if self.network == True and self.network_manager:
                    # Traiter la file de messages réseau
                    if hasattr(self.network_manager, 'properties_manager'):
                        self.network_manager.properties_manager.process_message_queue()
                    
                    # Mise à jour des propriétés des objets
                    self.update_network_object_properties()
                    
                    # Code existant pour l'envoi et la réception d'états
                    if self.current_time - self.last_state_update >= self.state_update_interval:
                        self.send_multiplayer_state()
                        self.network_manager.receive_game_state()
                        if self.map.grid != self.network_manager.local_map.grid or self.map.resources != self.network_manager.local_map.resources:
                            self.map = self.network_manager.local_map
                        self.last_state_update = self.current_time

                # Handle input
                curses.curs_set(0)  # Hide cursor
                stdscr.nodelay(True)  # Make getch() non-blocking
                key = stdscr.getch()  # Get the key pressed by the user
                action = Action(self.map)

                if key == curses.KEY_UP or key == ord('z'):
                    top_left_y = max(0, top_left_y - 1)
                elif key == curses.KEY_DOWN or key == ord('s'):
                    top_left_y = min(self.map.height - viewport_height, top_left_y + 1)
                elif key == curses.KEY_LEFT or key == ord('q'):
                    top_left_x = max(0, top_left_x - 1)
                elif key == curses.KEY_RIGHT or key == ord('d'):
                    top_left_x = min(self.map.width - viewport_width, top_left_x + 1)
                elif key == ord('Z'):
                    top_left_y = max(0, top_left_y - 5)
                elif key == ord('S'):
                    top_left_y = min(self.map.height - viewport_height, top_left_y + 5)
                elif key == ord('Q'):
                    top_left_x = max(0, top_left_x - 5)
                elif key == ord('D'):   
                    top_left_x = min(self.map.width - viewport_width, top_left_x + 5)

                ###### TEST KEYS #######

                elif key == ord('r'):
                    self.debug_print(self.players[0].buildings[0].position)
                    self.debug_print(action.get_adjacent_positions(self.players[0].buildings[0].position[0], self.players[0].buildings[0].position[1], self.players[0].buildings[0].size))
                elif key == ord('o'):
                    self.terminalon = not self.terminalon   
                elif key == ord('i'):
                    action.construct_building(self.players[2].units[1], Keep, 10, 10, self.players[2], self.get_current_time())
                    action.move_unit(self.players[1].units[1],15,15,self.get_current_time())
                elif key == ord('u'):
                    Building.kill_building(self.players[0], self.players[0].buildings[0], self.map)
                elif key == ord('y'):
                    Building.kill_building(self.players[0], self.players[0].buildings[-1], self.map)
                elif key == ord('t'):
                    self.players[0].owned_resources["Wood"] = 100


                #########################

                ###### CHEAT KEYS #######

                elif key == ord('b'):
                    self.map.grid[0][0].resource = Gold()
                    self.map.resources["Gold"].append((0, 0))
                elif key == ord('v'):
                    self.map.grid[1][1].resource = Wood()
                    self.map.resources["Wood"].append((1, 1))
                elif key == ord('h'):
                    self.map.grid[0][0].resource = None
                    self.map.resources["Gold"].remove((0, 0))
                elif key == ord('g'):
                    self.map.grid[1][1].resource = None
                    self.map.resources["Wood"].remove((1, 1))

                #########################


                elif key == curses.KEY_F9:
                    if not self.gui_running:
                        self.start_gui_thread()
                    else:
                        self.stop_gui_thread()
                        stdscr.clear()
                        stdscr.refresh()
                        continue
                elif key == ord('\t'):  # TAB key
                    generate_html_report(self.players)
                    self.debug_print(f"HTML report generated at turn {self.turn}")
                    if self.is_paused == False:
                        self.is_paused = True
                        self.debug_print("Game paused.")
                elif key == ord('p'):
                    self.is_paused = not self.is_paused
                    if self.is_paused:
                        self.debug_print("Game paused.")
                    else:
                        self.debug_print("Game resumed.")

                elif key == ord('n'):
                    self.IA_used = not self.IA_used
                    self.debug_print(f"IA used: {self.IA_used}")

                elif key == curses.KEY_F10: 
                    self.save_game()
                elif key == curses.KEY_F12:
                    # Find the latest save file in the directory
                    save_dir = os.path.join(os.path.dirname(__file__), '..', 'assets', 'annex')
                    save_files = [f for f in os.listdir(save_dir) if f.endswith('.dat')]
                    if save_files:
                        latest_save_file = max(save_files, key=lambda f: os.path.getctime(os.path.join(save_dir, f)))
                        latest_save_path = os.path.join(save_dir, latest_save_file)
                        self.load_game(latest_save_path)
                    else:
                        self.debug_print("No save files found.")

                #call the IA
                if not self.is_paused and self.turn % 200 == 0 and self.IA_used == True: # Call the IA every 5 turns: change 0, 5, 10, 15, ... depending on lag
                    for ia in self.ias:
                        ia.current_time_called = self.get_current_time()  # Update the current time for each IA
                        ia.run()  # Run the AI logic for each player
                    
                if not self.is_paused and self.turn % 10 == 0:
                    # Move units toward their target position
                    for player in self.players:
                        for unit in player.units:
                            if unit.task == "going_to_battle":
                                action.go_battle(unit, unit.target_attack, self.get_current_time())
                            elif unit.task == "attacking":
                                action._attack(unit, unit.target_attack, self.get_current_time())
                            elif unit.target_position:
                                target_x, target_y = unit.target_position
                                action.move_unit(unit, target_x, target_y, self.get_current_time())
                            elif unit.task == "gathering" or unit.task == "returning":
                                action._gather(unit, unit.last_gathered, self.get_current_time())
                            elif unit.task == "marching":
                                action.gather_resources(unit, unit.last_gathered, self.get_current_time())
                            elif unit.task == "is_attacked":
                                action._attack(unit, unit.is_attacked_by, self.get_current_time())
                            elif unit.task == "going_to_construction_site":
                                action.construct_building(unit, unit.construction_type, unit.target_building[0], unit.target_building[1], player, self.get_current_time())
                            elif unit.task == "constructing":
                                action._construct(unit, unit.construction_type, unit.target_building[0], unit.target_building[1], player, self.get_current_time())
                        for building in player.buildings:
                            if hasattr(building, 'training_queue') and building.training_queue != []:
                                unit = building.training_queue[0]
                                Unit.train_unit(unit, unit.spawn_position[0], unit.spawn_position[1], player, unit.spawn_building, self.map, self.get_current_time())
                            elif type(building).__name__ == "Keep":
                                nearby_enemies = IA.find_nearby_enemies(building.player.ai, max_distance=building.range, unit_position=building.position)  # 5 tile radius
                                if nearby_enemies:
                                    closest_enemy = min(nearby_enemies, 
                                        key=lambda e: IA.calculate_distance(building.player.ai, pos1=unit.position, pos2=e.position))
                                    action.attack_target(building, target=closest_enemy, current_time_called=self.current_time, game_map=self.map)
                                else: 
                                    building.target = None

                # Clear the screen and display the new part of the map after moving
                stdscr.clear()
                if self.terminalon :
                    self.map.display_viewport(stdscr, top_left_x, top_left_y, viewport_width, viewport_height, Map_is_paused=self.is_paused)
                stdscr.refresh()

                if self.gui_running:
                    self.update_gui()

                self.turn += 1

            active_players = [p for p in self.players if p.units or p.buildings]
            if active_players:
                self.debug_print(f"Player {active_players[0].name} wins the game!", 'Magenta')
            else:
                self.debug_print("No players left. Game over!", 'Magenta')
            input("Press Enter to exit...")

        except KeyboardInterrupt:
            self.debug_print("Game interrupted. Exiting...", 'Yellow')
        finally:
            if self.gui_running:
                self.stop_gui_thread()

    def check_victory(self):
        if self.turn % 500 == 0: # Check if the game is over
            active_players = [p for p in self.players if p.units or p.buildings] # Check if the player has units and buildings
            return len(active_players) == 0 # Check if there is only one player left
        else:
            return False

    #condition de victoire: être le dernier joueur avec des bâtiments
    def victory():
    
        def big_text(text):
            root = tk.Tk()
            root.title("Texte en gros")
            label = tk.Label(root, text=text, font=("Arial", 48), padx=20, pady=20)
            label.pack(expand=True)
            root.mainloop()

        if GameEngine.check_victory(GameEngine.self) ==True:
            time.stop()
            GUI.load_image(GUI.IMG_PATH / "victory.png")
            big_text(f"Player {GameEngine.active_players[0].name} wins the game!")

    def pause_game(self):
        self.is_paused = not self.is_paused

    def save_game(self, filename=None):
        if not self.is_paused:
            self.is_paused = True
            self.debug_print("Game paused.")
        
        # Generate a filename if none is provided
        if filename is None:
            for i in range(10):  # Limit to 10 auto-saves
                filename = f"../assets/annex/game_save{i}.dat"
                if not os.path.exists(filename):  # Check if the file exists
                    break
            else:
                self.debug_print("No available slots to save the game.")
                return
        else:
            # If a filename is provided, add a unique suffix if necessary
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(filename):
                filename = f"{base}_{counter}{ext}"
                counter += 1

        # Save the game state
        try:
            with open(filename, 'wb') as f:
                game_state = {
                    'players': self.players,
                    'map': self.map,
                    'turn': self.turn,
                    'is_paused': self.is_paused,
                    'changed_tiles': self.changed_tiles,
                    'ias': self.ias  # Add self.ias to the saved state
                }
                pickle.dump(game_state, f)
            self.debug_print(f"Game saved to {filename}.")
        except Exception as e:
            self.debug_print(f"Error saving game: {e}")


    def load_game(self, filename):
        if not self.is_paused:
            self.is_paused = True
            self.debug_print("Game paused.")
        try:
            with open(filename, 'rb') as f:
                game_state = pickle.load(f)
                self.players = game_state['players']
                self.map = game_state['map']
                self.turn = game_state['turn']
                self.is_paused = game_state['is_paused']
                self.changed_tiles = game_state['changed_tiles']
                self.ias = game_state.get('ias', None)  # Load self.ias or set it to None if missing
                self.current_time = time.time()
            self.debug_print(f"Game loaded from {filename}.")
        except Exception as e:
            self.debug_print(f"Error loading game: {e}")

    def send_multiplayer_state(self):
        """Envoie l'état du jeu via le gestionnaire réseau"""
        if self.network_manager:
            # Tous les joueurs doivent envoyer leur état
            self.network_manager.send_game_state(self)

    def update_network_object_properties(self):
        """Met à jour les propriétés réseau des objets du jeu"""
        if not hasattr(self.network_manager, 'properties_manager'):
            return
            
        # Pour chaque unité et bâtiment local dont nous sommes propriétaire
        for player in self.players:
            if player.id == self.network_manager.properties_manager.local_player_id:
                # Unités
                if hasattr(player, 'units'):
                    if isinstance(player.units, dict):
                        # Si units est un dictionnaire
                        for unit_id, unit in player.units.items():
                            if hasattr(unit, 'network_id'):
                                # Si l'unité a été modifiée depuis la dernière mise à jour
                                if hasattr(unit, 'is_moving') and (unit.is_moving or 
                                   hasattr(unit, 'is_attacked_by') and unit.is_attacked_by or 
                                   hasattr(unit, 'target_attack') and unit.target_attack):
                                    # Obtenir l'état et l'envoyer
                                    state = unit.get_network_state()
                                    self.network_manager.properties_manager.send_state_update(
                                        unit.network_id, state)
                    else:
                        # Si units est une liste
                        for unit in player.units:
                            if hasattr(unit, 'network_id'):
                                # Si l'unité a été modifiée depuis la dernière mise à jour
                                if hasattr(unit, 'is_moving') and (unit.is_moving or 
                                   hasattr(unit, 'is_attacked_by') and unit.is_attacked_by or 
                                   hasattr(unit, 'target_attack') and unit.target_attack):
                                    # Obtenir l'état et l'envoyer
                                    state = unit.get_network_state()
                                    self.network_manager.properties_manager.send_state_update(
                                        unit.network_id, state)
                # Bâtiments (code inchangé)
                for building in player.buildings:
                    if hasattr(building, 'network_id'):
                        # If building was modified since last update
                        if (hasattr(building, 'is_under_construction') and building.is_under_construction or
                            hasattr(building, 'is_attacked') and building.is_attacked):
                            # Get state and send it
                            state = building.get_network_state()
                            self.network_manager.properties_manager.send_state_update(
                                building.network_id, state)

    def __del__(self):
        """Destructeur pour fermer proprement les connexions"""
        if self.network_manager:
            self.network_manager.close()
