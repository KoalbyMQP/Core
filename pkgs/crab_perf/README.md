# crab_perf

Measures how the ROS 2 middleware (RMW) performs for the `crab_api` motor
interface. It uses Apex.AI's
[performance_test](https://index.ros.org/p/performance_test/) (2.3.0, the Humble
release) and a small `/motor/state` service probe.

Run it as its own instance alongside `crab-api` (and `control-test`). Pick the
middleware with an environment variable. Every metric is printed as a single
`key=value` line, so a captured log can be saved and parsed.

## What it measures, and what it can't

`performance_test` only benchmarks **publish/subscribe between its own
processes** using its built-in message types. It can't attach to an existing
topic or node, and it has no service support. So `crab_perf` measures two
things:

| Mode | Measures | Tool |
|---|---|---|
| `local`, `pub`/`sub`, `main`/`relay` | `/motor/move`-style traffic: one-way or round-trip latency, jitter, loss, throughput, CPU and memory for a message the size of `MotorMove` with the same QoS | `perf_test` |
| `state` | Real `/motor/state` calls to the running `/crab` node: round-trip time, timeouts, failures, discovery time | `state_probe` (rclpy) |

The `perf_test` modes use their own topic (`crab_perf_motor_move`) on the same
domain, so they never send moves to the robot. By default they mirror
`/motor/move`:

- `Array32` is a 32-byte payload. A serialized `MotorMove` with a short joint
  name is about 32 bytes.
- QoS is `RELIABLE`, `VOLATILE`, `KEEP_LAST` 10, as created by
  `create_subscription(..., 10)` in `crab2_node`.

`/motor/move` itself has no acknowledgement and no timestamp, so its delivery
to the real `/crab` node can't be timed from outside. `perf_test` gives the
middleware's share of that path. `PERFORMANCE.md` in `crab_api` covers the rest.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `RMW` | _(unset)_ | `cyclone`, `fastdds` or `zenoh`. Overrides `RMW_IMPLEMENTATION` when set. |
| `RMW_IMPLEMENTATION` | `rmw_cyclonedds_cpp` | Used when `RMW` is unset. |
| `ROS_DOMAIN_ID` | `42` | Must match `crab-api` for `state` mode. |
| `PERF_MODE` | `local` | `local`, `pub`, `sub`, `main`, `relay` or `state` (see below) |
| `PERF_RUNTIME` | `60` (`0` for `relay`) | Seconds to measure; `0` runs until the instance is stopped |
| `PERF_RATE` | `100` | Publish rate in Hz (`0` publishes as fast as possible) |
| `PERF_MSG` | `Array32` | Any `perf_test` message: `Array32` … `Array8m`, `Struct16` … `Struct32k`, `PointCloud512k` … |
| `PERF_RELIABILITY` | `RELIABLE` | `RELIABLE` or `BEST_EFFORT` |
| `PERF_DURABILITY` | `VOLATILE` | `VOLATILE` or `TRANSIENT_LOCAL` |
| `PERF_HISTORY` | `KEEP_LAST` | `KEEP_LAST` or `KEEP_ALL` |
| `PERF_HISTORY_DEPTH` | `10` | |
| `PERF_COMMUNICATOR` | `rclcpp-single-threaded-executor` | Also `rclcpp-static-single-threaded-executor` or `rclcpp-waitset` |
| `PERF_TOPIC` | `crab_perf_motor_move` | |
| `PERF_IGNORE` | `0` | Seconds at the start to leave out of the statistics |
| `PERF_MATCH_TIMEOUT` | `60` | Seconds to wait for the other side, or for `/motor/state` |
| `PERF_EXTRA_ARGS` | | Extra `perf_test` flags, e.g. `--zero-copy` |
| `PERF_DUMP_CSV` | `1` | Print the raw `perf_test` CSV logs at the end |
| `PERF_LOG_DIR` | `/tmp/crab_perf` | Where the CSVs are written; mount a volume here to keep them |
| `PROBE_JOINT` | `Shoulder` | Joint requested in `state` mode |
| `PROBE_RATE` | `1.0` | `/motor/state` requests per second |
| `PROBE_TIMEOUT` | `5.0` | Seconds before a request counts as timed out |
| `PROBE_REPORT_PERIOD` | `10` | Seconds between `state` interval lines |
| `ZENOH_ROUTER` | `auto` | Zenoh only. `auto` starts `rmw_zenohd` unless something is already listening on port 7447. Also `on` or `off`. |

### Modes

- **`local`**: a publisher and a subscriber run as two processes in this
  container. Measures one-way latency between processes on this host while
  `crab-api` and `control-test` load the machine.
- **`sub` + `pub`**: run two instances, one with each mode, to measure
  between containers. Start `sub` first. Latency is reported by `sub`. This is
  only valid when both run on the same machine (same clock).
