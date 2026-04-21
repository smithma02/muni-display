"""
Python 3 stub for MicroPython's ntptime module.
Time is already correct on the host — settime() is a no-op.
"""

host = "pool.ntp.org"


def settime():
    """No-op: host system time is already accurate."""
    print("[stub] ntptime.settime() — using host system time")
