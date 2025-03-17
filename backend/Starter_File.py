#Config File
import pygame
import sys
import curses
import os
from Players import *


# Game Mode
GameMode = None # "Utopia" or "Gold Rush"

# Set up map size
map_size = (120, 120) #minimum 120x120

# Set up GUI size
GUI_size = type('GUI_size', (object,), {})()
GUI_size.x = 800
GUI_size.y = 600

# Initialize empty players list
players = []

global_speedS = 10

class StartMenu:
    def __init__(self, screen_width=800, screen_height=600):
        pygame.init()
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("AIge of EmpAIre")
        
        self.colors = {
            'background': (50, 50, 50),
            'button': (100, 100, 100),
            'button_hover': (150, 150, 150),
            'text': (255, 255, 255),
            'disabled': (80, 80, 80)  # Color for disabled buttons
        }
        
        # Charger l'image de fond
        self.background_image = pygame.image.load(r'..\assets\MenuPhoto\menu.png')
        self.background_image = pygame.transform.scale(self.background_image, (screen_width, screen_height))
        # Adapter l'image à la taille de l'écran

        # Adjusted button positions for 3 buttons
        self.buttons = [
            {'text': 'Start Game', 'rect': pygame.Rect(300, 250, 200    , 50)},
            {'text': 'Load Game', 'rect': pygame.Rect(300, 320, 200, 50)},
            {'text': 'Exit', 'rect': pygame.Rect(300, 390, 200, 50)}
        ]
        self.font = pygame.font.Font(None, 48)
        
        # Check for save files
        self.has_saves = self.check_save_files()
    
    def check_save_files(self):
        save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'annex')
        save_files = [f for f in os.listdir(save_dir) if f.startswith('game_save') and f.endswith('.dat')]
        return len(save_files) > 0
    
    def draw(self):
        self.screen.blit(self.background_image, (0, 0))
        
        title = self.font.render("AIge of EmpAIre", True, self.colors['text'])
        title_rect = title.get_rect(center=(400, 150))
        self.screen.blit(title, title_rect)
        
        mouse_pos = pygame.mouse.get_pos()
        for button in self.buttons:
            # Disable Load Game button if no saves exist
            if button['text'] == 'Load Game' and not self.has_saves:
                color = self.colors['disabled']
            else:
                color = self.colors['button_hover'] if button['rect'].collidepoint(mouse_pos) else self.colors['button']
            
            pygame.draw.rect(self.screen, color, button['rect'], border_radius=5)
            
            text = self.font.render(button['text'], True, self.colors['text'])
            text_rect = text.get_rect(center=button['rect'].center)
            self.screen.blit(text, text_rect)
    
    def run(self):
        running = True
        while running:
            self.draw()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return 'quit'
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = event.pos
                    for button in self.buttons:
                        if button['rect'].collidepoint(mouse_pos):
                            return button['text']
            
            pygame.display.flip()

