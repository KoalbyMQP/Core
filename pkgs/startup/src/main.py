import pygame
import sys
import math
from constants import *
from components import lerp, draw_rounded_rect


def make_screen(state, ctx):
    from screens import (
        WelcomeScreen, NameScreen, WifiScanScreen,
        WifiPasswordScreen, ConnectingScreen, PullingScreen, DoneScreen
    )
    if state == "welcome":
        return WelcomeScreen()
    if state == "name":
        return NameScreen()
    if state == "wifi_scan":
        return WifiScanScreen(ctx.get("robot_name", ""))
    if state == "wifi_password":
        return WifiPasswordScreen(ctx.get("robot_name", ""), ctx.get("ssid", ""))
    if state == "connecting":
        return ConnectingScreen(ctx.get("robot_name", ""),
                                ctx.get("ssid", ""), ctx.get("password", ""))
    if state == "pulling":
        return PullingScreen(ctx.get("robot_name", ""))
    if state == "done":
        return DoneScreen(ctx.get("robot_name", ""))
    return WelcomeScreen()


def draw_bg(surf, t):
    surf.fill(BG)
    # Subtle animated gradient vignette
    cx, cy = W // 2, H // 2
    pulse = 0.04 * math.sin(t * 0.4)
    r = int(H * (0.75 + pulse))
    glow = pygame.Surface((W, H), pygame.SRCALPHA)
    for i in range(3):
        col = (*[int(c * (0.08 + i * 0.04)) for c in ACCENT], 20)
        rr = r - i * 60
        if rr > 0:
            pygame.draw.ellipse(glow, col,
                                (cx - rr, cy - rr // 2, rr * 2, rr))
    surf.blit(glow, (0, 0))


def draw_progress_dots(surf, state):
    states  = ["welcome", "name", "wifi_scan", "wifi_password",
                "connecting", "pulling", "done"]
    visible = states[1:]  # skip welcome
    if state not in visible:
        return
    idx = visible.index(state) if state in visible else 0
    n   = len(visible)
    dot_r, gap = 4, 16
    total_w = n * (dot_r * 2) + (n - 1) * gap
    sx = W // 2 - total_w // 2

    for i in range(n):
        x = sx + i * (dot_r * 2 + gap) + dot_r
        y = H - 24
        if i == idx:
            # Current: filled white
            pygame.draw.circle(surf, WHITE, (x, y), dot_r)
        else:
            # Others: white outline only
            pygame.draw.circle(surf, WHITE, (x, y), dot_r, 1)


def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("ZaraOS Setup")
    clock  = pygame.time.Clock()

    state   = "welcome"
    ctx     = {}
    current = make_screen(state, ctx)
    t       = 0.0

    # Transition
    trans_alpha = 0
    trans_dir   = 1   # 1 = fade in, -1 = fade out
    next_state  = None
    next_ctx    = None

    while True:
        dt = clock.tick(60) / 1000.0
        t += dt
        mx, my = pygame.mouse.get_pos()
        mouse_down = pygame.mouse.get_pressed()[0]

        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()

        # Transition fade
        if trans_dir == -1:
            trans_alpha = min(255, trans_alpha + int(dt * 600))
            if trans_alpha >= 255 and next_state:
                state   = next_state
                ctx     = next_ctx or {}
                current = make_screen(state, ctx)
                next_state = None
                trans_dir  = 1
        else:
            trans_alpha = max(0, trans_alpha - int(dt * 400))

        # Update current screen (only when not mid-fade-out)
        result = None
        if trans_dir == 1 or trans_alpha < 200:
            result = current.update(dt, events, (mx, my), mouse_down)

        if result and not next_state:
            if result == "exit":
                pygame.quit()
                sys.exit(0)
            if isinstance(result, tuple):
                ns, nc = result
            else:
                ns, nc = result, {}
            next_state = ns
            next_ctx   = {**ctx, **nc}
            trans_dir  = -1

        # Draw
        draw_bg(screen, t)
        current.draw(screen)
        draw_progress_dots(screen, state)

        # Fade overlay
        if trans_alpha > 0:
            overlay = pygame.Surface((W, H))
            overlay.fill(BG)
            overlay.set_alpha(trans_alpha)
            screen.blit(overlay, (0, 0))

        pygame.display.flip()


if __name__ == "__main__":
    main()