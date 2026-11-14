from startup_wizard import ble_protocol as p


# ── Request framing ──────────────────────────────────────────────────────────

def test_split_single_message():
    assert p.split_messages("get-ip\0") == (["get-ip"], "")


def test_split_keeps_partial_message_buffered():
    messages, rest = p.split_messages("get")
    assert messages == []
    assert rest == "get"
    assert p.split_messages(rest + "-ip\0") == (["get-ip"], "")


def test_split_multiple_messages_and_ignores_empty():
    assert p.split_messages("a\0\0b\0c") == (["a", "b"], "c")


# ── Response encoding ────────────────────────────────────────────────────────

def test_format_success():
    assert p.format_response(True, "10.0.0.5") == [b"0,10.0.0.5\0"]


def test_format_error():
    assert p.format_response(False, "nope") == [b"1,nope\0"]


def test_format_chunks_long_payload():
    chunks = p.format_response(True, "x" * 600)
    assert [len(c) for c in chunks] == [250, 250, 103]
    assert b"".join(chunks) == b"0," + b"x" * 600 + b"\0"


def _driver_station_decode(chunks):
    """Mirror of the completion logic in the Driver Station's ble-get-ip.ts."""
    message, success = "", True
    for chunk in chunks:
        data = chunk.decode()
        if message == "" and "," in data:
            status, rest = data.split(",", 1)
            if status in ("0", "1"):
                success = status == "0"
                data = rest
        message += data
        if len(chunk) < p.CHUNK_SIZE or message.endswith("\0"):
            return success, message.rstrip("\0")
    raise AssertionError("Driver Station would still be waiting for more data")


def test_driver_station_reads_short_and_long_responses():
    for payload in ("192.168.1.23", "y" * 247, "y" * 248, "z" * 700):
        assert _driver_station_decode(p.format_response(True, payload)) == (True, payload)
    assert _driver_station_decode(p.format_response(False, "err")) == (False, "err")


# ── IP selection ─────────────────────────────────────────────────────────────

def test_prefers_wifi_then_ethernet():
    addrs = {"eth0": "10.0.0.2", "wlan0": "10.0.0.3", "lo": "127.0.0.1"}
    assert p.pick_ip(addrs) == "10.0.0.3"
    del addrs["wlan0"]
    assert p.pick_ip(addrs) == "10.0.0.2"


def test_ignores_loopback_and_container_interfaces():
    addrs = {"lo": "127.0.0.1", "docker0": "172.17.0.1", "veth1a2b": "172.17.0.2",
             "cni0": "10.4.0.1", "end0": "192.168.1.9"}
    assert p.pick_ip(addrs) == "192.168.1.9"


def test_no_usable_interface():
    assert p.pick_ip({"lo": "127.0.0.1", "docker0": "172.17.0.1"}) is None


# ── Commands ─────────────────────────────────────────────────────────────────

def test_get_ip_command():
    assert p.handle_command("get-ip", lambda: {"wlan0": "10.1.2.3"}) == (True, "10.1.2.3")


def test_get_ip_without_network():
    assert p.handle_command("get-ip", lambda: {"lo": "127.0.0.1"}) == (False, "No network connection")


def test_unknown_command():
    assert p.handle_command("reboot", dict) == (False, "Unknown command: reboot")


def test_interface_addresses_includes_loopback():
    # Runs against the real machine: loopback always has 127.0.0.1.
    assert p.interface_addresses().get("lo") == "127.0.0.1"
