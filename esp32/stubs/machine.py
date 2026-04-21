"""
Python 3 stub for MicroPython's machine module.
Covers the subset used by the transit display firmware.
"""
import json
import os
import sys

# RTC memory is persisted in a local file so test_render.py behaves
# like a real deep-sleep wake cycle (state survives between test runs).
_RTC_FILE = os.path.join(os.path.dirname(__file__), '..', '.rtc_memory.json')


class RTC:
    def memory(self, data=None):
        if data is None:
            try:
                with open(_RTC_FILE, 'rb') as f:
                    return f.read()
            except FileNotFoundError:
                return b''
        with open(_RTC_FILE, 'wb') as f:
            f.write(data)


def deepsleep(ms):
    """Stub: print the sleep duration and exit instead of sleeping."""
    print(f"[stub] machine.deepsleep({ms} ms) — exiting test run")
    sys.exit(0)


def reset():
    print("[stub] machine.reset()")
    sys.exit(0)


class Pin:
    OUT = 1
    IN  = 0

    def __init__(self, num, mode=IN, value=None):
        self._num = num
        self._val = value or 0

    def __call__(self, v=None):
        if v is None:
            return self._val
        self._val = v

    def value(self, v=None):
        return self.__call__(v)


class SPI:
    def __init__(self, *args, **kwargs):
        pass

    def write(self, data):
        pass
