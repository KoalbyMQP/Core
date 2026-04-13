"""StartupWizard ROS2 node — service clients for WiFi, subscribers for errors."""

import queue
import threading

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

from zaraos_interfaces.msg import InstanceState, SystemError
from zaraos_interfaces.srv import WifiScan, WifiConnect


class StartupWizardNode(Node):
    """ROS2 node for the Startup Wizard — provides service clients
    for WiFi operations and subscribes to error/instance topics."""

    def __init__(self):
        super().__init__("startup_wizard")

        # Service clients for WiFi operations
        self.wifi_scan_client = self.create_client(WifiScan, "/zaraos/wifi/scan")
        self.wifi_connect_client = self.create_client(WifiConnect, "/zaraos/wifi/connect")

        # Queues for subscribers
        self.error_queue: queue.Queue = queue.Queue()
        self.instance_queue: queue.Queue = queue.Queue()

        self.create_subscription(SystemError, "/zaraos/system/errors",
                                 self._on_error, 10)
        self.create_subscription(InstanceState, "/zaraos/instances/state",
                                 self._on_instance_state, 10)

        self.get_logger().info("Startup wizard node started")

    def _on_error(self, msg: SystemError):
        self.error_queue.put({
            "source": msg.source,
            "severity": msg.severity,
            "message": msg.message,
        })

    def _on_instance_state(self, msg: InstanceState):
        self.instance_queue.put({
            "instance_id": msg.instance_id,
            "app": msg.app,
            "state": msg.state,
            "error": msg.error,
        })

    def call_wifi_scan(self) -> tuple[list, bool, str]:
        """Synchronous WiFi scan via ROS2 service. Returns (networks, success, error).
        networks is list of (ssid, signal_pct) tuples.

        Safe to call from a background thread — the future is resolved by the
        daemon spin thread, and we just block-wait on the Event here.
        """
        if not self.wifi_scan_client.wait_for_service(timeout_sec=5.0):
            return [], False, "WiFi scan service not available"

        request = WifiScan.Request()
        future = self.wifi_scan_client.call_async(request)

        # Block until the spin thread resolves the future (don't call spin here —
        # the main spin loop in the daemon thread handles callbacks).
        event = threading.Event()
        future.add_done_callback(lambda _: event.set())
        if not event.wait(timeout=15.0):
            return [], False, "WiFi scan timed out"

        if future.result() is None:
            return [], False, "WiFi scan failed"

        result = future.result()
        if not result.success:
            return [], False, result.error

        networks = list(zip(result.ssids, result.signal_strengths))
        return networks, True, ""

    def call_wifi_connect(self, ssid: str, password: str) -> tuple[bool, str]:
        """Synchronous WiFi connect via ROS2 service. Returns (success, message).

        Safe to call from a background thread — see call_wifi_scan docstring.
        """
        if not self.wifi_connect_client.wait_for_service(timeout_sec=5.0):
            return False, "WiFi connect service not available"

        request = WifiConnect.Request()
        request.ssid = ssid
        request.password = password
        future = self.wifi_connect_client.call_async(request)

        event = threading.Event()
        future.add_done_callback(lambda _: event.set())
        if not event.wait(timeout=30.0):
            return False, "WiFi connection timed out"

        if future.result() is None:
            return False, "WiFi connection failed"

        result = future.result()
        return result.success, result.message
