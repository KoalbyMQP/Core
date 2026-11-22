# Crab API motor command latency: findings and proposals

_Measured 2026-10-28 against the Urchin firmware running in `urchin-sim` (QEMU), with
the HerkuleX motor emulator (`urchin-motor-sim`) attached to the motor bus._

## Summary

On today's stack, one motor command takes **about 1.45 s** from a `/motor/move`
publish until the move reaches the HerkuleX bus. That figure projects real hardware at
115200 baud. With the node's 1 Hz state polling running, it rises to **about 3.1 s**.
Reading back a single joint position takes **about 2.7 s**, and the link sustains only
**about 0.5 moves/s**.

Almost none of this is ROS or Python: DDS adds about 1 ms and the node about 3 ms.
Nearly all of it comes from the Urchin firmware and the Pi ↔ ESP32 protocol. The main
causes are:

1. **A 1 s blocking LED blink on every command** (about 70% of the latency).
2. **Debug traffic:** 21 of the 23 frames the ESP32 sends per move are debug messages.
3. **Fixed 1027-byte frames** for every message, inside a three-message ticket
   handshake.

The HerkuleX servos can take new commands every 11.2 ms (about 89 Hz). The current
stack is about **100× slower than the hardware allows**. The quick firmware fixes below
recover about 3.5× (measured). The protocol changes are needed to reach a 50–89 Hz
control loop, which balancing and walking will require.

## How it was measured

Everything was timestamped against one clock on one machine:

| Tool | What it records |
|---|---|
| UART0 proxy between the Crab API and the simulator | First- and last-byte time of every 1027-byte frame in both directions. It can optionally pace bytes at a real UART rate. |
| Crab API benchmark | Wraps `send_packet`, the reply-queue pop and the reader thread at runtime, without modifying the library. It times each phase of `Crab.send()` for isolated moves, a 10-move burst, a 3-joint ticket and GetAngle reads. |
| `urchin-motor-sim -v` | Arrival time of every packet on the HerkuleX bus (torque writes, `S_JOG`, `RAM_READ`). |
| ROS benchmarks | Raw DDS latency between two processes (1,000 messages at 100 Hz), and publish → `/crab` callback → motor bus with the real node. |

**QEMU does not model baud rate.** A 1027-byte frame crosses in about 1 ms instead of
89 ms. The proxy therefore paced both directions at 115200 baud (8N1) to project real
hardware. Unless a row says otherwise, the numbers below are from these paced runs.

Each bottleneck was confirmed by rebuilding the firmware in a scratch copy with only
that one cause removed (variants V1–V3 below) and measuring again.

## Where the time goes today

Measurements are from isolated moves on the current firmware, paced at 115200, with no
state polling (medians).

| Stage | Time | Notes |
|---|---:|---|
| `/motor/move` publish → `/crab` callback | 1 ms | Raw DDS: p50 0.21 ms, p99 0.66 ms, max 0.9 ms |
| `ros2 topic pub --once` (if used) | +710 ms | CLI process start and discovery. Not representative of a real publisher. |
| Node + Crab Python → first byte out | 3 ms | |
| `FormatTicket` frame, Pi → ESP32 | 89 ms | 1027 bytes at 115200 |
| Firmware handles `FormatTicket` | **~1,030 ms** | 1,000 ms is `LED()` → `vTaskDelay(1000)` |
| Exchange reply 1 (status), ESP32 → Pi | 89 ms | 4 bytes of payload in a 1027-byte frame |
| Exchange reply 2 (ticket number), ESP32 → Pi | 89 ms | |
| **`Crab.send()` returns** | **1.30 s** | Before the move has reached the servo |
| `LoadTicket` frame, Pi → ESP32 | 89 ms | `PunchTicket` follows, another 89 ms |
| Firmware → torque-on packet on the motor bus | ~25 ms | Upper bound; mostly QEMU's emulated receive timeout |
| Torque-on → `S_JOG` packet | 7–10 ms | `vTaskDelay(10)` after every servo write |
| **Publish → `S_JOG` on the motor bus** | **1.45 s** | **3.1 s** with 1 Hz state polling (1.5 s waiting for the lock) |
| Servo motion | play time | As commanded (224 ms in the tests). Physically about 0.16 s per 60°. |
| Completion or acknowledgement back to the Pi | — | **Doesn't exist.** Nothing reports that a move was applied or finished. |
| GetAngle read: request → result | **2.7 s** | 1.43 s to reach the servo, then 1.27 s for the result to come back behind debug frames |

Traffic per isolated move: **3 frames out, 23 frames back (21 of them debug), 26.7 KB
on the wire**, for roughly 130 bytes of useful payload. At 115200, the return direction
alone carries 2.05 s of data per move. That is why back-to-back moves top out at about
0.5 moves/s: a 10-move burst took 20.1 s.

## Bottlenecks and how each was confirmed