class LoadGameMenu:
    def __init__(self, screen_width=800, screen_height=600):
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("AIge of EmpAIre - Load a game")
        
        self.colors = {
            'background': (50, 50, 50),
            'button': (175, 128, 79),
            'button_hover': (150, 150, 150),
            'text': (255, 255, 255),
            'selected': (120, 160, 120),
            'disabled': (80, 80, 80),
            'scrollbar': (70, 70, 70),
            'scrollbar_hover': (90, 90, 90)
        }
        self.loadmenu_image = pygame.image.load(r'..\assets\MenuPhoto\parametrebueno2.png')
        self.loadmenu_image = pygame.transform.scale(self.loadmenu_image, (screen_width, screen_height))
        
        # Get save files
        self.save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'annex')
        self.save_files = sorted([f for f in os.listdir(self.save_dir) if f.endswith('.dat')])
        
        # Scroll settings
        self.scroll_y = 0
        self.visible_saves = 5  # Number of saves visible at once
        self.button_height = 60
        self.button_spacing = 0
        self.scroll_area_height = self.visible_saves * (self.button_height + self.button_spacing)
        self.total_height = len(self.save_files) * (self.button_height + self.button_spacing)
        
        # Scrollbar
        self.scrollbar_width = 20
        self.scrollbar_height = (self.scroll_area_height / self.total_height) * self.scroll_area_height if self.total_height > self.scroll_area_height else 0
        self.scrollbar_rect = pygame.Rect(620, 180, self.scrollbar_width, self.scrollbar_height)
        self.scrolling = False
        
        # Create buttons for save files
        self.save_buttons = []
        for i, save_file in enumerate(self.save_files):
            y_pos = 180 + i * self.button_height
            self.save_buttons.append({
                'text': save_file,
                'rect': pygame.Rect(200, y_pos, 400, 50),
                'path': os.path.join(self.save_dir, save_file)
            })
        
        # Navigation buttons
        self.back_button = {'text': 'Retour', 'rect': pygame.Rect(50, 500, 120, 50)}
        self.load_button = {'text': 'Charger', 'rect': pygame.Rect(630, 500, 120, 50)}
        
        self.selected_save = None
        self.font = pygame.font.Font(None, 36)
        self.title_font = pygame.font.Font(None, 48)

    def handle_scroll(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:  # Mouse wheel up
                self.scroll_y = max(0, self.scroll_y - 30)
                self._update_scrollbar_position()
            elif event.button == 5:  # Mouse wheel down
                max_scroll = max(0, self.total_height - self.scroll_area_height)
                self.scroll_y = min(max_scroll, self.scroll_y + 30)
                self._update_scrollbar_position()
            elif self.scrollbar_rect.collidepoint(event.pos):  # Click on scrollbar
                self.scrolling = True
                self.scroll_start_y = event.pos[1]  # Save initial click position
                self.initial_scroll_y = self.scroll_y  # Save initial scroll position
        
        elif event.type == pygame.MOUSEBUTTONUP:
            self.scrolling = False
        
        elif event.type == pygame.MOUSEMOTION and self.scrolling:
            # Calculate movement delta
            delta_y = event.pos[1] - self.scroll_start_y
            scroll_range = self.scroll_area_height - self.scrollbar_height
            
            # Convert pixel movement to scroll movement
            scroll_delta = (delta_y / scroll_range) * (self.total_height - self.scroll_area_height)
            new_scroll = self.initial_scroll_y + scroll_delta
            
            # Apply bounds
            self.scroll_y = max(0, min(new_scroll, self.total_height - self.scroll_area_height))
            self._update_scrollbar_position()

    def _update_scrollbar_position(self):
        """Update scrollbar position based on current scroll_y"""
        if self.total_height > self.scroll_area_height:
            scroll_ratio = self.scroll_y / (self.total_height - self.scroll_area_height)
            scroll_range = self.scroll_area_height - self.scrollbar_height
            self.scrollbar_rect.y = 180 + scroll_ratio * scroll_range

    def draw(self):
        mouse_pos = pygame.mouse.get_pos()
        # Draw background
        self.screen.blit(self.loadmenu_image, (0, 0))
        
        # Draw title
        title = self.title_font.render("Load a game", True, self.colors['text'])
        title_rect = title.get_rect(center=(400, 80))
        self.screen.blit(title, title_rect)
        
        # Create a surface for the save list area
        save_list_surface = pygame.Surface((430, self.scroll_area_height))
        save_list_surface.fill(self.colors['background'])
        
        # Draw save file buttons
        visible_area = pygame.Rect(200, 180, 400, self.scroll_area_height)
        
        for i, button in enumerate(self.save_buttons):
            button_y = i * self.button_height - self.scroll_y
            if -self.button_height <= button_y <= self.scroll_area_height:
                # Update button rect position
                button['rect'].y = button_y + 180
                
                # Determine button color based on state
                color = self.colors['selected'] if button == self.selected_save else \
                       self.colors['button_hover'] if button['rect'].collidepoint(mouse_pos) else \
                       self.colors['button']
                
                # Draw button if it's in the visible area
                if visible_area.colliderect(button['rect']):
                    pygame.draw.rect(self.screen, color, button['rect'], border_radius=5)
                    text = self.font.render(button['text'], True, self.colors['text'])
                    text_rect = text.get_rect(center=button['rect'].center)
                    self.screen.blit(text, text_rect)
        
        # Draw scrollbar background
        if self.total_height > self.scroll_area_height:
            pygame.draw.rect(self.screen, self.colors['scrollbar'], 
                           (620, 180, self.scrollbar_width, self.scroll_area_height))
            
            # Draw scrollbar
            scrollbar_color = self.colors['scrollbar_hover'] if self.scrollbar_rect.collidepoint(mouse_pos) else self.colors['button']
            pygame.draw.rect(self.screen, scrollbar_color, self.scrollbar_rect)
        
        # Draw navigation buttons
        back_color = self.colors['button_hover'] if self.back_button['rect'].collidepoint(mouse_pos) else self.colors['button']
        pygame.draw.rect(self.screen, back_color, self.back_button['rect'], border_radius=5)
        back_text = self.font.render(self.back_button['text'], True, self.colors['text'])
        back_rect = back_text.get_rect(center=self.back_button['rect'].center)
        self.screen.blit(back_text, back_rect)
        
        load_color = self.colors['disabled'] if not self.selected_save else \
                    self.colors['button_hover'] if self.load_button['rect'].collidepoint(mouse_pos) else \
                    self.colors['button']
        pygame.draw.rect(self.screen, load_color, self.load_button['rect'], border_radius=5)
        load_text = self.font.render(self.load_button['text'], True, self.colors['text'])
        load_rect = load_text.get_rect(center=self.load_button['rect'].center)
        self.screen.blit(load_text, load_rect)

    def run(self):
        running = True
        while running:
            self.draw()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                elif event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP]:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = event.pos
                        
                        # Handle save file selection
                        for button in self.save_buttons:
                            if button['rect'].collidepoint(mouse_pos):
                                self.selected_save = button
                        
                        # Handle back button
                        if self.back_button['rect'].collidepoint(mouse_pos):
                            return 'back'
                        
                        # Handle load button
                        if self.load_button['rect'].collidepoint(mouse_pos) and self.selected_save:
                            return self.selected_save['path']
                    
                    # Handle scrolling
                    self.handle_scroll(event)
                
                elif event.type == pygame.MOUSEMOTION and self.scrolling:
                    self.handle_scroll(event)
            
            pygame.display.flip()

