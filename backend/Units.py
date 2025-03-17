import random
import math
from Building import TownCenter
from logger import debug_print
from Starter_File import global_speedS

# Unit Class
class Unit:
    global_speed = global_speedS
    def __init__(self, player, hp, cost, attack, speed, symbol="u", training_time=0, position=(0.0, 0.0)):
        self.player = player
        self.hp = hp
        self.cost = cost
        self.attack = attack
        self.speed = speed
        self.symbol = symbol
        self.training_time = training_time
        self.position = position
        self.target_position = None
        self.target_attack = None
        self.is_attacked_by = None
        self.spawn_building = None
        self.spawn_position = None
        self.direction = "south"
        self.current_frame = 0  # Initialiser à 0 si absent
        self.frame_counter = 0 
        self.is_moving = False

    def __str__(self):
        return self.symbol  # Ensure the building is represented by just the symbol
    
    def move(self, new_position):
        self.position = new_position

    def update(self):
        pass

    @classmethod
    def place_starting_units(cls, players, game_map):
        for player in players:
            town_centers = [building for building in player.buildings if isinstance(building, TownCenter)]
            
            if not town_centers:
                debug_print(f"No town centers found for {player.name}. Skipping unit placement.", 'Yellow')
                continue
                
            town_center = town_centers[0]  # Use the first town center
            center_x, center_y = town_center.position
            
            radius = 7  # Adjust radius as needed

            if player.civilization == "Marines":
                num_villagers = 15
            else:
                num_villagers = 3
                
            debug_print(f"Attempting to spawn {num_villagers} villagers for {player.name} around ({center_x}, {center_y})", 'Red')

            for _ in range(num_villagers):
                placed = False
                
                while not placed:
                    angle = random.uniform(0, 2 * math.pi)
                    distance = random.uniform(0, radius)
                    
                    spawn_x = center_x + int(distance * math.cos(angle))
                    spawn_y = center_y + int(distance * math.sin(angle))

                    if (0 <= spawn_x < game_map.width and 
                        0 <= spawn_y < game_map.height):
                        
                        if game_map.is_tile_free_for_unit(spawn_x, spawn_y):  # Check if tile is free
                            cls.spawn_unit(Villager, spawn_x, spawn_y, player, game_map)  # Place the villager --> IA should spawn them next to the appropriate building
                            placed = True
                        else:
                            pass  # Try again if tile is not free
                    else:
                        pass  # Try again if out of bounds
            debug_print(f"Spawned {num_villagers} villagers for {player.name} near the Town Center at ({center_x}, {center_y})", 'Red')


    @classmethod
    def spawn_unit(cls, unit_class, x, y, player, game_map):
        if isinstance(unit_class, type):
            if unit_class == Horseman:
                unit = unit_class(player, position=(x, y))
            elif unit_class == Villager:
                unit = unit_class(player, position=(x, y))
            else:
                unit = unit_class(player)
        else:
            unit = unit_class
        


        
        if (0 <= x < game_map.width and 
            0 <= y < game_map.height and 
            not (player.population >= player.max_population or 
                player.population >= sum(building.population_increase for building in player.buildings))):
            
            building = game_map.grid[y][x].building
            if not building or building.is_walkable():
                player.units.append(unit)
                unit.position = (x, y)
                player.population += 1
                game_map.place_unit(x, y, unit)
                return unit
            else:
                debug_print(f"Cannot place unit at ({x}, {y}): tile is not walkable.", 'Yellow')
                return None
        else:
            debug_print(f"Cannot place unit at ({x}, {y}): invalid position or population limit reached.", 'Yellow')
            return None

        
    @classmethod
    def train_unit(cls, unit_to_train, x, y, player, building, game_map, current_time_called):
    # Check if the player has enough resources
        for resource_type, amount in unit_to_train.cost.items():
            if player.owned_resources.get(resource_type, 0) < amount and unit_to_train not in player.training_units:
                debug_print(f"Not enough {resource_type} to train {unit_to_train}.", 'Yellow')
                return
        if isinstance(unit_to_train, type):
            if unit_to_train == Horseman:
                unit_to_train = unit_to_train(player, position=(x, y))
            elif unit_to_train == Villager:
                unit_to_train = unit_to_train(player, position=(x, y))
            else:
                unit_to_train = unit_to_train(player)
        
        if player.population < min(player.max_population, sum(building.population_increase for building in player.buildings)):
            unit_to_train.spawn_position = (x, y)
            unit_to_train.spawn_building = building
            if not hasattr(unit_to_train, 'training_start') or unit_to_train.training_start is None:
                unit_to_train.training_start = current_time_called
                for resource_type, amount in unit_to_train.cost.items():
                    if player.owned_resources.get(resource_type, 0) < amount and unit_to_train not in player.training_units:
                        debug_print(f"Not enough {resource_type} to train {unit_to_train.name} for {player.name}.", 'Yellow')
                        return
                    player.owned_resources[resource_type] -= amount
                    
                    debug_print(f"{player.name} spent {amount} {resource_type} to train {unit_to_train.name}.", 'Red')
                player.training_units.append(unit_to_train)
                building.training_queue.append(unit_to_train)

            if current_time_called - unit_to_train.training_start >= unit_to_train.training_time:
                cls.spawn_unit(unit_to_train, x, y, unit_to_train.player, game_map)
                building.training_queue.remove(unit_to_train)
                player.training_units.remove(unit_to_train)
                debug_print(f"Should have spawned {unit_to_train.name} at ({x}, {y})", 'Red')
                
                if building.training_queue:
                    next_unit = building.training_queue[0]
                    next_unit.training_start = current_time_called
                    debug_print(f"Starting training for {next_unit.name}", 'Red')
        else:
            debug_print(f"Too much population or not enough resources to train {unit_to_train.name} for {player.name}.", 'Yellow')
            if building.training_queue:
                building.training_queue.remove(unit_to_train)
                if building.training_queue:
                    next_unit = building.training_queue[0]
                    next_unit.training_start = current_time_called


        
    @classmethod
    def kill_unit(cls, player, unit_to_kill, game_map):
        if unit_to_kill in player.units:
            player.units.remove(unit_to_kill)  # Remove the unit from the player's list of units
            if unit_to_kill in player.ai.defending_units:
                player.ai.defending_units.remove(unit_to_kill)
            player.population -= 1  # Decrease the player's population
            x, y = unit_to_kill.position
            game_map.remove_unit(int(x), int(y), unit_to_kill)  # Assuming game_map is a property of the player
            debug_print(f"Unit {unit_to_kill.name} belonging to {player.name} at ({x}, {y}) killed. (RIP)", 'DarkRed')
        else:
            debug_print(f"Unit {unit_to_kill.name} does not belong to {player.name}.", 'Yellow')

    @classmethod
    def get_all_units(cls, players):
        units = []
        for player in players:
            units.extend(player.units)
        return units

