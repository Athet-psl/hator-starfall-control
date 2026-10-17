import unittest
from unittest.mock import patch

from starfall import device, layout
from starfall.device import Binding, Keyboard, Lighting


class FakeHid:
    """Feature reports 9 and 10 as the keyboard keeps them, behind fcntl.ioctl."""

    def __init__(self, junk_reads=0):
        self.reports = {device.KEYMAP: bytearray(device.FACTORY_KEYMAP),
                        device.LIGHTING: bytearray(Lighting(1, 10, 2, 5).frame())}
        self.junk_reads = junk_reads

    def ioctl(self, fd, request, buf, mutate):
        nr = request & 0xFF
        report = buf[0]
        if nr == 0x06:  # SET_FEATURE
            self.reports[report] = bytearray(buf[1:])
            return len(buf)
        data = bytearray(self.reports[report])
        if report == device.LIGHTING and self.junk_reads:
            self.junk_reads -= 1
            data[10] = 0x5F  # leftovers of another report
        buf[1:1 + len(data)] = data
        return len(data) + 1

    def __enter__(self):
        self.patches = [patch.object(device.fcntl, "ioctl", self.ioctl),
                        patch.object(device.os, "open", lambda *a: 99),
                        patch.object(device.os, "close", lambda fd: None),
                        patch.object(device.time, "sleep", lambda s: None)]
        for p in self.patches:
            p.start()
        return self

    def __exit__(self, *_):
        for p in self.patches:
            p.stop()


class LightingTest(unittest.TestCase):
    def test_frame_round_trip(self):
        light = Lighting(7, 10, 2, 5)
        self.assertEqual(light.frame()[:4], bytes([7, 10, 2, 5]))
        self.assertEqual(len(light.frame()), device.LIGHTING_SIZE)
        self.assertEqual(Lighting.parse(light.frame()), light)

    def test_effect_and_map(self):
        light = Lighting(9, 2, 3, 4)
        self.assertEqual(light.with_effect(5), Lighting(5, device.EFFECT_MAP, 3, 4))
        self.assertTrue(light.with_map(9).is_map)
        self.assertFalse(light.with_effect(1).is_map)


class KeymapTest(unittest.TestCase):
    def test_factory_round_trip(self):
        self.assertEqual(device.encode_keymap(device.FACTORY_BINDINGS), device.FACTORY_KEYMAP)

    def test_wrong_length(self):
        with self.assertRaises(ValueError):
            device.encode_keymap(device.FACTORY_BINDINGS[:-1])

    def test_unknown_bytes_survive(self):
        entry = bytes([3, 0, 0x04, 7])
        self.assertEqual(Binding.parse(entry).entry(), entry)


class KeyboardTest(unittest.TestCase):
    def test_lighting_skips_leftovers(self):
        with FakeHid(junk_reads=2), Keyboard("/dev/null") as keyboard:
            self.assertEqual(keyboard.lighting(), Lighting(1, 10, 2, 5))

    def test_set_lighting_reads_back(self):
        with FakeHid(), Keyboard("/dev/null") as keyboard:
            self.assertEqual(keyboard.set_lighting(Lighting(9, 1, 2, 3)), Lighting(9, 1, 2, 3))

    def test_set_keymap(self):
        with FakeHid() as hid, Keyboard("/dev/null") as keyboard:
            bindings = list(device.FACTORY_BINDINGS)
            bindings[layout.WIN_KEY.position] = Binding()
            keyboard.set_keymap(bindings)
            self.assertEqual(device.parse_keymap(hid.reports[device.KEYMAP])[layout.WIN_KEY.position], Binding())


class LayoutTest(unittest.TestCase):
    def test_every_keycap_has_its_own_position(self):
        positions = [key.position for key in layout.KEYS]
        self.assertEqual(len(positions), 104)
        self.assertEqual(len(set(positions)), len(positions))

    def test_presets(self):
        positions = {key.position for key in layout.KEYS}
        for number in device.PRESET_MAPS:
            self.assertTrue(layout.PRESET_KEYS[number] <= positions)
        top_row_1 = next(k for k in layout.KEYS if k.label == "1" and k.row == 1 and k.x < 15)
        self.assertIn(top_row_1.position, layout.PRESET_KEYS[8])

    def test_key_codes(self):
        self.assertEqual(layout.binding_for_code(30), Binding(usage=0x04))   # A
        self.assertEqual(layout.binding_for_code(29), Binding(mods=0x01))    # Left Ctrl
        self.assertIsNone(layout.binding_for_code(464))                      # Fn: not a key Linux sees

    def test_describe(self):
        self.assertEqual(layout.describe(Binding()), "Nothing")
        self.assertEqual(layout.describe(Binding(mods=0x01, usage=0x06)), "Left Ctrl + C")
        self.assertEqual(layout.describe(Binding(usage=layout.FN_USAGE)), "Fn")


if __name__ == "__main__":
    unittest.main()
