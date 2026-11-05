#!/usr/bin/env python3
"""Average the control_test -> crab -> motor-sim timings in a combined log.

Each test cycle runs from a "[control_test]: Publishing move:" line to the
next "[control_test]: Received state:" line; anything outside is ignored.

Usage: python3 control_test_timings.py 03_control_test.log
"""

import argparse
import re
import statistics

CHUNK_START = "[control_test]: Publishing move:"
CHUNK_END = "[control_test]: Received state:"
LINE = re.compile(r"^\[(\w+)\] \[([\d.]+)\] \[([\w-]+)\]: (.*)$")

# Event name -> (node, message prefix). The first matching line in a chunk wins.
EVENTS = {
    "publish_move": ("control_test", "Publishing move:"),
    "crab_recv_move": ("crab", "Received move:"),
    "request_state": ("control_test", "Requesting state:"),
    "crab_recv_state": ("crab", "Received state:"),
    "crab_sent_ticket": ("crab", "Move sent as ticket"),
    "sim_read_position": ("motor-sim", None),  # matched below
    "crab_reported_state": ("crab", "Reported state:"),
    "test_recv_state": ("control_test", "Received state:"),
}

# (label, start event, end event)
TIMINGS = [
    ("control_test publish move -> crab receive (ROS)",
     "publish_move", "crab_recv_move"),
    ("control_test request state -> crab receive (ROS)",
     "request_state", "crab_recv_state"),
    ("crab receive move -> crab send ticket (Crab API)",
     "crab_recv_move", "crab_sent_ticket"),
    ("crab send ticket -> motor-sim receive (serial)",
     "crab_sent_ticket", "sim_recv_move"),
    ("motor-sim return state -> crab receive (serial)",
     "sim_read_position", "crab_reported_state"),
    ("crab return state -> control_test receive (ROS)",
     "crab_reported_state", "test_recv_state"),
]


def parse_chunk(lines: list[str]) -> dict[str, float]:
    """Return the timestamp of each event found in one chunk."""
    events: dict[str, float] = {}
    for line in lines:
        m = LINE.match(line)
        if not m:
            continue
        _, stamp, node, text = m.groups()
        t = float(stamp)

        # motor-sim receiving the move: its first line after crab sends it.
        if (node == "motor-sim" and "crab_sent_ticket" in events
                and "sim_recv_move" not in events):
            events["sim_recv_move"] = t

        for name, (ev_node, prefix) in EVENTS.items():
            if name in events or node != ev_node:
                continue
            if name == "sim_read_position":
                if text.startswith("servo") and "read position" in text:
                    events[name] = t
            elif text.startswith(prefix):
                events[name] = t
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("log_file")
    args = parser.parse_args()

    chunks: list[list[str]] = []
    current: list[str] | None = None
    with open(args.log_file) as f:
        for line in f:
            if CHUNK_START in line:
                if current is not None:
                    print("warning: cycle with no 'Received state:' line; "
                          "keeping it anyway")
                    chunks.append(current)
                current = [line]
            elif current is not None:
                current.append(line)
                if CHUNK_END in line:
                    chunks.append(current)
                    current = None
    if current is not None:
        print("warning: last cycle has no 'Received state:' line; "
              "keeping it anyway")
        chunks.append(current)
    cycles = [parse_chunk(c) for c in chunks]

    samples: dict[str, list[float]] = {label: [] for label, _, _ in TIMINGS}
    for i, events in enumerate(cycles, 1):
        for label, start, end in TIMINGS:
            if start in events and end in events:
                samples[label].append((events[end] - events[start]) * 1000)
            else:
                missing = start if start not in events else end
                print(f"warning: cycle {i} has no '{missing}' event; "
                      f"skipping '{label}'")

    print(f"\n{args.log_file}: {len(cycles)} cycles\n")
    width = max(len(label) for label, _, _ in TIMINGS)
    print(f"{'Timing':<{width}}  {'n':>3}  {'mean ms':>9}  "
          f"{'min ms':>9}  {'max ms':>9}")
    print("-" * (width + 38))
    for label, _, _ in TIMINGS:
        vals = samples[label]
        if not vals:
            print(f"{label:<{width}}  {0:>3}  {'-':>9}  {'-':>9}  {'-':>9}")
            continue
        print(f"{label:<{width}}  {len(vals):>3}  "
              f"{statistics.mean(vals):>9.3f}  "
              f"{min(vals):>9.3f}  {max(vals):>9.3f}")


if __name__ == "__main__":
    main()
