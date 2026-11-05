#!/usr/bin/env python3
"""Sort a combined crab / control_test / motor-sim log by timestamp and chunk it.

Lines look like "[INFO] [1793740404.867410243] [control_test]: ...". Lines
without a timestamp (headers, tracebacks, stray prints) stay attached to the
timestamped line above them; any before the first timestamped line stay at the
top. Each "[control_test]: Publishing move:" line starts a new chunk, and the
startup lines before the first move are grouped by node.

Usage: python3 sort_control_test_log.py jumbled.log [-o sorted.log]
"""

import argparse
import re
import sys
from decimal import Decimal

LINE = re.compile(r"^\[\w+\] \[([\d.]+)\] \[([\w-]+)\]: ")
CHUNK_START = "[control_test]: Publishing move:"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("log_file")
    parser.add_argument("-o", "--output", help="write here instead of stdout")
    args = parser.parse_args()

    header: list[str] = []
    # (timestamp, node, [line, continuation lines...])
    entries: list[tuple[Decimal, str, list[str]]] = []
    with open(args.log_file) as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            m = LINE.match(line)
            if m:
                entries.append((Decimal(m.group(1)), m.group(2), [line]))
            elif entries:
                entries[-1][2].append(line)
            else:
                header.append(line)

    # Stable sort, so lines with equal timestamps keep their original order.
    entries.sort(key=lambda e: e[0])

    out: list[str] = header[:]
    started = False
    prev_node = None
    for _, node, lines in entries:
        is_start = CHUNK_START in lines[0]
        # Before the first move, separate each node's startup lines.
        new_group = is_start or (not started and node != prev_node)
        if new_group and out:
            out.append("")
        started = started or is_start
        prev_node = node
        out.extend(lines)

    text = "\n".join(out) + "\n"
    if args.output:
        with open(args.output, "w") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
