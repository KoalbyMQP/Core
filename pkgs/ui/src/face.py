import pygame
import math
import sys

pygame.init()

W, H = 1200, 600
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Face UI")

BLACK        = (0, 0, 0)
WHITE        = (255, 255, 255)
CARD_BG      = (22, 22, 28)
CARD_HOVER   = (38, 38, 48)
CARD_ACTIVE  = (28, 60, 90)
ACCENT       = (100, 200, 255)
TEXT_PRIMARY = (240, 240, 245)
TEXT_MUTED   = (110, 110, 130)
TOGGLE_ON    = (52, 199, 89)
TOGGLE_OFF   = (58, 58, 68)
BG_SETTINGS  = (18, 20, 22)

font_title = pygame.font.SysFont("Helvetica,Arial", 22, bold=True)
font_label = pygame.font.SysFont("Helvetica,Arial", 15, bold=True)
font_sub   = pygame.font.SysFont("Helvetica,Arial", 12)

SETTINGS = [
    {"label": "Wi-Fi",       "sub": "Home Network", "icon": "wifi",    "on": True},
    {"label": "Bluetooth",   "sub": "Connected",    "icon": "bt",      "on": True},
    {"label": "Pairing",     "sub": "Discoverable", "icon": "pair",    "on": False},
    {"label": "Flashlight",  "sub": "",             "icon": "flash",   "on": False},
    {"label": "Do Not Disturb","sub": "Off",        "icon": "moon",    "on": False},
    {"label": "Auto-Rotate", "sub": "On",           "icon": "rotate",  "on": True},
    {"label": "Display",     "sub": "100%",         "icon": "display", "on": True},
    {"label": "Sound",       "sub": "High",         "icon": "sound",   "on": True},
]

# transition: 0.0 = face, 1.0 = settings grid
transition   = 0.0
target_t     = 0.0
drag_active  = False
drag_start_x = None
drag_start_t = 0.0

clock = pygame.time.Clock()


def lerp(a, b, t):
    return a + (b - a) * t


# ── Icons ─────────────────────────────────────────────────────────────────────

