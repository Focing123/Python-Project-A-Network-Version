#IA
import random
import math

from Actions import *
from logger import debug_print
from Building import *
from Units import *
from backend.Starter_File import players, GameMode

class IA:
    def __init__(self, player, mode, game_map, current_time_called): #only one player --> IA class will be called for each player in GameEngine
        self.player = player
        self.mode = mode
        self.game_map = game_map
        self.players = players
        self.debug_print = debug_print
        self.current_time_called = current_time_called
        self.priorities = self.set_priorities()
        self.decided_builds = [] # Store the decided building positions to avoid overlap --> stored for whole game
        self.target_player = None  # Targeted player for attacks
        self.defending_units = []  # List to track defending units
        self.min_villagers = 2  # Minimum villagers to keep
        self.recovery_strategy = False
        self.secure_gold = [0, 0, 0] # True/False(need to secure), Number of Keep, True/False(presence of Camp), True/False(Camp just placed)
        self.nb_keep = 0
        self.entouring_units = []
        self.nb_encircling_attacks = 0
        self.already_encircling_units = []


#### PRIORITIES and UNIT_RESOURCES ####

    def get_inactive_units(self):
        inactive_villagers = []
        inactive_troops = []
        
        for unit in self.player.units:
            if unit.task is None:
                if isinstance(unit, Villager):
                    inactive_villagers.append(unit)
                elif isinstance(unit, (Swordsman, Archer, Horseman)):
                    inactive_troops.append(unit)
        
        # Count active villagers
        active_builders = len([u for u in self.player.units if isinstance(u, Villager) and (u.task == "constructing" or u.task == "going_to_construction_site")])
        active_gatherers = len([u for u in self.player.units if isinstance(u, Villager) and u.task == "gathering" or u.task == "marching"])
        
        total_villagers = active_builders + active_gatherers + len(inactive_villagers)
        
        desired_builders = max(1, total_villagers // 3)
        
        # Allocate inactive villagers based on desired ratios
        building_villagers = []
        gathering_villagers = []
        
        for villager in inactive_villagers:
            if active_builders < desired_builders:
                building_villagers.append(villager)
                active_builders += 1
            else:
                gathering_villagers.append(villager)

        return building_villagers, gathering_villagers, inactive_troops

    def set_priorities(self):
        if self.mode == "defensive":
            return {
                "villager_ratio": 0.7,
                "military_ratio": 0.3,
                "min_defenders": 5,     # Increased from 3
                "max_defenders": 8,     # New maximum defenders cap
                "attack_threshold": 10,
                "defense_radius": 15    # Radius for defensive patrol
            }
        else:  # aggressive
            return {
                "villager_ratio": 0.4,
                "military_ratio": 0.6,
                "min_defenders": 3,     # Increased from 2
                "max_defenders": 5,     # New maximum defenders cap
                "attack_threshold": 5,
                "defense_radius": 10    # Smaller radius for aggressive mode
            }
        
    def adjust_priorities(self):
        """
        Ajuste dynamiquement les priorités en fonction de l'état actuel du jeu.
        """
        # Analyse des ressources
        food = self.player.owned_resources["Food"]
        wood = self.player.owned_resources["Wood"]
        gold = self.player.owned_resources["Gold"]
        total_population = self.player.population
        max_population = self.player.max_population

        # Ajustement des priorités de construction
        if food < 100 or gold < 100 or wood < 100:
            self.priorities["villager_ratio"] = 0.8  # Augmenter la priorité aux villageois
            self.priorities["military_ratio"] = 0.2  # Réduire la production militaire
        else:
            self.priorities = self.set_priorities()  # Rétablir les priorités par défaut


#### MAIN LOOP ####

    def run(self):
        self.adjust_priorities()
        self.manage_defenders()  # New call to manage defenders
        building_villagers, gathering_villagers, inactive_troops = self.get_inactive_units()

        self.train_units()
        
        if self.recovery_strategy and self.player.owned_resources["Wood"] < 350:
            gathering_villagers.extend(building_villagers)
            building_villagers = []
        elif (self.player.owned_resources["Food"] >= 2000 and 
            self.player.owned_resources["Wood"] >= 2000 and 
            self.player.owned_resources["Gold"] >= 2000):
            building_villagers.extend(gathering_villagers)
            gathering_villagers = []

        self.build_structures(list(set(building_villagers)))
        
        _, remaining_builders, _ = self.get_inactive_units()
        remaining_builders = [v for v in remaining_builders if v not in building_villagers]
        gathering_villagers.extend(remaining_builders)
        
        gathering_villagers = list(set(gathering_villagers))
        self.gather_resources(gathering_villagers)
        
        # Check for nearby enemies for all units
        for unit in (u for u in self.player.units if u.task != "encircling"):
            nearby_enemies = self.find_nearby_enemies(5, unit.position)  # 5 tile radius
            if nearby_enemies:
                closest_enemy = min(nearby_enemies, 
                    key=lambda e: self.calculate_distance(unit.position, e.position))
                Action(self.game_map).go_battle(unit, closest_enemy, self.current_time_called)
        
        # Handle remaining military strategy
        if inactive_troops:
            self.attack(list(set(inactive_troops)))


#### TRAINING STRATEGY ####

    def train_units(self):
        # Modify the existing training logic for resources > 2000
        if (self.player.owned_resources["Food"] >= 2000 and 
            self.player.owned_resources["Wood"] >= 2000 and 
            self.player.owned_resources["Gold"] >= 2000 and 
            any(type(building).__name__ in ["Barracks", "Stable", "ArcheryRange"] for building in self.player.buildings) and 
            self.mode == "aggressive"):
            self.debug_print("Training strategy : Aggressive mode, training troops", 'Magenta')
            
            # Keep minimum villagers instead of killing all
            villagers = [unit for unit in self.player.units if isinstance(unit, Villager)]
            villagers_to_remove = villagers[self.min_villagers:]
            
            for unit in villagers_to_remove:
                Unit.kill_unit(self.player, unit, self.game_map)
                
            # Continue with military training
            free_slots = min(
                self.player.max_population - self.player.population - len(self.player.training_units),
                sum(building.population_increase for building in self.player.buildings) - self.player.population - len(self.player.training_units)
            )
            for _ in range(free_slots):
                self.train_troops()
        else:
            if (self.player.population + len(self.player.training_units) >= self.player.max_population or 
                    self.player.population + len(self.player.training_units) >= sum(building.population_increase for building in self.player.buildings)):
                return  # Population limit reached, cannot train more units

            total_units = len(self.player.units) + len(self.player.training_units)
            current_villagers = len([u for u in self.player.units if isinstance(u, Villager)]) + len([u for u in self.player.training_units if isinstance(u, Villager)])
            current_military = len([u for u in self.player.units if isinstance(u, (Swordsman, Archer, Horseman))]) + len([u for u in self.player.training_units if isinstance(u, (Swordsman, Archer, Horseman))])
            
            desired_villagers = max(1,int(total_units * self.priorities["villager_ratio"]))
            desired_military = max(1,int(total_units * self.priorities["military_ratio"]))
            
            if current_villagers < desired_villagers and self.player.owned_resources["Food"] > 50:
                self.train_villagers()
            elif current_military < desired_military and (
                    self.player.owned_resources["Wood"] > 50 and 
                    self.player.owned_resources["Gold"] > 50 and 
                    self.player.owned_resources["Food"] > 100 and 
                    any(type(building).__name__ in ["Barracks", "Stable", "ArcheryRange"] for building in self.player.buildings)):
                self.train_troops()
            elif self.player.owned_resources["Food"] > 50:
                self.train_villagers()

    def train_villagers(self):
        for building in self.player.buildings:
            if isinstance(building, TownCenter):
                x, y = building.position
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        new_x = x + dx
                        new_y = y + dy
                        if self.is_position_valid(new_x, new_y, 1, is_building=False):
                            Unit.train_unit(Villager, new_x, new_y, self.player, building, self.game_map, self.current_time_called)
                            #self.debug_print(f"{self.player.name} : Training villager at ({new_x}, {new_y})")
                            return

    def train_troops(self):
        buildings = [building for building in self.player.buildings if type(building).__name__ in ["Barracks", "ArcheryRange", "Stable"]]
        random.shuffle(buildings)
        
        for building in buildings:
            if type(building).__name__ == "Barracks":
                x, y = building.position
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        new_x = x + dx
                        new_y = y + dy
                        if self.is_position_valid(new_x, new_y, 1, is_building=False):
                            Unit.train_unit(Swordsman, new_x, new_y, self.player, building, self.game_map, self.current_time_called)
                            #self.debug_print(f"{self.player.name} : Training swordsman at ({new_x}, {new_y})")
                            return
            elif type(building).__name__ == "ArcheryRange":
                x, y = building.position
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        new_x = x + dx
                        new_y = y + dy
                        if self.is_position_valid(new_x, new_y, 1, is_building=False):  # Assuming villager size is 1
                            Unit.train_unit(Archer, new_x, new_y, self.player, building, self.game_map, self.current_time_called)
                            #self.debug_print(f"{self.player.name} : Training archer at ({new_x}, {new_y})")
                            return
            elif type(building).__name__ == "Stable":
                x, y = building.position
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        new_x = x + dx
                        new_y = y + dy
                        if self.is_position_valid(new_x, new_y, 1, is_building=False):  # Assuming villager size is 1
                            Unit.train_unit(Horseman, new_x, new_y, self.player, building, self.game_map, self.current_time_called)
                            #self.debug_print(f"{self.player.name} : Training horseman at ({new_x}, {new_y})")
                            return


#### GATHERING STRATEGY ####

    def gather_resources(self, villagers):
        #if villagers : self.debug_print(f"Farm : {[villager.name for villager in villagers]}")
        for villager in villagers:
            # Determine the resource type that the player has the least of
            if not self.recovery_strategy or "Town Center" not in [building.name for building in self.player.buildings]:
                resource_types = sorted(self.player.owned_resources, key=self.player.owned_resources.get) # Sorted in ascending order
                for resource_type in resource_types: # Gather the resource that the player has the least of
                    #self.debug_print(f"{villager.name} : Gathering {resource_type}")
                    if Action(self.game_map).gather_resources(villager, resource_type, self.current_time_called): # Gather the resource
                        break
            else:
                Action(self.game_map).gather_resources(villager, "Wood", self.current_time_called)

    def is_position_valid(self, x, y, building_size, is_building=True):
        # Check map boundaries
        if not (0 <= x < self.game_map.width - building_size and 
                0 <= y < self.game_map.height - building_size):
            return False
        if is_building:
            for build in self.decided_builds:
                if (abs(build[0] - x) < building_size + build[2] and
                    abs(build[1] - y) < building_size + build[2]):
                    return False

        # Check if area is free on map
        if not self.game_map.is_area_free(x, y, building_size):
            return False
            
        # Check for overlap with buildings under construction
        for building_info in self.player.constructing_buildings:
            # Get position from the dictionary format
            construct_x = building_info.get("position")[0]
            construct_y = building_info.get("position")[1]
            construct_size = building_info.get("size", building_size)  # Default to same size if not specified
            
            if (abs(construct_x - x) < max(building_size, construct_size) and
                abs(construct_y - y) < max(building_size, construct_size)):
                return False
        return True


#### BUILDING STRATEGY ####

    def build_structures(self, villagers):
        if not villagers:
            return
            
        villagers = list(set(villagers))  # Ensure no duplicates
        
        # Check if we should join existing construction (1/3 chance)
        if self.player.constructing_buildings and random.random() < 0.33:
            latest_construction = self.player.constructing_buildings[-1]
            # Add villager to existing construction
            for villager in villagers:
                Action(self.game_map).construct_building(
                    villager, 
                    latest_construction["type"],
                    latest_construction["position"][0], 
                    latest_construction["position"][1],
                    self.player,
                    self.current_time_called
                )
            self.debug_print(f"{self.player.name} : Villager joining existing {latest_construction['type'].__name__} construction at {latest_construction['position']}", 'Blue')
            return
        
        building_types = [Farm, Barracks, House, TownCenter, Stable, ArcheryRange, Keep, Camp, Construct]
        building_costs = {
            "Farm": {"Wood": 60, "Gold": 0},
            "Barracks": {"Wood": 175, "Gold": 0},
            "House": {"Wood": 25, "Gold": 0},
            "TownCenter": {"Wood": 350, "Gold": 0},
            "Stable": {"Wood": 175, "Gold": 0},
            "ArcheryRange": {"Wood": 175, "Gold": 0},
            "Keep": {"Wood": 35, "Gold": 125},
            "Camp": {"Wood": 100, "Gold": 0},
            "Construct": {"Wood": float('inf'), "Gold": float('inf')}
        }

        # Define military buildings and their max count
        military_buildings = ["Barracks", "Stable", "ArcheryRange"]
        MAX_MILITARY_BUILDINGS = 4

        building_counts = {building.__name__: 0 for building in building_types}
        for building in self.player.buildings:
            building_counts[type(building).__name__] += 1

        if building_counts["TownCenter"] == 0:
            if self.player.owned_resources["Wood"] >= 350:
                least_constructed_building = "TownCenter"
                self.debug_print("Strategy : No Town Center, building a Town Center", 'Magenta')
                self.recovery_strategy = False
            elif building_counts["Camp"] == 0:
                if self.player.owned_resources["Wood"] >= 100:
                    least_constructed_building = "Camp"
                    self.recovery_strategy = True
                    self.debug_print("Strategy : No Town Center, not enough Wood, building a Camp", 'Magenta')
            else:
                return False
                    
        # Check if food is low and prioritize building a Farm
        elif self.player.owned_resources["Food"] < 50 and self.player.owned_resources["Wood"] >= 60:
            least_constructed_building = "Farm"
            self.debug_print("Strategy : Low food, building a Farm", 'Magenta')
        # Check if population limit is reached and prioritize building a House
        elif (self.player.population + len(self.player.training_units) >= sum(building.population_increase for building in self.player.buildings)
              and self.player.owned_resources["Wood"] >= 25):
            least_constructed_building = "House"
            self.debug_print("Strategy : Population limit reached, building a House", 'Blue')
        elif GameMode == "Gold Rush":
            if self.player.owned_resources["Wood"] >= 100 and not self.secure_gold[2]:
                least_constructed_building = "Camp"
                self.secure_gold[2] = 1
                self.secure_gold[0] = 1
                self.debug_print("Strategy : Gold Rush, building a Camp near gold", 'Magenta')
            elif self.player.owned_resources["Gold"] >= 125 and self.player.owned_resources["Wood"] >= 35 and self.secure_gold[1] < 3:
                least_constructed_building = "Keep"
                self.secure_gold[0] = 1
                self.debug_print("Strategy : Gold Rush, building a Keep to secure gold", 'Magenta')
            else:
                # Filter out military buildings that have reached their limit
                constructable_buildings = [
                    b_name for b_name, costs in building_costs.items()
                    if all(self.player.owned_resources[resource] >= amount 
                        for resource, amount in costs.items())
                    and (b_name not in military_buildings or building_counts[b_name] < MAX_MILITARY_BUILDINGS)
                ]
                
                # Find the least constructed among constructable buildings
                least_constructed_building = min(
                    constructable_buildings,
                    key=lambda b: building_counts[b],
                    default="Farm"  # Default to Farm if no buildings are constructable
                )
        elif self.mode == "defensive" and len(self.decided_builds)%5 == self.nb_keep and self.player.owned_resources["Gold"] >= 125 and self.player.owned_resources["Wood"] >= 35:
            least_constructed_building = "Keep"
            self.debug_print("Strategy : Defensive mode, building a Keep", 'Magenta')
        else:
            # Filter out military buildings that have reached their limit
            constructable_buildings = [
                b_name for b_name, costs in building_costs.items()
                if all(self.player.owned_resources[resource] >= amount 
                      for resource, amount in costs.items())
                and (b_name not in military_buildings or building_counts[b_name] < MAX_MILITARY_BUILDINGS)
            ]
            
            # Find the least constructed among constructable buildings
            least_constructed_building = min(
                constructable_buildings,
                key=lambda b: building_counts[b],
                default="Farm"  # Default to Farm if no buildings are constructable
            )
        building_class = eval(least_constructed_building) # Get the class of the least constructed building
        if any(resource not in self.player.owned_resources or self.player.owned_resources[resource] < amount 
               for resource, amount in building_class(self.player).cost.items()):
            self.debug_print("Strategy : Cannot build, not enough resources, gathering", 'Magenta')
            self.gather_resources(villagers)
            return
        self.debug_print(f"No Particular strategy, building {least_constructed_building}", 'Magenta')
        # Check if the player has enough resources to construct the identified building
        build_position = None
        #Trick to build where we want
        if not self.player.buildings:
            player_should_build = [villagers[0]]
        elif self.secure_gold[0]:
            player_should_build = [Map.find_nearest_resource(self.game_map, villagers[0].position, "Gold", self.player)]
        else:
            player_should_build = self.player.buildings

        for existing_building in player_should_build:
            if isinstance(existing_building, Building) or isinstance(existing_building, Villager):
                x, y = existing_building.position
            else:
                x, y = existing_building
            for radius in range(5, 15): # buildings not too close to each other nor too far
                for dx in range(-radius, radius + 1):
                    for dy in range(-radius, radius + 1):
                        new_x = x + dx
                        new_y = y + dy
                        if self.is_position_valid(new_x, new_y, building_class(self.player).size + 1, is_building=True):
                            build_position = (new_x, new_y)
                            break
                    if build_position:
                        break
                if build_position:
                    break
            if build_position:
                break
        if build_position:
            self.debug_print(f"{self.player.name} : Building {building_class.__name__} at {build_position}", 'Blue')
            for villager in villagers:
                Action(self.game_map).construct_building(
                    villager, 
                    building_class,
                    build_position[0], 
                    build_position[1],
                    self.player,
                    self.current_time_called
                )
                if build_position not in self.decided_builds:
                    self.decided_builds.append((build_position[0], build_position[1], building_class(self.player).size))
                if self.secure_gold[0]:
                    if building_class.__name__ == "Keep":
                        self.nb_keep += 1
                        self.secure_gold[1] += 1
                    self.secure_gold[0] = 0


#### ATTACK STRATEGY ####

    def attack(self, troops):
        if not troops:
            return
        if not self.target_player:
            self.target_player = self.choose_best_target()

        if (self.player.owned_resources["Food"] >= 2000 and 
            self.player.owned_resources["Wood"] >= 2000 and 
            self.player.owned_resources["Gold"] >= 2000 and 
            any(type(building).__name__ in ["Barracks", "Stable", "ArcheryRange"] for building in self.player.buildings) and 
            self.mode == "aggressive") and self.nb_encircling_attacks < 1:
            self.group_attack(troops)
        else:
            self.strategic_attack(troops)

    def group_attack(self, troops):
        needed_attackers = 10 - len(self.entouring_units)
        if needed_attackers > 0:
            self.entouring_units.extend(troops[:needed_attackers])
            for troop in troops[:needed_attackers]:
                troop.task = "encircling"
        else:
            self.already_encircling_units = True
        
        if not self.already_encircling_units:
            target = self.find_ennemy_base()
            for troop in self.entouring_units:
                if troop.target_position is None:  # Assign target only once
                    target_x, target_y = target
                    while not self.game_map.is_tile_free(target_x, target_y):
                        angle = random.uniform(0, 2 * math.pi)
                        distance_to_target = len(self.target_player.buildings) * 2.5 + 7
                        target_x = int(target[0] + distance_to_target * math.cos(angle))
                        target_y = int(target[1] + distance_to_target * math.sin(angle))
                    troop.target_position = (target_x, target_y)
                    self.debug_print(f"Target set to {target_x, target_y} for {troop.name}", 'Magenta')
                    self.debug_print(f"Trying to circle the enemy base at {target_x, target_y} for {target}", 'Magenta')
        
        if len(self.entouring_units) == 10 and (
            all(not troop.is_moving for troop in self.entouring_units) or 
            any(troop.task == "attacking" for troop in self.entouring_units)):
            
            self.debug_print("Encircling strategy ready, attacking", 'Magenta')
            self.strategic_attack(self.entouring_units)
            
            self.already_encircling_units = False
            self.entouring_units = []
            self.nb_encircling_attacks += 1

    def strategic_attack(self, troops):
        if len(troops) < self.priorities["attack_threshold"]:
            return

        if self.target_player is None or (self.target_player.units == [] and self.target_player.buildings == []):
            self.target_player = self.choose_best_target()

        if not self.target_player:
            return

        targets = [t for t in self.find_strategic_targets() if t.player == self.target_player]
        if targets:
            target = self.choose_best_target_unit(self.target_player, targets)
            for troop in troops:
                #troop.task = None  # Clear any existing task
                Action(self.game_map).go_battle(troop, target, self.current_time_called)

    def find_strategic_targets(self):
        targets = []
        # Get all enemy buildings and units directly
        for player in self.players:
            if player != self.player:
                # Prioritize military buildings
                for building in player.buildings:
                    if isinstance(building, (Barracks, ArcheryRange, Stable)):
                        targets.append(building)
                targets.extend(player.buildings)  # Add remaining buildings
                targets.extend(player.units)      # Add all units
        
        return targets 

    def choose_best_target(self):
        return min(
            (p for p in self.players if p != self.player and (p.units or p.buildings)),
            key=lambda p: len([u for u in p.units if isinstance(u, Villager)]) + len(p.buildings),
            default=None
        )
    
    def choose_best_target_unit(self, target_player, targets):
        return min(
            targets,
            key=lambda t: self.calculate_distance(self.get_base_position(), t.position)
        )
    
    def calculate_distance(self, pos1, pos2):
        return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5
    
    def find_nearby_enemies(self, max_distance, unit_position):
        enemies = []
        for player in self.players:
            if player != self.player:
                for enemy in player.units:
                    dist = self.calculate_distance(unit_position, enemy.position)
                    if dist <= max_distance:
                        enemies.append(enemy)
                for building in player.buildings:
                    dist = self.calculate_distance(unit_position, building.position)
                    if dist <= max_distance:
                        enemies.append(building)
        return enemies
    
    def find_ennemy_base(self):
        return self.target_player.buildings[0].position


#### DEFENSE STRATEGY ####

    def assign_defenders(self, troops):
        defensive_troops = list(self.defending_units)  # Maintain existing defenders
        needed_defenders = self.priorities["min_defenders"] - len(defensive_troops)

        if needed_defenders > 0:
            defensive_troops.extend(troops[:needed_defenders])

        return defensive_troops

    def is_tile_free(self, x, y, game_map):
        if 0 <= y < len(game_map.grid) and 0 <= x < len(game_map.grid[y]):
            return game_map.grid[y][x].building or not game_map.grid[y][x].resource
        return False  # Si hors limites, considérez la case comme non libre


    def defend(self, unit):
                    
        # Find closest enemy units or buildings
        enemies = self.find_nearby_enemies(max_distance=15, unit_position=unit.position)
        if enemies:
            closest_enemy = min(enemies, key=lambda e: self.calculate_distance(unit.position, e.position))
            Action(self.game_map).go_battle(unit, closest_enemy, self.current_time_called)

    def get_base_position(self):
        # Find the position of the main base (TownCenter)
        for building in self.player.buildings:
            if isinstance(building, TownCenter):
                return building.position
        return (0, 0)  # Default position if no TownCenter

    def manage_defenders(self):
        """New method to manage defending units"""
        military_units = [u for u in self.player.units if isinstance(u, (Swordsman, Archer, Horseman))]
        current_defenders = len(self.defending_units)
        
        # Remove dead units from defenders list
        self.defending_units = [u for u in self.defending_units if u in self.player.units]
        
        # Calculate desired number of defenders based on resources and threat level
        threat_level = self.assess_threat_level()
        desired_defenders = min(
            self.priorities["max_defenders"],
            max(self.priorities["min_defenders"], int(threat_level * self.priorities["max_defenders"]))
        )
        
        # Add or remove defenders as needed
        if current_defenders < desired_defenders:
            available_units = [u for u in military_units if u not in self.defending_units and u.task != "attacking"]
            for unit in available_units[:desired_defenders - current_defenders]:
                unit.task = "defending"
                self.defending_units.append(unit)
        elif current_defenders > desired_defenders:
            for unit in self.defending_units[desired_defenders:]:
                unit.task = None
                self.defending_units.remove(unit)

    def assess_threat_level(self):
        """New method to assess threat level"""
        threat_level = 0.5  # Base threat level
        
        # Check for nearby enemies
        base_pos = self.get_base_position()
        nearby_enemies = self.find_nearby_enemies(20, base_pos)
        
        if nearby_enemies:
            threat_level += 0.3
            
        # Check resource levels
        if (self.player.owned_resources["Food"] < 200 or 
            self.player.owned_resources["Wood"] < 200 or 
            self.player.owned_resources["Gold"] < 200):
            threat_level += 0.2
            
        return min(1.0, threat_level)
