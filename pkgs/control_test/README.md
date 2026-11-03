# control_test

Exercises the `/crab` node from [`crab_api`](../crab_api). Every 10s the
`/control_test` node:

1. Publishes a `zaraos_interfaces/msg/MotorMove` to `/motor/move` with a random
   joint (`Shoulder`, `Hip`, or `Test`), position in `[-45, 45]` deg, and time in
   `[0.1, 0.49]` s (that is a multiple of 0.1)
2. One second later, calls the `/motor/state` service
   (`zaraos_interfaces/srv/GetMotorState`) for the same joint and logs the
   reported position.

## Running locally

From the root of the `Core` repo, inside `nix develop`, with `crab_node`
already running (see the `crab_api` README):

```sh
colcon build --base-paths pkgs --packages-up-to control_test
source install/setup.bash
ros2 run control_test control_test_node
```

## Testing with combined output

To test this node (`control_test_node`) and `crab_node` at the same time and combine
their ROS log outputs, use the following (ensure `urchin-sim` in the `Urchin_Framework`
repo is running in another terminal):

```sh
(trap 'kill 0'
   URCHIN_PORT=socket://localhost:5555 ros2 run crab_api crab_node >/dev/null &
   ros2 run control_test control_test_node)
```

Write these logs to a file with `tee` using:

```sh
(trap 'kill 0'
   URCHIN_PORT=socket://localhost:5555 ros2 run crab_api crab_node >/dev/null &
   ros2 run control_test control_test_node)  2>&1 | tee -a control_test.log
```

