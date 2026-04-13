import pygame
import sys
import threading

# Try ROS2 import — graceful fallback for desktop dev
_ros_available = False
_node = None
try:
    import rclpy
    from face_ui.node import FaceUINode
    _ros_available = True
except ImportError:
    pass

from face_ui.ui import draw_settings, grid_rects, SETTINGS, init_fonts
from face_ui.face import draw_face
from face_ui.constants import W, H, BG
from face_ui.overlays.auth_code import AuthCodeOverlay
from face_ui.overlays.error_toast import ErrorToast
from face_ui.overlays.instance_status import InstanceStatusBar


def _drain_queue(q):
    """Non-blocking drain of all pending items from a queue."""
    items = []
    while True:
        try:
            items.append(q.get_nowait())
        except Exception:
            break
    return items


def main():
    global _node

    # Initialize ROS2 if available
    if _ros_available:
        try:
            rclpy.init()
            _node = FaceUINode()
            spin_thread = threading.Thread(target=rclpy.spin, args=(_node,), daemon=True)
            spin_thread.start()
        except Exception as e:
            print(f"[face_ui] ROS2 init failed, running standalone: {e}")
            _node = None

    # Overlays
    auth_overlay = AuthCodeOverlay()
    error_toast = ErrorToast()
    instance_bar = InstanceStatusBar()

    # Instance tracking
    instances: dict = {}  # instance_id -> {app, state, error}

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
                pygame.quit()
                if _node:
                    _node.destroy_node()
                    rclpy.try_shutdown()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                if _node:
                    _node.destroy_node()
                    rclpy.try_shutdown()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                drag_active  = True
                drag_start_x = mx
                drag_start_t = transition

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if drag_active:
                    drag_active = False
                    target_t = 1.0 if transition > 0.4 else 0.0

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

        # ── Drain ROS2 messages ──────────────────────────────────
        if _node:
            for msg in _drain_queue(_node.auth_code_queue):
                auth_overlay.set_code(msg["code"], msg["expires_in"])

            for msg in _drain_queue(_node.auth_status_queue):
                auth_overlay.set_status(msg["status"], msg.get("label", ""))

            for msg in _drain_queue(_node.instance_queue):
                iid = msg["instance_id"]
                instances[iid] = msg
                instance_bar.update_instances(list(instances.values()))

            for msg in _drain_queue(_node.error_queue):
                error_toast.push(msg["message"], msg.get("severity", "error"))

        # ── Update overlays ──────────────────────────────────────
        auth_overlay.update(dt)
        error_toast.update(dt)
        instance_bar.update(dt)

        # ── Draw ─────────────────────────────────────────────────
        face_x     = int(-transition * W)
        settings_x = int((1.0 - transition) * W)

        screen.fill(BG)

        if transition < 0.99:
            draw_face(screen, face_x)

        if transition > 0.01:
            draw_settings(screen, settings_x, (mx, my))

        # Overlays on top
        if auth_overlay.active or auth_overlay._alpha > 0.01:
            auth_overlay.draw(screen)
        error_toast.draw(screen)
        instance_bar.draw(screen)

        pygame.display.flip()


if __name__ == "__main__":
    main()
