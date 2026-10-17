"""Write experiments approved by the user, then restore.

    experiment_ab.py try       A: ScrollLock acts as NumLock (keymap, report 9)
                               B: CM2 with keys 1-4 lit (mode 9 slot 0x0a + report 11)
    experiment_ab.py restore   factory keymap and the lighting frame saved by "try"
"""

import fcntl
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
FACTORY = HERE / "factory-readout.json"
SAVED = HERE / "before-experiment.json"
SCROLL_LOCK, NUM_LOCK = 0x47, 0x53
KEYS_1_TO_4 = (0x1E, 0x1F, 0x20, 0x21)


def ioc(nr, size):
    return (3 << 30) | (size << 16) | (ord("H") << 8) | nr


def node():
    for hidraw in sorted(Path("/sys/class/hidraw").iterdir()):
        if "258A:0000002A" in (hidraw / "device/uevent").read_text().upper() \
                and len((hidraw / "device/report_descriptor").read_bytes()) > 100:
            return f"/dev/{hidraw.name}"
    sys.exit("keyboard vendor interface not found")


def get(fd, report, size):
    buf = bytearray(size + 1)
    buf[0] = report
    n = fcntl.ioctl(fd, ioc(0x07, len(buf)), buf, True)
    return bytes(buf[1:n])


def put(fd, report, data):
    buf = bytearray([report]) + bytearray(data)
    fcntl.ioctl(fd, ioc(0x06, len(buf)), buf, True)
    time.sleep(0.3)


def lighting(fd):
    for _ in range(10):
        data = get(fd, 10, 41)
        if not any(data[4:]):
            return data[:4]
        time.sleep(0.2)
    sys.exit("no stable lighting frame")


def put_lighting(fd, frame):
    put(fd, 10, frame + bytes(41 - len(frame)))
    back = lighting(fd)
    print(f"  lighting {frame.hex(' ')} -> reads back {back.hex(' ')}", "OK" if back == frame else "DIFFERENT")


def put_keymap(fd, keymap):
    put(fd, 9, keymap)
    back = get(fd, 9, 504)
    print("  keymap reads back", "OK" if back == keymap else f"DIFFERENT ({sum(a != b for a, b in zip(back, keymap))} bytes)")


def factory_keymap():
    reads = json.loads(FACTORY.read_text())["reads"]
    return bytes.fromhex(next(r["data"] for r in reads if r["id"] == 9))[1:]


def try_both(fd):
    keymap = get(fd, 9, 504)
    frame = lighting(fd)
    SAVED.write_text(json.dumps({"lighting": frame.hex()}) + "\n")
    print(f"saved lighting {frame.hex(' ')}")
    entries = [keymap[i:i + 4] for i in range(0, 504, 4)]
    index = next(i for i, e in enumerate(entries) if e == bytes([0, 0, SCROLL_LOCK, 0]))
    print(f"A: ScrollLock is entry #{index}, remapping it to NumLock")
    remapped = bytearray(keymap)
    remapped[index * 4 + 2] = NUM_LOCK
    put_keymap(fd, bytes(remapped))

    lit = [i for i, e in enumerate(entries) if e[2] in KEYS_1_TO_4 and e[0] == e[1] == e[3] == 0]
    print(f"B: CM2 (mode 9, slot 0x0a), keys 1-4 are entries {lit}")
    put_lighting(fd, bytes([9, 0x0A]) + frame[2:4])
    cm = bytearray(126)
    for i in lit:
        cm[i] = 1
    try:
        put(fd, 11, cm)
        print("  report 11 written")
    except OSError as err:
        print(f"  report 11 write failed: {err}")
    print("  lighting now", lighting(fd).hex(" "))


def restore(fd):
    put_keymap(fd, factory_keymap())
    frame = bytes.fromhex(json.loads(SAVED.read_text())["lighting"])
    put_lighting(fd, frame)


def main():
    fd = os.open(node(), os.O_WRONLY)
    try:
        {"try": try_both, "restore": restore}[sys.argv[1]](fd)
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
