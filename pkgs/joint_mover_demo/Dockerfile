# Build from the Core repo root:
#   docker build \
#       --platform linux/arm64 \
#       -t joint-mover-demo:dev \
#       -f pkgs/joint_mover_demo/Dockerfile .
#
# The UI stage runs on the build machine's own platform: its output is plain JS/CSS, so an
# arm64 image needs no emulation for it.

FROM --platform=$BUILDPLATFORM node:22-slim AS ui
WORKDIR /ui
COPY pkgs/joint_mover_demo/ui/package.json pkgs/joint_mover_demo/ui/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY pkgs/joint_mover_demo/ui/ ./
RUN npm run build

FROM ros:humble

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ros-humble-rmw-cyclonedds-cpp && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /ros_ws
COPY pkgs/zaraos_interfaces /ros_ws/src/zaraos_interfaces
COPY pkgs/joint_mover_demo /ros_ws/src/joint_mover_demo

RUN /bin/bash -c 'source /opt/ros/humble/setup.bash && \
    if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then rosdep init; fi && \
    rosdep update && \
    apt-get update && \
    rosdep install --from-paths src --ignore-src -r -y && \
    rm -rf /var/lib/apt/lists/* && \
    colcon build --packages-up-to joint_mover_demo && \
    rm -rf build log'

COPY pkgs/joint_mover_demo/zaraos.json /etc/zaraos/package.json
# Cortex reads the app's UI from this directory: zara-ui.json + the federation build.
COPY --from=ui /ui/dist /etc/zaraos/ui

ENV ROS_DOMAIN_ID=42
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# As PID 1 the node ignores SIGTERM (no handler), so stop with SIGINT, which
# rclpy handles. The node is exec'd directly because `ros2 run` would be PID 1
# and does not forward the signal.
STOPSIGNAL SIGINT

ENTRYPOINT ["/bin/bash", "-c", \
    "source /opt/ros/humble/setup.bash && \
     source /ros_ws/install/setup.bash && \
     exec /ros_ws/install/joint_mover_demo/lib/joint_mover_demo/joint_mover"]
