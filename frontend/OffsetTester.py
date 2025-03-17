import pygame
import sys

class OffsetTester:
    def __init__(self, image_data, window_size=(800, 600), target_position=None):
        """
        image_data : Liste de tuples (chemin_image, retourner)
            chemin_image : Chemin de l'image
            retourner : Booléen indiquant si l'image doit être retournée horizontalement
        """
        # Initialisation de Pygame
        pygame.init()
        
        # Configuration de la fenêtre
        self.window_width, self.window_height = window_size
        self.screen = pygame.display.set_mode((self.window_width, self.window_height))
        pygame.display.set_caption("Test Offset")
        
        # Charger les données d'images
        self.image_data = image_data
        self.current_image_index = 0
        self.load_image(self.current_image_index)
        
        # Position cible (où le point rouge doit être affiché)
        if target_position is None:
            self.target_position = (self.window_width // 2, self.window_height // 2)
        else:
            self.target_position = target_position
        
        # Variables pour le déplacement
        self.dragging = False
        self.offset_x = 0
        self.offset_y = 0
    
    def load_image(self, index):
        """Charge l'image à l'index donné, et la retourne si nécessaire."""
        try:
            image_path, flip = self.image_data[index]
            self.image = pygame.image.load(image_path)
            if flip:  # Retourner l'image si nécessaire
                self.image = pygame.transform.flip(self.image, True, False)
        except pygame.error as e:
            print(f"Erreur lors du chargement de l'image : {e}")
            sys.exit()
        
        self.image_rect = self.image.get_rect()
        self.image_rect.center = (self.window_width // 2, self.window_height // 2)
    
    def run(self):
        # Boucle principale
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                # Navigation avec les flèches
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RIGHT:  # Image suivante
                        self.current_image_index = (self.current_image_index + 1) % len(self.image_data)
                        self.load_image(self.current_image_index)
                    elif event.key == pygame.K_LEFT:  # Image précédente
                        self.current_image_index = (self.current_image_index - 1) % len(self.image_data)
                        self.load_image(self.current_image_index)
                
                # Détecter le clic pour commencer à déplacer
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.image_rect.collidepoint(event.pos):  # Si clic sur l'image
                        self.dragging = True
                        mouse_x, mouse_y = event.pos
                        self.offset_x = self.image_rect.x - mouse_x
                        self.offset_y = self.image_rect.y - mouse_y
                
                # Arrêter le déplacement
                if event.type == pygame.MOUSEBUTTONUP:
                    self.dragging = False
                
                # Déplacer l'image
                if event.type == pygame.MOUSEMOTION:
                    if self.dragging:
                        mouse_x, mouse_y = event.pos
                        self.image_rect.x = mouse_x + self.offset_x
                        self.image_rect.y = mouse_y + self.offset_y
            
            # Affichage de l'image
            self.screen.fill((255, 255, 255))  # Fond blanc
            self.screen.blit(self.image, self.image_rect)
            
            # Affichage du point rouge (position cible)
            pygame.draw.circle(self.screen, (255, 0, 0), self.target_position, 5)
            
            # Calcul des offsets relatifs
            relative_offset_x = self.image_rect.x - self.target_position[0]
            relative_offset_y = self.image_rect.y - self.target_position[1]
            
            # Affichage des offsets relatifs
            font = pygame.font.Font(None, 36)
            offset_text = font.render(
                f"Offset: ({relative_offset_x}, {relative_offset_y})", True, (0, 0, 0)
            )
            self.screen.blit(offset_text, (10, 10))
            
            # Affichage du nom de l'image actuelle
            image_path = self.image_data[self.current_image_index][0]
            image_name = image_path.split("\\")[-1]
            image_text = font.render(f"Image: {image_name}", True, (0, 0, 0))
            self.screen.blit(image_text, (10, 50))
            
            # Mise à jour de l'écran
            pygame.display.flip()

# Exemple d'utilisation
if __name__ == "__main__":
    # Liste des données d'images (chemin, retourner)
    image_data = [
        # Etat "gathering" (récolte) - Directions spécifiques
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\villager\FarmingVillager\Farm\Attack\Villageract061.png", False),  # north
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\villager\FarmingVillager\Farm\Attack\Villageract001.png", False),  # south
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\villager\FarmingVillager\Farm\Attack\Villageract031.png", False),  # west
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\villager\FarmingVillager\Farm\Attack\Villageract031.png", True),   # east (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\villager\FarmingVillager\Farm\Attack\Villageract046.png", True),   # northeast (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\villager\FarmingVillager\Farm\Attack\Villageract046.png", False),  # northwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\villager\FarmingVillager\Farm\Attack\Villageract016.png", False),  # southwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\villager\FarmingVillager\Farm\Attack\Villageract016.png", True),   # southeast (flipped)

        # Etat "constructing" (construction/réparation) - Directions spécifiques
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\villager\FarmingVillager\Build & Repair\Act\Villageract061.png", False),  # north
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\villager\FarmingVillager\Build & Repair\Act\Villageract001.png", False),  # south
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\villager\FarmingVillager\Build & Repair\Act\Villageract031.png", False),  # west
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\villager\FarmingVillager\Build & Repair\Act\Villageract031.png", True),   # east (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\villager\FarmingVillager\Build & Repair\Act\Villageract046.png", True),   # northeast (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\villager\FarmingVillager\Build & Repair\Act\Villageract046.png", False),  # northwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\villager\FarmingVillager\Build & Repair\Act\Villageract016.png", False),  # southwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\villager\FarmingVillager\Build & Repair\Act\Villageract016.png", True),   # southeast (flipped)

        # Etat "walking" (marche) - Directions spécifiques
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Villager\Walk\Villagerwalk001.png", False),  # south
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Villager\Walk\Villagerwalk061.png", False),  # north
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Villager\Walk\Villagerwalk031.png", False),  # west
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Villager\Walk\Villagerwalk031.png", True),   # east (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Villager\Walk\Villagerwalk046.png", True),   # northeast (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Villager\Walk\Villagerwalk046.png", False),  # northwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Villager\Walk\Villagerwalk016.png", False),  # southwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Villager\Walk\Villagerwalk016.png", True),   # southeast (flipped)
        
        # Etat "attacking" (attack) - Directions spécifiques
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Villager\Attack\Villagerattack001.png", False),  # south
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Villager\Attack\Villagerattack061.png", False),  # north
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Villager\Attack\Villagerattack031.png", False),  # west
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Villager\Attack\Villagerattack031.png", True),   # east (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Villager\Attack\Villagerattack046.png", True),   # northeast (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Villager\Attack\Villagerattack046.png", False),  # northwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Villager\Attack\Villagerattack016.png", False),  # southwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Villager\Attack\Villagerattack016.png", True),   # southeast (flipped)


        # Etat "idle" (inactif) - Position spécifique
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Villager\Stand\Villagerstand017.png", False),  # south
    ]

    image_data_axethrower = [
        # Etat "walking" (marche) - Directions spécifiques
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Swordman\Walk\Axethrowerwalk001.png", False),  # south
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Swordman\Walk\Axethrowerwalk061.png", False),  # north
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Swordman\Walk\Axethrowerwalk031.png", False),  # west
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Swordman\Walk\Axethrowerwalk031.png", True),   # east (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Swordman\Walk\Axethrowerwalk046.png", True),   # northeast (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Swordman\Walk\Axethrowerwalk046.png", False),  # northwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Swordman\Walk\Axethrowerwalk016.png", False),  # southwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Swordman\Walk\Axethrowerwalk016.png", True),   # southeast (flipped)

        # Etat "attacking" (attaque) - Directions spécifiques
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Swordman\Attack\Axethrowerattack001.png", False),  # south
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Swordman\Attack\Axethrowerattack065.png", False),  # north
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Swordman\Attack\Axethrowerattack033.png", False),  # west
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Swordman\Attack\Axethrowerattack033.png", True),   # east (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Swordman\Attack\Axethrowerattack049.png", True),   # northeast (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Swordman\Attack\Axethrowerattack049.png", False),  # northwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Swordman\Attack\Axethrowerattack017.png", False),  # southwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Swordman\Attack\Axethrowerattack017.png", True),   # southeast (flipped)

        # Etat "idle" (inactif) - Position spécifique
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Swordman\Stand\Axethrowerstand001.png", False),  # south
    ]

    image_data_horseman = [
        # Etat "walking" (marche) - Directions spécifiques
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Horseman\Walk\Scoutwalk001.png", False),  # south
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Horseman\Walk\Scoutwalk041.png", False),  # north
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Horseman\Walk\Scoutwalk021.png", False),  # west
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Horseman\Walk\Scoutwalk021.png", True),   # east (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Horseman\Walk\Scoutwalk031.png", True),   # northeast (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Horseman\Walk\Scoutwalk031.png", False),  # northwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Horseman\Walk\Scoutwalk011.png", False),  # southwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Horseman\Walk\Scoutwalk011.png", True),   # southeast (flipped)

        # Etat "attacking" (attaque) - Directions spécifiques
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Horseman\Attack\Scoutattack001.png", False),  # south
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Horseman\Attack\Scoutattack041.png", False),  # north
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Horseman\Attack\Scoutattack021.png", False),  # west
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Horseman\Attack\Scoutattack021.png", True),   # east (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Horseman\Attack\Scoutattack031.png", True),   # northeast (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Horseman\Attack\Scoutattack031.png", False),  # northwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Horseman\Attack\Scoutattack011.png", False),  # southwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Horseman\Attack\Scoutattack011.png", True),   # southeast (flipped)

        # Etat "idle" (inactif) - Position spécifique
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Horseman\Stand\Scoutstand001.png", False),  # south
    ]

    image_data_archer = [
        # Etat "walking" (marche) - Directions spécifiques
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Archer\Walk\Archerwalk001.png", False),  # south
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Archer\Walk\Archerwalk041.png", False),  # north
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Archer\Walk\Archerwalk021.png", False),  # west
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Archer\Walk\Archerwalk021.png", True),   # east (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Archer\Walk\Archerwalk031.png", True),   # northeast (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Archer\Walk\Archerwalk031.png", False),  # northwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Archer\Walk\Archerwalk011.png", False),  # southwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Archer\Walk\Archerwalk011.png", True),   # southeast (flipped)

        # Etat "attacking" (attaque) - Directions spécifiques
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Archer\Attack\Archerattack001.png", False),  # south
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Archer\Attack\Archerattack041.png", False),  # north
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Archer\Attack\Archerattack021.png", False),  # west
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Archer\Attack\Archerattack021.png", True),   # east (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Archer\Attack\Archerattack031.png", True),   # northeast (flipped)
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Archer\Attack\Archerattack031.png", False),  # northwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Archer\Attack\Archerattack011.png", False),  # southwest
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Archer\Attack\Archerattack011.png", True),   # southeast (flipped)

        # Etat "idle" (inactif) - Position spécifique
        (r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\Archer\Stand\Archerstand001.png", False),  # south
    ]

    imagedetree = [(r"C:\Users\gtfor\Documents\STI 3A\Python-Project\assets\units\2\villager\attacking\northeast\13.png",False)]

    # Position cible (où le point rouge doit apparaître)
    target_position = (400, 300)  # Position au centre de la fenêtre
    
    # Lancer le test
    tester = OffsetTester(image_data, target_position=target_position)
    tester.run()
