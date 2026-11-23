# Build from the Core repo root (control_test depends on zaraos_interfaces):
#   docker build --platform linux/arm64 -t control-test:dev -f pkgs/control_test/Dockerfile .
FROM ros:humble

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ros-humble-rmw-cyclonedds-cpp && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /ros_ws
COPY pkgs/zaraos_interfaces /ros_ws/src/zaraos_interfaces
COPY pkgs/control_test /ros_ws/src/control_test

RUN /bin/bash -c 'source /opt/ros/humble/setup.bash && \
    if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then rosdep init; fi && \
    rosdep update && \
    apt-get update && \
    rosdep install --from-paths src --ignore-src -r -y && \
    rm -rf /var/lib/apt/lists/* && \
    colcon build --packages-up-to control_test && \
    rm -rf build log'

# Embedded manifest read by Cortex's POST /requirements/discover.
COPY pkgs/control_test/zaraos.json /etc/zaraos/package.json

ENV ROS_DOMAIN_ID=42
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# As PID 1 the node ignores SIGTERM (no handler), so stop with SIGINT, which
# rclpy handles. The node is exec'd directly because `ros2 run` would be PID 1
# and does not forward the signal.
STOPSIGNAL SIGINT

ENTRYPOINT ["/bin/bash", "-c", \
    "source /opt/ros/humble/setup.bash && \
     source /ros_ws/install/setup.bash && \
     exec /ros_ws/install/control_test/lib/control_test/control_test_node"]
