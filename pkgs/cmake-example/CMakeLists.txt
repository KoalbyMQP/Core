# Copyright 2026 <Jacob Molnia/anomalymotion>

cmake_minimum_required(VERSION 3.8)
project(cmake_example)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)

# Include directories
include_directories(include)

# Create executable
add_executable(hello_world_node src/hello_world.cpp)
ament_target_dependencies(hello_world_node rclcpp)

# Install targets
install(TARGETS
  hello_world_node
  DESTINATION lib/${PROJECT_NAME})

# Install include directory
install(DIRECTORY include/
  DESTINATION include/)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()