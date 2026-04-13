"""
ROS2-backed system module for the ZaraOS startup wizard.

Same interface as system.py — screen code does `import system`
and this module gets injected via sys.modules before import.

WiFi scan/connect go through ROS2 services to the cortex_bridge.
Local operations (hostname, config files) remain direct.
"""

import os
import subprocess
import threading
import time

from startup_wizard.constants import (
    DATA_CONFIG_DIR, ROBOT_CONFIG_PATH, SETUP_DONE_FLAG, HOSTNAME_PATH,
)

# The node reference is set by main.py after initialization
_node = None


def set_node(node):
    """Set the ROS2 node reference. Called by main.py during startup."""
    global _node
    _node = node


# ── WiFi (via ROS2 services) ────────────────────────────────────────

def scan_networks():
    """Scan for WiFi networks via ROS2 service."""
    if _node is None:
        return []
    networks, success, error = _node.call_wifi_scan()
    if not success:
        return []
    return [(ssid, int(sig)) for ssid, sig in networks]


def connect_wifi(ssid, password):
    """Connect to WiFi via ROS2 service. Returns (ok, message)."""
    if _node is None:
        return False, "ROS2 node not available"
    return _node.call_wifi_connect(ssid, password)


def verify_internet(host="8.8.8.8", timeout=5):
    """Check internet connectivity (local operation)."""
    r = subprocess.run(
        f"ping -c 1 -W {timeout} {host}",
        shell=True, capture_output=True, text=True
    )
    return r.returncode == 0


# ── Hostname (local operation) ──────────────────────────────────────

def set_hostname(name):
    """Set system hostname (local operation, no ROS2 needed)."""
    safe = "".join(c for c in name.lower() if c.isalnum() or c == "-")
    safe = safe.strip("-") or "zaraos"
    subprocess.run(f"hostname {safe}", shell=True, capture_output=True, text=True)
    try:
        with open(HOSTNAME_PATH, "w") as f:
            f.write(safe + "\n")
    except OSError:
        pass
    return safe


# ── Robot config (local operation) ──────────────────────────────────

def write_robot_config(name):
    """Write robot config file (local operation)."""
    os.makedirs(DATA_CONFIG_DIR, exist_ok=True)
    with open(ROBOT_CONFIG_PATH, "w") as f:
        f.write(f"ROBOT_NAME={name}\n")


# ── Container pulls ─────────────────────────────────────────────────

class PullJob:
    """Pull container images — same interface as system.py PullJob."""
    def __init__(self, images):
        self.images   = images
        self.total    = len(images)
        self.done     = 0
        self.current  = ""
        self.status   = "pending"
        self.error    = ""
        self._thread  = None

    def start(self):
        self.status  = "running"
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        for img in self.images:
            self.current = img
            r = subprocess.run(
                ["nerdctl", "pull", img],
                capture_output=True, text=True
            )
            if r.returncode != 0:
                self.error  = f"Failed to pull {img}: {r.stderr.strip()}"
                self.status = "error"
                return
            self.done += 1
        self.status = "success"

    @property
    def progress(self):
        if self.total == 0:
            return 1.0
        return self.done / self.total

    def is_done(self):
        return self.status in ("success", "error")


# ── Finalize ────────────────────────────────────────────────────────

def finalize_setup():
    """Mark setup as complete."""
    os.makedirs(DATA_CONFIG_DIR, exist_ok=True)
    open(SETUP_DONE_FLAG, "w").close()
