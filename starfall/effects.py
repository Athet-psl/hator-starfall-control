"""Previews of the Starfall's built-in lighting effects (modes 1, 3-7).

Snake, Corners and Spiral follow videos of the keyboard at the slowest speed,
measured key by key. They run over the keyboard's matrix: 6 rows of 21
columns, the grid its own animations use. Breathing and Wave are
approximations. Reactive and Ripple follow key presses and live in the UI.
"""

import math

from . import layout
from .device import COLUMNS, ROWS, SLOWEST

TIMED = (1, 3, 4, 5, 6, 7)  # effects that only depend on time
LAST = COLUMNS - 1


def cell(key):
    """(row, column) of a keycap in the matrix."""
    return key.row, key.position // ROWS


def effect_period(speed):
    return 1.6 + 0.9 * speed  # seconds per Breathing or Wave cycle; 0 is the fastest


def pace(speed):
    """How many times faster than the slowest speed an effect runs. Only the slowest
    speed was filmed, so the others are scaled like Breathing."""
    return effect_period(SLOWEST) / effect_period(speed)


def _band(x, low, high, edge=1.0):
    """1 inside [low, high], fading to 0 over `edge` columns outside it."""
    return max(0.0, 1.0 - max(low - x, x - high, 0.0) / edge)


def _lerp(a, b, t):
    return a + (b - a) * min(1.0, max(0.0, t))


def glow(mode, key, t, speed):
    """How brightly `key` is lit, 0-1, `t` seconds into a timed effect."""
    if mode == 1:
        return 1.0
    if mode in (3, 7):
        phase = (t / effect_period(speed)) % 1.0
        if mode == 3:
            return 0.5 - 0.5 * math.cos(2 * math.pi * phase)
        band = phase * 1.3 - 0.15
        return 1.0 - math.exp(-((key.centre[0] / layout.WIDTH - band) / 0.06) ** 2)
    row, col = cell(key)
    t *= pace(speed)
    if mode == 4:
        return snake(row, col, t)
    if mode == 5:
        return corners(row, col, t)
    if mode == 6:
        return spiral(row, col, t)
    return 0.0


# Snake: every row runs a band of 13 columns back and forth, each row the
# other way from the one above. At each end it turns with 7 columns still lit.

SNAKE_CYCLE = 3.4
SNAKE_LENGTH = 13
SNAKE_SHOWN = 7


def snake(row, col, t):
    travel = 1 - abs(2 * ((t / SNAKE_CYCLE) % 1.0) - 1)  # 0 -> 1 -> 0
    start = _lerp(SNAKE_SHOWN - SNAKE_LENGTH, COLUMNS - SNAKE_SHOWN, travel)
    x = col if row % 2 else LAST - col
    return _band(x, start, start + SNAKE_LENGTH - 1)


# Corners: the top three rows run in from the left, the bottom three from the
# right. The outer rows run off the far end; the others come back and meet in
# the middle. The middle block then spreads to the edges, and the keyboard
# clears from the middle out.

CORNERS_CYCLE = 5.4
CORNERS_SPEED = 13.5  # columns a second


def corners(row, col, t):
    t %= CORNERS_CYCLE
    if t < 3.1:
        # Lanes count from the outer row in; x runs from the corner they start at.
        lane, x = (row, col) if row < 3 else (5 - row, LAST - col)
        return _corner_lane(lane, x, t)
    if t < 3.95:
        if row == 5:
            return 0.0
        return _band(col, 8, 10) if row == 0 else _band(col, 7, 12)
    if t < 4.35:
        return _band(col, _lerp(7, 0, (t - 3.95) / 0.4), _lerp(12, LAST, (t - 3.95) / 0.4))
    if t < 4.5:
        return 1.0
    gap = 10 * (t - 4.5)
    return 1.0 - _band(col, 9.5 - gap, 9.5 + gap)


