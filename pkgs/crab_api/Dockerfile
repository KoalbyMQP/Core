# Build from the Core repo root (crab_api depends on zaraos_interfaces):
#   docker build --platform linux/arm64 -t crab-api:dev -f pkgs/crab_api/Dockerfile .
FROM ros:humble

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3-pip \
    ros-humble-rmw-cyclonedds-cpp && \
    rm -rf /var/lib/apt/lists/*

# The Crab API is not a rosdep key, so install it from the release wheel directly.
RUN python3 -m pip install --no-cache-dir \
    https://github.com/KoalbyMQP/Urchin-Framework/releases/download/crab-api/crab_api-0.1.1-py3-none-any.whl

WORKDIR /ros_ws
COPY pkgs/zaraos_interfaces /ros_ws/src/zaraos_interfaces
COPY pkgs/crab_api /ros_ws/src/crab_api

RUN /bin/bash -c 'source /opt/ros/humble/setup.bash && \
    if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then rosdep init; fi && \
    rosdep update && \
    apt-get update && \
    rosdep install --from-paths src --ignore-src -r -y && \
    rm -rf /var/lib/apt/lists/* && \
    colcon build --packages-up-to crab_api && \
    rm -rf build log'

# Embedded manifest read by Cortex's POST /requirements/discover.
COPY pkgs/crab_api/zaraos.json /etc/zaraos/package.json

ENV ROS_DOMAIN_ID=42
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# Urchin is found by scanning USB serial ports. Set URCHIN_PORT
# (e.g. socket://10.0.2.2:5555) to use the QEMU simulator instead.
ENTRYPOINT ["/bin/bash", "-c", \
    "source /opt/ros/humble/setup.bash && \
     source /ros_ws/install/setup.bash && \
     exec ros2 run crab_api crab_node"]
