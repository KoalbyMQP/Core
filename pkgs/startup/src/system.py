import os
import subprocess
import threading
import time
from constants import *


def _run(cmd, **kwargs):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kwargs)


# ── WiFi ──────────────────────────────────────────────────────────────────────

def scan_networks():
    """Return list of (ssid, signal_pct) sorted by signal strength."""
    _run("wpa_cli -i wlan0 scan")
    time.sleep(2)
    result = _run("wpa_cli -i wlan0 scan_results")
    networks = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        try:
            signal_dbm = int(parts[2])
            ssid = parts[4].strip()
            if not ssid:
                continue
            # Convert dBm to 0-100
            signal_pct = max(0, min(100, 2 * (signal_dbm + 100)))
            networks.append((ssid, signal_pct))
        except (ValueError, IndexError):
            continue
    # Deduplicate, keep strongest
    seen = {}
    for ssid, sig in networks:
        if ssid not in seen or sig > seen[ssid]:
            seen[ssid] = sig
    return sorted(seen.items(), key=lambda x: -x[1])


def connect_wifi(ssid, password):
    """Write wpa_supplicant config and bring up wlan0. Returns (ok, message)."""
    conf = f"""ctrl_interface=/var/run/wpa_supplicant
ap_scan=1
network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
"""
    os.makedirs(DATA_CONFIG_DIR, exist_ok=True)

    # Write persistent copy to /data
    with open(WIFI_CONFIG_PATH, "w") as f:
        f.write(f"SSID={ssid}\nPASSWORD={password}\n")

    # Write wpa_supplicant conf
    with open(WPA_CONF_PATH, "w") as f:
        f.write(conf)

    _run("killall wpa_supplicant 2>/dev/null || true")
    _run("rm -f /var/run/wpa_supplicant/wlan0")
    time.sleep(0.5)

    r = _run("wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant.conf")
    if r.returncode != 0:
        return False, f"wpa_supplicant failed: {r.stderr.strip()}"

    time.sleep(3)
    r = _run("udhcpc -i wlan0 -t 10 -T 3 -n")
    if r.returncode != 0:
        return False, "DHCP failed — check password"

    return True, "Connected"


def verify_internet(host="8.8.8.8", timeout=5):
    r = _run(f"ping -c 1 -W {timeout} {host}")
    return r.returncode == 0


# ── Hostname ──────────────────────────────────────────────────────────────────

def set_hostname(name):
    safe = "".join(c for c in name.lower() if c.isalnum() or c == "-")
    safe = safe.strip("-") or "zaraos"
    _run(f"hostname {safe}")
    try:
        with open(HOSTNAME_PATH, "w") as f:
            f.write(safe + "\n")
    except OSError:
        pass
    return safe


# ── Robot config ──────────────────────────────────────────────────────────────

def write_robot_config(name):
    os.makedirs(DATA_CONFIG_DIR, exist_ok=True)
    with open(ROBOT_CONFIG_PATH, "w") as f:
        f.write(f"ROBOT_NAME={name}\n")


# ── Container pulls ───────────────────────────────────────────────────────────

class PullJob:
    """
    Pulls a list of container images in sequence.
    Thread-safe status updates for the UI to poll.
    """
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
        base = self.done / self.total
        # Each image counts as one unit; we can't get sub-image progress from nerdctl easily
        return base

    def is_done(self):
        return self.status in ("success", "error")


# ── Finalize ──────────────────────────────────────────────────────────────────

def finalize_setup():
    os.makedirs(DATA_CONFIG_DIR, exist_ok=True)
    open(SETUP_DONE_FLAG, "w").close()