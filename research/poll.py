"""Read-only: poll the HATOR Starfall lighting report (feature report 10) and log every change.

Only GET_FEATURE requests. Run as root: poll.py SECONDS
"""

import fcntl
import os
import sys
import time
from pathlib import Path

REPORT, SIZE = 10, 41


def hidiocgfeature(size):
    return (3 << 30) | (size << 16) | (ord("H") << 8) | 0x07


def find_node():
    for hidraw in sorted(Path("/sys/class/hidraw").iterdir()):
        uevent = (hidraw / "device/uevent").read_text().upper()
        if "258A:0000002A" in uevent and len((hidraw / "device/report_descriptor").read_bytes()) > 100:
            return f"/dev/{hidraw.name}"
    sys.exit("keyboard vendor interface not found")


def main():
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 120
    fd = os.open(find_node(), os.O_RDWR)
    start = time.monotonic()
    last = None
    try:
        while time.monotonic() - start < seconds:
            buf = bytearray(SIZE + 1)
            buf[0] = REPORT
            try:
                n = fcntl.ioctl(fd, hidiocgfeature(len(buf)), buf, True)
                data = bytes(buf[1:n])
            except OSError as err:
                data = f"error {err}".encode()
            if data != last:
                trimmed = data.rstrip(b"\0") if isinstance(data, bytes) else data
                print(f"{time.strftime('%H:%M:%S')} +{time.monotonic() - start:6.1f}s  {trimmed.hex(' ')}", flush=True)
                last = data
            time.sleep(0.2)
    finally:
        os.close(fd)
    print("done", flush=True)


if __name__ == "__main__":
    main()
