import math
import os
import pygame
import sys
import threading
import traceback

# ── ROS2 setup (before any screen import) ────────────────────────────
_ros_available = False
_node = None

try:
    import rclpy
    from startup_wizard.node import StartupWizardNode
    _ros_available = True
except ImportError:
    pass

# Inject ROS2-backed system module if available, otherwise use real system module.
# This MUST happen before importing screens, since screens.py does `import system`.
if _ros_available:
    try:
        from startup_wizard import system_ros
        sys.modules["system"] = system_ros
    except ImportError:
        pass

from startup_wizard.constants import *
from startup_wizard.components import lerp, draw_rounded_rect

NON_RENDERING_DRIVERS = {"dummy", "offscreen"}


def init_display():
    requested = os.environ.get("SDL_VIDEODRIVER", "").strip()
    attempts = []
    if requested:
        attempts.append(("requested", requested, os.environ.get("SDL_KMSDRM_REQUIRE_DRM_MASTER")))
        if requested == "kmsdrm":
            attempts.append(("fbcon-fallback", "fbcon", None))
    else:
        attempts.append(("kmsdrm", "kmsdrm", None))
        attempts.append(("fbcon", "fbcon", None))
        attempts.append(("auto", None, None))

    seen = set()
    last_err = None
    dri_nodes = [node for node in ("/dev/dri/card0", "/dev/dri/renderD128") if os.path.exists(node)]
    print(
        f"[startup_wizard] display init: requested={requested or '<auto>'} dri_nodes={dri_nodes}",
        flush=True,
    )

    for label, driver, drm_master in attempts:
        key = (driver, drm_master)
        if key in seen:
            continue
        seen.add(key)

        pygame.quit()
        if driver:
            os.environ["SDL_VIDEODRIVER"] = driver
        else:
            os.environ.pop("SDL_VIDEODRIVER", None)

        if drm_master is None:
            os.environ.pop("SDL_KMSDRM_REQUIRE_DRM_MASTER", None)
        else:
            os.environ["SDL_KMSDRM_REQUIRE_DRM_MASTER"] = drm_master

        pygame.init()
        try:
            screen = pygame.display.set_mode((W, H))
            pygame.display.set_caption("ZaraOS Setup")
            active_driver = pygame.display.get_driver()
            if active_driver in NON_RENDERING_DRIVERS:
                raise pygame.error(f"non-rendering SDL backend selected: {active_driver}")
            print(
                f"[startup_wizard] display backend ready: attempt={label} driver={active_driver}",
                flush=True,
            )
            return screen
        except pygame.error as err:
            last_err = err
            print(
                f"[startup_wizard] display backend failed: attempt={label} driver={driver or '<auto>'} "
                f"drm_master={os.environ.get('SDL_KMSDRM_REQUIRE_DRM_MASTER', '<unset>')} err={err}",
                flush=True,
            )

    raise last_err or pygame.error("no usable SDL video backend")


def make_screen(state, ctx):
    from startup_wizard.screens import (
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
    visible = states[1:]
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
            pygame.draw.circle(surf, WHITE, (x, y), dot_r)
        else:
            pygame.draw.circle(surf, WHITE, (x, y), dot_r, 1)


def main():
    global _node
    try:
        # Initialize ROS2 if available
        if _ros_available:
            try:
                rclpy.init()
                _node = StartupWizardNode()
                # Set node reference in system_ros so service calls work
                if "system" in sys.modules and hasattr(sys.modules["system"], "set_node"):
                    sys.modules["system"].set_node(_node)
                spin_thread = threading.Thread(target=rclpy.spin, args=(_node,), daemon=True)
                spin_thread.start()
            except Exception as e:
                print(f"[startup_wizard] ROS2 init failed, running standalone: {e}", flush=True)
                _node = None

        screen = init_display()
        clock  = pygame.time.Clock()

        state   = "welcome"
        ctx     = {}
        current = make_screen(state, ctx)
        t       = 0.0

        trans_alpha = 0
        trans_dir   = 1
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
                    pygame.quit()
                    if _node:
                        _node.destroy_node()
                        rclpy.try_shutdown()
                    sys.exit()
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    pygame.quit()
                    if _node:
                        _node.destroy_node()
                        rclpy.try_shutdown()
                    sys.exit()

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

            result = None
            if trans_dir == 1 or trans_alpha < 200:
                result = current.update(dt, events, (mx, my), mouse_down)

            if result and not next_state:
                if result == "exit":
                    pygame.quit()
                    if _node:
                        _node.destroy_node()
                        rclpy.try_shutdown()
                    sys.exit(0)
                if isinstance(result, tuple):
                    ns, nc = result
                else:
                    ns, nc = result, {}
                next_state = ns
                next_ctx   = {**ctx, **nc}
                trans_dir  = -1

            draw_bg(screen, t)
            current.draw(screen)
            draw_progress_dots(screen, state)

            if trans_alpha > 0:
                overlay = pygame.Surface((W, H))
                overlay.fill(BG)
                overlay.set_alpha(trans_alpha)
                screen.blit(overlay, (0, 0))

            pygame.display.flip()
    except Exception:
        print("[startup_wizard] fatal exception", flush=True)
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
