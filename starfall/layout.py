"""Names of keys, the Starfall's physical layout, its lighting effects and preset maps."""

from .device import FACTORY_BINDINGS, Binding

# HID keyboard usages a key can send: usage -> (label, Linux key code)
USAGES = {
    **{0x04 + i: (chr(ord("A") + i), code) for i, code in enumerate(
        (30, 48, 46, 32, 18, 33, 34, 35, 23, 36, 37, 38, 50, 49, 24, 25, 16, 19, 31, 20, 22, 47, 17, 45, 21, 44))},
    **{0x1E + i: (str((i + 1) % 10), 2 + i) for i in range(10)},
    0x28: ("Enter", 28), 0x29: ("Esc", 1), 0x2A: ("Backspace", 14), 0x2B: ("Tab", 15), 0x2C: ("Space", 57),
    0x2D: ("-", 12), 0x2E: ("=", 13), 0x2F: ("[", 26), 0x30: ("]", 27), 0x31: ("\\", 43), 0x32: ("ISO #", None),
    0x33: (";", 39), 0x34: ("'", 40), 0x35: ("`", 41), 0x36: (",", 51), 0x37: (".", 52), 0x38: ("/", 53),
    0x39: ("Caps Lock", 58),
    **{0x3A + i: (f"F{i + 1}", code) for i, code in enumerate((59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 87, 88))},
    0x46: ("Print Screen", 99), 0x47: ("Scroll Lock", 70), 0x48: ("Pause", 119), 0x49: ("Insert", 110),
    0x4A: ("Home", 102), 0x4B: ("Page Up", 104), 0x4C: ("Delete", 111), 0x4D: ("End", 107),
    0x4E: ("Page Down", 109), 0x4F: ("Right", 106), 0x50: ("Left", 105), 0x51: ("Down", 108), 0x52: ("Up", 103),
    0x53: ("Num Lock", 69), 0x54: ("Num /", 98), 0x55: ("Num *", 55), 0x56: ("Num -", 74), 0x57: ("Num +", 78),
    0x58: ("Num Enter", 96),
    **{0x59 + i: (f"Num {(i + 1) % 10}", code) for i, code in enumerate((79, 80, 81, 75, 76, 77, 71, 72, 73, 82))},
    0x63: ("Num .", 83), 0x64: ("ISO \\", 86), 0x65: ("Menu", 127),
    **{0x68 + i: (f"F{13 + i}", 183 + i) for i in range(12)},
    0x7F: ("Mute", 113), 0x80: ("Volume Up", 115), 0x81: ("Volume Down", 114),
}
FN_USAGE = 0xB0  # what the matrix holds for Fn: the keyboard handles it itself

# Modifier bits -> (label, Linux key code)
MODIFIERS = {
    0x01: ("Left Ctrl", 29), 0x02: ("Left Shift", 42), 0x04: ("Left Alt", 56), 0x08: ("Left Win", 125),
    0x10: ("Right Ctrl", 97), 0x20: ("Right Shift", 54), 0x40: ("Right Alt", 100), 0x80: ("Right Win", 126),
}

GROUPS = [
    ("Letters", [0x04 + i for i in range(26)]),
    ("Digits", [0x1E + i for i in range(10)]),
    ("Symbols", [0x2D, 0x2E, 0x2F, 0x30, 0x31, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38]),
    ("Editing", [0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x39, 0x65]),
    ("Function keys", [0x3A + i for i in range(12)] + [0x68 + i for i in range(12)]),
    ("Navigation", [0x46, 0x47, 0x48, 0x49, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F, 0x50, 0x51, 0x52]),
    ("Numpad", [0x53, 0x54, 0x55, 0x56, 0x57, 0x58] + [0x59 + i for i in range(10)] + [0x63]),
    ("Volume", [0x7F, 0x80, 0x81]),
]


def binding_for_code(code):
    """The Binding that sends Linux key `code`, or None."""
    for bit, (_, mod_code) in MODIFIERS.items():
        if mod_code == code:
            return Binding(mods=bit)
    for usage, (_, usage_code) in USAGES.items():
        if usage_code == code:
            return Binding(usage=usage)
    return None


