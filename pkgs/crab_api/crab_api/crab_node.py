"""ROS interface to the Urchin motor controller via the Crab API."""

import os
import queue
import threading
import time

import rclpy
from ament_index_python.packages import get_package_share_directory
from Crab import Crab, TicketType
from HerkuleX import HerkuleX, HerkuleXCommandNames, JogLedColor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from Types import Item
from zaraos_interfaces.msg import MotorMove
from zaraos_interfaces.srv import GetMotorState

# HerkuleX.MoveOne takes its play time in firmware ticks rather than
# milliseconds, and rejects anything over 500 ms.
TICK_SECONDS = 0.0112

# Urchin reports GetAngle results on its debug stream as "RawTicket:<deg>".
ANGLE_PREFIX = "RawTicket:"


class CrabNode(Node):
    """Forwards /motor/move to Urchin and serves /motor/state."""

    def __init__(self):
        super().__init__("crab")

        default_bridge = os.path.join(
            get_package_share_directory("crab_api"), "bridge.toml"
        )
        bridge_file = self.declare_parameter("bridge_file", default_bridge).value
        self.angle_timeout = self.declare_parameter("angle_timeout", 0.5).value

        self.get_logger().info(f"Loading bridge file {bridge_file}")
        self.crab = Crab(bridge_file)
        # Crab is not thread-safe: each request blocks on a shared reply
        # queue. Held per request, so moves can slip in between joint reads.
        self.crab_lock = threading.Lock()
        self.joints = [m.Joint.decode() for m in self.crab.bridge.Motors]
        self.get_logger().info(f"Connected motors: {', '.join(self.joints)}")

        # Separate groups so a slow angle read does not hold up moves.
        self.create_subscription(
            MotorMove,
            "/motor/move",
            self.move_callback,
            10,
            callback_group=MutuallyExclusiveCallbackGroup(),
        )
        self.create_service(
            GetMotorState,
            "/motor/state",
            self.state_callback,
            callback_group=MutuallyExclusiveCallbackGroup(),
        )

    def move_callback(self, msg: MotorMove) -> None:
        """Send a MoveOne command for the requested joint."""
        self.get_logger().info(
            f"Received move: joint={msg.joint_name} "
            f"position={msg.position:.2f} deg time={msg.time:.3f} s"
        )

        if msg.joint_name not in self.joints:
            self.get_logger().error(
                f'Unknown joint "{msg.joint_name}", '
                f"expected one of: {', '.join(self.joints)}"
            )
            return

        try:
            command = HerkuleX.MoveOne(
                msg.joint_name,
                float(msg.position),
                round(msg.time / TICK_SECONDS),
                JogLedColor.LED_BLUE,
            )
        except ValueError as e:
            self.get_logger().error(f"Rejected move: {e}")
            return

        with self.crab_lock:
            ticket = self.crab.send(TicketType.Interrupt, [command], None, False)
        if ticket < 0:
            self.get_logger().error("Urchin has no free ticket for move")
        else:
            self.get_logger().info(f"Move sent as ticket #{ticket}")

    def read_angle(self, joint: str) -> float | None:
        """Ask Urchin for a joint's angle in degrees, or None on timeout."""
        # Discard stale debug output so the next angle line is ours.
        while not self.crab.Debug.empty():
            self.crab.Debug.get_nowait()

        # HerkuleX.GetAngle builds its Item without the required values
        # argument, so construct the command directly.
        command = Item(joint, HerkuleXCommandNames.GetAngle, [])
        if self.crab.send(TicketType.Interrupt, [command], None, False) < 0:
            return None

        deadline = time.monotonic() + self.angle_timeout
        while (remaining := deadline - time.monotonic()) > 0:
            try:
                data = self.crab.Debug.get(timeout=remaining)
            except queue.Empty:
                break
            line = bytes(data).decode("utf-8", errors="ignore").rstrip("\x00")
            if line.startswith(ANGLE_PREFIX):
                return float(line[len(ANGLE_PREFIX) :])
        return None

    def state_callback(
        self, request: GetMotorState.Request, response: GetMotorState.Response
    ) -> GetMotorState.Response:
        """Read the requested joint's angle from Urchin."""
        self.get_logger().info(f"Received state: joint={request.joint_name}")

        joint = request.joint_name
        if joint not in self.joints:
            response.success = False
            response.message = (
                f'Unknown joint "{joint}", expected one of: {", ".join(self.joints)}'
            )
            self.get_logger().error(response.message)
            return response

        with self.crab_lock:
            angle = self.read_angle(joint)
        if angle is None:
            response.success = False
            response.message = f"No angle reported for {joint}"
            self.get_logger().warn(response.message)
            return response

        response.success = True
        response.position = angle
        self.get_logger().info(f"Reported state: {joint}={angle:.2f} deg")
        return response

    def destroy_node(self) -> None:
        """Stop the Crab serial thread before tearing down the node."""
        self.crab.close()
        super().destroy_node()


def main(args=None) -> None:
    """Run the crab node."""
    rclpy.init(args=args)
    node = CrabNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        # Let in-flight Crab requests finish before closing the serial
        # reader they are waiting on.
        executor.shutdown()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
