# cortex_bridge

ROS2 node that bridges the Cortex HTTP control plane to ROS2 topics and services. Polls Cortex via localhost HTTP and publishes state changes. Also serves WiFi scan/connect services for the startup wizard.

## Published Topics

| Topic | Type | QoS | Description |
|-------|------|-----|-------------|
| `/zaraos/auth/code` | `AuthCode` | Latched | New pairing code generated (polled every 1s) |
| `/zaraos/auth/status` | `AuthStatus` | Latched | Pairing outcome (paired/expired) |
| `/zaraos/instances/state` | `InstanceState` | Default | Container instance state changes (polled every 2s) |
| `/zaraos/system/errors` | `SystemError` | Default | Error events from Cortex event log (polled every 3s) |

## Services

| Service | Type | Description |
|---------|------|-------------|
| `/zaraos/wifi/scan` | `WifiScan` | Scans via `wpa_cli`, returns deduplicated SSIDs sorted by signal |
| `/zaraos/wifi/connect` | `WifiConnect` | Writes `wpa_supplicant.conf`, connects, runs DHCP, verifies internet |

## Cortex Connection

Connects to `http://127.0.0.1:8080` (no authentication). Uses only stdlib `urllib` -- no extra HTTP dependencies.

## Dependencies

- `zaraos_interfaces` (must be built first)
- Cortex running on localhost:8080

## Run

```bash
ros2 run cortex_bridge bridge_node
```
