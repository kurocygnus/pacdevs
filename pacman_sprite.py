import pygame
import os

class PacmanSprite:
    def __init__(self, base_path):
        self.frames = {
            "closed": pygame.image.load(os.path.join(base_path, "pacman_closed.png")).convert_alpha(),
            "half_up": pygame.image.load(os.path.join(base_path, "pacman_half_up.png")).convert_alpha(),
            "half_down": pygame.image.load(os.path.join(base_path, "pacman_half_down.png")).convert_alpha(),
            "half_left": pygame.image.load(os.path.join(base_path, "pacman_half_left.png")).convert_alpha(),
            "half_right": pygame.image.load(os.path.join(base_path, "pacman_half_right.png")).convert_alpha(),
            "open_up": pygame.image.load(os.path.join(base_path, "pacman_open_up.png")).convert_alpha(),
            "open_down": pygame.image.load(os.path.join(base_path, "pacman_open_down.png")).convert_alpha(),
            "open_left": pygame.image.load(os.path.join(base_path, "pacman_open_left.png")).convert_alpha(),
            "open_right": pygame.image.load(os.path.join(base_path, "pacman_open_right.png")).convert_alpha(),
        }

    def get_frame(self, state):
        return self.frames.get(state, self.frames["closed"])