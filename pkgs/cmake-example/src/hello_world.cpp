// Copyright 2026 <Jacob Molnia/anomalymotion>

#include <chrono>
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "cmake-example/hello_world.hpp"

using namespace std::chrono_literals;

namespace cmake_example
{

std::string HelloWorld::get_message()
{
  return "Hello World from CMake!";
}

class HelloWorldNode : public rclcpp::Node
{
public:
  HelloWorldNode()
  : Node("hello_world_node")
  {
    timer_ = this->create_wall_timer(
      1s, std::bind(&HelloWorldNode::timer_callback, this));
    RCLCPP_INFO(this->get_logger(), "Hello World Node started");
  }

private:
  void timer_callback()
  {
    HelloWorld hw;
    RCLCPP_INFO(this->get_logger(), "%s", hw.get_message().c_str());
  }

  rclcpp::TimerBase::SharedPtr timer_;
};

}  // namespace cmake_example

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<cmake_example::HelloWorldNode>());
  rclcpp::shutdown();
  return 0;
}
