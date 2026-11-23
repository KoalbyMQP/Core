"""Time /motor/state round trips against the running /crab node.

performance_test only covers publish/subscribe, so this probe measures the
service side directly: request sent -> response received, on one clock.

Each request makes the crab node send a GetAngle ticket to Urchin, and the
firmware never frees tickets, so keep PROBE_RATE and PERF_RUNTIME modest.
"""

import math
import os
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from zaraos_interfaces.srv import GetMotorState

from crab_perf.run import env, log


def percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return math.nan
    k = (len(sorted_vals) - 1) * pct / 100
    lo, hi = math.floor(k), math.ceil(k)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def stats(rtts: list[float]) -> dict:
    if not rtts:
        return {}
    vals = sorted(rtts)
    mean = sum(vals) / len(vals)
    return {
        "rtt_mean_ms": mean,
        "rtt_std_ms": math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals)),
        "rtt_min_ms": vals[0],
        "rtt_p50_ms": percentile(vals, 50),
        "rtt_p90_ms": percentile(vals, 90),
        "rtt_p99_ms": percentile(vals, 99),
        "rtt_max_ms": vals[-1],
    }


class Counts:
    def __init__(self):
        self.sent = 0
        self.ok = 0
        self.failed = 0      # response with success=false
        self.timeouts = 0
        self.skipped = 0     # tick skipped because a request was in flight
        self.rtts: list[float] = []

    def fields(self) -> dict:
        return {
            "sent": self.sent,
            "responses": len(self.rtts),
            "ok": self.ok,
            "failed": self.failed,
            "timeouts": self.timeouts,
            "skipped": self.skipped,
            **stats(self.rtts),
        }


class StateProbe(Node):
    def __init__(self):
        super().__init__("crab_perf_state_probe")
        self.joint = env("PROBE_JOINT", "Shoulder")
        self.rate = float(env("PROBE_RATE", "1.0"))
        self.timeout = float(env("PROBE_TIMEOUT", "5.0"))
        self.runtime = float(env("PERF_RUNTIME", "60"))
        self.report_period = float(env("PROBE_REPORT_PERIOD", "10"))
        self.rmw = os.environ.get("RMW_IMPLEMENTATION", "")

        self.client = self.create_client(GetMotorState, "/motor/state")
        self.total = Counts()
        self.interval = Counts()
        self.pending: tuple[int, float] | None = None  # (request id, t_sent)
        self.next_id = 0
        self.start = 0.0  # set by begin()
        self.done = False

    def wait_for_service(self) -> bool:
        match_timeout = float(env("PERF_MATCH_TIMEOUT", "60"))
        t0 = time.perf_counter()
        if not self.client.wait_for_service(timeout_sec=match_timeout):
            log("error", msg="motor_state_service_not_found",
                timeout_s=match_timeout)
            return False
        log("discovered", service="/motor/state", rmw=self.rmw,
            discovery_ms=(time.perf_counter() - t0) * 1000)
        return True

    def begin(self) -> None:
        self.start = time.perf_counter()
        self.create_timer(1.0 / self.rate, self.tick)
        self.create_timer(self.report_period, self.report)

    def tick(self) -> None:
        now = time.perf_counter()
        if self.runtime > 0 and now - self.start >= self.runtime:
            self.done = True
            return

        if self.pending is not None:
            if now - self.pending[1] < self.timeout:
                self.total.skipped += 1
                self.interval.skipped += 1
                return
            # Give up on it; a late response is ignored by its id.
            self.total.timeouts += 1
            self.interval.timeouts += 1
            self.pending = None

        request_id = self.next_id
        self.next_id += 1
        self.pending = (request_id, time.perf_counter())
        self.total.sent += 1
        self.interval.sent += 1
        future = self.client.call_async(
            GetMotorState.Request(joint_name=self.joint)
        )
        future.add_done_callback(lambda f: self.on_response(request_id, f))

    def on_response(self, request_id: int, future) -> None:
        t_recv = time.perf_counter()
        if self.pending is None or self.pending[0] != request_id:
            return  # already counted as a timeout
        rtt_ms = (t_recv - self.pending[1]) * 1000
        self.pending = None
        response = future.result()
        for counts in (self.total, self.interval):
            counts.rtts.append(rtt_ms)
            if response is not None and response.success:
                counts.ok += 1
            else:
                counts.failed += 1

    def report(self) -> None:
        log("interval", role="state", rmw=self.rmw, joint=self.joint,
            t=time.perf_counter() - self.start, **self.interval.fields())
        self.interval = Counts()

    def summary(self) -> None:
        elapsed = time.perf_counter() - self.start
        log("summary", role="state", mode="state", rmw=self.rmw,
            joint=self.joint, rate_hz=self.rate, duration_s=elapsed,
            **self.total.fields())


def main(args=None) -> None:
    rclpy.init(args=args)
    node = StateProbe()
    log("start", mode="state", rmw=node.rmw, joint=node.joint,
        rate_hz=node.rate, runtime_s=node.runtime, timeout_s=node.timeout)
    code = 0
    try:
        if node.wait_for_service():
            node.begin()
            while rclpy.ok() and not node.done:
                rclpy.spin_once(node, timeout_sec=0.1)
        else:
            code = 1
    except (KeyboardInterrupt, ExternalShutdownException):
        log("stop", signal="SIGINT")
    finally:
        if node.start:
            node.summary()
        log("done", exit_code=code)
        node.destroy_node()
        rclpy.try_shutdown()
    raise SystemExit(code)


if __name__ == "__main__":
    main()
