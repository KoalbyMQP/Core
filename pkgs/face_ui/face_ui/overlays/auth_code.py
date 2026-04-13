"""Auth code overlay — displays pairing code on the robot's screen."""

import math
import time
import pygame


class AuthCodeOverlay:
    """
    Renders a semi-transparent overlay showing the 6-digit pairing code.
    The face remains visible (dimmed) underneath.
    """

    def __init__(self):
        self._code: str | None = None
        self._expires_at: float = 0.0
        self._status: str | None = None  # "paired", "expired", "failed"
        self._status_label: str = ""
        self._status_time: float = 0.0

        # Animation state
        self._alpha = 0.0
        self._t = 0.0
        self._char_offsets: list[float] = [0.0] * 6

    def set_code(self, code: str, expires_in: int):
        """Show a new pairing code."""
        self._code = code
        self._expires_at = time.time() + expires_in
        self._status = None
        self._alpha = 0.0
        self._t = 0.0
        self._char_offsets = [0.0] * len(code)

    def set_status(self, status: str, label: str = ""):
        """Update with pairing result (paired/expired/failed)."""
        self._status = status
        self._status_label = label
        self._status_time = time.time()

    def clear(self):
        """Dismiss the overlay."""
        self._code = None
        self._status = None

    @property
    def active(self) -> bool:
        """Whether the overlay should be drawn."""
        if self._status:
            # Show status for 2 seconds after status change
            return time.time() - self._status_time < 2.0
        return self._code is not None and time.time() < self._expires_at

    def update(self, dt: float):
        """Update animation state."""
        if not self.active:
            self._alpha = max(0.0, self._alpha - dt * 3.0)
            return

        self._t += dt

        # Fade in
        target_alpha = 1.0
        self._alpha += (target_alpha - self._alpha) * min(1.0, dt * 5.0)

        # Staggered character drop-in animation
        for i in range(len(self._char_offsets)):
            delay = i * 0.08
            if self._t > delay:
                self._char_offsets[i] += (0.0 - self._char_offsets[i]) * min(1.0, dt * 8.0)
            else:
                self._char_offsets[i] = -30.0

    def draw(self, surf: pygame.Surface):
        """Render the overlay."""
        if self._alpha < 0.01:
            return

        w, h = surf.get_size()
        alpha = int(self._alpha * 255)

        # Semi-transparent dark overlay
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((10, 11, 14, min(alpha, 200)))
        surf.blit(overlay, (0, 0))

        if self._status:
            self._draw_status(surf, w, h, alpha)
        elif self._code:
            self._draw_code(surf, w, h, alpha)

    def _draw_code(self, surf: pygame.Surface, w: int, h: int, alpha: int):
        """Draw the pairing code digits."""
        code = self._code or ""

        # Title
        title_font = pygame.font.SysFont("DejaVuSans,Arial", 16)
        title = title_font.render("Pairing Code", True, (200, 200, 210))
        title_s = pygame.Surface(title.get_size(), pygame.SRCALPHA)
        title_s.blit(title, (0, 0))
        title_s.set_alpha(alpha)
        surf.blit(title_s, (w // 2 - title.get_width() // 2, h // 2 - 100))

        # Code digits — large monospaced font with spacing
        digit_font = pygame.font.SysFont("DejaVuSansMono,Courier", 64, bold=True)
        total_w = len(code) * 60
        start_x = w // 2 - total_w // 2

        for i, ch in enumerate(code):
            digit = digit_font.render(ch, True, (255, 255, 255))
            x = start_x + i * 60 + 30 - digit.get_width() // 2
            y = h // 2 - 40 + int(self._char_offsets[i] if i < len(self._char_offsets) else 0)

            digit_s = pygame.Surface(digit.get_size(), pygame.SRCALPHA)
            digit_s.blit(digit, (0, 0))
            digit_s.set_alpha(alpha)
            surf.blit(digit_s, (x, y))

        # Countdown timer
        remaining = max(0, int(self._expires_at - time.time()))
        timer_font = pygame.font.SysFont("DejaVuSans,Arial", 14)
        timer_text = f"Expires in {remaining}s"
        timer = timer_font.render(timer_text, True, (90, 95, 115))
        timer_s = pygame.Surface(timer.get_size(), pygame.SRCALPHA)
        timer_s.blit(timer, (0, 0))
        timer_s.set_alpha(alpha)
        surf.blit(timer_s, (w // 2 - timer.get_width() // 2, h // 2 + 50))

        # Instruction text
        instr_font = pygame.font.SysFont("DejaVuSans,Arial", 13)
        instr = instr_font.render("Enter this code in your app to connect", True, (90, 95, 115))
        instr_s = pygame.Surface(instr.get_size(), pygame.SRCALPHA)
        instr_s.blit(instr, (0, 0))
        instr_s.set_alpha(alpha)
        surf.blit(instr_s, (w // 2 - instr.get_width() // 2, h // 2 + 76))

    def _draw_status(self, surf: pygame.Surface, w: int, h: int, alpha: int):
        """Draw the pairing status message."""
        if self._status == "paired":
            color = (200, 220, 200)
            text = "Paired!"
        elif self._status == "expired":
            color = (255, 90, 90)
            text = "Code expired"
        else:
            color = (255, 90, 90)
            text = f"Pairing failed"

        font = pygame.font.SysFont("DejaVuSans,Arial", 28, bold=True)
        label = font.render(text, True, color)
        label_s = pygame.Surface(label.get_size(), pygame.SRCALPHA)
        label_s.blit(label, (0, 0))
        label_s.set_alpha(alpha)
        surf.blit(label_s, (w // 2 - label.get_width() // 2, h // 2 - 20))

        if self._status_label:
            sub_font = pygame.font.SysFont("DejaVuSans,Arial", 14)
            sub = sub_font.render(self._status_label, True, (90, 95, 115))
            sub_s = pygame.Surface(sub.get_size(), pygame.SRCALPHA)
            sub_s.blit(sub, (0, 0))
            sub_s.set_alpha(alpha)
            surf.blit(sub_s, (w // 2 - sub.get_width() // 2, h // 2 + 20))
