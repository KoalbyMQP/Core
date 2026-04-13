"""
ROS2 bridge node for the Cortex HTTP control plane.

Polls Cortex via localhost HTTP and publishes state changes
on ROS2 topics. Also serves WiFi scan/connect services for
the startup wizard.
"""

import subprocess
import time
import threading

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

from builtin_interfaces.msg import Time as TimeMsg

from zaraos_interfaces.msg import (
    AuthCode,
    AuthStatus,
    InstanceState,
    LogLine,
    SystemError,
)
from zaraos_interfaces.srv import WifiScan, WifiConnect

from cortex_bridge.cortex_client import CortexClient


def _now_stamp() -> TimeMsg:
    """Create a builtin_interfaces/Time from current time."""
    t = time.time()
    msg = TimeMsg()
    msg.sec = int(t)
    msg.nanosec = int((t % 1) * 1e9)
    return msg


class CortexBridgeNode(Node):
    """Bridges Cortex HTTP API to ROS2 topics and services."""

    def __init__(self):
        super().__init__("cortex_bridge")

        self.client = CortexClient()

        # -- QoS: reliable + transient local so late subscribers get last value --
        latched_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )

        # Publishers
        self.pub_auth_code = self.create_publisher(AuthCode, "/zaraos/auth/code", latched_qos)
        self.pub_auth_status = self.create_publisher(AuthStatus, "/zaraos/auth/status", latched_qos)
        self.pub_instance_state = self.create_publisher(InstanceState, "/zaraos/instances/state", 10)
        self.pub_system_error = self.create_publisher(SystemError, "/zaraos/system/errors", 10)

        # Service servers
        self.srv_wifi_scan = self.create_service(WifiScan, "/zaraos/wifi/scan", self._handle_wifi_scan)
        self.srv_wifi_connect = self.create_service(
            WifiConnect, "/zaraos/wifi/connect", self._handle_wifi_connect
        )

        # State tracking for diff-based publishing
        self._last_pending_code: str | None = None
        self._last_instances: dict[str, str] = {}  # id -> state
        self._last_event_time: str | None = None

        # Timers
        self.create_timer(1.0, self._poll_auth)
        self.create_timer(2.0, self._poll_instances)
        self.create_timer(3.0, self._poll_events)

        self.get_logger().info("Cortex bridge node started")

    # ── Auth polling ─────────────────────────────────────────────────

    def _poll_auth(self):
        """Poll for pending auth codes and publish changes."""
        pending = self.client.get_pending_code()

        if pending and "code" in pending:
            code = pending["code"]
            if code != self._last_pending_code:
                # New code generated
                self._last_pending_code = code
                msg = AuthCode()
                msg.code = code
                msg.expires_in = 120  # matches Cortex codeExpiry
                msg.stamp = _now_stamp()
                self.pub_auth_code.publish(msg)
                self.get_logger().info(f"Published auth code (expires in 120s)")
        elif self._last_pending_code is not None:
            # Code expired or was consumed
            self._last_pending_code = None
            # Check if it was paired (consumed) vs expired
            events = self.client.get_events(event_type="auth_paired", limit=1)
            if events:
                evt = events[0]
                msg = AuthStatus()
                msg.status = "paired"
                msg.label = evt.get("data", {}).get("label", "")
                msg.stamp = _now_stamp()
                self.pub_auth_status.publish(msg)
                self.get_logger().info(f"Published auth status: paired ({msg.label})")
            else:
                msg = AuthStatus()
                msg.status = "expired"
                msg.label = ""
                msg.stamp = _now_stamp()
                self.pub_auth_status.publish(msg)
                self.get_logger().info("Published auth status: expired")

    # ── Instance state polling ───────────────────────────────────────

    def _poll_instances(self):
        """Poll instance list, publish state changes."""
        instances = self.client.get_instances()
        current: dict[str, dict] = {}
        for inst in instances:
            iid = inst.get("id", "")
            current[iid] = inst

        # Detect changes
        for iid, inst in current.items():
            old_state = self._last_instances.get(iid)
            new_state = inst.get("state", "")
            if old_state != new_state:
                msg = InstanceState()
                msg.instance_id = iid
                msg.app = inst.get("app", "")
                msg.version = inst.get("version", "")
                msg.image = inst.get("image", "")
                msg.state = new_state
                msg.error = inst.get("error", "") or ""
                msg.stamp = _now_stamp()
                self.pub_instance_state.publish(msg)
                self.get_logger().info(
                    f"Instance {msg.app} ({iid}): {old_state or 'new'} -> {new_state}"
                )

        self._last_instances = {iid: inst.get("state", "") for iid, inst in current.items()}

    # ── Event polling (errors) ───────────────────────────────────────

    def _poll_events(self):
        """Poll for error events and publish as SystemError."""
        kwargs = {"limit": 10}
        if self._last_event_time:
            kwargs["since"] = self._last_event_time

        events = self.client.get_events(**kwargs)
        for evt in events:
            etype = evt.get("type", "")
            self._last_event_time = evt.get("timestamp", self._last_event_time)

            if etype == "instance_start_failed":
                data = evt.get("data", {})
                msg = SystemError()
                msg.source = "instance"
                msg.severity = "error"
                msg.message = (
                    f"Failed to start {data.get('app', 'unknown')}: "
                    f"{data.get('error', 'unknown error')}"
                )
                msg.stamp = _now_stamp()
                self.pub_system_error.publish(msg)
                self.get_logger().warn(f"System error: {msg.message}")

    # ── WiFi services ────────────────────────────────────────────────

    def _handle_wifi_scan(self, request, response):
        """Handle WiFi scan service request."""
        self.get_logger().info("WiFi scan requested")
        try:
            result = subprocess.run(
                "wpa_cli -i wlan0 scan", shell=True,
                capture_output=True, text=True, timeout=5
            )
            time.sleep(2)
            result = subprocess.run(
                "wpa_cli -i wlan0 scan_results", shell=True,
                capture_output=True, text=True, timeout=5
            )

            networks = []
            for line in result.stdout.splitlines()[1:]:
                parts = line.split("\t")
                if len(parts) < 5:
                    continue
                try:
                    signal_dbm = int(parts[2])
                    ssid = parts[4].strip()
                    if not ssid:
                        continue
                    signal_pct = max(0, min(100, 2 * (signal_dbm + 100)))
                    networks.append((ssid, signal_pct))
                except (ValueError, IndexError):
                    continue

            # Deduplicate, keep strongest
            seen: dict[str, int] = {}
            for ssid, sig in networks:
                if ssid not in seen or sig > seen[ssid]:
                    seen[ssid] = sig

            sorted_nets = sorted(seen.items(), key=lambda x: -x[1])
            response.ssids = [n[0] for n in sorted_nets]
            response.signal_strengths = [n[1] for n in sorted_nets]
            response.success = True
            response.error = ""
        except Exception as e:
            response.ssids = []
            response.signal_strengths = []
            response.success = False
            response.error = str(e)

        return response

    def _handle_wifi_connect(self, request, response):
        """Handle WiFi connect service request."""
        ssid = request.ssid
        password = request.password
        self.get_logger().info(f"WiFi connect requested: {ssid}")

        try:
            import os

            # Write wpa_supplicant config
            conf = f'''ctrl_interface=/var/run/wpa_supplicant
ap_scan=1
network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
'''
            data_config_dir = "/data/config"
            os.makedirs(data_config_dir, exist_ok=True)

            with open(f"{data_config_dir}/wifi.conf", "w") as f:
                f.write(f"SSID={ssid}\nPASSWORD={password}\n")

            with open("/etc/wpa_supplicant.conf", "w") as f:
                f.write(conf)

            subprocess.run("killall wpa_supplicant 2>/dev/null || true",
                           shell=True, capture_output=True, text=True)
            subprocess.run("rm -f /var/run/wpa_supplicant/wlan0",
                           shell=True, capture_output=True, text=True)
            time.sleep(0.5)

            r = subprocess.run(
                "wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant.conf",
                shell=True, capture_output=True, text=True
            )
            if r.returncode != 0:
                response.success = False
                response.message = f"wpa_supplicant failed: {r.stderr.strip()}"
                return response

            time.sleep(3)
            r = subprocess.run(
                "udhcpc -i wlan0 -t 10 -T 3 -n",
                shell=True, capture_output=True, text=True
            )
            if r.returncode != 0:
                response.success = False
                response.message = "DHCP failed — check password"
                return response

            # Verify internet
            r = subprocess.run(
                "ping -c 1 -W 5 8.8.8.8",
                shell=True, capture_output=True, text=True
            )
            if r.returncode != 0:
                response.success = False
                response.message = "Connected but no internet — check password"
                return response

            response.success = True
            response.message = "Connected"

        except Exception as e:
            response.success = False
            response.message = str(e)

            # Publish system error
            err_msg = SystemError()
            err_msg.source = "wifi"
            err_msg.severity = "error"
            err_msg.message = f"WiFi connection failed: {e}"
            err_msg.stamp = _now_stamp()
            self.pub_system_error.publish(err_msg)

        return response


def main(args=None):
    rclpy.init(args=args)
    node = CortexBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