def draw_icon(surf, key, cx, cy, size, color):
    s = size // 2
    if key == "wifi":
        for r in (s, int(s*0.65), int(s*0.35)):
            pygame.draw.arc(surf, color,
                pygame.Rect(cx-r, cy-r+4, r*2, r*2),
                math.radians(35), math.radians(145), max(2, size//14))
        pygame.draw.circle(surf, color, (cx, cy + int(s*0.55)), max(2, size//14))

    elif key == "bt":
        lw = max(2, size//18)
        pygame.draw.line(surf, color, (cx, cy-s), (cx, cy+s), lw)
        pygame.draw.line(surf, color, (cx, cy-s), (cx+s//2, cy-s//3), lw)
        pygame.draw.line(surf, color, (cx+s//2, cy-s//3), (cx-s//2, cy+s//3), lw)
        pygame.draw.line(surf, color, (cx-s//2, cy+s//3), (cx+s//2, cy+s//3), lw)
        pygame.draw.line(surf, color, (cx+s//2, cy+s//3), (cx, cy+s), lw)

    elif key == "pair":
        lw = max(2, size//18)
        pygame.draw.circle(surf, color, (cx-s//2, cy), s//2, lw)
        pygame.draw.circle(surf, color, (cx+s//2, cy), s//2, lw)
        pygame.draw.line(surf, color, (cx-s//2+s//2, cy-2), (cx+s//2-s//2, cy-2), lw)
        pygame.draw.line(surf, color, (cx-s//2+s//2, cy+2), (cx+s//2-s//2, cy+2), lw)

    elif key == "flash":
        pygame.draw.polygon(surf, color,
            [(cx, cy-s), (cx-s//3, cy-2), (cx+s//4, cy-2), (cx, cy+s),
             (cx+s//3, cy+2), (cx-s//4, cy+2)])

    elif key == "moon":
        pygame.draw.circle(surf, color, (cx, cy), s, max(2, size//16))
        pygame.draw.circle(surf, CARD_BG, (cx + s//3, cy - s//4), int(s*0.75))

    elif key == "rotate":
        lw = max(2, size//18)
        pygame.draw.arc(surf, color,
            pygame.Rect(cx-s+2, cy-s+2, s*2-4, s*2-4),
            math.radians(40), math.radians(320), lw)
        tx = cx + int((s-4)*math.cos(math.radians(40)))
        ty = cy - int((s-4)*math.sin(math.radians(40)))
        pygame.draw.polygon(surf, color, [(tx, ty), (tx-5, ty-3), (tx+2, ty-6)])

    elif key == "display":
        lw = max(2, size//18)
        pygame.draw.rect(surf, color, (cx-s, cy-int(s*0.7), s*2, int(s*1.4)), lw,
                         border_radius=4)
        pygame.draw.line(surf, color, (cx, cy+int(s*0.7)), (cx, cy+s), lw)
        pygame.draw.line(surf, color, (cx-s//2, cy+s), (cx+s//2, cy+s), lw)

    elif key == "sound":
        lw = max(2, size//18)
        pygame.draw.polygon(surf, color,
            [(cx-s, cy-s//3), (cx-s//4, cy-s//3), (cx+s//3, cy-s),
             (cx+s//3, cy+s), (cx-s//4, cy+s//3), (cx-s, cy+s//3)], lw)
        for r in (int(s*0.55), int(s*0.85)):
            pygame.draw.arc(surf, color,
                pygame.Rect(cx+s//4, cy-r, r, r*2),
                math.radians(-40), math.radians(40), lw)


def draw_toggle(surf, x, y, on):
    tw, th = 38, 22
    pygame.draw.rect(surf, TOGGLE_ON if on else TOGGLE_OFF,
                     (x, y, tw, th), border_radius=11)
    kx = x + tw - 13 if on else x + 9
    pygame.draw.circle(surf, WHITE, (kx, y + 11), 8)


# ── Face ──────────────────────────────────────────────────────────────────────

def draw_oval(surf, cx, cy, rx, ry):
    pts = []
    for i in range(60):
        a = 2 * math.pi * i / 60
        pts.append((cx + rx*math.cos(a), cy + ry*math.sin(a)))
    pygame.draw.polygon(surf, WHITE, pts)


def draw_face(surf, offset_x):
    cx = W // 2 + offset_x
    cy = H // 2
    draw_oval(surf, cx - 270, cy - 45, 118, 170)
    draw_oval(surf, cx + 270, cy - 45, 118, 170)
    # flat mouth
    pygame.draw.line(surf, WHITE,
                     (cx - 110, cy + 205), (cx + 110, cy + 205), 7)


# ── Settings Grid ─────────────────────────────────────────────────────────────

COLS, ROWS = 4, 2
PAD_X, PAD_Y = 60, 50
TOP_Y = 80

def grid_rects():
    rects = []
    cw = (W - PAD_X*2) // COLS
    ch = (H - TOP_Y - PAD_Y) // ROWS
    for i, s in enumerate(SETTINGS):
        col = i % COLS
        row = i // COLS
        x = PAD_X + col * cw
        y = TOP_Y + row * ch
        rects.append(pygame.Rect(x + 8, y + 8, cw - 16, ch - 16))
    return rects


def draw_settings(surf, offset_x):
    surf_s = pygame.Surface((W, H))
    surf_s.fill(BG_SETTINGS)

    rects = grid_rects()
    mx, my = pygame.mouse.get_pos()
    mx -= offset_x   # adjust for surface offset

    for i, (s, r) in enumerate(zip(SETTINGS, rects)):
        hover = r.collidepoint(mx, my)
        bg = CARD_ACTIVE if s["on"] else (CARD_HOVER if hover else CARD_BG)
        pygame.draw.rect(surf_s, bg, r, border_radius=18)
        pygame.draw.rect(surf_s, (45, 45, 58), r, 1, border_radius=18)

        icon_col = ACCENT if s["on"] else TEXT_MUTED
        draw_icon(surf_s, s["icon"], r.x + 38, r.y + r.height//2 - 8, 36, icon_col)

        lbl = font_label.render(s["label"], True, TEXT_PRIMARY)
        surf_s.blit(lbl, (r.x + 16, r.bottom - 38))
        if s["sub"]:
            sub = font_sub.render(s["sub"], True, ACCENT if s["on"] else TEXT_MUTED)
            surf_s.blit(sub, (r.x + 16, r.bottom - 20))

        draw_toggle(surf_s, r.right - 50, r.y + 12, s["on"])

    surf.blit(surf_s, (offset_x, 0))
    return rects


# ── Main loop ─────────────────────────────────────────────────────────────────

while True:
    dt = clock.tick(60) / 1000.0
    mx, my = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.quit(); sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            drag_active  = True
            drag_start_x = mx
            drag_start_t = transition

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if drag_active:
                drag_active = False
                # snap
                target_t = 1.0 if transition > 0.4 else 0.0

                # tap (barely moved) → toggle setting if on grid
                if abs(mx - drag_start_x) < 10 and transition > 0.85:
                    rects = grid_rects()
                    adj_x = mx - int(lerp(0, -W, transition) + W * transition)
                    for i, r in enumerate(rects):
                        if r.move(int(W * transition), 0).collidepoint(mx, my):
                            SETTINGS[i]["on"] = not SETTINGS[i]["on"]
                            break

    if drag_active and drag_start_x is not None:
        delta = drag_start_x - mx           # positive = dragging left
        transition = max(0.0, min(1.0, drag_start_t + delta / W))
    else:
        transition = lerp(transition, target_t, min(1.0, dt * 18))

    # face slides out left, settings slides in from right
    face_x     = int(-transition * W)
    settings_x = int((1.0 - transition) * W)

    screen.fill(BG_SETTINGS)

    if transition < 0.99:
        draw_face(screen, face_x)

    if transition > 0.01:
        draw_settings(screen, settings_x)

    pygame.display.flip()