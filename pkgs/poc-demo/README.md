# Proof-of-concept Demo App

This is a proof-of-concept app that demonstrates the full software stack:
- Driver station: starts the app and streams logs
- ZaraOS: actually runs the app
- Urchin: handles motor control

## Building container image

This app has two versions, one that is standalone Python, and one that uses ROS. The
standalone python version is intended to be used for the demo.

Build the standalone Python version for the Pi:

```sh
cd pkgs/poc-demo
docker buildx build \
    --platform linux/arm64 \
    -f Dockerfile-standalone \
    -t poc-demo-standalone:dev \
    --load .
```

Build the ROS version with (run from the root of the `Core` repo):

```sh
docker buildx build \
    --platform linux/arm64 \
    -f pkgs/poc-demo/Dockerfile-ros \
    -t poc-demo-ros:dev \
    --load .
```