class GameSettingsMenu:
    def __init__(self, screen_width=800, screen_height=600):

        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("AIge of EmpAIre - Setting of the game")
        
        # Store screen dimensions and center position
        self.screen_width = screen_width
        self.center_x = screen_width // 2
        
        self.colors = {
            'background': (50, 50, 50),
            'button': (175, 128, 79),
            'button_hover': (150, 150, 150),
            'text': (255, 255, 255),
            'selected': (120, 160, 120),
            'input_bg': (70, 70, 70)
        }
        
        self.settingmenu_image = pygame.image.load(r'..\assets\MenuPhoto\parametrebueno.png')
        self.settingmenu_image = pygame.transform.scale(self.settingmenu_image, (screen_width, screen_height))

        self.font = pygame.font.Font(None, 36)
        self.title_font = pygame.font.Font(None, 48)
        
        # Game settings
        self.game_modes = ["Utopia", "Gold Rush"]
        self.current_mode = 0
        global GameMode
        GameMode = self.game_modes[self.current_mode]
        self.map_width = 120
        self.map_height = 120
        self.num_players = 3
        
        # Popup settings
        self.show_mode_popup = False
        button_width = 200
        button_height = 50
        
        # Center positions
        self.center_x = screen_width // 2
        self.label_offset = 150  # Distance from center for labels
        
        # Map size controls
        self.width_input = {
            'text': str(self.map_width),
            'active': False
        }
        
        self.height_input = {
            'text': str(self.map_height),
            'active': False
        }
        
        # Map size buttons
        self.width_button = {
            'text': str(self.map_width),
            'rect': pygame.Rect(self.center_x + 40, 295, 80, 50),
            'active': False
        }
        
        self.height_button = {
            'text': str(self.map_height),
            'rect': pygame.Rect(self.center_x + 180, 295, 80, 50),
            'active': False
        }
        
        self.player_input = {
            'text': str(self.num_players),
            'active': False
        }
        
        # Mode button - centered
        self.mode_button = {
            'text': self.game_modes[self.current_mode], 
            'rect': pygame.Rect(self.center_x + 45, 195, 200, 50)
        }
        
        # Create mode selection buttons for popup
        popup_x = self.mode_button['rect'].right + 10  # Position to the right of the mode button
        self.mode_options = []
        for i, mode in enumerate(self.game_modes):
            self.mode_options.append({
                'text': mode,
                'rect': pygame.Rect(popup_x, 195 + i * 50, 200, 50)  # Align with mode button vertically
            })
        
        # Update popup background rect
        self.popup_rect = pygame.Rect(
            popup_x, 
            195,  # Same Y as mode button
            200,  # Same width as mode button
            len(self.game_modes) * 50  # Height for all options
        )
        
        # Player count button - centered
        self.player_button = {
            'text': str(self.num_players),
            'rect': pygame.Rect(self.center_x + 105, 395, 80, 50),
            'active': False
        }
        
        # Navigation buttons
        self.start_button = {'text': 'Continue', 'rect': pygame.Rect(self.center_x + 70, 510, 150, button_height)}
        self.back_button = {'text': 'Back', 'rect': pygame.Rect(self.center_x - 210, 510, 150, button_height)}

    def draw(self):
        mouse_pos = pygame.mouse.get_pos()
        self.screen.blit(self.settingmenu_image, (0, 0))
        
        # Draw title
        title = self.title_font.render("Setting of the map", True, self.colors['text'])
        title_rect = title.get_rect(center=(self.center_x, 80))
        self.screen.blit(title, title_rect)
        
        # Draw labels with right alignment
        mode_label = self.font.render("Game mode :", True, self.colors['text'])
        mode_rect = mode_label.get_rect(right=self.center_x - 60, centery=220)
        self.screen.blit(mode_label, mode_rect)
        
        # Draw map size label and button
        size_label = self.font.render("Size of the map :", True, self.colors['text'])
        size_rect = size_label.get_rect(right=self.center_x - 40, centery=320)
        self.screen.blit(size_label, size_rect)
        
        players_label = self.font.render("Number of players :", True, self.colors['text'])
        players_rect = players_label.get_rect(right=self.center_x - 25, centery=420)
        self.screen.blit(players_label, players_rect)

        # Draw width and height buttons/inputs
        for button, input_field in [(self.width_button, self.width_input), (self.height_button, self.height_input)]:
            color = self.colors['selected'] if input_field['active'] else (
                self.colors['button_hover'] if button['rect'].collidepoint(mouse_pos) 
                else self.colors['button']
            )
            pygame.draw.rect(self.screen, color, button['rect'], border_radius=5)
            text = self.font.render(
                input_field['text'] if input_field['active'] else button['text'],
                True, self.colors['text']
            )
            text_rect = text.get_rect(center=button['rect'].center)
            self.screen.blit(text, text_rect)
        
        # Draw 'x' separator between width and height
        separator = self.font.render("x", True, self.colors['text'])
        separator_rect = separator.get_rect(center=(self.center_x + 150, 320))
        self.screen.blit(separator, separator_rect)
        
        
        # Draw mode button
        color = self.colors['button_hover'] if self.mode_button['rect'].collidepoint(mouse_pos) else self.colors['button']
        pygame.draw.rect(self.screen, color, self.mode_button['rect'], border_radius=5)
        text = self.font.render(self.mode_button['text'], True, self.colors['text'])
        text_rect = text.get_rect(center=self.mode_button['rect'].center)
        self.screen.blit(text, text_rect)
        
        # Draw mode selection popup if active
        if self.show_mode_popup:
            pygame.draw.rect(self.screen, self.colors['background'], self.popup_rect)
            pygame.draw.rect(self.screen, self.colors['button'], self.popup_rect, 2)
            
            # Draw the options
            for option in self.mode_options:
                color = self.colors['button_hover'] if option['rect'].collidepoint(mouse_pos) else self.colors['button']
                if option['text'] == self.mode_button['text']:
                    color = self.colors['selected']
                pygame.draw.rect(self.screen, color, option['rect'], border_radius=5)
                text = self.font.render(option['text'], True, self.colors['text'])
                text_rect = text.get_rect(center=option['rect'].center)
                self.screen.blit(text, text_rect)
        
        # Draw player count button/input
        color = self.colors['selected'] if self.player_input['active'] else (
            self.colors['button_hover'] if self.player_button['rect'].collidepoint(mouse_pos) 
            else self.colors['button']
        )
        pygame.draw.rect(self.screen, color, self.player_button['rect'], border_radius=5)
        text = self.font.render(
            self.player_input['text'] if self.player_input['active'] else self.player_button['text'],
            True, self.colors['text']
        )
        text_rect = text.get_rect(center=self.player_button['rect'].center)
        self.screen.blit(text, text_rect)
        
        # Draw navigation buttons
        for button in [self.start_button, self.back_button]:
            color = self.colors['button_hover'] if button['rect'].collidepoint(mouse_pos) else self.colors['button']
            pygame.draw.rect(self.screen, color, button['rect'], border_radius=5)
            text = self.font.render(button['text'], True, self.colors['text'])
            text_rect = text.get_rect(center=button['rect'].center)
            self.screen.blit(text, text_rect)

    def run(self):
        running = True
        while running:
            self.draw()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = event.pos
                    
                    # Handle game mode selection
                    if self.mode_button['rect'].collidepoint(mouse_pos):
                        self.show_mode_popup = not self.show_mode_popup
                    elif self.show_mode_popup:
                        for i, option in enumerate(self.mode_options):
                            if option['rect'].collidepoint(mouse_pos):
                                self.current_mode = i
                                self.mode_button['text'] = self.game_modes[i]
                                global GameMode
                                GameMode = self.game_modes[i]
                                self.show_mode_popup = False
                                break
                        # Close popup if clicked outside
                        if not self.popup_rect.collidepoint(mouse_pos):
                            self.show_mode_popup = False
                    
                    # Handle width button click
                    elif self.width_button['rect'].collidepoint(mouse_pos):
                        self.width_input['active'] = True
                        self.height_input['active'] = False
                        self.width_input['text'] = ''
                    
                    # Handle height button click
                    elif self.height_button['rect'].collidepoint(mouse_pos):
                        self.height_input['active'] = True
                        self.width_input['active'] = False
                        self.height_input['text'] = ''
                    
                    # Handle player count button click
                    elif self.player_button['rect'].collidepoint(mouse_pos):
                        self.player_input['active'] = True
                        self.width_input['active'] = False
                        self.player_input['text'] = ''
                    
                    # Handle navigation
                    elif self.back_button['rect'].collidepoint(mouse_pos):
                        return 'back'
                    elif self.start_button['rect'].collidepoint(mouse_pos):
                        return {
                            'mode': self.game_modes[self.current_mode],
                            'map_size': (self.map_width, self.map_height),
                            'num_players': self.num_players
                        }
                    
                    # Deactivate inputs if clicking elsewhere
                    else:
                        if self.width_input['active']:
                            if self.width_input['text']:
                                self.map_width = max(120, min(500, int(self.width_input['text'])))
                                self.width_button['text'] = str(self.map_width)
                            self.width_input['active'] = False
                        if self.height_input['active']:
                            if self.height_input['text']:
                                self.map_height = max(120, min(500, int(self.height_input['text'])))
                                self.height_button['text'] = str(self.map_height)
                            self.height_input['active'] = False
                        if self.player_input['active']:
                            if self.player_input['text']:
                                self.num_players = max(2, min(8, int(self.player_input['text'])))
                                self.player_button['text'] = str(self.num_players)
                            self.player_input['active'] = False
                
                elif event.type == pygame.KEYDOWN:
                    # Handle width input
                    if self.width_input['active']:
                        if event.key == pygame.K_RETURN:
                            if self.width_input['text']:
                                self.map_width = max(120, min(500, int(self.width_input['text'])))
                                self.width_button['text'] = str(self.map_width)
                            self.width_input['active'] = False
                        elif event.key == pygame.K_BACKSPACE:
                            self.width_input['text'] = self.width_input['text'][:-1]
                        elif event.unicode.isnumeric():
                            self.width_input['text'] += event.unicode
                    
                    # Handle height input
                    if self.height_input['active']:
                        if event.key == pygame.K_RETURN:
                            if self.height_input['text']:
                                self.map_height = max(120, min(500, int(self.height_input['text'])))
                                self.height_button['text'] = str(self.map_height)
                            self.height_input['active'] = False
                        elif event.key == pygame.K_BACKSPACE:
                            self.height_input['text'] = self.height_input['text'][:-1]
                        elif event.unicode.isnumeric():
                            self.height_input['text'] += event.unicode
                    # Handle player count input
                    if self.player_input['active']:
                        if event.key == pygame.K_RETURN:
                            if self.player_input['text']:
                                self.num_players = max(2, min(8, int(self.player_input['text'])))
                                self.player_button['text'] = str(self.num_players)
                            self.player_input['active'] = False
                        elif event.key == pygame.K_BACKSPACE:
                            self.player_input['text'] = self.player_input['text'][:-1]
                        elif event.unicode.isnumeric():
                            self.player_input['text'] += event.unicode
            
            pygame.display.flip()

