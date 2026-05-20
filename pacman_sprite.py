import pygame
import os


class PacmanSprite:
    def __init__(self, base_path):
        self.frames = {
            "closed": self._load_frame(base_path, "pacman_closed.png"),
            "half_up": self._load_frame(base_path, "pacman_half_up.png"),
            "half_down": self._load_frame(base_path, "pacman_half_down.png"),
            "half_left": self._load_frame(base_path, "pacman_half_left.png"),
            "half_right": self._load_frame(base_path, "pacman_half_right.png"),
            "open_up": self._load_frame(base_path, "pacman_open_up.png"),
            "open_down": self._load_frame(base_path, "pacman_open_down.png"),
            "open_left": self._load_frame(base_path, "pacman_open_left.png"),
            "open_right": self._load_frame(base_path, "pacman_open_right.png"),
        }

    def _load_frame(self, base_path, filename):
        image = pygame.image.load(os.path.join(base_path, filename))
        if pygame.display.get_surface() is not None:
            return image.convert_alpha()
        return image

    def get_frame(self, state):
        return self.frames.get(state, self.frames["closed"])
