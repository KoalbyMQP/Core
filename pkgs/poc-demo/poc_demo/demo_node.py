import time

import rclpy
from Crab import Crab, TicketType
from HerkuleX import HerkuleX, JogLedColor
from rclpy.node import Node


class DemoNode(Node):
    def __init__(self):
        super().__init__("poc_demo_node")
        self.timer = self.create_timer(1.0, self.timer_callback)
        self.get_logger().info("Demo node started")

        # Get bridge file
        # package_path = roslib.packages.get_pkg_dir("poc_status")
        # bridge_file = os.path.join(package_path, "bridge.toml")
        bridge_file = "bridge.toml"

        self.crab = Crab(bridge_file, True)

    def timer_callback(self):
        self.get_logger().info("timer_callback called")
        self.get_logger().info("Health check #1")
        self.crab.GetHealth("AckCheck")

        self.get_logger().info("Waiting for 3 seconds ...")
        time.sleep(3)

        self.get_logger().info("Moving shoulder")
        command = HerkuleX.MoveOne("Shoulder", float(-23), 40, JogLedColor.LED_BLUE)
        ticketNumber = self.crab.send(TicketType.Interrupt, [command], None, False)
        self.get_logger().info(f"Ticket #{ticketNumber} sent")

        # time.sleep(1)
        # print("\n\n\n\n\n\n")
        # command = HerkuleX.MoveOne("Shoulder", float(23), 40, JogLedColor.LED_RED)
        # ticket = self.crab.send(TicketType.Asynchronous, [command], None, False)
        # print("Main:ticket" + str(ticket))

        # self.get_logger().info("Health check #2")
        # self.crab.GetHealth("AckCheck")


def main() -> None:
    rclpy.init()
    node = DemoNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    # cProfile.run("main()")
    main()
