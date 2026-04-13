import pygame

from face_ui.constants import *
from face_ui.face import draw_face
from face_ui.icons import draw_icon

font_label = None
font_sub   = None

def init_fonts():
    global font_label, font_sub
    font_label = pygame.font.SysFont("Helvetica,Arial", 15, bold=True)
    font_sub   = pygame.font.SysFont("Helvetica,Arial", 12)


def grid_rects():
    rects = []
    cw = (W - PAD_X * 2) // COLS
    ch = (H - TOP_Y - PAD_Y) // ROWS
    for i in range(len(SETTINGS)):
        col = i % COLS
        row = i // COLS
        x = PAD_X + col * cw
        y = TOP_Y + row * ch
        rects.append(pygame.Rect(x + 8, y + 8, cw - 16, ch - 16))
    return rects


def draw_settings(surf, offset_x, mouse_pos):
    surf_s = pygame.Surface((W, H))
    surf_s.fill(BG)

    rects = grid_rects()
    mx = mouse_pos[0] - offset_x
    my = mouse_pos[1]

    for i, (s, r) in enumerate(zip(SETTINGS, rects)):
        hover = r.collidepoint(mx, my)
        if s["on"]:
            bg = CARD_ACTIVE
        elif hover:
            bg = CARD_HOVER
        else:
            bg = CARD_BG

        pygame.draw.rect(surf_s, bg, r, border_radius=18)

        # Active indicator: left edge accent bar
        if s["on"]:
            bar = pygame.Rect(r.x, r.y + 24, 4, r.height - 48)
            pygame.draw.rect(surf_s, ACCENT, bar, border_radius=2)
        else:
            pygame.draw.rect(surf_s, (45, 45, 58), r, 1, border_radius=18)

        icon_col = ACCENT if s["on"] else TEXT_MUTED
        draw_icon(surf_s, s["icon"],
                  r.x + r.width // 2, r.y + r.height // 2 - 12,
                  42, icon_col, filled=s["on"])

        lbl = font_label.render(s["label"], True, TEXT_PRIMARY)
        surf_s.blit(lbl, (r.x + 14, r.bottom - 38))
        if s["sub"]:
            sub = font_sub.render(s["sub"], True, ACCENT if s["on"] else TEXT_MUTED)
            surf_s.blit(sub, (r.x + 14, r.bottom - 20))

    surf.blit(surf_s, (offset_x, 0))
    return rects
