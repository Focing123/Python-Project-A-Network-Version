#Actions.py

import heapq
import math

from frontend.Terrain import *
from logger import debug_print
from Units import *
from Building import *


class Action:
    def __init__(self, game_map):
        self.map = game_map
        self.debug_print = debug_print


    def get_direction(self, start_x, start_y, target_x, target_y):
        # Calculer les différences
        dx = target_x - start_x
        dy = target_y - start_y

        # Calcul de l'angle en radians, converti en degrés
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360

        # Adapter pour une carte isométrique et inverser l'orientation si nécessaire
        # Définition des plages pour une carte isométrique
        if 337.5 <= angle or angle < 22.5:  # Droite -> Sud-Est
            return "southeast"
        elif 22.5 <= angle < 67.5:  # Bas-droit -> Sud
            return "south"
        elif 67.5 <= angle < 112.5:  # Bas-gauche -> Sud-Ouest
            return "southwest"
        elif 112.5 <= angle < 157.5:  # Gauche -> Ouest
            return "west"
        elif 157.5 <= angle < 202.5:  # Haut-gauche -> Nord-Ouest
            return "northwest"
        elif 202.5 <= angle < 247.5:  # Haut -> Nord
            return "north"
        elif 247.5 <= angle < 292.5:  # Haut-droit -> Nord-Est
            return "northeast"
        elif 292.5 <= angle < 337.5:  # Droite -> Est
            return "east"



    def move_unit(self, unit, target_x, target_y, current_time_called):
        # Check if the target destination is valid
        if not self._is_within_bounds(target_x, target_y) or (not self.map.is_tile_free_for_unit(int(target_x), int(target_y)) and not isinstance(self.map.grid[target_y][target_x].building, Building)):
            return False

        # Get current/starting position of the unit
        start_x, start_y = int(unit.position[0]), int(unit.position[1])
        unit.target_position = (target_x, target_y)
        unit.direction = self.get_direction(start_x, start_y, target_x, target_y)
        unit.is_moving = True

        # If the target is a building, find an adjacent tile
        if isinstance(self.map.grid[target_y][target_x].building, Building) and not type(self.map.grid[target_y][target_x].building).__name__ == "Farm":
            adjacent_tiles = self.get_adjacent_positions(target_x, target_y, self.map.grid[target_y][target_x].building.size)
            for tile in adjacent_tiles:
                if self.map.is_tile_free_for_unit(tile[0], tile[1]):
                    target_x, target_y = tile
                    break

        # If path is not already constructed, construct it using A* algorithm
        if not hasattr(unit, 'path') or not unit.path:
            unit.path = self.astar_pathfinding((int(start_x), int(start_y)), (target_x, target_y))

        # Initialize last move time if not already set
        if not hasattr(unit, 'last_move_time'):
            unit.last_move_time = current_time_called

        # Calculate time passed since the last move
        current_time = current_time_called
        time_since_last_move = min(0.2, current_time - unit.last_move_time) # Limit the time to 0.2 seconds --> good for smooth movement

        # Calculate the maximum distance the unit can move
        distance_to_move = unit.speed * time_since_last_move

        # Ensure there’s a path to follow and the unit can move
        if unit.path and distance_to_move > 0:
            # Get the next target position in the path
            next_step = unit.path[0]

            # Check if the next step is free (dynamic obstacle detection)
            if not self.map.is_tile_free_for_unit(next_step[0], next_step[1]):
                # Recalculate path if the next step is blocked
                unit.path = self.astar_pathfinding((int(start_x), int(start_y)), (target_x, target_y))
                if not unit.path:
                    self.debug_print("Path not found or obstructed", 'Yellow')
                    return False  # No valid path found

            # Calculate the direction vector to the next step
            direction_x = next_step[0] - unit.position[0]
            direction_y = next_step[1] - unit.position[1]
            distance_to_next_step = (direction_x**2 + direction_y**2) ** 0.5
            unit.direction = self.get_direction(unit.position[0], unit.position[1],next_step[0], next_step[1])
            # If within reach of the next step, move directly there
            if distance_to_move >= distance_to_next_step:
                unit.position = next_step
                unit.path.pop(0)  # Remove the step from the path

                # Snap to the tile if it's the last step before the target
                if not unit.path:  # No more steps in the path
                    unit.position = (target_x, target_y)
                    unit.path = None
                    unit.target_position = None
                    Map.move_unit(self.map, unit, int(unit.position[0]), int(unit.position[1]), int(start_x), int(start_y))
                    del unit.last_move_time
                    if hasattr(unit, 'last_gather_time'):
                        del unit.last_gather_time
                    if hasattr(unit, 'path'):
                        del unit.path
                    if hasattr(unit, 'last_move_time'):
                        del unit.last_move_time
                    unit.is_moving = False
                    #self.debug_print("Reached target!")
                    return True
            else:
                # Otherwise, move partway towards the next step
                normalized_x = direction_x / distance_to_next_step
                normalized_y = direction_y / distance_to_next_step

                # Calculate the new position based on the unit's speed
                unit.position = (
                    unit.position[0] + normalized_x * distance_to_move,
                    unit.position[1] + normalized_y * distance_to_move,
                )

            # Update the last move time
            unit.last_move_time = current_time
            Map.move_unit(self.map, unit, int(unit.position[0]), int(unit.position[1]), int(start_x), int(start_y))

            return True

        return False


    def astar_pathfinding(self, start, goal):
        open_list = []
        heapq.heappush(open_list, (0, start))  # Initialisation avec le point de départ

        came_from = {}  # Stocker les nœuds explorés
        g_cost = {start: 0}  # Coût actuel pour atteindre chaque nœud
        closed_set = set()  # Ensemble des nœuds déjà visités

        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])  # Distance Manhattan

        while open_list:
            _, current = heapq.heappop(open_list)

            # Si nous atteignons l'objectif
            if current == goal:
                return self._reconstruct_path(came_from, current)

            closed_set.add(current)

            for neighbor in self._get_neighbors(current):
                if neighbor in closed_set:
                    continue

                # Vérifier si le voisin est bloqué
                if not self.map.is_tile_free_for_unit(neighbor[0], neighbor[1]):
                    continue

                # Coût du chemin jusqu'au voisin
                tentative_g_cost = g_cost[current] + self._move_cost(current, neighbor)

                if neighbor not in g_cost or tentative_g_cost < g_cost[neighbor]:
                    g_cost[neighbor] = tentative_g_cost
                    priority = tentative_g_cost + heuristic(neighbor, goal)
                    heapq.heappush(open_list, (priority, neighbor))
                    came_from[neighbor] = current

        # Aucun chemin trouvé
        return None

    def _is_within_bounds(self, x, y):
        return 0 <= x < self.map.width and 0 <= y < self.map.height

    def _get_neighbors(self, position):
        x, y = position
        neighbors = []

        # Possible directions
        directions = [
            (-1, 0), (1, 0),
            (0, -1), (0, 1),
            (-1, -1), (-1, 1),
            (1, -1), (1, 1)
        ]

        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if self._is_within_bounds(nx, ny) and self.map.is_tile_free_for_unit(nx, ny):
                neighbors.append((nx, ny))

        return neighbors

    def get_adjacent_positions(self, x, y, size):
        adjacent_positions = []

        # Left side and right side (excluding corners)
        for i in range(size):
            # Left side (vertical from y to y+size-1, column x-1)
            if 0 <= x - 1 < self.map.width:  # Check if left is within bounds
                adjacent_positions.append((x - 1, y + i))

            # Right side (vertical from y to y+size-1, column x + size)
            if 0 <= x + size < self.map.width:  # Check if right is within bounds
                adjacent_positions.append((x + size, y + i))

            # Top side (horizontal from x to x+size-1, row y-1)
            if 0 <= y - 1 < self.map.height:  # Check if top is within bounds
                adjacent_positions.append((x + i, y - 1))

            # Bottom side (horizontal from x to x+size-1, row y + size)
            if 0 <= y + size - 1 < self.map.height:  # Check if bottom is within bounds
                adjacent_positions.append((x + i, y + size))  # y + size - 1 is the bottom row, use y+size for adjacent

        # Corners (if not already included)
        if 0 <= x - 1 < self.map.width and 0 <= y - 1 < self.map.height:  # Top-left corner
            adjacent_positions.append((x - 1, y - 1))
        if 0 <= x + size -1 < self.map.width and 0 <= y - 1 < self.map.height:  # Top-right corner
            adjacent_positions.append((x + size - 1, y - 1))
        if 0 <= x - 1 < self.map.width and 0 <= y + size < self.map.height:  # Bottom-left corner
            adjacent_positions.append((x - 1, y + size - 1))
        if 0 <= x + size < self.map.width and 0 <= y + size - 1 < self.map.height:  # Bottom-right corner
            adjacent_positions.append((x + size - 1, y + size - 1))

        # Remove duplicates by converting to a set and back to a list
        adjacent_positions = list(set(adjacent_positions))

        return adjacent_positions




    def _move_cost(self, current, neighbor):
        return 1 if abs(current[0] - neighbor[0]) + abs(current[1] - neighbor[1]) == 1 else 1.414

    def _reconstruct_path(self, came_from, current):
        path = []
        while current in came_from:
            path.append(current)
            current = came_from[current]
        path.reverse()  #inverse the path for it to be in the right order
        return path
    
    def gather_resources(self, unit, resource_type, current_time_called):
        if resource_type == "Gold" or resource_type == "Wood":
            unit.last_gathered = resource_type
            # Find the coordinates of the nearest resource of the specified type
            if unit.target_resource is None:
                target = Map.find_nearest_resource(self.map, unit.position, resource_type, unit.player)
                if target is not None:
                    unit.target_resource = target
                else:
                    #self.debug_print(f"No {resource_type} resources found.")
                    unit.task = None
                    unit.target_resource = None
                    unit.target_position = None
                    return False
            # Find a free tile around the target resource
            adjacent_tiles = self._get_neighbors((unit.target_resource[0], unit.target_resource[1]))
            free_tile = None

            # Check if unit is already adjacent to the resource (within a small threshold)
            if not any(abs(unit.position[0] - tile[0]) < 0.1 and abs(unit.position[1] - tile[1]) < 0.1 for tile in adjacent_tiles):
                # Move to an adjacent tile if not already there
                for tile in adjacent_tiles:
                    if self.map.is_tile_free_for_unit(tile[0], tile[1]):
                        free_tile = tile
                        break

                # If a free tile was found, move the unit towards it
                if free_tile:
                    # Update unit's position by calling move_unit
                    self.move_unit(unit, free_tile[0], free_tile[1], current_time_called)
                    unit.task = "marching"
                    return True
                else:
                    self.debug_print("No free tile found around the resource.", 'Yellow')
                    return False

            if any(abs(unit.position[0] - tile[0]) < 0.1 and abs(unit.position[1] - tile[1]) < 0.1 for tile in adjacent_tiles):
                unit.task = "gathering"
                self._gather(unit, resource_type, current_time_called)
                return True

        elif resource_type == "Food":
            unit.last_gathered = resource_type
            # Find the coordinates of the nearest resource of the specified type
            target = Map.find_nearest_resource(self.map, unit.position, resource_type, unit.player)
            if target is not None:
                unit.target_resource = target
            else:
                #self.debug_print(f"No {resource_type} resources found.")
                unit.task = None
                unit.target_position = None
                unit.target_resource = None
                return False
            # Move to the target tile if not already there
            if not (abs(unit.position[0] - unit.target_resource[0]) < 0.1 and abs(unit.position[1] - unit.target_resource[1]) < 0.1):
                # Update unit's position by calling move_unit
                self.move_unit(unit, unit.target_resource[0], unit.target_resource[1], current_time_called)
                unit.task = "marching"
                return True
            else:
                unit.task = "gathering"
                if hasattr(unit, 'last_gather_time'):
                    del unit.last_gather_time
                if hasattr(unit, 'path'):
                    del unit.path
                if hasattr(unit, 'last_move_time'):
                    del unit.last_move_time
                self._gather(unit, resource_type, current_time_called)
                return True

        else:
            self.debug_print("Invalid resource type.", 'Yellow')
            return False

    def _gather(self, unit, resource_type, current_time_called):
        unit.is_moving = False
        tile = self.map.grid[unit.target_resource[1]][unit.target_resource[0]] if unit.target_resource is not None else None
        
        unit.direction = self.get_direction(unit.position[0], unit.position[1], unit.target_resource[0], unit.target_resource[1])

        # Check if there is a resource on the target tile and it's the correct type
        if (tile and tile.resource and tile.resource.type == resource_type) or (resource_type == "Food" and tile.building and tile.building.name == "Farm"):
            if resource_type == "Food":
                tile.building.is_farmed = True
            # Ensure the unit has capacity to gather more of this resource
            if unit.carrying[resource_type] < unit.carry_capacity and (tile.resource and tile.resource.amount > 0 or (tile.building and tile.building.name == "Farm" and tile.building.food > 0)):
                # Initialize last gather time if it hasn't been set
                if not hasattr(unit, 'last_gather_time'):
                    unit.last_gather_time = current_time_called

                # Calculate time since last gather action
                time_since_last_gather = current_time_called - unit.last_gather_time
                gatherable_amount = unit.gather_rate * time_since_last_gather

                # Calculate the actual amount the unit can carry
                space_left = unit.carry_capacity - unit.carrying[resource_type]
                amount_to_gather = min(gatherable_amount, space_left)

                # Update unit's carrying load and the resource amount on the tile
                if amount_to_gather > 0:
                    unit.carrying[resource_type] += amount_to_gather
                    if resource_type == "Gold" or resource_type == "Wood":
                        tile.resource.amount -= amount_to_gather
                        # If resource is depleted, remove it from the map
                        if tile.resource.amount <= 0:
                            tile.resource = None
                            self.map.resources[resource_type].remove(unit.target_resource)
                    elif resource_type == "Food" and tile.building.name == "Farm":
                        tile.building.food -= amount_to_gather
                        if tile.building.food <= 0:
                            Building.kill_building(unit.player, tile.building, self.map)                           

                    # Update the last gather time
                    unit.last_gather_time = current_time_called
        else:
            # No resource found; start returning resources if carrying any
            if unit.carrying[resource_type] > 0:
                unit.task = "returning"
        
        # Check if unit's carrying capacity is full or if it needs to return due to lack of resource
        if unit.carrying[resource_type] >= unit.carry_capacity or unit.task == "returning":
            unit.task = "returning"
            # Locate the nearest drop-off location (Town Center or Camp)
            if resource_type == "Food" and tile.building:
                tile.building.is_farmed = False
            returning_position = Map.find_drop_point(self.map, unit.position, unit.player)

            # Move the unit to a tile around the building at the returning position if found
            if returning_position:
                building = self.map.grid[returning_position[1]][returning_position[0]].building
                if building:
                    building_size = building.size  # Assuming building has a size attribute
                    building_position = building.position

                    # Find a tile around the building
                    surrounding_tiles = []
                    for dx in range(-1, building_size + 1):
                        for dy in range(-1, building_size + 1):
                            if (dx == -1 or dx == building_size) or (dy == -1 or dy == building_size):
                                tile_x = building_position[0] + dx
                                tile_y = building_position[1] + dy
                                if self.map.is_tile_free_for_unit(tile_x, tile_y):
                                    surrounding_tiles.append((tile_x, tile_y))

                    if surrounding_tiles:
                        new_position = surrounding_tiles[0]  # Choose the first accessible tile
                        self.move_unit(unit, new_position[0], new_position[1], current_time_called)

                        # Check if unit has reached the drop-off destination to deposit resources
                        if abs(unit.position[0] - new_position[0]) < 1.01 and abs(unit.position[1] - new_position[1]) < 1.01:
                            # Deposit resources and reset carrying load
                            if isinstance(building, Building):
                                building.drop_point(unit, resource_type)
                            unit.carrying[resource_type] = 0
                            unit.task = None
                            unit.target_resource = None
                            unit.target_position = None

                            # Clear movement-related attributes
                            if hasattr(unit, 'last_gather_time'):
                                del unit.last_gather_time
                            if hasattr(unit, 'path'):
                                del unit.path
                            if hasattr(unit, 'last_move_time'):
                                del unit.last_move_time
            else:
                self.debug_print("No valid building found for resource return.", 'Yellow')
                unit.task = None

    def go_battle(self, unit, enemy_unit, current_time_called):
        if not enemy_unit:
            unit.task = None
            unit.target_attack = None
            if hasattr(unit, 'path'):
                del unit.path
            if hasattr(unit, 'last_move_time'):
                del unit.last_move_time
            return

        unit.task = "going_to_battle"
        unit.target_attack = enemy_unit

        # Get the current position of the enemy
        if isinstance(enemy_unit, Building):
            adjacent_tiles = self.get_adjacent_positions(enemy_unit.position[0], enemy_unit.position[1], enemy_unit.size)
            free_tiles = [tile for tile in adjacent_tiles if self.map.is_tile_free_for_unit(tile[0], tile[1])]
            for tile in free_tiles:
                if self.map.is_tile_free_for_unit(tile[0], tile[1]):
                    target_x, target_y = tile
                    break
        else:
            target_x, target_y = enemy_unit.position

        # Check if the unit is within range to attack
        if isinstance(enemy_unit, Unit) and ((unit.position[0] - target_x)**2 + (unit.position[1] - target_y)**2)**0.5 <= unit.range + 0.25: # Add a small threshold to ensure the unit is within range
            unit.task = "attacking"
            enemy_unit.is_attacked_by = unit
            enemy_unit.task = "is_attacked"
            unit.is_moving = False
            self._attack(unit, enemy_unit, current_time_called)
        elif isinstance(enemy_unit, Building) and (unit.position[0] == target_x and unit.position[1] == target_y or (isinstance(unit, Archer) and abs(unit.position[0] - target_x) <= unit.range and unit.position[1] == target_y)):
            unit.task = "attacking"
            unit.target_position = None
            unit.is_moving = False
            self._attack(unit, enemy_unit, current_time_called)
        else:
            self.move_unit(unit, int(target_x), int(target_y), current_time_called)

    
    def _attack(self, unit, enemy_unit, current_time_called):
        unit.is_moving = False
        if hasattr(unit, 'path'):
            del unit.path
        if hasattr(unit, 'last_move_time'):
            del unit.last_move_time
        if unit.target_position is not None:
            unit.target_position = None
        if not enemy_unit or enemy_unit.hp <= 0:
            unit.task = None
            unit.target_attack = None
            return
        distance = ((unit.position[0] - enemy_unit.position[0])**2 + (unit.position[1] - enemy_unit.position[1])**2)**0.5 if not isinstance(enemy_unit, Building) else 0
        if distance <= unit.range + 0.6: # Add a small threshold to ensure the unit is within range
            if not hasattr(unit, 'last_hit_time'):
                unit.last_hit_time = 0

            time_since_last_hit = current_time_called - unit.last_hit_time
            if time_since_last_hit >= 1.0:  # Ensure at least 1 second between attacks
                if unit.attack >= enemy_unit.hp:
                    enemy_unit.hp = 0
                    if isinstance(enemy_unit, Building):
                        Building.kill_building(enemy_unit.player, enemy_unit, self.map)
                        self.debug_print(f"{unit.name} has destroyed the building {enemy_unit.name}.", 'Red')

                    else:
                        Unit.kill_unit(enemy_unit.player, enemy_unit, self.map)
                    unit.task = None
                    del unit.last_hit_time
                    unit.target_attack = None
                    if hasattr(unit, 'path'):
                        del unit.path
                    if hasattr(unit, 'last_move_time'):
                        del unit.last_move_time
                else:
                    self.debug_print(f"{unit.name} is attacking {enemy_unit.name}...", 'Red')
                    enemy_unit.hp -= unit.attack
                    if isinstance(enemy_unit, Building):
                            enemy_unit.is_attacked = True
                    if not isinstance(enemy_unit, Building):
                        enemy_unit.is_attacked_by = unit
                        enemy_unit.task = "is_attacked"

                unit.last_hit_time = current_time_called
        else:
            unit.task = "going_to_battle"  # Reset to movement phase
            self.debug_print(f"not entering attack phase, distance: {distance}", 'Red')

    def construct_building(self, unit, building_type, x, y, player, current_time_called):
        # Check if unit is already stuck or in an impossible construction state
        if unit.task is not None:
            # Check if task is stale or impossible
            if (hasattr(unit, 'target_building') and 
                (unit.target_building[0] != x or unit.target_building[1] != y)):
                # Reset task if trying to build at a different location
                unit.task = None
                del unit.target_building
                if hasattr(unit, 'path'):
                    del unit.path
                if hasattr(unit, 'last_move_time'):
                    del unit.last_move_time
                return False

        # Validate construction site
        if self.map.grid[y][x].building and not self.map.grid[y][x].building.name == "Construct":  
            if not self.map.is_area_free(x, y, building_type(player).size):
                self.debug_print(f"Cannot construct building at ({x}, {y}): area not free.", 'Yellow')
                unit.task = None
                return False
        elif self.map.grid[y][x].resource:
            self.debug_print(f"Cannot construct building at ({x}, {y}): resource present.", 'Yellow')
            unit.task = None
            return False
        
        if any(resource not in unit.player.owned_resources or unit.player.owned_resources[resource] < amount 
               for resource, amount in building_type(player).cost.items()):
            self.debug_print("Cannot construct building: insufficient resources.", 'Yellow')
            unit.task = None
            return False

        # Set construction attributes
        unit.construction_type = building_type
        unit.target_building = (x, y)

        # Movement to construction site
        if unit.task != "going_to_construction_site":
            unit.task = "going_to_construction_site"
            
            adjacent_positions = self.get_adjacent_positions(x, y, building_type(player).size)
            for pos in adjacent_positions:
                if self.map.is_tile_free_for_unit(pos[0], pos[1]):
                    self.move_unit(unit, pos[0], pos[1], current_time_called)
                    break
        
        # Reached construction site
        if unit.target_position is None:
            unit.task = "constructing"
            unit.direction = self.get_direction(unit.position[0], unit.position[1], x, y)
            
            # Track construction with additional safeguards
            self._track_construction(unit, building_type, x, y, player, current_time_called)
            
            # Ensure construction start time
            if not hasattr(unit, 'start_building'):
                unit.start_building = current_time_called
            
            # Spawn construction marker if needed
            Building.spawn_building(player, x, y, Construct, self.map)

        return True

    def _track_construction(self, unit, building_type, x, y, player, current_time_called):
        # Find or create construction entry
        construction_entry = next(
            (b for b in player.constructing_buildings if b["position"] == (x, y)), 
            None
        )

        if construction_entry:
            # Prevent duplicate workers
            if unit not in construction_entry.get("workers", []):
                construction_entry["num_workers"] = construction_entry.get("num_workers", 0) + 1
                construction_entry.setdefault("workers", []).append(unit)
        else:
            # Create new construction entry
            new_entry = {
                "position": (x, y),
                "num_workers": 1,
                "workers": [unit],
                "type": building_type,
                "start_time": current_time_called,
                "completed": False
            }
            for resource, amount in building_type(player).cost.items():
                player.owned_resources[resource] -= amount
                self.debug_print(f"{player.name} spent {amount} {resource} to construct {building_type.__name__}.", 'Blue')
            player.constructing_buildings.append(new_entry)

    def _construct(self, unit, building_type, x, y, player, current_time_called):
        # Find active construction entry
        construction_entry = next(
            (b for b in player.constructing_buildings if b["position"] == (x, y)), 
            None
        )
        
        if not construction_entry or construction_entry.get("completed", False):
            unit.task = None
            return False

        # Calculate construction time
        num_workers = construction_entry.get("num_workers", 1)
        actual_building_time = 3 * building_type(player).build_time / (num_workers + 2)

        # Check construction completion
        if current_time_called - unit.start_building >= actual_building_time:
            # Remove existing building
            if self.map.grid[y][x].building:
                Building.kill_building(player, self.map.grid[y][x].building, self.map)
            
            # Spawn new building
            Building.spawn_building(player, x, y, building_type, self.map)

            # Mark construction as completed
            construction_entry["completed"] = True

            # Reset workers
            for worker in construction_entry.get("workers", []):
                worker.task = None
                for attr in ['target_building', 'construction_type', 'start_building']:
                    if hasattr(worker, attr):
                        delattr(worker, attr)

            # Remove completed construction
            player.constructing_buildings = [
                b for b in player.constructing_buildings if not b.get("completed", False)
            ]
            
            self.debug_print(f"Building {building_type.__name__} completed at ({x}, {y}).", 'Blue')
            return True

        return False
        
    def attack_target(self, building, target, current_time_called, game_map): # for the Keep
        if target is not None:
            building.target = target
            if current_time_called - building.last_attack_time >= 1:
                building.last_attack_time = current_time_called
                if building.attack >= target.hp:
                    target.hp = 0
                    if isinstance(target, Building):
                        Building.kill_building(target.player, target, game_map)
                    else:
                        Unit.kill_unit(target.player, target, game_map)
                else:
                    target.hp -= building.attack
                    target.is_attacked = True
                    self.debug_print(f"{building.name} is attacking {target.name}...", 'Red')
                return True