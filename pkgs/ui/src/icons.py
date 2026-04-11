import pygame
import math

def draw_icon(surf, key, cx, cy, size, color, filled=False):
    s = size // 2
    lw = max(2, size // 14)

    if key == "wifi":
        pygame.draw.circle(surf, color, (cx, cy + s // 2), max(3, size // 12))
        for i, radius in enumerate([int(s * 0.45), int(s * 0.75), s]):
            alpha = 255 if filled else 200
            pygame.draw.arc(surf, color,
                pygame.Rect(cx - radius, cy - radius + s // 2, radius * 2, radius * 2),
                math.radians(40), math.radians(140), lw)

    elif key == "bt":
        # Classic Bluetooth rune shape
        hw = s // 3
        pygame.draw.line(surf, color, (cx, cy - s), (cx, cy + s), lw)
        pygame.draw.line(surf, color, (cx, cy - s), (cx + hw, cy - s // 2), lw)
        pygame.draw.line(surf, color, (cx + hw, cy - s // 2), (cx - hw, cy + s // 2), lw)
        pygame.draw.line(surf, color, (cx - hw, cy + s // 2), (cx + hw, cy + s // 2), lw)
        pygame.draw.line(surf, color, (cx + hw, cy + s // 2), (cx, cy + s), lw)

    elif key == "pair":
        # Two interlocked rings
        gap = s // 3
        for ox in (-gap, gap):
            pygame.draw.circle(surf, color, (cx + ox, cy), int(s * 0.55), lw)

    elif key == "flash":
        # Solid lightning bolt
        pts = [
            (cx + s // 4, cy - s),
            (cx - s // 5, cy - s // 8),
            (cx + s // 5, cy - s // 8),
            (cx - s // 4, cy + s),
            (cx + s // 5, cy + s // 8),
            (cx - s // 5, cy + s // 8),
        ]
        pygame.draw.polygon(surf, color, pts)

    elif key == "moon":
        # Filled crescent
        pygame.draw.circle(surf, color, (cx, cy), s)
        pygame.draw.circle(surf, (22, 22, 28), (cx + s // 3, cy - s // 5), int(s * 0.78))

    elif key == "rotate":
        # Arrow arc — clockwise rotation symbol
        r = s - 2
        pygame.draw.arc(surf, color,
            pygame.Rect(cx - r, cy - r, r * 2, r * 2),
            math.radians(50), math.radians(310), lw + 1)
        # arrowhead at the end of the arc
        end_a = math.radians(50)
        ex = cx + int(r * math.cos(end_a))
        ey = cy - int(r * math.sin(end_a))
        pygame.draw.polygon(surf, color, [
            (ex, ey),
            (ex + 7, ey - 3),
            (ex + 3, ey + 6),
        ])

    elif key == "display":
        # Monitor with stand
        mw, mh = int(s * 1.6), int(s * 1.1)
        pygame.draw.rect(surf, color,
            (cx - mw // 2, cy - mh // 2 - 4, mw, mh), lw, border_radius=4)
        pygame.draw.line(surf, color, (cx, cy + mh // 2 - 4), (cx, cy + s - 2), lw)
        pygame.draw.line(surf, color, (cx - s // 2, cy + s - 2), (cx + s // 2, cy + s - 2), lw)

    elif key == "sound":
        # Speaker cone + two arcs
        cone = [
            (cx - s // 2, cy - s // 4),
            (cx - s // 8, cy - s // 4),
            (cx + s // 4, cy - s * 9 // 10),
            (cx + s // 4, cy + s * 9 // 10),
            (cx - s // 8, cy + s // 4),
            (cx - s // 2, cy + s // 4),
        ]
        if filled:
            pygame.draw.polygon(surf, color, cone)
        else:
            pygame.draw.polygon(surf, color, cone, lw)
        for r in (int(s * 0.5), int(s * 0.85)):
            pygame.draw.arc(surf, color,
                pygame.Rect(cx + s // 5, cy - r, r, r * 2),
                math.radians(-35), math.radians(35), lw)