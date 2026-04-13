# startup_wizard

First-boot setup wizard for ZaraOS. Walks through a 7-screen flow to configure the robot's name, connect to WiFi, and pull container images. Built with Pygame.

## Screen Flow

1. **Welcome** -- intro splash
2. **Name** -- set the robot's name (writes hostname + config)
3. **WiFi Scan** -- scan for available networks
4. **WiFi Password** -- enter password for selected network
5. **Connecting** -- connect to WiFi, verify internet
6. **Pulling** -- pull container images (`nerdctl pull`)
7. **Done** -- setup complete, writes `/data/.setup-done`

The wizard only runs when `/data/.setup-done` does NOT exist.

## ROS2 Integration

WiFi scan and connect operations are routed through ROS2 services (`/zaraos/wifi/scan`, `/zaraos/wifi/connect`) served by `cortex_bridge`. Local operations (hostname, config files) are handled directly.

**Module injection pattern**: `system_ros.py` implements the same interface as `system.py`. When ROS2 is available, `main.py` injects `system_ros` into `sys.modules["system"]` before screens are imported, so screen code calls `system.scan_networks()` without knowing whether ROS2 is behind it.

## Desktop Testing

```bash
python -m startup_wizard.test_desktop
```

This swaps in `system_mock.py` (simulated WiFi, no real hardware calls) so the full flow can be exercised on macOS/Linux without `wpa_cli` or `nerdctl`.

## Display

1024x600 pixels. Uses KMSDRM on Raspberry Pi for direct framebuffer rendering.

## Dependencies

- `zaraos_interfaces`
- `cortex_bridge` (provides WiFi services)
- `pygame`

## Run

```bash
ros2 run startup_wizard startup_wizard_node
```
