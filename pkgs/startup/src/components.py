import pygame
import math
from constants import *


def lerp(a, b, t):
    return a + (b - a) * min(1.0, t)


def lerp_color(a, b, t):
    t = min(1.0, max(0.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_rounded_rect(surf, color, rect, radius=RADIUS, border=0, border_color=None):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border and border_color:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)


def draw_glow(surf, color, center, radius, intensity=60):
    glow_surf = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
    for r in range(radius, 0, -4):
        alpha = int(intensity * (1 - r / radius) ** 2)
        c = (*color, alpha)
        pygame.draw.circle(glow_surf, c, (radius * 2, radius * 2), r)
    surf.blit(glow_surf, (center[0] - radius * 2, center[1] - radius * 2),
              special_flags=pygame.BLEND_RGBA_ADD)


class Button:
    def __init__(self, rect, label, style="primary"):
        self.rect   = pygame.Rect(rect)
        self.label  = label
        self.style  = style
        self.hover_t = 0.0
        self.press_t = 0.0
        self._font  = None

    def _get_font(self):
        if not self._font:
            self._font = pygame.font.SysFont("DejaVuSans,Arial", 15, bold=True)
        return self._font

    def update(self, dt, mouse_pos, mouse_down):
        hovered = self.rect.collidepoint(mouse_pos)
        self.hover_t = lerp(self.hover_t, 1.0 if hovered else 0.0, dt * LERP_SPEED)
        self.press_t = lerp(self.press_t, 1.0 if (hovered and mouse_down) else 0.0, dt * 25)

    def draw(self, surf):
        # All buttons: outline style, ghost is dimmer
        if self.style == "ghost":
            border_base = (45, 48, 62)
            text_base   = TEXT_MUTED
        else:
            border_base = (80, 85, 105)
            text_base   = TEXT_MUTED

        border_col = lerp_color(border_base, WHITE, self.hover_t)
        text_col   = lerp_color(text_base, WHITE, self.hover_t)

        scale = lerp(1.0, 0.96, self.press_t)
        r = self.rect.inflate(
            int(self.rect.w * (scale - 1)),
            int(self.rect.h * (scale - 1))
        )
        r.center = self.rect.center

        btn_surf = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        pygame.draw.rect(btn_surf, (0, 0, 0, 0),
                         (0, 0, r.w, r.h), border_radius=RADIUS)
        pygame.draw.rect(btn_surf, (*border_col, int(180 + 75 * self.hover_t)),
                         (0, 0, r.w, r.h), 1, border_radius=RADIUS)
        surf.blit(btn_surf, (r.x, r.y))

        lbl = self._get_font().render(self.label, True, text_col)
        surf.blit(lbl, lbl.get_rect(center=r.center))

    def is_clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONUP and event.button == 1
                and self.rect.collidepoint(event.pos))


