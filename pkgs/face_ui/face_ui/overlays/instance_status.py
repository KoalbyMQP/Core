"""Instance status indicator — small bar showing running app count."""

import pygame


class InstanceStatusBar:
    """Small status bar at the bottom showing running apps."""

    def __init__(self):
        self._instances: list[dict] = []  # [{app, state, error}]
        self._alpha = 0.0

    def update_instances(self, instances: list[dict]):
        """Update the instance list from ROS2 messages."""
        self._instances = instances

    @property
    def active(self) -> bool:
        return len(self._instances) > 0

    def update(self, dt: float):
        target = 1.0 if self._instances else 0.0
        self._alpha += (target - self._alpha) * min(1.0, dt * 4.0)

    def draw(self, surf: pygame.Surface):
        if self._alpha < 0.01:
            return

        w, h = surf.get_size()
        alpha = int(self._alpha * 180)

        running = [i for i in self._instances if i.get("state") == "running"]
        crashed = [i for i in self._instances if i.get("state") == "crashed"]

        if not running and not crashed:
            return

        # Bar background at bottom
        bar_h = 28
        bar_surf = pygame.Surface((w, bar_h), pygame.SRCALPHA)
        bar_surf.fill((18, 20, 26, alpha))

        font = pygame.font.SysFont("DejaVuSans,Arial", 11)
        x = 12

        if running:
            # Green dot + count
            pygame.draw.circle(bar_surf, (100, 200, 120, alpha), (x + 5, bar_h // 2), 4)
            x += 16
            text = font.render(f"{len(running)} running", True, (200, 220, 200))
            text_s = pygame.Surface(text.get_size(), pygame.SRCALPHA)
            text_s.blit(text, (0, 0))
            text_s.set_alpha(alpha)
            bar_surf.blit(text_s, (x, bar_h // 2 - text.get_height() // 2))
            x += text.get_width() + 16

        if crashed:
            # Red dot + count
            pygame.draw.circle(bar_surf, (255, 90, 90, alpha), (x + 5, bar_h // 2), 4)
            x += 16
            text = font.render(f"{len(crashed)} crashed", True, (255, 90, 90))
            text_s = pygame.Surface(text.get_size(), pygame.SRCALPHA)
            text_s.blit(text, (0, 0))
            text_s.set_alpha(alpha)
            bar_surf.blit(text_s, (x, bar_h // 2 - text.get_height() // 2))

        # App names
        names = ", ".join(i.get("app", "?") for i in running[:3])
        if names:
            name_text = font.render(names, True, (90, 95, 115))
            name_s = pygame.Surface(name_text.get_size(), pygame.SRCALPHA)
            name_s.blit(name_text, (0, 0))
            name_s.set_alpha(alpha)
            bar_surf.blit(name_s, (w - name_text.get_width() - 12, bar_h // 2 - name_text.get_height() // 2))

        surf.blit(bar_surf, (0, h - bar_h))