def _corner_lane(lane, x, t):
    run = CORNERS_SPEED * t
    if lane == 0:
        return _band(x, run - 9, run)
    if lane == 1:
        if t < 2.0:
            head = run + 1.6
            return _band(x, min(head - 9, 12), min(head, LAST))
        if t < 2.7:
            return _band(x, _lerp(12, 9, (t - 2.0) / 0.2), _lerp(LAST, 17, (t - 2.0) / 0.2))
        return _band(x, _lerp(9, 8, (t - 2.7) / 0.4), _lerp(17, 12, (t - 2.7) / 0.4))
    head = run - 0.4
    far = _band(x, min(head - 11, 10), min(head, LAST - CORNERS_SPEED * max(0.0, t - 2.5)))
    if t < 1.5:
        return far
    near = _band(x, 9 * max(0.0, t - 2.2), min(CORNERS_SPEED * (t - 1.5), 8))
    return max(far, near)


# Spiral: a snake winds in along the rows, from the top right to the middle of
# row 2, each key staying lit for 0.85 s behind it. The middle then goes dark,
# lights up again as a 3x3 block, and a diamond-shaped ring spreads out from it.

SPIRAL_CYCLE = 15.5
SPIRAL_SPEED = 16.9   # matrix cells a second
SPIRAL_TRAIL = 0.85   # seconds a key stays lit after the snake passes
SPIRAL_FADE = 0.25
SPIRAL_MIDDLE = (2, 9)
SPIRAL_BLOCK = 11.04  # the middle lights up again
SPIRAL_RING = 12.74   # and spreads out as a ring
SPIRAL_HOLLOW = 13.27  # whose middle goes dark half a second later
SPIRAL_ROW_WIDTH = 1.25  # a row counts as 1.25 columns in the ring


def _spiral_path():
    path = [(0, c) for c in range(LAST, -1, -1)]          # the outer ring, from the top right
    path += [(r, 0) for r in range(1, 5)]
    path += [(5, c) for c in range(COLUMNS)]
    path += [(r, LAST) for r in range(4, 0, -1)]
    path += [(1, c) for c in range(LAST - 1, 0, -1)]      # the next ring in
    path += [(r, 1) for r in (2, 3)]
    path += [(4, c) for c in range(1, LAST)]
    path += [(r, LAST - 1) for r in (3, 2)]
    path += [(2, c) for c in range(LAST - 2, 1, -1)]      # rows 2 and 3
    path += [(3, c) for c in range(2, LAST - 2)]
    path += [(2, c) for c in range(LAST - 3, SPIRAL_MIDDLE[1] - 1, -1)]  # and back to the middle
    return path


def _visits(path):
    """Cell -> the times the snake's head reaches it."""
    visits = {}
    for step, place in enumerate(path):
        visits.setdefault(place, []).append(step / SPIRAL_SPEED)
    return visits


SPIRAL_PATH = _spiral_path()
SPIRAL_END = len(SPIRAL_PATH) / SPIRAL_SPEED
_SPIRAL_VISITS = _visits(SPIRAL_PATH)
_SPIRAL_TAIL = set(SPIRAL_PATH[-5:])  # stays lit a little longer when the snake stops


def _fade(age, lit):
    """1 for `lit` seconds, then fading out over SPIRAL_FADE."""
    if age < 0:
        return 0.0
    return max(0.0, min(1.0, 1 - (age - lit) / SPIRAL_FADE))


def spiral(row, col, t):
    t %= SPIRAL_CYCLE
    if t < SPIRAL_END + SPIRAL_TRAIL + SPIRAL_FADE:
        brightness = max((_fade(t - at, SPIRAL_TRAIL) for at in _SPIRAL_VISITS.get((row, col), ())), default=0.0)
        if (row, col) in _SPIRAL_TAIL:
            brightness = max(brightness, _fade(t - SPIRAL_END, SPIRAL_TRAIL))
        return brightness
    dy, dx = abs(row - SPIRAL_MIDDLE[0]), abs(col - SPIRAL_MIDDLE[1])
    if SPIRAL_BLOCK <= t < SPIRAL_RING:
        return 1.0 if max(dx, dy) <= 1 else 0.0
    if t >= SPIRAL_RING:
        outer = 2 + 8.75 * (t - SPIRAL_RING)
        inner = 7.5 * (t - SPIRAL_HOLLOW)
        return _band(dx + SPIRAL_ROW_WIDTH * dy, inner, outer)
    return 0.0
