"""Error toast overlay — slide-in notifications from top-right."""

import time
import pygame


class ErrorToast:
    """Queue of error messages that slide in from the top-right and auto-dismiss."""

    def __init__(self):
        self._toasts: list[dict] = []  # {message, severity, time, y_offset}
        self._max_visible = 3

    def push(self, message: str, severity: str = "error"):
        """Add a new toast notification."""
        self._toasts.append({
            "message": message,
            "severity": severity,
            "time": time.time(),
            "slide_t": 0.0,
        })
        # Keep only last N
        if len(self._toasts) > self._max_visible * 2:
            self._toasts = self._toasts[-self._max_visible:]

    @property
    def active(self) -> bool:
        return len(self._toasts) > 0

    def update(self, dt: float):
        """Update animation and remove expired toasts."""
        now = time.time()
        # Remove toasts older than 5 seconds
        self._toasts = [t for t in self._toasts if now - t["time"] < 5.0]
        # Animate slide-in
        for toast in self._toasts:
            toast["slide_t"] = min(1.0, toast["slide_t"] + dt * 6.0)

    def draw(self, surf: pygame.Surface):
        """Render visible toasts."""
        if not self._toasts:
            return

        w, _ = surf.get_size()
        font = pygame.font.SysFont("DejaVuSans,Arial", 13)
        padding = 12
        toast_h = 36
        margin = 8
        max_toast_w = 340

        for i, toast in enumerate(self._toasts[-self._max_visible:]):
            age = time.time() - toast["time"]

            # Slide in from right
            slide = toast["slide_t"]
            # Fade out in last second
            fade = min(1.0, (5.0 - age) / 0.5) if age > 4.5 else 1.0
            alpha = int(min(slide, fade) * 220)
            if alpha < 5:
                continue

            x_offset = int((1.0 - slide) * (max_toast_w + 20))
            x = w - max_toast_w - margin + x_offset
            y = margin + i * (toast_h + margin)

            # Background
            severity = toast["severity"]
            if severity == "error":
                bg_color = (60, 20, 20)
                text_color = (255, 90, 90)
                border_color = (120, 40, 40)
            elif severity == "warning":
                bg_color = (50, 40, 15)
                text_color = (255, 200, 80)
                border_color = (100, 80, 30)
            else:
                bg_color = (20, 30, 50)
                text_color = (100, 200, 255)
                border_color = (40, 60, 100)

            toast_surf = pygame.Surface((max_toast_w, toast_h), pygame.SRCALPHA)
            pygame.draw.rect(toast_surf, (*bg_color, alpha), (0, 0, max_toast_w, toast_h), border_radius=8)
            pygame.draw.rect(toast_surf, (*border_color, alpha), (0, 0, max_toast_w, toast_h), 1, border_radius=8)

            # Text
            text = font.render(toast["message"][:50], True, text_color)
            text_s = pygame.Surface(text.get_size(), pygame.SRCALPHA)
            text_s.blit(text, (0, 0))
            text_s.set_alpha(alpha)
            toast_surf.blit(text_s, (padding, toast_h // 2 - text.get_height() // 2))

            surf.blit(toast_surf, (x, y))
