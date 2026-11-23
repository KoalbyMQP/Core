"""Run performance_test for the crab_api motor interface and log the metrics.

Configured entirely through environment variables (see README.md) so it can
be started as a Cortex instance. Every metric line starts with "[crab_perf]"
and is written as key=value pairs, so a captured log can be grepped or parsed.
"""

import math
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field

from ament_index_python.packages import get_package_prefix

PREFIX = "[crab_perf]"

RMW_ALIASES = {
    "cyclone": "rmw_cyclonedds_cpp",
    "cyclonedds": "rmw_cyclonedds_cpp",
    "fastdds": "rmw_fastrtps_cpp",
    "fastrtps": "rmw_fastrtps_cpp",
    "zenoh": "rmw_zenoh_cpp",
}

# mode -> list of (role, perf_test arguments)
MODES = {
    # Publisher and subscriber as two processes in this container.
    "local": [
        ("sub", ["-p", "0", "-s", "1", "--expected-num-pubs", "1"]),
        ("pub", ["-p", "1", "-s", "0", "--expected-num-subs", "1"]),
    ],
    # One side each; run two instances to measure across containers.
    "sub": [("sub", ["-p", "0", "-s", "1", "--expected-num-pubs", "1"])],
    "pub": [("pub", ["-p", "1", "-s", "0", "--expected-num-subs", "1"])],
    # Round trip on a single clock; the relay echoes every sample back.
    "main": [("main", ["--roundtrip-mode", "Main"])],
    "relay": [("relay", ["--roundtrip-mode", "Relay"])],
}

ZENOH_ROUTER_PORT = 7447


def log(event: str, **fields) -> None:
    """Print one metric/event line."""
    parts = [PREFIX, event] + [f"{k}={_fmt(v)}" for k, v in fields.items()]
    print(" ".join(parts), flush=True)


def _fmt(value) -> str:
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return "nan"
        return f"{value:.4f}" if abs(value) < 1e5 else f"{value:.0f}"
    return str(value)