class Villager(Unit):
    cost = {"Wood": 50, "Gold": 0}
    @staticmethod
    def lire_noms_fichier(fichier="../assets/annex/noms_villageois.txt"):
        try:
            with open(fichier, "r") as f:
                noms = [ligne.strip() for ligne in f if ligne.strip()]
            return noms
        except FileNotFoundError:
            debug_print(f"Le fichier {fichier} n'a pas été trouvé.", 'Yellow')
            return ["Villager"]  # in case file not found

    def __init__(self, player, position, name=None):
        if name is None:
            noms_disponibles = self.lire_noms_fichier()
            name = random.choice(noms_disponibles)

        super().__init__(player, hp=25, cost={"Food": 50}, attack=2, speed=0.8 * Unit.global_speed, symbol="v", training_time=3 / Unit.global_speed)
        self.carrying = {"Wood": 0, "Food": 0, "Gold": 0}
        self.carry_capacity = 20  # Can carry up to 20 of any resource
        self.gather_rate = 25/60 * Unit.global_speed  # 25 resources per minute (in resources per second)
        self.name = name
        self.task = None
        self.last_gathered = None
        self.target_resource = None
        self.range = 0.99
        self.is_acting = None
        self.position = position
        self.sprite = "villager"
        self.sprite_height = 50
        self.z = 0
        self.max_hp = 25
        

    @property
    def bbox_bottom(self):
        return self.position[1] + self.sprite_height

# Swordsman Class
class Swordsman(Unit):
    cost = {"Wood": 50, "Gold": 20}
    def __init__(self, player):
        super().__init__(player, hp=40, cost={"Food": 50, "Gold": 20}, attack=4, speed=0.9 * Unit.global_speed, symbol="s", training_time=20 / Unit.global_speed)
        self.range = 0.99
        self.task = None
        self.name = "Swordsman"
        self.is_acting = None
        self.sprite = "swordman"
        self.sprite_height = 52
        self.z = 64
        self.max_hp = 40 # Maximum health points

    @property
    def bbox_bottom(self):
        return self.position[1] + self.sprite_height


# Horseman Class
class Horseman(Unit):
    cost = {"Wood": 80, "Gold": 60}
    def __init__(self, player,position, direction="en_bas"):
        super().__init__(player, hp=45, cost={"Food": 80, "Gold": 20}, attack=4, speed=1.2 * Unit.global_speed, symbol="h", training_time=30 / Unit.global_speed)
        self.range = 0.99
        self.task = None
        self.name = "Horseman"
        self.is_acting = None
        self.position = position
        self.direction = direction
        self.sprite = "horseman"
        self.sprite_height = 90
        self.z = 64
        self.max_hp = 45

    @property
    def bbox_bottom(self):
        return self.position[1] + self.sprite_height


# Archer Class
class Archer(Unit):
    cost = {"Wood": 30, "Gold": 40}
    def __init__(self, player):
        super().__init__(player, hp=30, cost={"Wood": 25, "Gold": 45}, attack=4, speed=1 * Unit.global_speed, symbol="a", training_time=35 / Unit.global_speed)
        self.range = 4  # Archers have a range of 4 tiles
        self.task = None
        self.name = "Archer"
        self.is_acting = None
        self.sprite = "archer"
        self.sprite_height = 54
        self.z = 64
        self.max_hp = 30
        self.arrow_progress = 0
        self.fireball_progress = 0

    @property
    def bbox_bottom(self):
        return self.position[1] + self.sprite_height