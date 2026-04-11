"""
Mock system module for local desktop testing.
Simulates WiFi scanning, connecting, container pulls, etc.
so every screen in the setup flow can be exercised on macOS/Linux desktop.
"""

import os
import threading
import time
from constants import DATA_CONFIG_DIR, WIFI_CONFIG_PATH, ROBOT_CONFIG_PATH, SETUP_DONE_FLAG


# ── WiFi (fake) ──────────────────────────────────────────────────────────────

def scan_networks():
    """Return fake networks after a short delay to mimic real scan."""
    time.sleep(1.5)
    return [
        ("MyHomeWiFi",        92),
        ("Neighbors_5G",      74),
        ("CoffeeShop-Free",   61),
        ("NETGEAR-2.4G",      45),
        ("xfinitywifi",       30),
    ]


def connect_wifi(ssid, password):
    """Simulate a successful WiFi connection."""
    time.sleep(2)
    return True, "Connected"


def verify_internet(host="8.8.8.8", timeout=5):
    time.sleep(0.5)
    return True


# ── Hostname ─────────────────────────────────────────────────────────────────

def set_hostname(name):
    safe = "".join(c for c in name.lower() if c.isalnum() or c == "-")
    safe = safe.strip("-") or "zaraos"
    print(f"[mock] set_hostname -> {safe}")
    return safe


# ── Robot config ─────────────────────────────────────────────────────────────

def write_robot_config(name):
    print(f"[mock] write_robot_config -> {name}")


# ── Container pulls (fake) ───────────────────────────────────────────────────

class PullJob:
    """Simulates pulling container images with realistic timing."""
    def __init__(self, images):
        self.images   = images
        self.total    = len(images)
        self.done     = 0
        self.current  = ""
        self.status   = "pending"   # pending | running | success | error
        self.error    = ""
        self._thread  = None

    def start(self):
        self.status  = "running"
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        for img in self.images:
            self.current = img
            time.sleep(2)           # simulate download time
            self.done += 1
        self.status = "success"

    @property
    def progress(self):
        if self.total == 0:
            return 1.0
        return self.done / self.total

    def is_done(self):
        return self.status in ("success", "error")


# ── Finalize ─────────────────────────────────────────────────────────────────

def finalize_setup():
    print("[mock] finalize_setup — skipping flag write on desktop")
