FROM ros:humble

ENV SDL_AUDIODRIVER=dummy \
    XDG_RUNTIME_DIR=/tmp

WORKDIR /ros_ws
COPY pkgs /ros_ws/src/

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3-pygame \
        ros-humble-rmw-cyclonedds-cpp \
        ros-humble-cyclonedds && \
    rm -rf /var/lib/apt/lists/*

RUN /bin/bash -c "source /opt/ros/humble/setup.bash && \
    if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then rosdep init; fi && \
    rosdep update && \
    rosdep install --from-paths src --ignore-src -r -y && \
    colcon build --packages-up-to startup_wizard && \
    rm -rf build log"

ENTRYPOINT ["/bin/bash", "-c", \
    "source /opt/ros/humble/setup.bash && \
     source /ros_ws/install/setup.bash && \
     ros2 run startup_wizard startup_wizard_node"]
