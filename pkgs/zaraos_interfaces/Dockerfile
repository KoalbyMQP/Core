FROM ros:humble

WORKDIR /ros_ws
COPY pkgs /ros_ws/src/

RUN /bin/bash -c "source /opt/ros/humble/setup.bash && \
    if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then rosdep init; fi && \
    rosdep update && \
    rosdep install --from-paths src --ignore-src -r -y && \
    colcon build --packages-up-to zaraos_interfaces && \
    rm -rf build log"

CMD ["/bin/bash", "-c", "source /opt/ros/humble/setup.bash && source /ros_ws/install/setup.bash && exec bash"]
