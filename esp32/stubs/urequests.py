"""
Python 3 stub for MicroPython's urequests module.
Delegates to the `requests` library (already installed for the Pi version).
"""
import requests as _requests


class _Response:
    def __init__(self, resp):
        self._resp = resp
        self.text = resp.content.decode('utf-8-sig')

    def close(self):
        self._resp.close()


def get(url, timeout=15):
    resp = _requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return _Response(resp)
