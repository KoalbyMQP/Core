import math
import pygame

from constants import *

def _rotated_oval_pts(cx, cy, rx, ry, angle_deg, n=60):
    a = math.radians(angle_deg)
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = rx * math.cos(t)
        y = ry * math.sin(t)
        rx2 = x * math.cos(a) - y * math.sin(a) + cx
        ry2 = x * math.sin(a) + y * math.cos(a) + cy
        pts.append((rx2, ry2))
    return pts


def draw_face(surf, offset_x):
    cx = W // 2 + offset_x
    cy = H // 2
    # Eyes: tilted inward ~20°, left tilts +20, right tilts -20
    left_pts  = _rotated_oval_pts(cx - 270, cy - 45, 118, 170, -20)
    right_pts = _rotated_oval_pts(cx + 270, cy - 45, 118, 170, 20)
    pygame.draw.polygon(surf, WHITE, left_pts)
    pygame.draw.polygon(surf, WHITE, right_pts)
    # Flat mouth
    pygame.draw.line(surf, WHITE,
                     (cx - 110, cy + 205), (cx + 110, cy + 205), 7)