Paths below are relative to the Urchin-Framework repo.

### 1. A 1 s blocking LED blink on every command

`FormatTicket()` calls `LED()` (`Urchin_Firmware/src/Conversation/UnPacker.cpp:126`), and
that calls `Pulse()`, which does `vTaskDelay(1000)`
(`Urchin_Firmware/src/Global/GLOBAL.c:78`). This runs **inside the receive task**, so no
serial input is processed for a full second on every ticket.

**V1 (delay removed):**

| | Before | V1 |
|---|---:|---:|
| `send()` | 1.30 s | 0.31 s |
| Publish → motor bus | 1.43 s | 0.44 s |
| GetAngle read | 2.7 s | 1.8 s |

### 2. Debug traffic fills the link, and turning it off deadlocks the firmware

`-DDEBUG` is on in `Urchin_Firmware/platformio.ini:24`. Every move sends about 21 debug
frames of 1027 bytes each. The shipping task drains the whole debug queue
(`Urchin_Firmware/src/ESP_PI_Communication/Shipping.c:99`), so Exchange replies and angle
results wait behind it. In a burst, each reply waited behind 18 debug frames.

- **Angle results only travel as debug text.** The firmware sends the result as a
  `RawTicket:%lf` debug message (`UnPacker.cpp:352`). Reads therefore can't work
  without the debug stream.
- **Building without `DEBUG` deadlocks on the first command.** `PrintfToPI` still queues
  messages, using `xQueueSend(..., portMAX_DELAY)`
  (`Urchin_Firmware/src/ESP_PI_Communication/Coms.c:18`), but nothing drains the queue.
  Once its 16 slots fill, the receive task blocks forever.

**V2 (V1, plus debug prints made no-ops when `DEBUG` is off):**

| | V1 | V2 |
|---|---:|---:|
| 10-move burst | 19.2 s (0.5 moves/s) | 4.8 s (2.1 moves/s) |

Isolated latency barely changes (0.42 s publish → motor bus), because debug traffic
mainly hurts throughput and reads.

### 3. The shipping task runs every 100 ms

The task loop is `vTaskDelay(100)` and then send whatever is queued (`Shipping.c:37`).
Each reply waits up to 100 ms before it starts transmitting.

**V3 (V2, plus a 10 ms loop):** firmware-to-reply time 34 → 23 ms; publish → motor bus
0.41 s; burst 2.2 moves/s.

### 4. Fixed 1027-byte frames inside a three-message handshake

Every message on UART0 is a 1027-byte frame (`COMS_SIZE 1024`,
`Urchin_Firmware/src/ESP_PI_Communication/Coms.h:13`), whatever its content. A move
needs `FormatTicket` → two replies → `LoadTicket` → `PunchTicket`: five frames and one
full round trip.

After V3, about 90% of the remaining 0.41 s is these frames on the wire (5 × 89 ms),
so the firmware can't get below about 0.4 s per move without a protocol change.

### 5. Joints in one ticket are not moved together

Each item in a ticket is sent as its own `LoadTicket` frame (Crab `Crab.py:233`). Each
joint also gets its own torque-on and its own single-servo `S_JOG`.

Measured on a 3-joint ticket at 115200: the joints started at **+0, +97 and +187 ms**.
A 20-joint pose would take about 1.8 s to apply, with the joints starting at different
times.

The firmware also re-sends torque-on before every move (`UnPacker.cpp:300`) and sleeps
10 ms after every servo write (`Urchin_Firmware/src/Herkulex/Herkulex.cpp:1688`).

### 6. The Pi side serializes everything

- **Moves wait behind state polls.** The `/crab` node uses one lock for moves and state
  polls (`pkgs/crab_api/crab_api/crab_node.py:43`), because `Crab` isn't thread-safe.
  With 1 Hz polling, moves waited a median 1.5 s for the lock.
- **Crab's reply waits block forever.** `Crab._QueSmartPop` waits with no timeout
  (`Crab_API/src/Crab.py:47`), so a lost reply hangs the caller.
- **Every frame sent prints a 1 KB line.** `ESPSerial.send_packet` prints the whole
  buffer (`Crab_API/src/ESPSerial.py:102`), and `send()` prints `"got here"`. That's
  cheap here (well under 1 ms) but noisy.
- **The node's period parameter is strictly typed.** `state_publish_period` must be
  given as a float: `-p state_publish_period:=2` crashes the node.

## Hardware limits