- **`main` + `relay`**: round-trip latency on one clock; `relay` echoes every
  sample back. Use it across machines. Start `relay` first; it runs until
  stopped. One-way latency is roughly half the round trip.
- **`state`**: calls `/motor/state` on the running `/crab` node at
  `PROBE_RATE`. **Each call makes crab send a GetAngle ticket, and the firmware
  never frees tickets.** Keep the rate and runtime low, or the node starts
  failing with "no free ticket". With `crab2_node` as it is today, every response
  has `success=false` (it doesn't read the angle back yet). The round-trip time
  is still measured, and failures are counted separately.

### Comparing RMWs

`state` mode only works if `crab-api` uses the same RMW. Zenoh and DDS do not
interoperate. `crab-api` and `control-test` currently install only CycloneDDS
and hard-code `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`. To compare RMWs end to
end, add `ros-humble-rmw-fastrtps-cpp` / `ros-humble-rmw-zenoh-cpp` to their
images and set the same `RMW_IMPLEMENTATION` on every instance.

**Zenoh** needs one router (`rmw_zenohd`) per system. By default every node
looks for it at `tcp/localhost:7447` and listens only on `localhost`. With host
networking, `ZENOH_ROUTER=auto` starts the router inside the first `crab_perf`
instance, and everything else finds it. Containers on a bridge network must
also tell each node where the router is and listen on a reachable address.
Set the following on **every** instance:

```sh
ZENOH_CONFIG_OVERRIDE='connect/endpoints=["tcp/<router-host>:7447"];listen/endpoints=["tcp/0.0.0.0:0"]'
```

## Output

Every line from `crab_perf` starts with `[crab_perf]`. Lines prefixed with
`[perf_test:<role>]` are `perf_test`'s own start-up output.

```text
[crab_perf] start mode=local rmw=rmw_zenoh_cpp run_id=20261113-144510 msg=Array32 rate_hz=100 runtime_s=60 ...
[crab_perf] interval role=sub rmw=rmw_zenoh_cpp t=1.0002 recv=99 sent=0 lost=0 lat_mean_ms=0.3049 lat_min_ms=0.0688 lat_max_ms=0.6016 lat_std_ms=0.0971 cpu_pct=0.0625 maxrss_kb=22384
[crab_perf] interval role=pub rmw=rmw_zenoh_cpp t=1.0002 recv=0 sent=99 lost=0 cpu_pct=0.1250 maxrss_kb=22192
...
[crab_perf] summary role=sub mode=local rmw=rmw_zenoh_cpp run_id=... intervals=60 duration_s=60.0 recv=5940 sent=0 lost=0 lat_mean_ms=0.2810 lat_std_ms=0.0903 lat_min_ms=0.0374 lat_max_ms=0.6266 loss_pct=0.0000 recv_rate_hz=98.98 throughput_kbps=25.65 cpu_mean_pct=0.06 cpu_max_pct=0.12 maxrss_kb=22384
[crab_perf] csv_begin role=sub file=20261113-144510_local_sub_rmw_zenoh_cpp.csv
...raw perf_test CSV...
[crab_perf] csv_end role=sub
[crab_perf] done exit_code=0 log_dir=/tmp/crab_perf
```

- `interval` lines arrive once per second (`perf_test`) or every
  `PROBE_REPORT_PERIOD` (`state`). `summary` covers the whole run and is also
  printed when the instance is stopped early.
- `perf_test` only reports min, max, mean and variance for each one-second
  interval. The summary therefore pools these (a weighted mean and pooled
  standard deviation) and has no percentiles. `state` mode keeps every sample
  and reports p50, p90 and p99.
- `perf_test` writes its latency variance as s² × 1000. `crab_perf` converts it
  to ms before reporting `lat_std_ms`.
- The `pub` side's `sent` misses the last partial second, so use the `sub` (or
  `main`) side's `recv`/`lost` for loss.

Capturing a run:

```sh
cortex logs --follow > perf_zenoh.log                  # or: docker logs -f <container>
grep '\[crab_perf\] summary' perf_*.log                # one line per run/role
sed -n '/csv_begin role=sub/,/csv_end/p' perf_zenoh.log # raw perf_test CSV
```

## Running

```sh
just build                                  # from pkgs/crab_perf
cortex run --image crab-perf:dev            # set RMW / PERF_* on the instance
```

Or with Docker directly (build context is the Core repo root):

```sh
docker build -t crab-perf:dev -f pkgs/crab_perf/Dockerfile .
docker run --rm --network host -e RMW=fastdds -e PERF_RUNTIME=30 crab-perf:dev
docker run --rm --network host -e RMW=cyclone -e PERF_MODE=state -e PROBE_RATE=0.5 crab-perf:dev
```

The container stops with SIGINT. `crab_perf` passes it on to `perf_test`, and
still prints the summary and CSV.
