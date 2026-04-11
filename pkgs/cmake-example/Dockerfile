FROM koalbymqp/zaraos-dev:latest

WORKDIR /ros_ws/src/cmake-example
COPY . .

WORKDIR /ros_ws
RUN /bin/bash -c "source /opt/ros/humble/setup.bash && \
    rosdep update && \
    rosdep install --from-paths src --ignore-src -r -y && \
    colcon build --packages-select cmake_example"

ENTRYPOINT ["/bin/bash", "-c", \
    "source /opt/ros/humble/setup.bash && \
     source /ros_ws/install/setup.bash && \
     ros2 run cmake_example hello_world_node"]
