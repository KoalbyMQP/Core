# python-example

Example ROS 2 Python package with a simple hello world node.

## Structure

- `package.xml` - Package metadata and dependencies
- `setup.py` - Python package setup
- `setup.cfg` - Install configuration
- `pyproject.toml` - Modern Python packaging for uv
- `python_example/` - Python module (note underscore, not hyphen)
- `resources/` - Resource marker file

## Developer workflow

Standard steps are documented in the [MQP dev guide](https://github.com/KoalbyMQP/ZaraOS/wiki).

Quick reference using `just` from this directory:

| Command | What it does |
|---|---|
| `just build` | Builds a local container image tagged `python-example:dev` |
| `just run` | Starts the image on the local Cortex server, saves the instance ID |
| `just logs` | Streams live logs from the running instance |
| `just stop` | Stops the running instance |
| `just deploy` | Runs the latest registry image (no local build) |

## CI / releases

The Jenkinsfile runs on every push. On a version tag (`vX.Y.Z`) it additionally:

1. Builds a Python wheel and source distribution, archives them as Jenkins artifacts.
2. Creates a colcon install tarball.
3. Creates a GitHub release in `KoalbyMQP/Core` titled **Python Example vX.Y.Z** and attaches the wheel and tarball.
4. Builds and pushes `koalbymqp/python-example:<tag>` to Docker Hub.

> The release title format `Python Example <tag>` is required — the Cortex registry parser uses it to match releases to the correct app.

## Using uv for local development

```bash
cd python-example
uv venv
uv pip install -e ".[dev]"
uv run ...
```
