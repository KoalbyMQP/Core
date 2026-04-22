FROM ros:humble

WORKDIR /ros_ws
COPY pkgs /ros_ws/src/

RUN /bin/bash -c "source /opt/ros/humble/setup.bash && \
    if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then rosdep init; fi && \
    rosdep update && \
    rosdep install --from-paths src --ignore-src -r -y && \
    colcon build --packages-up-to cmake_example && \
    rm -rf build log"

ENTRYPOINT ["/bin/bash", "-c", \
    "source /opt/ros/humble/setup.bash && \
     source /ros_ws/install/setup.bash && \
     ros2 run cmake_example hello_world_node"]
