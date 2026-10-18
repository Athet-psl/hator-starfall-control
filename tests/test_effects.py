import unittest

from starfall import effects, layout


class EffectsTest(unittest.TestCase):
    def test_glow_stays_in_range(self):
        for mode in effects.TIMED:
            for speed in (0, 4):
                for step in range(0, 400, 7):
                    for key in layout.KEYS:
                        glow = effects.glow(mode, key, step / 20, speed)
                        self.assertTrue(0.0 <= glow <= 1.0, (mode, speed, step, key.label, glow))

    def test_snake_rows_mirror_each_other(self):
        for step in range(40):
            t = step / 10
            for col in range(effects.COLUMNS):
                self.assertAlmostEqual(effects.snake(1, col, t), effects.snake(0, effects.LAST - col, t))

    def test_spiral_path_winds_in_to_the_middle(self):
        path = effects.SPIRAL_PATH
        self.assertEqual(path[0], (0, effects.LAST))
        self.assertEqual(path[-1], effects.SPIRAL_MIDDLE)
        self.assertEqual({row for row, _ in path}, set(range(6)))
        for (r1, c1), (r2, c2) in zip(path, path[1:]):
            self.assertEqual(abs(r1 - r2) + abs(c1 - c2), 1)

    def test_corners_fill_then_clear_from_the_middle(self):
        self.assertTrue(all(effects.corners(row, col, 4.4) == 1.0 for row in range(6) for col in range(21)))
        self.assertEqual(effects.corners(2, 10, 5.2), 0.0)
        self.assertEqual(effects.corners(2, 0, 5.2), 1.0)


if __name__ == "__main__":
    unittest.main()
