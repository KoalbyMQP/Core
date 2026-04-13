"""FaceUI ROS2 node — subscribes to auth, instance, and error topics."""

import queue

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

from zaraos_interfaces.msg import (
    AuthCode,
    AuthStatus,
    InstanceState,
    SystemError,
)


class FaceUINode(Node):
    """ROS2 node for the Face UI — receives messages via subscriptions,
    pushes them into thread-safe queues for the Pygame main loop to drain."""

    def __init__(self):
        super().__init__("face_ui")

        self.auth_code_queue: queue.Queue = queue.Queue()
        self.auth_status_queue: queue.Queue = queue.Queue()
        self.instance_queue: queue.Queue = queue.Queue()
        self.error_queue: queue.Queue = queue.Queue()

        # Latched QoS for auth (get last value on subscribe)
        latched_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )

        self.create_subscription(AuthCode, "/zaraos/auth/code",
                                 self._on_auth_code, latched_qos)
        self.create_subscription(AuthStatus, "/zaraos/auth/status",
                                 self._on_auth_status, latched_qos)
        self.create_subscription(InstanceState, "/zaraos/instances/state",
                                 self._on_instance_state, 10)
        self.create_subscription(SystemError, "/zaraos/system/errors",
                                 self._on_system_error, 10)

        self.get_logger().info("Face UI node started")

    def _on_auth_code(self, msg: AuthCode):
        self.auth_code_queue.put({"code": msg.code, "expires_in": msg.expires_in})

    def _on_auth_status(self, msg: AuthStatus):
        self.auth_status_queue.put({"status": msg.status, "label": msg.label})

    def _on_instance_state(self, msg: InstanceState):
        self.instance_queue.put({
            "instance_id": msg.instance_id,
            "app": msg.app,
            "version": msg.version,
            "state": msg.state,
            "error": msg.error,
        })

    def _on_system_error(self, msg: SystemError):
        self.error_queue.put({
            "source": msg.source,
            "severity": msg.severity,
            "message": msg.message,
        })
