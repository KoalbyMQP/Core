import rclpy
import zara_commands as zc
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from zaraos_interfaces.msg import MotorMove


class JointMoverNode(Node):
    def __init__(self):
        super().__init__("joint_mover")
        self.move_pub = self.create_publisher(MotorMove, "/motor/move", 10)
        zc.command()(self.move_joint)
        # zc.control(min=0, max=100, default=50)(self.speed)

    def move_joint(self, joint_name: str, position: float):
        """
        Moves a specified joint to a specified position. Returns `{"joint": joint_name, "target": position}`
        """
        msg = MotorMove(
            joint_name=joint_name,
            position=float(position),
            time=0.5,
        )
        self.move_pub.publish(msg)
        return {"joint": joint_name, "target": position}


def main(args=None) -> None:
    """Run the control test node."""
    rclpy.init(args=args)
    node = JointMoverNode()
    zc.start("http")
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
