"""
Python 3 stub for MicroPython's network module.
Assumes the host machine is already connected to a network.
"""

STA_IF = 1


class WLAN:
    def __init__(self, interface=STA_IF):
        self._active = False

    def active(self, val=None):
        if val is not None:
            self._active = val
        return self._active

    def isconnected(self):
        return True   # assume host machine has network

    def connect(self, ssid, password):
        print(f"[stub] network.WLAN.connect({ssid!r}) — already connected on host")

    def disconnect(self):
        pass

    def ifconfig(self):
        return ('127.0.0.1', '255.0.0.0', '127.0.0.1', '8.8.8.8')
