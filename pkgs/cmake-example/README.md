# cmake-example

Example ROS2 CMake/C++ package with a simple hello world node.

## Structure

- `CMakeLists.txt` - Build configuration
- `package.xml` - Package metadata and dependencies
- `include/cmake-example/` - Public headers
- `src/` - Source files

## Build

```bash
colcon build --packages-select cmake_example
```

## Run

```bash
source install/setup.bash
ros2 run cmake_example hello_world_node
```