| Limit | Value |
|---|---|
| HerkuleX control period | 11.2 ms, so about 89 Hz is the most useful update rate |
| DRS-0601 / 0602 speed | about 0.16 s per 60° at 14.8 V |
| HerkuleX bus | 115200 now; servos support up to about 0.667–1 Mbps |
| Synchronized `S_JOG` for 20 servos (88 bytes) | 7.6 ms at 115200, 0.9 ms at 1 Mbps |
| Reading 20 servo positions | about 5–15 ms at 1 Mbps (estimate; depends on each servo's reply delay) |
| ESP32 UART | up to about 5 Mbps; USB-serial bridges up to about 1–3 Mbps |

A full command-plus-feedback cycle for every joint at 50–89 Hz is within reach of the
hardware. Balance controllers often want 100 Hz – 1 kHz, so once the software is fixed,
the HerkuleX update period will be the limiting factor for control design.

## Proposed improvements

### Phase 1: firmware quick fixes (small diffs, measured gain)

| # | Change | Measured / expected gain |
|---|---|---|
| 1 | Make the status LED non-blocking (toggle it, or blink from a timer) | −1,000 ms per command (measured) |
| 2 | Make debug messages non-blocking (`xQueueSend` with timeout 0; drop when the queue is full) and off by default in control builds. Fixes the deadlock without `DEBUG`. | 4× burst throughput (measured) |
| 3 | Return GetAngle results (and other data) on the Exchange stream instead of as debug text | Reads stop depending on debug output; about −1.3 s per read |
| 4 | Have the shipping task block on its queues (or a task notification) instead of polling every 100 ms, and send replies before debug messages | About −20 ms per reply (measured with a 10 ms poll) |
| 5 | Stop sending torque-on before every move, replace `vTaskDelay(10)` after servo writes with `uart_wait_tx_done`, and move all joints in a ticket with **one multi-servo `S_JOG`** | −10–20 ms per joint; joints start together |

With 1, 2 and 4: about 0.41 s publish → motor bus and about 2.2 moves/s (measured, V3).

### Phase 2: a real-time protocol between the Pi and the ESP32

| # | Change | Why |
|---|---|---|
| 6 | **Variable-length framing** (length + COBS + CRC16) instead of fixed 1027-byte frames | A 20-joint target message is about 100 bytes instead of about 20 KB |
| 7 | **A one-way `SetTargets` message** (sequence number + target and play time for every joint). Keep tickets for scripted sequences. | Removes the handshake round trip from the control path |
| 8 | **Streamed state:** the ESP32 polls all servos at a fixed rate aligned to the 11.2 ms tick and pushes one compact `State` message (positions, status, sequence number of the last applied target) | Gives feedback without request/response, and acknowledges commands for free |
| 9 | **Faster links:** Pi ↔ ESP32 at 921600 – 2 Mbps (or the Pi's GPIO UART / SPI, skipping USB latency); HerkuleX bus at 0.667 – 1 Mbps | Frame times drop from 89 ms to below 1 ms |

**Projected cycle** (calculated, not measured):

| Step | Time |
|---|---:|
| `SetTargets` for 20 joints at 921600 | ~1 ms |
| ESP32 handling on real hardware | <1 ms |
| Synchronized `S_JOG` at 1 Mbps | ~1 ms |
| 20 position reads | ~5–15 ms |
| `State` message back | ~1 ms |
| **Total** | **about 10–20 ms, i.e. 50–89 Hz**, the HerkuleX ceiling |

### Phase 3: the ROS side

| # | Change |
|---|---|
| 10 | In the `/crab` node, publish streamed `State` messages and send `SetTargets` without a lock or polling timer. Add timeouts to all Crab reply waits. Use `sensor_msgs/JointState` for state and a single multi-joint command topic (keep-last-1 QoS) for targets. |
| 11 | Long-term, implement the bridge as a C++ **ros2_control** hardware interface (the standard path for legged robots) running in a real-time thread. Python's garbage collector and global interpreter lock add timing jitter a balance loop can't tolerate. ROS 2 itself is not a bottleneck: about 0.2 ms median between processes. |

## Caveats

- **The simulator can't evaluate links faster than about 115200.** When bytes arrive
  faster than real UART speed, QEMU's emulated UART receive path adds about 185–195 ms
  per frame. Faster link speeds have to be evaluated on real hardware.
- **The firmware processing times (~25 ms) are upper bounds.** In the paced runs they are
  mostly QEMU's emulated receive timeout. Confirm them on a real ESP32, for example by
  toggling a GPIO pin around each handler and watching it on a logic analyzer.
- **The 115200 projection doesn't include USB-serial latency** (typically 1–16 ms per
  transfer, depending on the adapter's latency timer).
- **V2/V3 couldn't measure reads,** because with `DEBUG` off GetAngle has no way to
  return its result (see bottleneck 2).

## Sources

- [HerkuleX DRS-0601 (RobotShop)](https://robotshop.com/products/herkulex-drs-0601-smart-robot-servo)
- [HerkuleX DRS-0601 (ServoDatabase)](https://servodatabase.com/servo/herkulex/drs-0601)
- [HerkuleX DRS-0602 (ServoDatabase)](https://servodatabase.com/servo/herkulex/drs-0602)
- [HerkuleX cookbook (mbed)](https://os.mbed.com/cookbook/HerkuleX)
