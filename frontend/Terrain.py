import random
import math
import curses

from backend.Starter_File import GameMode

class Map:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.grid = [[Tile(x, y) for x in range(width)] for y in range(height)] # THis is for N*M maps to work
        self.resources = {"Gold": [], "Wood": []}
        self.pre_post_entities = {"pre": {"Construct" : []}, "post": {}}
        self.buildings = []
        self.rubbles = []
        self.generate_map()

    def generate_map(self):
        
        self.generate_resources()

    def generate_resources(self):
        
        num_resources = int(self.width * self.height * 0.03)  # 3% of the map as resource tiles

        # Gold Generation
        num_gold = int(num_resources * 0.3)  # 30% of resource tiles as gold

        # Check if gamemode is a starter_file and then adjust gold generation based on the mode
        if GameMode == "Utopia":
            # Utopia: Gold is randomly placed
            for _ in range(num_gold):
                x = random.randint(0, self.width - 1)
                y = random.randint(0, self.height - 1)
                tile = self.grid[y][x]

                if tile.resource is None:  # Ensure no other resources overwrite the tile
                    resource = Gold()
                    tile.resource = resource
                    self.resources["Gold"].append((x, y))  # Store the position of Gold resources
        

        elif GameMode == "Gold Rush":
            # Gold Rush: All gold resources are concentrated in a smaller circle within a larger circle
            center_x = self.width // 2
            center_y = self.height // 2

            # Define a larger radius and a smaller radius for gold placement
            large_radius = min(self.width, self.height) // 10
            small_radius = large_radius // 1  # Smaller radius for denser gold placement

            for _ in range(num_gold):
                # Generate coordinates within the smaller circle inside the larger circle
                while True:
                    angle = random.uniform(0, 2 * math.pi)
                    distance = random.uniform(0, small_radius)
                    x = int(center_x + distance * math.cos(angle))
                    y = int(center_y + distance * math.sin(angle))

                    # Ensure the coordinates are within the grid bounds and within the larger circle
                    if (x - center_x) ** 2 + (y - center_y) ** 2 <= large_radius ** 2:
                        x = max(0, min(x, self.width - 1))
                        y = max(0, min(y, self.height - 1))
                        tile = self.grid[y][x]

                        if tile.resource is None:  # Ensure no other resources overwrite the tile
                            resource = Gold()
                            tile.resource = resource
                            self.resources["Gold"].append((x, y))  # Store the position of Gold resources
                        break  # Exit the loop once a valid position is found


        # Wood Generation
        num_wood = (num_resources - num_gold) // 10  # Remaining resource tiles as wood --> increase the '15' for less forests
        for _ in range(num_wood):
            # Generate a random forest
            forest_size = random.randint(20, 50)
            start_x = random.randint(0, self.width - 1)
            start_y = random.randint(0, self.height - 1)

            # Create an irregular forest by deciding tile placement randomly
            x, y = start_x, start_y
            tile = self.grid[y][x]
            directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

            for _ in range(forest_size):
                # Choose a random direction
                dx, dy = random.choice(directions)
                x += dx
                y += dy

                # Ensure the forest fits within the grid boundaries
                x = max(0, min(x, self.width - 1))
                y = max(0, min(y, self.height - 1))
                tile = self.grid[y][x]

                if tile.resource is None:  # Avoid overwriting existing resources
                    resource = Wood()
                    tile.resource = resource
                    self.resources["Wood"].append((x, y))  # Store Wood resource position


    def is_tile_free(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            tile = self.grid[y][x]
            is_free = tile.resource is None and (tile.building is None or tile.building.is_walkable() == True) and tile.unit == []
            return is_free
        return False
    
    def is_tile_free_for_unit(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            tile = self.grid[y][x]
            is_free = tile.resource is None and (tile.building is None or tile.building.is_walkable() == True)
            return is_free
        return False
    
    def is_area_free(self, x, y, size):
        for i in range(size):
            for j in range(size):
                if not self.is_tile_free(x + i, y + j):
                    return False
        return True

    def place_building(self, x, y, building):
        if self.is_area_free(x, y, building.size):
            building.x = x
            building.y = y
            for i in range(building.size):
                for j in range(building.size):
                    self.grid[y + j][x + i].building = building
                    if self.grid[y + j][x + i].rubble:
                        self.grid[y + j][x + i].rubble = None
                        if self.grid[y + j][x + i].rubble in self.rubbles:
                            self.rubbles.remove(self.grid[y + j][x + i].rubble)
                        

    def remove_building(self, x, y, building):
        for i in range(building.size):
            for j in range(building.size):
                self.grid[y + j][x + i].building = None
                if building.name == "Construct":
                    continue
                if building.is_attacked == True:
                    rubble = Rubble(size=building.size, position=(x + i, y + j))
                    self.grid[y + j][x + i].rubble = rubble
                    if i == 0 and j == 0:
                        self.rubbles.append(rubble)
    
    def place_unit(self, x, y, unit):
        if 0 <= x < self.width and 0 <= y < self.height:
            tile = self.grid[y][x]
            tile.unit.append(unit)  # Place the unit on the tile

    def remove_unit(self, x, y, unit):
        tile = self.grid[y][x]
        if tile.unit is not None and unit in tile.unit:
            tile.unit.remove(unit)  # Remove the unit from the tile
        else:
            print(f"Terrain File : No unit on tile ({x}, {y})")

    def move_unit(self, unit, target_x, target_y, start_x, start_y):
        if 0 <= target_x < self.width and 0 <= target_y < self.height:
            self.remove_unit(start_x, start_y, unit)
            self.place_unit(target_x, target_y, unit)
        else:
            print(f"Terrain File : Target ({target_x}, {target_y}) is out of bounds.")
            
    def get_viewport(self, top_left_x, top_left_y, viewport_width, viewport_height):
        viewport = []
        for y in range(top_left_y, min(top_left_y + viewport_height, self.height)):
            row = []
            for x in range(top_left_x, min(top_left_x + viewport_width, self.width)):
                row.append(self.grid[y][x])
            viewport.append(row)
        return viewport

    def display_viewport(self, stdscr, top_left_x, top_left_y, viewport_width, viewport_height, Map_is_paused=False, changed_tiles=None):
        if changed_tiles is None:
            changed_tiles = set()
        # Initialize colors inside display_viewport
        self.setup_colors()
        
        # Draw the viewport content
        for y in range(viewport_height):
            for x in range(viewport_width):
                map_x = top_left_x + x
                map_y = top_left_y + y
                if 0 <= map_x < self.width and 0 <= map_y < self.height:
                    tile = self.grid[map_y][map_x]
                    if (map_x, map_y) in changed_tiles or not changed_tiles:
                        if tile.building:
                            # Assign color based on player's ID
                            player_id = tile.building.player.id
                            color_pair = curses.color_pair((player_id % 8) + 1)  # Cycle through colors
                            stdscr.addstr(y, x * 2, str(tile.building), color_pair)
                        elif tile.unit:
                            # Assign color based on player's ID
                            for unit in tile.unit:
                                player_id = unit.player.id
                                color_pair = curses.color_pair((player_id % 8) + 1)  # Cycle through colors
                                stdscr.addstr(y, x * 2, str(unit), color_pair)
                        else:
                            stdscr.addstr(y, x * 2, str(tile))

        # Draw red borders if game is paused
        if Map_is_paused:
            border_color = curses.color_pair(4)  # Red border color pair
            # Draw horizontal borders
            for x in range(viewport_width * 2):
                stdscr.addstr(0, x, "─", border_color)  # Top border
                stdscr.addstr(viewport_height - 1, x, "─", border_color)  # Bottom border
            
            # Draw vertical borders
            for y in range(viewport_height):
                stdscr.addstr(y, 0, "│", border_color)  # Left border
                stdscr.addstr(y, viewport_width * 2 - 1, "│", border_color)  # Right border
            
            # Draw corners
            stdscr.addstr(0, 0, "┌", border_color)  # Top-left corner
            stdscr.addstr(0, viewport_width * 2 - 1, "┐", border_color)  # Top-right corner
            stdscr.addstr(viewport_height - 1, 0, "└", border_color)  # Bottom-left corner
            stdscr.addstr(viewport_height - 1, viewport_width * 2 - 1, "┘", border_color)  # Bottom-right corner

        stdscr.refresh()

    def setup_colors(self):
        curses.start_color()
        # Define color pairs: pair number, foreground color, background color
        curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)    # Player 1 (Blue)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)     # Player 2 (Red)
        curses.init_pair(3, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Player 3 (Purple)
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Player 4 (Green)
        curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Player 5 (Yellow)
        curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Player 6 (Cyan)
        curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Player 7 (White)
        curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_WHITE)   # Player 8 (Black background, White text)
        curses.init_pair(9, curses.COLOR_RED, curses.COLOR_BLACK)     # Pause border (Red)
    def find_nearest_resource(self, start_position, resource_type, player):
        min_distance = float('inf')
        nearest_resource = None

        if resource_type in ("Wood", "Gold"):
            # Iterate through each resource position for the specified type
            for resource_x, resource_y in self.resources[resource_type]:
                distance = abs(start_position[0] - resource_x) + abs(start_position[1] - resource_y)

                adjacent_tiles = []
                for x in range(-1, 2):
                    for y in range(-1, 2):
                        if x == 0 and y == 0:
                            continue
                        adjacent_tiles.append((resource_x + x, resource_y + y))

                if distance < min_distance and any(self.is_tile_free_for_unit(x, y) for x, y in adjacent_tiles):
                    min_distance = distance
                    nearest_resource = (resource_x, resource_y)

        elif resource_type == "Food":
            # Iterate through each building position for the specified type
            for building in player.buildings:
                if building.name == "Farm" and building.is_farmed == False:
                    distance = abs(start_position[0] - building.position[0]) + abs(start_position[1] - building.position[1])
                    if distance < min_distance:
                        min_distance = distance
                        nearest_resource = building.position
        else:
            #print(f"Invalid resource type: {resource_type}")
            pass
        if nearest_resource is None:
            #print(f"No available {resource_type} resources found.")
            pass
        return nearest_resource

    def find_drop_point(self, start_position, player):
        min_distance = float('inf')
        nearest_drop_point = None
        # Iterate through each building owned by the player
        for building in player.buildings:
            if building.name in ["Town Center", "Camp"]:  # Check if the building is a valid drop-off point
                distance = abs(start_position[0] - building.position[0]) + abs(start_position[1] - building.position[1])
                if distance < min_distance:
                    min_distance = distance
                    nearest_drop_point = building.position

        if nearest_drop_point is None:
            #print("No available drop-off points found.")
            pass
        return nearest_drop_point    

class Tile:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.resource = None
        self.building = None
        self.unit = []
        self.rubble = None

    def __str__(self):
        if self.unit:
            return getattr(self.unit, 'symbol', '?')
        elif self.building:
            return getattr(self.building, 'symbol', '?')
        elif self.resource:
            return getattr(self.resource, 'symbol', '?')
        #test, on va le supprimer plus tard
        elif self.rubble:
            return "x"
        else:
            return "." 


# Resource Class
class Resource:
    def __init__(self, resource_type, amount, symbol="R"):
        self.type = resource_type  # "Wood", "Gold", "Food"
        self.amount = amount
        self.symbol = symbol

    def gather(self, amount):
        gathered = min(self.amount, amount)
        self.amount -= gathered
        return gathered


# Wood Resource Class
class Wood(Resource):
    def __init__(self):
        self.variant = random.randint(0, 2)  # Randomly select tree variant
        super().__init__(resource_type="Wood", amount=100, symbol="W")


# Food Resource Class
class Food(Resource):
    def __init__(self):
        super().__init__(resource_type="Food", amount=300, symbol="F")  # 300 per farm

# Gold Resource Class
class Gold(Resource):
    def __init__(self):
        super().__init__(resource_type="Gold", amount=800, symbol="G")  # 800 per tile


# Rubble Class
class Rubble:
    def __init__(self, size=1, position=(0, 0), symbol = "x"):
        self.size = size
        self.position = position
        self.symbol = symbol  # Symbol for rubble
        self.is_walkable = True  # Units cannot walk over rubble

    def __str__(self):
        return self.symbol