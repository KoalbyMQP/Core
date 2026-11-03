"""Exercise the /crab node with random moves and state reads."""

import random

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from zaraos_interfaces.msg import MotorMove
from zaraos_interfaces.srv import GetMotorState

JOINTS = ["Shoulder", "Hip", "Test"]
MOVE_PERIOD = 10.0
STATE_DELAY = 1.0

# The Crab API rejects moves longer than 44 firmware ticks (~0.498 s).
TIMES = [0.10, 0.20, 0.30, 0.40]
# MIN_TIME = 0.1
# MAX_TIME = 0.49


class ControlTestNode(Node):
    """Publishes a random /motor/move, then queries /motor/state."""

    def __init__(self):
        super().__init__("control_test")
        self.move_pub = self.create_publisher(MotorMove, "/motor/move", 10)
        self.state_client = self.create_client(GetMotorState, "/motor/state")
        self.state_timer = None
        self.create_timer(MOVE_PERIOD, self.send_move)

    def send_move(self) -> None:
        """Publish a random move and schedule a state read for its joint."""
        msg = MotorMove(
            joint_name=random.choice(JOINTS),
            position=random.uniform(-45.0, 45.0),
            time=random.choice(TIMES),
            # time=random.uniform(MIN_TIME, MAX_TIME),
        )
        self.get_logger().info(
            f"Publishing move: joint={msg.joint_name} "
            f"position={msg.position:.2f} deg time={msg.time:.3f} s"
        )
        self.move_pub.publish(msg)

        self.state_timer = self.create_timer(
                STATE_DELAY, lambda: self.request_state(msg.joint_name)
        )

    def request_state(self, joint: str) -> None:
        """Ask /crab for a joint's position (fires once)."""
        self.state_timer.cancel()
        self.destroy_timer(self.state_timer)
        self.state_timer = None

        if not self.state_client.service_is_ready():
            self.get_logger().warn("/motor/state service is not available")
            return

        self.get_logger().info(f"Requesting state: joint={joint}")
        future = self.state_client.call_async(
            GetMotorState.Request(joint_name=joint)
        )
        future.add_done_callback(lambda f: self.log_state(joint, f))

    def log_state(self, joint: str, future) -> None:
        """Log the /motor/state response."""
        response = future.result()
        if response.success:
            self.get_logger().info(
                f"Received state: joint={joint} position={response.position:.2f} deg"
            )
        else:
            self.get_logger().error(
                f"State request for {joint} failed: {response.message}"
            )


def main(args=None) -> None:
    """Run the control test node."""
    rclpy.init(args=args)
    node = ControlTestNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
