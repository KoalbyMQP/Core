"""
Setup-time Bluetooth (BLE) GATT server.

While the first-boot setup wizard runs, advertises the service the Driver
Station's "Find IP with Bluetooth" button looks for and answers its requests
(protocol in ble_protocol.py). The wizard only runs until setup is done, so
the robot stops being discoverable once it is set up: BlueZ drops our
advertisement and GATT service as soon as this process exits.

Talks to the host's bluetoothd over the system D-Bus, so the container needs
/run/dbus mounted. To test on a Linux machine with BlueZ:

    sudo python3 -m startup_wizard.ble_server
"""

import socket
import threading

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib

from startup_wizard import ble_protocol

BLUEZ = "org.bluez"
DBUS_OM_IFACE = "org.freedesktop.DBus.ObjectManager"
DBUS_PROP_IFACE = "org.freedesktop.DBus.Properties"
ADAPTER_IFACE = "org.bluez.Adapter1"
GATT_MANAGER_IFACE = "org.bluez.GattManager1"
GATT_SERVICE_IFACE = "org.bluez.GattService1"
GATT_CHRC_IFACE = "org.bluez.GattCharacteristic1"
LE_ADV_MANAGER_IFACE = "org.bluez.LEAdvertisingManager1"
LE_ADV_IFACE = "org.bluez.LEAdvertisement1"

APP_PATH = "/org/zaraos/setup"


def _log(msg):
    print(f"[startup_wizard] BLE: {msg}", flush=True)


class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = "org.freedesktop.DBus.Error.InvalidArgs"


class Application(dbus.service.Object):
    """Root object; BlueZ calls GetManagedObjects to discover our service."""

    def __init__(self, bus):
        self.path = dbus.ObjectPath(APP_PATH)
        super().__init__(bus, self.path)
        self.service = SetupService(bus, APP_PATH + "/service0")

    @dbus.service.method(DBUS_OM_IFACE, out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self):
        objects = {self.service.path: self.service.properties()}
        for chrc in self.service.characteristics:
            objects[chrc.path] = chrc.properties()
        return objects


class SetupService(dbus.service.Object):
    def __init__(self, bus, path):
        self.path = dbus.ObjectPath(path)
        super().__init__(bus, self.path)
        self.characteristics = [CommunicationCharacteristic(bus, path + "/char0", self)]

    def properties(self):
        return {
            GATT_SERVICE_IFACE: {
                "UUID": ble_protocol.SERVICE_UUID,
                "Primary": True,
                "Characteristics": dbus.Array([c.path for c in self.characteristics], signature="o"),
            }
        }


class CommunicationCharacteristic(dbus.service.Object):
    """Requests are written in; responses go back as notifications."""

    def __init__(self, bus, path, service):
        self.path = dbus.ObjectPath(path)
        super().__init__(bus, self.path)
        self.service = service
        self.notifying = False
        self.buffer = ""

    def properties(self):
        return {
            GATT_CHRC_IFACE: {
                "Service": self.service.path,
                "UUID": ble_protocol.CHARACTERISTIC_UUID,
                "Flags": dbus.Array(["write", "notify"], signature="s"),
            }
        }

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()
        return self.properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE, in_signature="aya{sv}")
    def WriteValue(self, value, options):
        self.buffer += bytes(value).decode("utf-8", errors="replace")
        messages, self.buffer = ble_protocol.split_messages(self.buffer)
        for message in messages:
            ok, payload = ble_protocol.handle_command(message)
            _log(f"{message!r} -> {'ok' if ok else 'error'}: {payload}")
            for chunk in ble_protocol.format_response(ok, payload):
                self._notify(chunk)

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        # The Driver Station subscribes right before each request, so this is
        # a good point to drop any partial message left by a previous client.
        self.notifying = True
        self.buffer = ""

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        self.notifying = False

    @dbus.service.signal(DBUS_PROP_IFACE, signature="sa{sv}as")
    def PropertiesChanged(self, interface, changed, invalidated):
        pass

    def _notify(self, chunk):
        if not self.notifying:
            return
        value = dbus.Array([dbus.Byte(b) for b in chunk], signature="y")
        self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])


class Advertisement(dbus.service.Object):
    """Advertises our service UUID so the Driver Station's scan filter finds us."""

    def __init__(self, bus, path):
        self.path = dbus.ObjectPath(path)
        super().__init__(bus, self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != LE_ADV_IFACE:
            raise InvalidArgsException()
        return {
            "Type": "peripheral",
            "ServiceUUIDs": dbus.Array([ble_protocol.SERVICE_UUID], signature="s"),
            # Name comes from the adapter alias, which _run sets to the hostname.
            "Includes": dbus.Array(["local-name"], signature="s"),
        }

    @dbus.service.method(LE_ADV_IFACE)
    def Release(self):
        _log("advertisement released by BlueZ")


def _find_adapter(bus):
    manager = dbus.Interface(bus.get_object(BLUEZ, "/"), DBUS_OM_IFACE)
    for path, interfaces in manager.GetManagedObjects().items():
        if GATT_MANAGER_IFACE in interfaces and LE_ADV_MANAGER_IFACE in interfaces:
            return path
    return None


def _run():
    try:
        dbus.mainloop.glib.threads_init()
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()

        adapter_path = _find_adapter(bus)
        if adapter_path is None:
            _log("no Bluetooth LE adapter found, not advertising")
            return

        name = socket.gethostname()
        adapter = bus.get_object(BLUEZ, adapter_path)
        adapter_props = dbus.Interface(adapter, DBUS_PROP_IFACE)
        adapter_props.Set(ADAPTER_IFACE, "Powered", dbus.Boolean(True))
        adapter_props.Set(ADAPTER_IFACE, "Alias", dbus.String(name))

        app = Application(bus)
        advertisement = Advertisement(bus, APP_PATH + "/advertisement0")

        dbus.Interface(adapter, GATT_MANAGER_IFACE).RegisterApplication(
            app.path, {},
            reply_handler=lambda: _log("GATT service registered"),
            error_handler=lambda e: _log(f"GATT service registration failed: {e}"),
        )
        dbus.Interface(adapter, LE_ADV_MANAGER_IFACE).RegisterAdvertisement(
            advertisement.path, {},
            reply_handler=lambda: _log(f"advertising as {name!r}"),
            error_handler=lambda e: _log(f"advertisement registration failed: {e}"),
        )

        GLib.MainLoop().run()
    except Exception as e:
        _log(f"stopped: {e}")


def start():
    """Advertise in a background thread for as long as this process runs.

    Never raises or blocks setup: without a Bluetooth adapter or system D-Bus
    (desktop testing, QEMU) it just logs and does nothing.
    """
    threading.Thread(target=_run, name="ble-server", daemon=True).start()


if __name__ == "__main__":
    _log("running standalone, Ctrl+C to stop")
    _run()
