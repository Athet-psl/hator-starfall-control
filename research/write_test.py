"""First write test on the HATOR Starfall lighting report (feature report 10), approved by the user.

1. read the current frame; 2. write the same frame back; 3. brightness 0 for 5 s; 4. restore.
Each write is read back. Run as root.
"""

import fcntl
import os
import sys
import time
from pathlib import Path

REPORT, SIZE = 10, 41


def ioc(nr, size):
    return (3 << 30) | (size << 16) | (ord("H") << 8) | nr


def find_node():
    for hidraw in sorted(Path("/sys/class/hidraw").iterdir()):
        uevent = (hidraw / "device/uevent").read_text().upper()
        if "258A:0000002A" in uevent and len((hidraw / "device/report_descriptor").read_bytes()) > 100:
            return f"/dev/{hidraw.name}"
    sys.exit("keyboard vendor interface not found")


def get(fd):
    """The stable 4-byte lighting frame (reads right after a change can carry junk after byte 4)."""
    for _ in range(10):
        buf = bytearray(SIZE + 1)
        buf[0] = REPORT
        n = fcntl.ioctl(fd, ioc(0x07, len(buf)), buf, True)
        data = bytes(buf[1:n])
        if not any(data[4:]):
            return data[:4]
        time.sleep(0.2)
    sys.exit(f"no stable frame: {data.hex(' ')}")


def put(fd, frame):
    buf = bytearray(SIZE + 1)
    buf[0] = REPORT
    buf[1:1 + len(frame)] = frame
    fcntl.ioctl(fd, ioc(0x06, len(buf)), buf, True)
    time.sleep(0.3)
    back = get(fd)
    print(f"  wrote {frame.hex(' ')}, reads back {back.hex(' ')}", "OK" if back == frame else "DIFFERENT", flush=True)
    return back == frame


def main():
    fd = os.open(find_node(), os.O_RDWR)
    try:
        original = get(fd)
        print(f"current: {original.hex(' ')}", flush=True)
        print("1. same frame back", flush=True)
        if not put(fd, original):
            return
        time.sleep(2)
        print("2. brightness 0 for 5 s", flush=True)
        put(fd, original[:3] + b"\x00")
        time.sleep(5)
        print("3. restore", flush=True)
        put(fd, original)
    except OSError as err:
        print(f"write failed: {err}", flush=True)
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
