"""The HATOR Starfall's vendor HID interface (Sino Wealth 258a:002a).

Worked out from the keyboard itself: HATOR's Windows app is for a different
chip. Interface 1 has these feature reports:

    10  lighting, 41 bytes: [mode, map, speed, brightness, 0 ...]
    9   keymap, 504 bytes: 126 matrix positions of [0, modifier bits, HID usage, 0],
        column by column (21 columns of 6 rows)

Both are read back with GET_FEATURE. The node is opened write-only: feature
reports work through such a handle, and the keystrokes that the same
interface sends stay unreadable.
"""

import fcntl
import os
import time
from pathlib import Path
from typing import NamedTuple

VENDOR, PRODUCT = 0x258A, 0x002A
LIGHTING, LIGHTING_SIZE = 10, 41
KEYMAP, KEYMAP_SIZE = 9, 504
COLUMNS, ROWS = 21, 6
POSITIONS = COLUMNS * ROWS

EFFECTS = range(1, 9)   # modes 1-8: the keyboard's own animations (Fn+ScrLk)
MAP_MODE = 9            # mode 9 lights a key map, chosen by the map byte:
PRESET_MAPS = range(1, 9)   # 1-8: the built-in maps M1-M8 (Fn+1...8)
CUSTOM_MAPS = (9, 10)       # CM1, CM2 (Fn+9, Fn+0), recorded on the keyboard with Fn+PrtSc
EFFECT_MAP = 10         # the map byte the keyboard keeps while an effect runs
SLOWEST = 4             # speed 0 is the fastest
BRIGHTEST = 5           # brightness 0 turns the lighting off

FACTORY_KEYMAP = bytes.fromhex(
    "000000000000350000002b000000390000020000000100000000290000001e00000014000000040000001d0000080000"
    "00003a0000001f0000001a000000160000001b000004000000003b000000200000000800000007000000060000000000"
    "00003c00000021000000150000000900000019000000000000003d00000022000000170000000a000000050000002c00"
    "00003e000000230000001c0000000b00000011000000000000003f00000024000000180000000d000000100000000000"
    "000040000000250000000c0000000e00000036000040000000004100000026000000120000000f00000037000000b000"
    "0000420000002700000013000000330000003800000065000000430000002d0000002f00000034000000000000000000"
    "0000440000002e00000030000000320000200000001000000000450000002a0000003100000028000000640000000000"
    "000046000000490000004c000000000000000000000050000000470000004a0000004d00000000000000520000005100"
    "0000480000004b0000004e00000000000000000000004f00000000000000530000005f0000005c000000590000006200"
    "00000000000054000000600000005d0000005a000000000000000000000055000000610000005e0000005b0000006300"
    "000000000000560000005700000000000000580000000000"
)


class Lighting(NamedTuple):
    mode: int
    map: int
    speed: int
    brightness: int

    @classmethod
    def parse(cls, frame):
        return cls(*frame[:4])

    def frame(self):
        return bytes(self) + bytes(LIGHTING_SIZE - 4)

    @property
    def is_map(self):
        return self.mode == MAP_MODE

    def with_effect(self, mode):
        return self._replace(mode=mode, map=EFFECT_MAP)

    def with_map(self, number):
        return self._replace(mode=MAP_MODE, map=number)


class Binding(NamedTuple):
    """What a matrix position sends: modifier bits and/or a HID keyboard usage.

    `kind` and `extra` are the entry's first and last bytes. They're always 0
    on this keyboard and are kept as read, so a keymap writes back unchanged.
    """

    mods: int = 0
    usage: int = 0
    kind: int = 0
    extra: int = 0

    @classmethod
    def parse(cls, entry):
        return cls(mods=entry[1], usage=entry[2], kind=entry[0], extra=entry[3])

    def entry(self):
        return bytes([self.kind, self.mods, self.usage, self.extra])

    @property
    def empty(self):
        return not (self.mods or self.usage or self.kind or self.extra)


def parse_keymap(data):
    return [Binding.parse(data[i:i + 4]) for i in range(0, KEYMAP_SIZE, 4)]


def encode_keymap(bindings):
    if len(bindings) != POSITIONS:
        raise ValueError(f"a keymap has {POSITIONS} positions, not {len(bindings)}")
    return b"".join(binding.entry() for binding in bindings)


FACTORY_BINDINGS = parse_keymap(FACTORY_KEYMAP)


def _ioc(nr, size):
    return (3 << 30) | (size << 16) | (ord("H") << 8) | nr


def find_node(sysfs=Path("/sys/class/hidraw")):
    """/dev/hidrawN of the keyboard's vendor interface, or None if it isn't connected."""
    wanted = f"{VENDOR:08X}:{PRODUCT:08X}"
    try:
        nodes = sorted(sysfs.iterdir())
    except OSError:
        return None
    for hidraw in nodes:
        try:
            uevent = (hidraw / "device/uevent").read_text().upper()
            descriptor = (hidraw / "device/report_descriptor").read_bytes()
        except OSError:
            continue
        if wanted in uevent and bytes([0x85, KEYMAP]) in descriptor:  # Report ID 9: the vendor interface
            return f"/dev/{hidraw.name}"
    return None


class Keyboard:
    """An open handle to the keyboard's vendor interface. Raises OSError when it's gone."""

    def __init__(self, node):
        self.node = node
        self.fd = os.open(node, os.O_WRONLY)

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _get(self, report, size):
        buf = bytearray(size + 1)
        buf[0] = report
        n = fcntl.ioctl(self.fd, _ioc(0x07, len(buf)), buf, True)
        return bytes(buf[1:n])

    def _set(self, report, data):
        buf = bytearray([report]) + bytearray(data)
        fcntl.ioctl(self.fd, _ioc(0x06, len(buf)), buf, True)

    def lighting(self):
        # Right after a change, or a keymap read, the report can carry leftovers after byte 4.
        for _ in range(10):
            frame = self._get(LIGHTING, LIGHTING_SIZE)
            if len(frame) >= 4 and not any(frame[4:]):
                return Lighting.parse(frame)
            time.sleep(0.05)
        return Lighting.parse(frame)

    def set_lighting(self, lighting):
        self._set(LIGHTING, lighting.frame())
        time.sleep(0.05)
        back = self.lighting()
        if back != lighting:
            raise OSError(f"the keyboard kept {tuple(back)} instead of {tuple(lighting)}")
        return back

    def keymap(self):
        data = self._get(KEYMAP, KEYMAP_SIZE)
        if len(data) != KEYMAP_SIZE:
            raise OSError(f"short keymap: {len(data)} bytes")
        return parse_keymap(data)

    def set_keymap(self, bindings):
        data = encode_keymap(bindings)
        self._set(KEYMAP, data)
        time.sleep(0.1)
        back = self.keymap()
        if encode_keymap(back) != data:
            raise OSError("the keymap didn't read back as written")
        return back
