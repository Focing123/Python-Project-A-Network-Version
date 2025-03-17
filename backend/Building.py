#Bulding.py

from Units import *

import random
import math

from backend.Starter_File import players as players_list
from logger import debug_print
from Starter_File import global_speedS

# Building Class
class Building:
    global_speed = global_speedS
    def __init__(self, player, name, hp, build_time, cost, size=1, position=(0, 0)):
        self.player = player  # The player who owns the building
        self.name = name
        self.hp = hp
        self.build_time = build_time  # Time it takes to build the building
        self.cost = cost  # Cost is represented as {"Resource": amount}
        self.size = size  # Size is represented as (width, height)
        self.built = False  # Flag to track if the building has been built
        self.population_increase = 0
        self.position = position  # Store the position of the TownCenter
        self.symbol = 'B'
        self.nb_workers = None # Number of workers for the building --> impact building time
        self.max_hp = hp
        self.is_attacked = False

    def __str__(self):
        return self.symbol  # Ensure the building is represented by just the symbol
    
    @classmethod
    def place_starting_buildings(cls, game_map):
        num_players = len(players_list)
        map_center_x = game_map.width // 2
        map_center_y = game_map.height // 2
        radius = int(0.45 * min(game_map.width, game_map.height))  # 90% of half the map size
    
        angle_step = 360 // num_players  # Equal angular distance between town centers
        random.seed()  # Explicitly seed the random number generator

        for i, player in enumerate(players_list):
            angle = math.radians(i * angle_step)
            town_center_x = map_center_x + int(radius * math.cos(angle))
            town_center_y = map_center_y + int(radius * math.sin(angle))

            # Adjust the location if tile is not free
            while not game_map.is_area_free(town_center_x, town_center_y, TownCenter(player).size):
                town_center_x += random.choice([-1, 0, 1])
                town_center_y += random.choice([-1, 0, 1])

            if game_map.is_area_free(town_center_x, town_center_y, TownCenter(player).size):
                # Create an instance of Building (or TownCenter) to call spawn_building
                building_instance = TownCenter(player)
                player.ai.decided_builds.append((town_center_x, town_center_y, TownCenter(player).size))
                building_instance.spawn_building(player, town_center_x, town_center_y, TownCenter, game_map)

                # Check if the civilization is Marines
                if player.civilization == "Marines":
                    marine_buildings = [
                        (TownCenter, 5, 0), (TownCenter, -5, 0), 
                        (Barracks, 10, 4), (Barracks, -9, -4), 
                        (Stable, 10, -4), (Stable, -9, 4),
                        (ArcheryRange, 13, 0), (ArcheryRange, -12, 0)
                    ]

                    for building, offset_x, offset_y in marine_buildings:
                        new_x = town_center_x + offset_x
                        new_y = town_center_y + offset_y

                        while not game_map.is_area_free(new_x, new_y, building(player).size):
                            new_x += random.choice([-1, 0, 1])
                            new_y += random.choice([-1, 0, 1])

                        # Spawn the building with the map passed in
                        player.ai.decided_builds.append((new_x, new_y, building(player).size))
                        building_instance.spawn_building(player, new_x, new_y, building, game_map)

                    debug_print(f"Placed additional buildings for {player.name} (Marines) around ({town_center_x}, {town_center_y})", 'Blue')
                else:
                    debug_print(f"{player.civilization} civilization does not have additional starting buildings.", 'Yellow')
            else:
                debug_print(f"Failed to place starting town center at ({town_center_x}, {town_center_y})", 'Yellow')

    @classmethod
    def spawn_building(self, player, x, y, building_class, game_map):
        if not game_map.is_area_free(x, y, building_class(player).size):
            debug_print(f"Cannot spawn building at ({x}, {y}): area is not free.", 'Yellow')
            return False
        building = building_class(player)
        building.position = (x, y)
        game_map.place_building(x, y, building)  # Use the passed map instead of cls.map
        player.buildings.append(building)  # Add the building to the player's list of buildings
        #debug_print(f"Building {building.name} belonging to {player.name} at ({x}, {y}) spawned.")

    @classmethod
    def kill_building(cls, player, building_to_kill, game_map):
        if building_to_kill in player.buildings:
            if building_to_kill.position in player.ai.decided_builds and not building_to_kill.name == "Construct":
                player.ai.decided_builds.remove(building_to_kill.position)
            player.buildings.remove(building_to_kill)
            x, y = building_to_kill.position
            game_map.remove_building(int(x), int(y), building_to_kill)  # Assuming game_map is a property of the player
            debug_print(f"Building {building_to_kill} belonging to {player.name} at ({x}, {y}) killed.", 'DarkBlue')
        else:
            debug_print(f"Building {building_to_kill} does not belong to {player.name}.", 'Yellow')