def env(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


def resolve_rmw() -> str:
    """Pick the RMW from $RMW (short alias) or $RMW_IMPLEMENTATION."""
    alias = os.environ.get("RMW", "").strip().lower()
    if alias:
        rmw = RMW_ALIASES.get(alias, alias)
    else:
        rmw = env("RMW_IMPLEMENTATION", "rmw_cyclonedds_cpp")
    if rmw not in RMW_ALIASES.values():
        log("warning", msg=f"untested_rmw_{rmw}")
    os.environ["RMW_IMPLEMENTATION"] = rmw
    return rmw


def port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def maybe_start_zenoh_router(rmw: str) -> subprocess.Popen | None:
    """rmw_zenoh needs a router for discovery; start one unless one runs."""
    if rmw != "rmw_zenoh_cpp":
        return None
    setting = env("ZENOH_ROUTER", "auto").lower()
    if setting == "off" or (setting == "auto" and port_open(ZENOH_ROUTER_PORT)):
        log("zenoh_router", status="external")
        return None
    log("zenoh_router", status="starting")
    router = subprocess.Popen(
        ["ros2", "run", "rmw_zenoh_cpp", "rmw_zenohd"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    for _ in range(50):
        if port_open(ZENOH_ROUTER_PORT):
            break
        time.sleep(0.1)
    else:
        log("warning", msg="zenoh_router_not_listening")
    return router


# perf_test's CSV writes its variance as s^2 * 1000 (the ns->ms conversion is
# applied once to a squared value), so multiply by 1000 more to get ms^2.
VARIANCE_TO_MS2 = 1000.0


@dataclass
class Summary:
    """Aggregates perf_test's per-interval rows into whole-run statistics."""

    role: str
    intervals: int = 0
    duration: float = 0.0
    received: int = 0
    sent: int = 0
    recv_duration: float = 0.0  # time covered by intervals that received
    sent_duration: float = 0.0  # time covered by intervals that sent
    lost: int = 0
    data_received: int = 0
    lat_min: float = math.inf
    lat_max: float = -math.inf
    lat_sum: float = 0.0      # sum of n * mean
    lat_sq_sum: float = 0.0   # sum of n * (variance + mean^2)
    cpu: list = field(default_factory=list)
    maxrss_kb: int = 0

    def add(self, row: dict) -> None:
        self.intervals += 1
        self.duration += row["T_loop"]
        recv = int(row["received"])
        self.received += recv
        self.sent += int(row["sent"])
        if recv:
            self.recv_duration += row["T_loop"]
        if row["sent"] > 0:
            self.sent_duration += row["T_loop"]
        self.lost += int(row["lost"])
        self.data_received += int(row["data_received"])
        if recv > 0:
            mean = row["latency_mean (ms)"]
            var = row["latency_variance (ms)"] * VARIANCE_TO_MS2
            self.lat_min = min(self.lat_min, row["latency_min (ms)"])
            self.lat_max = max(self.lat_max, row["latency_max (ms)"])
            self.lat_sum += recv * mean
            self.lat_sq_sum += recv * (var + mean * mean)
        cpu = row.get("cpu_usage (%)")
        if cpu is not None and not math.isnan(cpu):
            self.cpu.append(cpu)
        self.maxrss_kb = max(self.maxrss_kb, int(row.get("ru_maxrss", 0)))

    def fields(self) -> dict:
        out = {
            "intervals": self.intervals,
            "duration_s": self.duration,
            "recv": self.received,
            "sent": self.sent,
            "lost": self.lost,
        }
        if self.received:
            mean = self.lat_sum / self.received
            var = max(self.lat_sq_sum / self.received - mean * mean, 0.0)
            out.update(
                lat_mean_ms=mean,
                lat_std_ms=math.sqrt(var),
                lat_min_ms=self.lat_min,
                lat_max_ms=self.lat_max,
                loss_pct=100.0 * self.lost / (self.received + self.lost),
                recv_rate_hz=self.received / self.recv_duration,
                throughput_kbps=8 * self.data_received / 1000 / self.recv_duration,
            )
        if self.sent:
            out["sent_rate_hz"] = self.sent / self.sent_duration
        if self.cpu:
            out["cpu_mean_pct"] = sum(self.cpu) / len(self.cpu)
            out["cpu_max_pct"] = max(self.cpu)
        out["maxrss_kb"] = self.maxrss_kb
        return out


class CsvTail:
    """Reads rows from a perf_test CSV log as perf_test appends them."""

    START_MARKER = "---EXPERIMENT-START---"

    def __init__(self, path: str):
        self.path = path
        self.pos = 0
        self.header: list[str] | None = None
        self.seen_start = False
        self.skipped_warmup = False

    def read_rows(self) -> list[dict]:
        try:
            with open(self.path) as f:
                f.seek(self.pos)
                chunk = f.read()
        except FileNotFoundError:
            return []
        # Only consume complete lines.
        end = chunk.rfind("\n") + 1
        self.pos += len(chunk[:end].encode())
        rows = []
        for line in chunk[:end].splitlines():
            if not self.seen_start:
                self.seen_start = line.strip() == self.START_MARKER
                continue
            cells = [c.strip() for c in line.split(",")]
            if self.header is None:
                self.header = cells
                continue
            if len(cells) != len(self.header):
                continue
            if not self.skipped_warmup:
                # The first row covers start-up; its T_loop is meaningless.
                self.skipped_warmup = True
                continue
            row = {}
            for key, cell in zip(self.header, cells):
                try:
                    row[key] = float(cell)
                except ValueError:
                    row[key] = math.nan
            rows.append(row)
        return rows


def interval_fields(row: dict) -> dict:
    out = {
        "t": row["T_experiment"],
        "recv": int(row["received"]),
        "sent": int(row["sent"]),
        "lost": int(row["lost"]),
    }
    if row["received"] > 0:
        out.update(
            lat_mean_ms=row["latency_mean (ms)"],
            lat_min_ms=row["latency_min (ms)"],
            lat_max_ms=row["latency_max (ms)"],
            lat_std_ms=math.sqrt(
                max(row["latency_variance (ms)"], 0.0) * VARIANCE_TO_MS2
            ),
        )
    out["cpu_pct"] = row.get("cpu_usage (%)", math.nan)
    out["maxrss_kb"] = int(row.get("ru_maxrss", 0))
    return out


def forward_output(role: str, stream) -> None:
    """Echo a perf_test process's own output, prefixed with its role."""
    for line in stream:
        line = line.rstrip()
        if line:
            print(f"[perf_test:{role}] {line}", flush=True)


def build_command(perf_test: str, role_args: list[str], logfile: str,
                  runtime: int) -> list[str]:
    cmd = [
        perf_test,
        "-c", env("PERF_COMMUNICATOR", "rclcpp-single-threaded-executor"),
        "-m", env("PERF_MSG", "Array32"),
        "-t", env("PERF_TOPIC", "crab_perf_motor_move"),
        "-r", env("PERF_RATE", "100"),
        "--reliability", env("PERF_RELIABILITY", "RELIABLE"),
        "--durability", env("PERF_DURABILITY", "VOLATILE"),
        "--history", env("PERF_HISTORY", "KEEP_LAST"),
        "--history-depth", env("PERF_HISTORY_DEPTH", "10"),
        "--max-runtime", str(runtime),
        "--ignore", env("PERF_IGNORE", "0"),
        "--wait-for-matched-timeout", env("PERF_MATCH_TIMEOUT", "60"),
        "-l", logfile,
    ]
    cmd += role_args
    cmd += env("PERF_EXTRA_ARGS", "").split()
    return cmd


def main() -> None:
    rmw = resolve_rmw()
    mode = env("PERF_MODE", "local").lower()

    if mode == "state":
        # The service probe is a plain rclpy node with its own logging.
        state_probe = os.path.join(
            get_package_prefix("crab_perf"), "lib", "crab_perf", "state_probe"
        )
        maybe_start_zenoh_router(rmw)
        # exec so stop signals reach the probe directly and it can print
        # its summary; a zenoh router started above keeps running.
        os.execv(state_probe, [state_probe])

    if mode not in MODES:
        log("error", msg=f"unknown_PERF_MODE_{mode}",
            expected="|".join(list(MODES) + ["state"]))
        sys.exit(2)

    perf_test = os.path.join(
        get_package_prefix("performance_test"), "lib", "performance_test",
        "perf_test",
    )
    # A relay should outlive the main side, so by default it runs until stopped.
    runtime = int(env("PERF_RUNTIME", "0" if mode == "relay" else "60"))
    out_dir = env("PERF_LOG_DIR", "/tmp/crab_perf")
    os.makedirs(out_dir, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")

    log("start", mode=mode, rmw=rmw, run_id=run_id,
        msg=env("PERF_MSG", "Array32"), rate_hz=env("PERF_RATE", "100"),
        runtime_s=runtime, reliability=env("PERF_RELIABILITY", "RELIABLE"),
        history_depth=env("PERF_HISTORY_DEPTH", "10"),
        communicator=env("PERF_COMMUNICATOR", "rclcpp-single-threaded-executor"),
        domain=os.environ.get("ROS_DOMAIN_ID", "0"))

    router = maybe_start_zenoh_router(rmw)

    procs = []
    for role, role_args in MODES[mode]:
        logfile = os.path.join(out_dir, f"{run_id}_{mode}_{role}_{rmw}.csv")
        # In local mode give the subscriber slack so it sees the last samples.
        role_runtime = runtime + 2 if (mode == "local" and role == "sub"
                                       and runtime > 0) else runtime
        cmd = build_command(perf_test, role_args, logfile, role_runtime)
        print(f"{PREFIX} launch role={role} cmd: {' '.join(cmd)}", flush=True)
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            bufsize=1,
        )
        threading.Thread(target=forward_output, args=(role, proc.stdout),
                         daemon=True).start()
        procs.append((role, proc, CsvTail(logfile), Summary(role), logfile))
        if role == "sub":
            time.sleep(1.0)  # let the subscriber come up first

    stopping = False

    def stop(signum, _):
        nonlocal stopping
        if not stopping:
            stopping = True
            log("stop", signal=signal.Signals(signum).name)
            for _, proc, *_ in procs:
                if proc.poll() is None:
                    proc.send_signal(signal.SIGINT)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    def drain() -> None:
        for role, _, tail, summary, _ in procs:
            if role == "relay":
                tail.read_rows()  # the relay records no metrics
                continue
            for row in tail.read_rows():
                summary.add(row)
                log("interval", role=role, rmw=rmw, **interval_fields(row))

    while any(proc.poll() is None for _, proc, *_ in procs):
        drain()
        time.sleep(0.25)
    drain()

    exit_code = 0
    for role, proc, _, summary, logfile in procs:
        if proc.returncode not in (0, -signal.SIGINT):
            exit_code = 1
            log("error", role=role, msg="perf_test_failed",
                exit_code=proc.returncode)
        if role != "relay":
            log("summary", role=role, mode=mode, rmw=rmw, run_id=run_id,
                **summary.fields())

    if env("PERF_DUMP_CSV", "1") == "1":
        for role, _, _, _, logfile in procs:
            if os.path.exists(logfile):
                print(f"{PREFIX} csv_begin role={role} file="
                      f"{os.path.basename(logfile)}", flush=True)
                with open(logfile) as f:
                    sys.stdout.write(f.read())
                print(f"{PREFIX} csv_end role={role}", flush=True)

    if router:
        router.terminate()
    log("done", exit_code=exit_code, log_dir=out_dir)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
