"""
Message protocol for the setup-time Bluetooth (BLE) service.

Must match the Driver Station client (ZaraOS-DriverStation
apps/driver-station/lib/ble-get-ip.ts and ble-uuid.ts):

  - Requests are UTF-8 text written to the characteristic, possibly split
    across several writes, and terminated by a NUL byte, e.g. "get-ip\\0".
  - Responses are sent as notifications: "<status>,<payload>\\0", where
    status "0" means success and "1" means error, split into chunks of at
    most CHUNK_SIZE bytes.

Kept free of D-Bus/BlueZ imports so it can be unit tested anywhere.
"""

import fcntl
import os
import socket
import struct

SERVICE_UUID = "a3fbe4df-f5a7-4daf-93f5-463222da42af"
CHARACTERISTIC_UUID = "e88352cb-896c-40a9-a8ea-2626dbc540b8"
CHUNK_SIZE = 250

# Interfaces checked first, in order, when reporting the robot's IP.
PREFERRED_INTERFACES = ("wlan0", "eth0")
# Container/virtual interfaces that are never the robot's reachable address.
IGNORED_INTERFACE_PREFIXES = ("lo", "docker", "veth", "cni", "br-", "nerdctl", "virbr", "flannel")

_SIOCGIFADDR = 0x8915


def split_messages(buffer):
    """Split accumulated text into complete NUL-terminated messages.

    Returns (messages, remainder): the remainder is any trailing partial
    message to keep buffering until its terminator arrives.
    """
    *messages, remainder = buffer.split("\0")
    return [m for m in messages if m], remainder


def format_response(ok, payload):
    """Encode a response as the list of notification chunks to send."""
    data = f"{0 if ok else 1},{payload}\0".encode("utf-8")
    return [data[i:i + CHUNK_SIZE] for i in range(0, len(data), CHUNK_SIZE)]


def pick_ip(addresses):
    """Choose the address the Driver Station should connect to.

    `addresses` maps interface name -> IPv4 address. Prefers WiFi, then
    Ethernet, then any other non-virtual interface. Returns None if none.
    """
    for name in PREFERRED_INTERFACES:
        if addresses.get(name):
            return addresses[name]
    for name in sorted(addresses):
        if addresses[name] and not name.startswith(IGNORED_INTERFACE_PREFIXES):
            return addresses[name]
    return None


def interface_addresses():
    """Return {interface name: IPv4 address} for interfaces that have one."""
    addresses = {}
    try:
        names = os.listdir("/sys/class/net")
    except OSError:
        return addresses
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for name in names:
            try:
                packed = fcntl.ioctl(sock.fileno(), _SIOCGIFADDR,
                                     struct.pack("256s", name[:15].encode()))
            except OSError:
                continue  # interface is down or has no IPv4 address
            addresses[name] = socket.inet_ntoa(packed[20:24])
    return addresses


def handle_command(command, get_addresses=interface_addresses):
    """Run one request and return (ok, payload)."""
    command = command.strip()
    if command == "get-ip":
        ip = pick_ip(get_addresses())
        if ip is None:
            return False, "No network connection"
        return True, ip
    return False, f"Unknown command: {command}"
