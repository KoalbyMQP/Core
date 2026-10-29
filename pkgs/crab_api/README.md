# crab_api

ROS interface to the Urchin motor controller, built on the
[Crab API](https://github.com/KoalbyMQP/Urchin-Framework/tree/main/Crab_API).

The `/crab` node:

| Topic           | Direction | Type                               | Description                                              |
| --------------- | --------- | ---------------------------------- | -------------------------------------------------------- |
| `/motor/move`   | subscribe | `zaraos_interfaces/msg/MotorMove`  | Move `joint_name` to `position` (deg) over `time` (s)    |
| `/motor/states` | publish   | `zaraos_interfaces/msg/MotorStates` | Position (deg) of every motor in the bridge file        |

### Parameters

| Name                   | Default                        | Description                                    |
| ---------------------- | ------------------------------ | ---------------------------------------------- |
| `bridge_file`          | `share/crab_api/bridge.toml`   | Urchin bridge file listing the connected motors |
| `state_publish_period` | `1.0`                          | Seconds between `/motor/states` messages        |
| `angle_timeout`        | `0.5`                          | Seconds to wait for Urchin to report an angle   |

Urchin is found by scanning USB serial ports. Set `URCHIN_PORT` (e.g.
`socket://localhost:5555`) to connect to the QEMU simulator instead.

### Limitations

- `time` must be at most ~0.49 s; longer moves are rejected by the Crab API.
- The firmware never frees tickets, and every move and every per-joint angle
  read uses one, so a long-running node will eventually get
  "no free ticket" errors.

## Running locally

From the root of the `Core` repo, inside `nix develop`:

```sh
colcon build --base-paths pkgs --packages-up-to crab_api
source install/setup.bash
URCHIN_PORT=socket://localhost:5555 ros2 run crab_api crab_node
```

Then, from another shell:

```sh
ros2 topic pub --once /motor/move zaraos_interfaces/msg/MotorMove \
    "{joint_name: Shoulder, position: -23.0, time: 0.3}"
ros2 topic echo /motor/states
```

## Building container image

Run from the root of the `Core` repo:

```sh
docker buildx build \
    --platform linux/arm64 \
    -f pkgs/crab_api/Dockerfile \
    -t crab-api:dev \
    --load .
```