# TownCenter Class
class TownCenter(Building):
    def __init__(self, player):
        super().__init__(player, "Town Center", hp=1000, build_time=15 / Building.global_speed, cost={"Wood": 350}, size=4)
        self.symbol = 'T'
        self.population_increase = 5
        self.training_queue = []
        self.sprite = "towncenter"
        self.sizeizo = (256, 256)  # (width, height)
        self.z = 230 # Verifier sur image
        self.max_hp = 1000

    def spawn_villager(self):
        if self.built:
            return Villager(self.player)

    def drop_point(self, unit, resource_type):
        # Town Center acts as a drop point for resources
        # Add the gathered resources to the player's inventory
        if resource_type in unit.carrying:
            amount = int(unit.carrying[resource_type])
            unit.player.owned_resources[resource_type] += amount
            debug_print(f"Town Center: {unit.player.name} dropped {amount} {resource_type}.", 'green')
        else:
            debug_print("No valid resource to drop.", 'Yellow')
        

    def is_walkable(self):
        return False


# House Class
class House(Building):
    def __init__(self, player):
        super().__init__(player, "House", hp=200, build_time=25 / Building.global_speed, cost={"Wood": 25}, size=2)
        self.symbol = 'H'
        self.population_increase = 5
        self.sprite = "house"
        self.sizeizo = (128, 128)  # (width, height)
        self.z = 130
        self.max_hp = 200

    def is_walkable(self):
        return False


# Camp Class
class Camp(Building):
    def __init__(self, player):
        super().__init__(player, "Camp", hp=200, build_time=25 / Building.global_speed, cost={"Wood": 100}, size=2)
        self.symbol = 'C'
        self.sprite = "camp"
        self.sizeizo = (128, 128)  # (width, height)
        self.z = 130
        self.max_hp = 200


    def drop_point(self, unit, resource_type):
        # Camp acts as a drop point for resources
        # Add the gathered resources to the player's inventory
        if resource_type in unit.carrying:
            amount = int(unit.carrying[resource_type])
            unit.player.owned_resources[resource_type] += amount
            debug_print(f"Camp: {unit.player.name} dropped {amount} {resource_type}.", 'green')
        else:
            debug_print("No valid resource to drop.", 'Yellow')
    
    def is_walkable(self):
        return False


class Farm(Building):
    def __init__(self, player):
        super().__init__(player, "Farm", hp=100, build_time=10 / Building.global_speed, cost={"Wood": 60}, size=2)
        self.symbol = 'F'
        self.food = 300  # Contains 300 Food
        self.is_farmed = False
        self.sprite = "farm"
        self.sizeizo = (128, 64) # (width, height)
        self.z = 0
        self.max_hp = 100


    def is_walkable(self):
        return True

# Barracks Class
class Barracks(Building):
    def __init__(self, player):
        super().__init__(player, "Barracks", hp=500, build_time=50 / Building.global_speed, cost={"Wood": 175}, size=3)
        self.symbol = 'B'
        self.training_queue = []
        self.sprite = "barracks"
        self.sizeizo = (224, 192)  # (width, height)
        self.z = 185
        self.max_hp = 500

 
    def spawn_swordsman(self):
        if self.built:
            return Swordsman(self.player)
        
    def is_walkable(self):
        return False


# Stable Class
class Stable(Building):
    def __init__(self, player):
        super().__init__(player, "Stable", hp=500, build_time=50 / Building.global_speed, cost={"Wood": 175}, size=3)
        self.symbol = 'S'
        self.training_queue = []
        self.sprite = "stable"
        self.sizeizo = (192, 192)  # (width, height)
        self.z = 180
        self.max_hp = 500

    def spawn_horseman(self):
        if self.built:
            return Horseman(self.player)
        
    def is_walkable(self):
        return False


# ArcheryRange Class
class ArcheryRange(Building):
    def __init__(self, player):
        super().__init__(player, "Archery Range", hp=500, build_time=50 / Building.global_speed, cost={"Wood": 175}, size=3)
        self.symbol = 'A'
        self.training_queue = []
        self.sprite = "archeryrange"
        self.sizeizo = (192, 192)  # (width, height)
        self.z = 180
        self.max_hp = 500


    def spawn_archer(self):
        if self.built:
            return Archer(self.player)
        
    def is_walkable(self):
        return False


# Keep Class
class Keep(Building):
    def __init__(self, player):
        super().__init__(player, "Keep", hp=800, build_time=80 / Building.global_speed, cost={"Wood": 35, "Gold": 125}, size=1)
        self.symbol = 'K'
        self.attack = 5
        self.range = 8
        self.sprite = "keep"
        self.last_attack_time = 0    
        self.sizeizo = (64, 64)  # (width, height)
        self.z = 60
        self.max_hp = 800
        self.target = None
        self.fireball_progress = 0

    
    def is_walkable(self):
        return False
    

# Construct Class
class Construct(Building):
    def __init__(self, player):
        super().__init__(player, "Construct", hp=1, build_time=0, cost={"Wood": 1}, size=2)
        self.symbol = '%'
        self.sprite = "construct"
        self.future_building = None
        self.workers = []
        self.sizeizo = (128, 64)  # (width, height)
        self.z = 50
    
    def is_walkable(self):
        return False