class PlayerSettingsMenu:
    def __init__(self, num_players, screen_width=800, screen_height=600):
        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()
            
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("AIge of EmpAIre - Player Settings")
        
        self.num_players = num_players
        self.civilizations = ["Means", "Leans", "Marines"]
        self.ai_modes = ["aggressive", "defensive"]
        
        self.colors = {
            'background': (50, 50, 50),
            'button': (175, 128, 79),
            'button_hover': (150, 150, 150),
            'text': (255, 255, 255),
            'selected': (120, 160, 120),
            'scrollbar': (70, 70, 70),
            'scrollbar_hover': (90, 90, 90)
        }

        self.settingmenu_image = pygame.image.load(r'..\assets\MenuPhoto\parametrebueno3.png')
        self.settingmenu_image = pygame.transform.scale(self.settingmenu_image, (screen_width, screen_height))
        
        # Scroll settings
        self.scroll_y = 0
        self.visible_players = 4
        self.button_height = 60
        self.button_spacing = 0
        self.scroll_area_height = self.visible_players * self.button_height
        self.total_height = num_players * self.button_height
        
        # Scrollbar settings
        self.scrollbar_width = 20
        self.scrollbar_area = pygame.Rect(680, 250, self.scrollbar_width, self.scroll_area_height)  # Adjusted x and y position
        self.scrollbar_height = min(
            self.scroll_area_height,
            (self.scroll_area_height / self.total_height) * self.scroll_area_height
        )
        self.scrollbar_rect = pygame.Rect(
            680, 
            250, 
            self.scrollbar_width,
            self.scrollbar_height
        )
        self.scrolling = False
        self.scroll_start_y = 0
        self.initial_scroll_y = 0
        
        # Create a button for each player
        self.player_buttons = []
        for i in range(num_players):
            y_pos = 250 + i * self.button_height 
            self.player_buttons.append({
                'player': f'Player {i+1}',
                'civ_rect': pygame.Rect(250, y_pos, 180, 50),
                'ai_rect': pygame.Rect(480, y_pos + 30, 180, 50),
                'civ_index': 0,
                'ai_index': 0
            })
        
        # Navigation buttons
        self.back_button = {'text': 'Back', 'rect': pygame.Rect(210, 520, 120, 50)}
        self.start_button = {'text': 'Start Game', 'rect': pygame.Rect(505, 520, 120, 50)}
        
        self.font = pygame.font.Font(None, 36)
        self.title_font = pygame.font.Font(None, 48)

    def handle_scroll(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:  # Mouse wheel up
                self.scroll_y = max(0, self.scroll_y - self.button_height)
            elif event.button == 5:  # Mouse wheel down
                max_scroll = self.total_height - self.scroll_area_height
                self.scroll_y = min(max_scroll if max_scroll > 0 else 0, self.scroll_y + self.button_height)
            elif self.scrollbar_rect.collidepoint(event.pos):
                self.scrolling = True
                self.scroll_start_y = event.pos[1]
                self.initial_scroll_y = self.scroll_y
        elif event.type == pygame.MOUSEBUTTONUP:
            self.scrolling = False
        elif event.type == pygame.MOUSEMOTION and self.scrolling:
            # Calculate scroll movement based on mouse drag
            delta_y = event.pos[1] - self.scroll_start_y
            scroll_ratio = delta_y / (self.scroll_area_height - self.scrollbar_height)
            self.scroll_y = self.initial_scroll_y + scroll_ratio * (self.total_height - self.scroll_area_height)
            self.scroll_y = max(0, min(self.total_height - self.scroll_area_height, self.scroll_y))

    def draw(self):
        mouse_pos = pygame.mouse.get_pos()
        self.screen.blit(self.settingmenu_image, (0, 0))
        
        # Draw title
        title = self.title_font.render("Player Settings", True, self.colors['text'])
        title_rect = title.get_rect(center=(400, 80))
        self.screen.blit(title, title_rect)
        
        # Draw headers - moved down
        civ_header = self.font.render("Civilization", True, self.colors['text'])
        ai_header = self.font.render("AI Mode", True, self.colors['text'])
        self.screen.blit(civ_header, (215, 200))  
        self.screen.blit(ai_header, (515, 200))  
        
        # Draw visible player buttons
        start_idx = max(0, int(self.scroll_y / self.button_height))
        end_idx = min(self.num_players, start_idx + self.visible_players)
        
        for i in range(start_idx, end_idx):
            button = self.player_buttons[i]
            y_pos = 250 + (i - start_idx) * self.button_height  # Adjusted to match new initial position
            
            # Update button positions
            button['civ_rect'].y = y_pos
            button['ai_rect'].y = y_pos
            
            # Draw the player label
            player_text = self.font.render(button['player'], True, self.colors['text'])
            player_rect = player_text.get_rect(right=button['civ_rect'].left - 20, centery=y_pos + 25)
            self.screen.blit(player_text, player_rect)
            
            # Draw civilization button
            civ_color = self.colors['button_hover'] if button['civ_rect'].collidepoint(mouse_pos) else self.colors['button']
            pygame.draw.rect(self.screen, civ_color, button['civ_rect'], border_radius=5)
            civ_text = self.font.render(self.civilizations[button['civ_index']], True, self.colors['text'])
            civ_rect = civ_text.get_rect(center=button['civ_rect'].center)
            self.screen.blit(civ_text, civ_rect)
            
            # Draw AI mode button
            ai_color = self.colors['button_hover'] if button['ai_rect'].collidepoint(mouse_pos) else self.colors['button']
            pygame.draw.rect(self.screen, ai_color, button['ai_rect'], border_radius=5)
            ai_text = self.font.render(self.ai_modes[button['ai_index']], True, self.colors['text'])
            ai_rect = ai_text.get_rect(center=button['ai_rect'].center)
            self.screen.blit(ai_text, ai_rect)
        
        # Draw scrollbar if needed
        if self.total_height > self.scroll_area_height:
            # Draw scrollbar background
            pygame.draw.rect(self.screen, self.colors['scrollbar'], self.scrollbar_area, border_radius=5)
            
            # Calculate and update scrollbar position
            scroll_ratio = self.scroll_y / (self.total_height - self.scroll_area_height)
            scrollbar_y = 250 + scroll_ratio * (self.scroll_area_height - self.scrollbar_height)  # Adjusted base y position
            self.scrollbar_rect.y = scrollbar_y
            
            # Draw scrollbar handle
            color = self.colors['scrollbar_hover'] if self.scrollbar_rect.collidepoint(pygame.mouse.get_pos()) else self.colors['button']
            pygame.draw.rect(self.screen, color, self.scrollbar_rect, border_radius=5)
        
        # Draw navigation buttons
        for button in [self.back_button, self.start_button]:
            color = self.colors['button_hover'] if button['rect'].collidepoint(mouse_pos) else self.colors['button']
            pygame.draw.rect(self.screen, color, button['rect'], border_radius=5)
            text = self.font.render(button['text'], True, self.colors['text'])
            text_rect = text.get_rect(center=button['rect'].center)
            self.screen.blit(text, text_rect)

    def run(self):
        running = True
        while running:
            self.draw()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                
                # Handle scrolling
                self.handle_scroll(event)
                
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_pos = event.pos
                    
                    # Handle back button
                    if self.back_button['rect'].collidepoint(mouse_pos):
                        return None
                    
                    # Handle start button
                    if self.start_button['rect'].collidepoint(mouse_pos):
                        return [{'civilization': self.civilizations[button['civ_index']], 
                                'ai_mode': self.ai_modes[button['ai_index']]} 
                               for button in self.player_buttons]
                    
                    # Handle civilization and AI mode selection
                    for button in self.player_buttons:
                        if button['civ_rect'].collidepoint(mouse_pos):
                            button['civ_index'] = (button['civ_index'] + 1) % len(self.civilizations)
                        elif button['ai_rect'].collidepoint(mouse_pos):
                            button['ai_index'] = (button['ai_index'] + 1) % len(self.ai_modes)
            
            pygame.display.flip()

def start_menu(save_file=None):
    menu = StartMenu()
    action = menu.run()
    
    if action == 'Start Game':
        settings_menu = GameSettingsMenu()
        settings = settings_menu.run()
        
        if settings == 'back':
            return start_menu(save_file)
        elif settings:
            # Import GameEngine at the start
            from Game_Engine import GameEngine
            
            # Update global settings
            global GameMode, map_size, players
            GameMode = settings['mode']
            map_size = settings['map_size']
            num_players = int(settings['num_players'])
            
            # Clear existing players list
            players.clear()
            
            # Show player settings menu
            player_settings_menu = PlayerSettingsMenu(num_players)
            player_settings = player_settings_menu.run()
            
            if player_settings:
                # Create players with selected settings
                for i, settings in enumerate(player_settings):
                    player_id = i + 1
                    new_player = Player(
                        f'Player {player_id}',
                        settings['civilization'],
                        settings['ai_mode'],
                        player_id=player_id
                    )
                    players.append(new_player)
                
                # Close pygame before starting curses
                pygame.quit()
                
                # Start the game with updated players list
                curses.wrapper(lambda stdscr: GameEngine(
                    game_mode=GameMode,
                    map_size=map_size,
                    players=players,
                    sauvegarde=False
                ).run(stdscr))
            else:
                # If player settings menu was closed, return to main menu
                return start_menu(save_file)
        else:
            pygame.quit()
            sys.exit()
    elif action == 'Load Game' and menu.has_saves:
        load_menu = LoadGameMenu()
        selected_save = load_menu.run()
        
        if selected_save == 'back':
            return start_menu(save_file)  # Return to main menu
        elif selected_save:  # If a save file was selected
            pygame.quit()
            from Game_Engine import GameEngine
            curses.wrapper(lambda stdscr: start_game(stdscr, selected_save))
        else:  # If window was closed
            pygame.quit()
            sys.exit()
    elif action in ['Exit', 'quit']:
        pygame.quit()
        print("Exiting game")
        sys.exit()

def start_game(stdscr, save_file=None):
    from Game_Engine import GameEngine
    curses.curs_set(0)
    stdscr.clear()
    
    if save_file:
        game_engine = GameEngine(
            game_mode=GameMode,
            map_size=map_size,
            players=players,
            sauvegarde=True
        )
        game_engine.load_game(save_file)
    else:
        game_engine = GameEngine(
            game_mode=GameMode,
            map_size=map_size,
            players=players,
            sauvegarde=False
        )

    game_engine.run(stdscr)