# cmake-example

Example ROS 2 CMake/C++ package with a simple hello world node.

## Structure

- `CMakeLists.txt` - Build configuration
- `package.xml` - Package metadata and dependencies
- `include/cmake-example/` - Public headers
- `src/` - Source files

## Developer workflow

Standard steps are documented in the [MQP dev guide](https://github.com/KoalbyMQP/ZaraOS/wiki).

Quick reference using `just` from this directory:

| Command | What it does |
|---|---|
| `just build` | Builds a local container image tagged `cmake-example:dev` |
| `just run` | Starts the image on the local Cortex server, saves the instance ID |
| `just logs` | Streams live logs from the running instance |
| `just stop` | Stops the running instance |
| `just deploy` | Runs the latest registry image (no local build) |

## CI / releases

The Jenkinsfile runs on every push. On a version tag (`vX.Y.Z`) it additionally:

1. Creates a colcon tarball and archives it as a Jenkins artifact.
2. Creates a GitHub release in `KoalbyMQP/Core` titled **CMake Example vX.Y.Z** and attaches the tarball.
3. Builds and pushes `koalbymqp/cmake-example:<tag>` to Docker Hub.

> The release title format `CMake Example <tag>` is required — the Cortex registry parser uses it to match releases to the correct app.
