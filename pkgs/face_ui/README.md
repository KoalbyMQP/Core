# face_ui

Robot face display with a swipeable settings panel and ROS2-driven overlays. Built with Pygame.

## What It Does

- Renders an animated robot face as the primary display
- Swipe left to reveal a settings grid panel
- Overlays driven by ROS2 messages:
  - **Auth code overlay** -- shows 6-digit pairing code from Cortex on screen
  - **Error toast** -- shows system error notifications with severity
  - **Instance status bar** -- shows container state changes (starting, running, crashed, etc.)

## ROS2 Subscriptions

| Topic | Type | Description |
|-------|------|-------------|
| `/zaraos/auth/code` | `AuthCode` | Display pairing code overlay |
| `/zaraos/auth/status` | `AuthStatus` | Update pairing status |
| `/zaraos/instances/state` | `InstanceState` | Update instance status bar |
| `/zaraos/system/errors` | `SystemError` | Show error toast |

The ROS2 node runs on a background thread. Messages are passed to the Pygame main loop via thread-safe queues.

## Standalone Mode

If ROS2 is not available (e.g., desktop development), the UI runs standalone with no overlays. No crash, no special flags needed -- the import failure is caught silently.

## Display

1200x600 pixels. Uses KMSDRM on Raspberry Pi for direct framebuffer rendering.

## Dependencies

- `zaraos_interfaces`
- `pygame`

## Run

```bash
ros2 run face_ui face_ui_node
# or without ROS2:
python -m face_ui.main
```
