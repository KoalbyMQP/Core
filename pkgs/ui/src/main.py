import pygame
import sys

pygame.init()

from ui import draw_settings, grid_rects, SETTINGS, W, H, BG, init_fonts
from face import draw_face

def main():
    init_fonts()

    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Face UI")
    clock = pygame.time.Clock()

    transition   = 0.0
    target_t     = 0.0
    drag_active  = False
    drag_start_x = None
    drag_start_t = 0.0


    def lerp(a, b, t):
        return a + (b - a) * t


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
                    target_t = 1.0 if transition > 0.4 else 0.0

                    # Tap on a setting card
                    if abs(mx - drag_start_x) < 10 and transition > 0.85:
                        rects = grid_rects()
                        for i, r in enumerate(rects):
                            if r.move(int(W * transition), 0).collidepoint(mx, my):
                                SETTINGS[i]["on"] = not SETTINGS[i]["on"]
                                break

        if drag_active and drag_start_x is not None:
            delta = drag_start_x - mx
            transition = max(0.0, min(1.0, drag_start_t + delta / W))
        else:
            transition = lerp(transition, target_t, min(1.0, dt * 18))

        face_x     = int(-transition * W)
        settings_x = int((1.0 - transition) * W)

        screen.fill(BG)

        if transition < 0.99:
            draw_face(screen, face_x)

        if transition > 0.01:
            draw_settings(screen, settings_x, (mx, my))

        pygame.display.flip()

if __name__ == "__main__":
    main()