def describe(binding):
    """"Left Ctrl", "A", "Left Ctrl + A", "Fn", "Nothing" or a raw description."""
    if binding.empty:
        return "Nothing"
    if binding.kind or binding.extra:
        return "Code " + binding.entry().hex(" ")
    if binding.usage == FN_USAGE and not binding.mods:
        return "Fn"
    parts = [MODIFIERS[bit][0] for bit in MODIFIERS if binding.mods & bit]
    if binding.usage:
        parts.append(USAGES.get(binding.usage, (f"Usage 0x{binding.usage:02x}",))[0])
    return " + ".join(parts)


# Physical layout: (keycap label, factory binding, x, y, width, height) in key units.
_ROW_Y = (0, 1.25, 2.25, 3.25, 4.25, 5.25)


def _key(label, usage=0, mods=0, x=0.0, row=0, w=1.0, h=1.0):
    return label, Binding(mods=mods, usage=usage), x, _ROW_Y[row], w, h


def _run(labels, usages, x, row):
    return [_key(label, usage, x=x + i, row=row) for i, (label, usage) in enumerate(zip(labels, usages))]


KEYCAPS = [
    _key("Esc", 0x29, x=0, row=0),
    *_run(["F1", "F2", "F3", "F4"], range(0x3A, 0x3E), 2, 0),
    *_run(["F5", "F6", "F7", "F8"], range(0x3E, 0x42), 6.5, 0),
    *_run(["F9", "F10", "F11", "F12"], range(0x42, 0x46), 11, 0),
    *_run(["PrtSc", "ScrLk", "Pause"], (0x46, 0x47, 0x48), 15.25, 0),

    *_run(["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "="],
          (0x35, *range(0x1E, 0x28), 0x2D, 0x2E), 0, 1),
    _key("Backspace", 0x2A, x=13, row=1, w=2),
    *_run(["Ins", "Home", "PgUp"], (0x49, 0x4A, 0x4B), 15.25, 1),
    *_run(["Num", "/", "*", "-"], (0x53, 0x54, 0x55, 0x56), 18.5, 1),

    _key("Tab", 0x2B, x=0, row=2, w=1.5),
    *_run(list("QWERTYUIOP[]"), (0x14, 0x1A, 0x08, 0x15, 0x17, 0x1C, 0x18, 0x0C, 0x12, 0x13, 0x2F, 0x30), 1.5, 2),
    _key("\\", 0x31, x=13.5, row=2, w=1.5),
    *_run(["Del", "End", "PgDn"], (0x4C, 0x4D, 0x4E), 15.25, 2),
    *_run(["7", "8", "9"], (0x5F, 0x60, 0x61), 18.5, 2),
    _key("+", 0x57, x=21.5, row=2, h=2),

    _key("Caps", 0x39, x=0, row=3, w=1.75),
    *_run(list("ASDFGHJKL;'"), (0x04, 0x16, 0x07, 0x09, 0x0A, 0x0B, 0x0D, 0x0E, 0x0F, 0x33, 0x34), 1.75, 3),
    _key("Enter", 0x28, x=12.75, row=3, w=2.25),
    *_run(["4", "5", "6"], (0x5C, 0x5D, 0x5E), 18.5, 3),

    _key("Shift", mods=0x02, x=0, row=4, w=2.25),
    *_run(list("ZXCVBNM,./"), (0x1D, 0x1B, 0x06, 0x19, 0x05, 0x11, 0x10, 0x36, 0x37, 0x38), 2.25, 4),
    _key("Shift", mods=0x20, x=12.25, row=4, w=2.75),
    _key("↑", 0x52, x=16.25, row=4),
    *_run(["1", "2", "3"], (0x59, 0x5A, 0x5B), 18.5, 4),
    _key("Enter", 0x58, x=21.5, row=4, h=2),

    _key("Ctrl", mods=0x01, x=0, row=5, w=1.25),
    _key("Win", mods=0x08, x=1.25, row=5, w=1.25),
    _key("Alt", mods=0x04, x=2.5, row=5, w=1.25),
    _key("", 0x2C, x=3.75, row=5, w=6.25),
    _key("Alt", mods=0x40, x=10, row=5, w=1.25),
    _key("Fn", FN_USAGE, x=11.25, row=5, w=1.25),
    _key("Menu", 0x65, x=12.5, row=5, w=1.25),
    _key("Ctrl", mods=0x10, x=13.75, row=5, w=1.25),
    *_run(["←", "↓", "→"], (0x50, 0x51, 0x4F), 15.25, 5),
    _key("0", 0x62, x=18.5, row=5, w=2),
    _key(".", 0x63, x=20.5, row=5),
]
WIDTH, HEIGHT = 22.5, 6.25

# The matrix position of each keycap, found through the factory keymap.
_FACTORY_POSITION = {binding: index for index, binding in enumerate(FACTORY_BINDINGS) if not binding.empty}


class Keycap:
    def __init__(self, label, factory, x, y, w, h):
        self.label, self.factory = label, factory
        self.x, self.y, self.w, self.h = x, y, w, h
        self.position = _FACTORY_POSITION[factory]
        self.row = _ROW_Y.index(y)

    @property
    def is_fn(self):
        return self.factory.usage == FN_USAGE

    @property
    def centre(self):
        return self.x + self.w / 2, self.y + self.h / 2


KEYS = [Keycap(*spec) for spec in KEYCAPS]
WIN_KEY = next(k for k in KEYS if k.factory == Binding(mods=0x08))

# The keyboard's built-in effects (lighting modes 1-8)
EFFECT_INFO = {
    1: ("Static", "Every key lit."),
    2: ("Reactive", "A key lights up when you press it. Speed sets how long it fades."),
    3: ("Breathing", "The whole keyboard slowly lights up and fades."),
    4: ("Snake", "Light runs along the rows, back and forth."),
    5: ("Corners", "Light runs in from two corners to the centre, spins, then spreads out."),
    6: ("Spiral", "A spiral winds in to the centre, then a ring spreads out from it."),
    7: ("Wave", "A dark wave sweeps over the lit keyboard from left to right."),
    8: ("Ripple", "Light ripples out from every key you press."),
}

# Keys lit by the built-in maps M1-M8 (labels as on the keycaps, left modifiers)
_PRESET_LABELS = {
    1: "Esc W A S D ↑ ↓ ← →",
    2: "PrtSc Home End PgUp PgDn F1 F2 F3 1 2 3 4 5 Tab Q W E R A S D G B LShift LCtrl LAlt Space",
    3: "1 2 3 4 5 6 7 Q W E R T A S D F G C V LShift LCtrl",
    4: "1 2 3 4 5 6 7 8 9 0 Q W E R T Y U P A S D F G H J K L Z X N M LShift LCtrl LAlt",
    5: "Esc ` 1 2 3 4 5 6 Tab Q W E R D F G V B LCtrl LAlt",
    6: "W R A S D LShift LCtrl LAlt ↑ ↓ ← →",
    7: "1 2 3 4 W E R A S F Z X C V LShift LCtrl LAlt ↑ ↓ ← →",
    8: "1 2 3 4 5 6 Q W E R D F B",
}
_SPECIAL = {"LShift": Binding(mods=0x02), "LCtrl": Binding(mods=0x01), "LAlt": Binding(mods=0x04),
            "Space": Binding(usage=0x2C)}
_MAIN_BLOCK = {k.label: k for k in KEYS if k.x < 18.5}  # not the numpad: "1" is the top-row 1


def _preset_keys(text):
    keys = set()
    for label in text.split():
        if label in _SPECIAL:
            keys.add(next(k.position for k in KEYS if k.factory == _SPECIAL[label]))
        else:
            keys.add(_MAIN_BLOCK[label].position)
    return frozenset(keys)


PRESET_KEYS = {number: _preset_keys(text) for number, text in _PRESET_LABELS.items()}