class TextInput:
    def __init__(self, rect, placeholder="", secret=False):
        self.rect        = pygame.Rect(rect)
        self.placeholder = placeholder
        self.secret      = secret
        self.text        = ""
        self.focused     = False
        self.cursor_t    = 0.0
        self.focus_t     = 0.0
        self._font       = None

    def _get_font(self):
        if not self._font:
            self._font = pygame.font.SysFont("DejaVuSans,Arial", 15)
        return self._font

    def update(self, dt):
        self.cursor_t += dt
        self.focus_t = lerp(self.focus_t, 1.0 if self.focused else 0.0, dt * LERP_SPEED)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.focused = self.rect.collidepoint(event.pos)
        if not self.focused:
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key not in (pygame.K_RETURN, pygame.K_TAB, pygame.K_ESCAPE):
                if len(self.text) < 64:
                    self.text += event.unicode

    def draw(self, surf):
        border_col = lerp_color(CARD_BORDER, ACCENT, self.focus_t)
        bg         = lerp_color(CARD_BG, (22, 26, 36), self.focus_t)
        draw_rounded_rect(surf, bg, self.rect, RADIUS,
                          border=1, border_color=border_col)

        # Focus glow
        if self.focus_t > 0.05:
            glow = pygame.Surface((self.rect.w + 20, self.rect.h + 20), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*ACCENT, int(15 * self.focus_t)),
                             (10, 10, self.rect.w, self.rect.h), border_radius=RADIUS)
            surf.blit(glow, (self.rect.x - 10, self.rect.y - 10))

        font = self._get_font()
        pad  = 18
        display = ("•" * len(self.text)) if self.secret else self.text

        if display:
            txt_surf = font.render(display, True, TEXT_PRIMARY)
            # Clip to input bounds
            clip = pygame.Rect(self.rect.x + pad, self.rect.y,
                               self.rect.w - pad * 2, self.rect.h)
            surf.set_clip(clip)
            surf.blit(txt_surf, (self.rect.x + pad,
                                 self.rect.centery - txt_surf.get_height() // 2))
            surf.set_clip(None)

            # Cursor
            if self.focused and math.sin(self.cursor_t * 3) > 0:
                cx = self.rect.x + pad + txt_surf.get_width() + 2
                cy = self.rect.centery - 10
                pygame.draw.line(surf, ACCENT, (cx, cy), (cx, cy + 20), 1)
        else:
            ph = font.render(self.placeholder, True, TEXT_SUBTLE)
            surf.blit(ph, (self.rect.x + pad,
                           self.rect.centery - ph.get_height() // 2))
            if self.focused and math.sin(self.cursor_t * 3) > 0:
                cx = self.rect.x + pad + 2
                cy = self.rect.centery - 10
                pygame.draw.line(surf, ACCENT, (cx, cy), (cx, cy + 20), 1)


class NetworkCard:
    def __init__(self, rect, ssid, signal):
        self.rect    = pygame.Rect(rect)
        self.ssid    = ssid
        self.signal  = signal  # 0-100
        self.hover_t = 0.0
        self.selected = False
        self._font   = None
        self._sub    = None

    def _fonts(self):
        if not self._font:
            self._font = pygame.font.SysFont("DejaVuSans,Arial", 14, bold=True)
            self._sub  = pygame.font.SysFont("DejaVuSans,Arial", 12)
        return self._font, self._sub

    def update(self, dt, mouse_pos):
        self.hover_t = lerp(self.hover_t,
                            1.0 if self.rect.collidepoint(mouse_pos) else 0.0,
                            dt * LERP_SPEED)

    def draw(self, surf):
        if self.selected:
            bg = CARD_ACTIVE
            border = ACCENT_DIM
        else:
            bg = lerp_color(CARD_BG, CARD_HOVER, self.hover_t)
            border = lerp_color(CARD_BORDER, ACCENT_DIM, self.hover_t * 0.5)

        draw_rounded_rect(surf, bg, self.rect, 12, border=1, border_color=border)

        font, sub = self._fonts()

        # Signal bars
        bx = self.rect.x + 16
        by = self.rect.centery
        bar_w, bar_gap = 4, 3
        bars = 4
        for i in range(bars):
            bh = 5 + i * 5
            threshold = (i + 1) / bars
            col = WHITE if self.signal / 100 >= threshold else TEXT_SUBTLE
            pygame.draw.rect(surf, col,
                             (bx + i * (bar_w + bar_gap),
                              by - bh // 2, bar_w, bh),
                             border_radius=2)

        icon_w = bars * (bar_w + bar_gap) + 8
        lbl = font.render(self.ssid, True, TEXT_PRIMARY if self.selected else TEXT_PRIMARY)
        surf.blit(lbl, (self.rect.x + 16 + icon_w,
                        self.rect.centery - lbl.get_height() // 2))

        strength = "Strong" if self.signal > 66 else "Fair" if self.signal > 33 else "Weak"
        s = sub.render(strength, True, TEXT_PRIMARY if self.selected else TEXT_MUTED)
        surf.blit(s, (self.rect.right - s.get_width() - 16,
                      self.rect.centery - s.get_height() // 2))

    def is_clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONUP
                and event.button == 1
                and self.rect.collidepoint(event.pos))


class ProgressBar:
    def __init__(self, rect):
        self.rect    = pygame.Rect(rect)
        self.value   = 0.0   # 0.0 – 1.0
        self._anim_t = 0.0

    def update(self, dt):
        self._anim_t += dt
        self._anim_t %= 2.0

    def draw(self, surf):
        draw_rounded_rect(surf, CARD_BG, self.rect, self.rect.h // 2)
        if self.value > 0:
            fill_w = max(self.rect.h, int(self.rect.w * self.value))
            fill_r = pygame.Rect(self.rect.x, self.rect.y, fill_w, self.rect.h)
            draw_rounded_rect(surf, (90, 92, 108), fill_r, self.rect.h // 2)
            # Shimmer
            shimmer_x = self.rect.x + int(fill_w * (self._anim_t / 2.0))
            shimmer_surf = pygame.Surface((40, self.rect.h), pygame.SRCALPHA)
            for i in range(40):
                a = int(60 * math.sin(math.pi * i / 40))
                shimmer_surf.fill((220, 220, 230, a), (i, 0, 1, self.rect.h))
            surf.blit(shimmer_surf, (shimmer_x - 20, self.rect.y))


class OSKeyboard:
    """
    Full on-screen keyboard. Call handle_event() for mouse, update() each frame.
    Writes into a target TextInput via .target.
    """
    ROWS = [
        list("QWERTYUIOP"),
        list("ASDFGHJKL"),
        list("ZXCVBNM"),
    ]

    def __init__(self, y_start):
        self.y_start = y_start
        self.target  = None       # TextInput to write into
        self.caps    = False
        self._keys   = []         # list of (rect, value)
        self._hover  = {}
        self._press  = {}
        self._build()

    def _build(self):
        self._keys = []
        key_h  = 46
        gap    = 6
        margin = PADDING

        for row_i, row in enumerate(self.ROWS):
            n      = len(row)
            key_w  = (W - margin * 2 - gap * (n - 1)) // n
            offset = (W - (n * key_w + gap * (n - 1))) // 2
            y      = self.y_start + row_i * (key_h + gap)
            for col_i, ch in enumerate(row):
                x = offset + col_i * (key_w + gap)
                self._keys.append((pygame.Rect(x, y, key_w, key_h), ch))

        # Bottom row: SPACE, BACKSPACE, DONE
        y     = self.y_start + 3 * (key_h + gap)
        bw    = (W - margin * 2 - gap * 2) // 3
        items = [
            (pygame.Rect(margin,                y, bw,     key_h), "⌫"),
            (pygame.Rect(margin + bw + gap,     y, bw + (W - margin*2 - bw*3 - gap*2), key_h), "SPACE"),
            (pygame.Rect(W - margin - bw,       y, bw,     key_h), "↵"),
        ]
        self._keys.extend(items)

    def update(self, dt, mouse_pos, mouse_down):
        for rect, val in self._keys:
            k = val
            hovered = rect.collidepoint(mouse_pos)
            self._hover[k] = lerp(self._hover.get(k, 0.0),
                                  1.0 if hovered else 0.0, dt * LERP_SPEED)
            self._press[k] = lerp(self._press.get(k, 0.0),
                                  1.0 if (hovered and mouse_down) else 0.0, dt * 30)

    def handle_event(self, event):
        if event.type != pygame.MOUSEBUTTONUP or event.button != 1:
            return
        for rect, val in self._keys:
            if rect.collidepoint(event.pos):
                self._on_key(val)
                return

    def _on_key(self, val):
        if self.target is None:
            return
        if val == "⌫":
            self.target.text = self.target.text[:-1]
        elif val == "SPACE":
            if len(self.target.text) < 64:
                self.target.text += " "
        elif val == "↵":
            pass  # caller checks target.text
        elif val == "CAPS":
            self.caps = not self.caps
        else:
            ch = val if self.caps else val.lower()
            if len(self.target.text) < 64:
                self.target.text += ch

    def draw(self, surf):
        key_h = 46
        for rect, val in self._keys:
            k   = val
            h_t = self._hover.get(k, 0.0)
            p_t = self._press.get(k, 0.0)

            is_special = val in ("⌫", "SPACE", "↵")
            bg    = lerp_color(CARD_BG, CARD_HOVER, h_t)
            bord  = lerp_color(CARD_BORDER, ACCENT_DIM, h_t)

            scale = lerp(1.0, 0.93, p_t)
            r     = rect.inflate(int(rect.w * (scale - 1)), int(rect.h * (scale - 1)))
            r.center = rect.center

            draw_rounded_rect(surf, bg, r, 10, border=1, border_color=bord)

            if is_special:
                col  = ACCENT if val == "↵" else TEXT_MUTED
                size = 13
            else:
                col  = TEXT_PRIMARY
                size = 15

            font = pygame.font.SysFont("DejaVuSans,Arial", size, bold=is_special)
            lbl  = font.render(val if (self.caps or is_special) else val.lower(), True, col)
            surf.blit(lbl, lbl.get_rect(center=r.center))


class StatusDot:
    """Animated pulsing dot for connection status."""
    def __init__(self, pos, color):
        self.pos   = pos
        self.color = color
        self._t    = 0.0

    def update(self, dt):
        self._t += dt

    def draw(self, surf):
        pulse = 0.6 + 0.4 * math.sin(self._t * 4)
        r = int(6 * pulse)
        # no glow
        pygame.draw.circle(surf, self.color, self.pos, r)


def draw_title(surf, text, y, font_size=28, color=TEXT_PRIMARY):
    font = pygame.font.SysFont("DejaVuSans,Arial", font_size, bold=True)
    lbl  = font.render(text, True, color)
    surf.blit(lbl, (W // 2 - lbl.get_width() // 2, y))
    return y + lbl.get_height()


def draw_subtitle(surf, text, y, color=TEXT_MUTED):
    font = pygame.font.SysFont("DejaVuSans,Arial", 13)
    lbl  = font.render(text, True, color)
    surf.blit(lbl, (W // 2 - lbl.get_width() // 2, y))
    return y + lbl.get_height()


def draw_label(surf, text, pos, size=12, color=TEXT_MUTED, bold=False):
    font = pygame.font.SysFont("DejaVuSans,Arial", size, bold=bold)
    lbl  = font.render(text, True, color)
    surf.blit(lbl, pos)