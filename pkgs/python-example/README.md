# python-example

Example ROS2 Python package with a simple hello world node.

## Structure

- `package.xml` - Package metadata and dependencies
- `setup.py` - Python package setup
- `setup.cfg` - Install configuration
- `pyproject.toml` - Modern Python packaging for uv
- `python_example/` - Python module (note underscore, not hyphen)
- `resources/` - Resource marker file

## Build with colcon

```bash
colcon build --packages-select python_example
```

## Run

```bash
source install/setup.bash
ros2 run python_example hello_world_node
```

## Using uv for Development

We use [uv](https://github.com/astral-sh/uv) for fast Python package management.

### Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Create virtual environment and install package

```bash
cd python-example
uv venv
source .venv/bin/activate
uv pip install -e .
```

### Install with dev dependencies

```bash
uv pip install -e ".[dev]"
```