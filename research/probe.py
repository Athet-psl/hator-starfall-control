"""Read-only probe of the HATOR Starfall (258a:002a) vendor channel.

Only GET_FEATURE (HIDIOCGFEATURE) requests: nothing is written to the keyboard.
Run as root; writes probe.json next to this script, owned by the invoking user.
"""

import fcntl
import json
import os
import sys
from pathlib import Path

REPORTS = {5: 5, 9: 504, 10: 41, 11: 126, 12: 1920}  # report id -> size from the descriptor
OUT = Path(__file__).with_name("probe.json")


def hidiocgfeature(size):
    return (3 << 30) | (size << 16) | (ord("H") << 8) | 0x07


def find_node():
    for hidraw in sorted(Path("/sys/class/hidraw").iterdir()):
        uevent = (hidraw / "device/uevent").read_text()
        descriptor = (hidraw / "device/report_descriptor").read_bytes()
        if "258A:0000002A" in uevent.upper() and len(descriptor) > 100:
            return f"/dev/{hidraw.name}", descriptor
    sys.exit("keyboard vendor interface not found")


def main():
    node, descriptor = find_node()
    result = {"node": node, "descriptor": descriptor.hex(), "reads": []}
    fd = os.open(node, os.O_RDWR)
    try:
        for attempt in range(2):
            for report_id, size in REPORTS.items():
                buf = bytearray(size + 1)
                buf[0] = report_id
                try:
                    n = fcntl.ioctl(fd, hidiocgfeature(len(buf)), buf, True)
                    entry = {"id": report_id, "attempt": attempt, "len": n, "data": bytes(buf[:n]).hex()}
                except OSError as err:
                    entry = {"id": report_id, "attempt": attempt, "error": str(err)}
                result["reads"].append(entry)
                print(report_id, entry.get("len", entry.get("error")))
    finally:
        os.close(fd)
    OUT.write_text(json.dumps(result, indent=1) + "\n")
    uid, gid = int(os.environ.get("SUDO_UID", 0)), int(os.environ.get("SUDO_GID", 0))
    if uid:
        os.chown(OUT, uid, gid)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
