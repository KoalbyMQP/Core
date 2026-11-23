# Build from the Core repo root (crab_perf depends on zaraos_interfaces):
#   docker build --platform linux/arm64 -t crab-perf:dev -f pkgs/crab_perf/Dockerfile .
FROM ros:humble

# performance_test plus every RMW the benchmark can be pointed at.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ros-humble-performance-test \
    ros-humble-rmw-cyclonedds-cpp \
    ros-humble-rmw-fastrtps-cpp \
    ros-humble-rmw-zenoh-cpp && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /ros_ws
COPY pkgs/zaraos_interfaces /ros_ws/src/zaraos_interfaces
COPY pkgs/crab_perf /ros_ws/src/crab_perf

RUN /bin/bash -c 'source /opt/ros/humble/setup.bash && \
    if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then rosdep init; fi && \
    rosdep update && \
    apt-get update && \
    rosdep install --from-paths src --ignore-src -r -y && \
    rm -rf /var/lib/apt/lists/* && \
    colcon build --packages-up-to crab_perf && \
    rm -rf build log'

# Embedded manifest read by Cortex's POST /requirements/discover.
COPY pkgs/crab_perf/zaraos.json /etc/zaraos/package.json

ENV ROS_DOMAIN_ID=42
# Override the middleware with RMW=cyclone|fastdds|zenoh, which takes
# precedence over RMW_IMPLEMENTATION. See README.md for the PERF_* settings.
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ENV PERF_MODE=local

# The launcher forwards SIGINT to perf_test so it can print a summary.
STOPSIGNAL SIGINT

ENTRYPOINT ["/bin/bash", "-c", \
    "source /opt/ros/humble/setup.bash && \
     source /ros_ws/install/setup.bash && \
     exec /ros_ws/install/crab_perf/lib/crab_perf/crab_perf"]
