"""HATOR Starfall Control: lighting and key settings for the HATOR Starfall keyboard.

Every change goes straight to the keyboard, which keeps it without the app.
Follows the system's light or dark scheme (STARFALL_THEME=light|dark forces one).
"""

import json
import math
import os
import random
import sys
import time

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPainter, QPainterPath, QPalette, QPen
from PyQt6.QtWidgets import (
    QAbstractButton, QApplication, QButtonGroup, QDialog, QDialogButtonBox, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSlider, QStackedWidget, QVBoxLayout, QWidget,
)

from . import __author__, __version__, layout
from .device import (
    BRIGHTEST, CUSTOM_MAPS, EFFECTS, PRESET_MAPS, SLOWEST, Binding, Keyboard, Lighting, find_node, parse_keymap,
)
from .layout import EFFECT_INFO, GROUPS, KEYS, MODIFIERS, PRESET_KEYS, USAGES, WIN_KEY, binding_for_code, describe

APP_NAME = "HATOR Starfall Control"
POLL_MS = 1500
UDEV_RULE = ('SUBSYSTEM=="hidraw", ATTRS{idVendor}=="258a", ATTRS{idProduct}=="002a", '
             'GROUP="plugdev", MODE="0620"')
UDEV_HINT = (f"echo '{UDEV_RULE}' | sudo tee /etc/udev/rules.d/70-starfall-control.rules && "
             "sudo udevadm control --reload && sudo udevadm trigger --subsystem-match=hidraw")
ROW_COLOURS = ("#4f6bff", "#22e07a", "#a855ff", "#ff4fc8", "#ff4040", "#ff9a1f")  # the LED colour of each row
FN_SHORTCUTS = [
    ("Fn + ScrLk", "Next effect"), ("Fn + 1…8", "Key maps M1–M8"), ("Fn + 9 / Fn + 0", "Custom maps CM1 / CM2"),
    ("Fn + ↑ / ↓", "Brightness"), ("Fn + → / ←", "Faster / slower"), ("Fn + PrtSc", "Record a custom map"),
    ("Fn + Win", "Game mode: Win key off"), ("Fn + Esc", "Factory reset"), ("Fn + F1…F12", "Media and apps"),
]
BACKUP_FORMAT = 1


# Theme


class Theme:
    def __init__(self):
        forced = os.environ.get("STARFALL_THEME")
        window = QApplication.palette().color(QPalette.ColorRole.Window)
        self.dark = forced == "dark" or (forced != "light" and window.lightness() < 128)
        if self.dark:
            self.bg, self.surface, self.hover, self.raised = "#1c1c1e", "#2a2a2d", "#333337", "#3a3a3e"
            self.border, self.text, self.dim = "#3a3a3d", "#f2f2f7", "#98989d"
        else:
            self.bg, self.surface, self.hover, self.raised = "#f5f5f7", "#ebebef", "#e2e2e8", "#ffffff"
            self.border, self.text, self.dim = "#d6d6dc", "#1d1d1f", "#6e6e73"
        self.accent = QApplication.palette().color(QPalette.ColorRole.Highlight).name()
        self.green, self.orange, self.red = "#34c759", "#ff9f0a", "#ff453a"

    def stylesheet(self):
        return f"""
        QWidget#root, QWidget#page, QScrollArea#page > QWidget > QWidget {{ background: {self.bg}; }}
        QLabel {{ color: {self.text}; background: transparent; }}
        QLabel[dim="true"] {{ color: {self.dim}; }}
        QFrame#panel {{ background: {self.surface}; border: 1px solid {self.border}; border-radius: 12px; }}
        QFrame#banner {{ background: {self.surface}; border: 1px solid {self.orange}; border-radius: 10px; }}
        QFrame#segment {{ background: {self.surface}; border-radius: 9px; }}
        QPushButton#seg {{ border: none; border-radius: 7px; padding: 6px 18px; color: {self.text};
                           background: transparent; }}
        QPushButton#seg:checked {{ background: {self.raised}; }}
        QPushButton#seg:hover:!checked {{ background: {self.hover}; }}
        QPushButton#flat {{ border: none; border-radius: 6px; padding: 5px 9px; color: {self.text};
                            background: transparent; }}
        QPushButton#flat:hover {{ background: {self.hover}; }}
        QPushButton#outline {{ border: 1px solid {self.border}; border-radius: 8px; padding: 6px 14px;
                               color: {self.text}; background: {self.raised}; }}
        QPushButton#outline:hover {{ background: {self.hover}; }}
        QPushButton#outline:disabled {{ color: {self.dim}; }}
        QPushButton#tile {{ border: 1px solid {self.border}; border-radius: 10px; padding: 9px 12px;
                            background: {self.surface}; color: {self.text}; text-align: left; }}
        QPushButton#tile:hover {{ background: {self.hover}; }}
        QPushButton#tile:checked {{ border: 2px solid {self.accent}; background: {self.raised}; }}
        QPushButton#tile:disabled {{ color: {self.dim}; }}
        QLabel#pill {{ border: 1px solid {self.border}; border-radius: 10px; padding: 3px 12px;
                       color: {self.dim}; background: {self.bg}; }}
        QFrame#hline {{ background: {self.border}; border: none; }}
        QListWidget {{ background: {self.surface}; border: 1px solid {self.border}; border-radius: 8px;
                       color: {self.text}; }}
        QLineEdit {{ background: {self.raised}; border: 1px solid {self.border}; border-radius: 7px;
                     padding: 5px 8px; color: {self.text}; }}
        """


def font(scale=1.0, weight=None):
    f = QFont(QApplication.font())
    f.setPointSizeF(f.pointSizeF() * scale)
    if weight is not None:
        f.setWeight(weight)
    return f


def dim_label(text="", scale=0.92, wrap=False):
    label = QLabel(text)
    label.setProperty("dim", True)
    label.setFont(font(scale))
    label.setWordWrap(wrap)
    return label


def hline():
    line = QFrame()
    line.setObjectName("hline")
    line.setFixedHeight(1)
    return line


def button(text, slot, name="outline"):
    widget = QPushButton(text)
    widget.setObjectName(name)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.clicked.connect(slot)
    return widget


class Switch(QAbstractButton):
    def __init__(self, theme):
        super().__init__()
        self.theme = theme
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(44, 26)

    def sizeHint(self):
        return QSize(44, 26)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        on = self.isChecked()
        track = QColor(self.theme.accent if on else self.theme.border)
        if not self.isEnabled():
            track.setAlpha(110)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(QRectF(0, 0, 44, 26), 13, 13)
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QPointF(31 if on else 13, 13), 10, 10)


class Segmented(QFrame):
    changed = pyqtSignal(int)

    def __init__(self, labels):
        super().__init__()
        self.setObjectName("segment")
        row = QHBoxLayout(self)
        row.setContentsMargins(3, 3, 3, 3)
        row.setSpacing(2)
        self.group = QButtonGroup(self)
        for index, label in enumerate(labels):
            seg = QPushButton(label)
            seg.setObjectName("seg")
            seg.setCheckable(True)
            seg.setCursor(Qt.CursorShape.PointingHandCursor)
            seg.setFont(font(1.05))
            self.group.addButton(seg, index)
            row.addWidget(seg)
        self.group.button(0).setChecked(True)
        self.group.idClicked.connect(self.changed.emit)


def panel(title, *widgets, spacing=10):
    frame = QFrame()
    frame.setObjectName("panel")
    box = QVBoxLayout(frame)
    box.setContentsMargins(18, 14, 18, 16)
    box.setSpacing(spacing)
    if title:
        heading = QLabel(title)
        heading.setFont(font(1.1, QFont.Weight.DemiBold))
        box.addWidget(heading)
    for widget in widgets:
        if isinstance(widget, QWidget):
            box.addWidget(widget)
        else:
            box.addLayout(widget)
    return frame


def scroll_page(*widgets):
    page = QScrollArea()
    page.setObjectName("page")
    page.setWidgetResizable(True)
    page.setFrameShape(QFrame.Shape.NoFrame)
    inner = QWidget()
    column = QVBoxLayout(inner)
    column.setContentsMargins(28, 18, 28, 24)
    column.setSpacing(16)
    for widget in widgets:
        column.addWidget(widget)
    column.addStretch(1)
    page.setWidget(inner)
    return page


# The keyboard picture


def effect_period(speed):
    return 1.6 + 0.9 * speed  # seconds per cycle; 0 is the fastest


class KeyboardView(QWidget):
    """The Starfall drawn key by key. In "lighting" mode it plays an approximation of the
    current effect; in "keys" mode it shows what each key sends and takes clicks."""

    key_clicked = pyqtSignal(object)  # Keycap

    def __init__(self, theme, mode):
        super().__init__()
        self.theme = theme
        self.mode = mode
        self.lighting = None
        self.bindings = None
        self.hover = None
        self.presses = []  # (time, Keycap) for reactive and ripple effects
        self.start = time.monotonic()
        self.next_press = 0.0
        self.setMouseTracking(True)
        self.setMinimumHeight(220)
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.update)

    def sizeHint(self):
        return QSize(900, 290)

    def heightForWidth(self, width):
        return int(width * (layout.HEIGHT + 0.9) / (layout.WIDTH + 0.9))

    def hasHeightForWidth(self):
        return True

    def set_lighting(self, lighting):
        self.lighting = lighting
        self._animate()
        self.update()

    def set_bindings(self, bindings):
        self.bindings = bindings
        self.update()

    def showEvent(self, event):
        self._animate()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def _animate(self):
        moving = (self.mode == "lighting" and self.lighting is not None and not self.lighting.is_map
                  and self.lighting.mode != 1 and self.lighting.brightness > 0)
        if moving and self.isVisible():
            self.timer.start()
        else:
            self.timer.stop()

    # geometry

    def _unit(self):
        pad = 0.45
        unit = min(self.width() / (layout.WIDTH + 2 * pad), self.height() / (layout.HEIGHT + 2 * pad))
        ox = (self.width() - layout.WIDTH * unit) / 2
        oy = (self.height() - layout.HEIGHT * unit) / 2
        return unit, ox, oy

    def _rect(self, key, unit, ox, oy):
        return QRectF(ox + key.x * unit, oy + key.y * unit, key.w * unit, key.h * unit)

    def key_at(self, pos):
        unit, ox, oy = self._unit()
        return next((k for k in KEYS if self._rect(k, unit, ox, oy).contains(pos)), None)

    # lighting preview

    def _glow(self, key, t):
        light = self.lighting
        if light is None or light.brightness == 0:
            return 0.0
        if light.is_map:
            return 1.0 if key.position in PRESET_KEYS.get(light.map, ()) else 0.0
        period = effect_period(light.speed)
        phase = (t / period) % 1.0
        u = key.centre[0] / layout.WIDTH
        v = key.centre[1] / layout.HEIGHT
        mode = light.mode
        if mode == 1:
            return 1.0
        if mode == 3:
            return 0.5 - 0.5 * math.cos(2 * math.pi * phase)
        if mode == 4:
            order = sorted(KEYS, key=lambda k: (k.row, k.x if k.row % 2 == 0 else -k.x))
            head = phase * len(order)
            behind = (head - order.index(key)) % len(order)
            return max(0.0, 1.0 - behind / 7)
        if mode in (5, 6):
            centre = math.hypot(u - 0.5, (v - 0.5) * 0.4)
            if phase < 0.6:
                fill = phase / 0.6
                if mode == 5:
                    d = min(math.hypot(1 - u, v * 0.4), math.hypot(u, (1 - v) * 0.4)) / 0.75
                    return 1.0 if d < fill else 0.0
                angle = (math.atan2(v - 0.5, u - 0.5) / (2 * math.pi)) % 1.0
                return 1.0 if (1 - centre / 0.55) * 0.75 + angle * 0.25 < fill else 0.0
            ring = (phase - 0.6) / 0.4 * 0.6
            return math.exp(-((centre - ring) / 0.05) ** 2)
        if mode == 7:
            band = phase * 1.3 - 0.15
            return 1.0 - math.exp(-((u - band) / 0.06) ** 2)
        now = time.monotonic()
        fade = 0.25 + 0.3 * light.speed
        glow = 0.0
        for pressed_at, pressed in self.presses:
            age = now - pressed_at
            if mode == 2 and pressed is key:
                glow = max(glow, math.exp(-age / fade))
            elif mode == 8:
                du = (key.centre[0] - pressed.centre[0]) / layout.WIDTH
                dv = (key.centre[1] - pressed.centre[1]) / layout.WIDTH
                radius = age * 0.45 / (0.6 + 0.3 * light.speed)
                glow = max(glow, math.exp(-((math.hypot(du, dv) - radius) / 0.025) ** 2) * math.exp(-age))
        return glow

    def _typing(self, now):
        """Pretend someone types, so reactive and ripple have something to show."""
        self.presses = [(at, key) for at, key in self.presses if now - at < 4]
        if self.lighting and self.lighting.mode in (2, 8) and not self.lighting.is_map and now >= self.next_press:
            letters = [k for k in KEYS if k.row in (2, 3, 4) and k.w == 1 and k.x < 13]
            self.presses.append((now, random.choice(letters)))
            self.next_press = now + random.uniform(0.15, 0.6) * (1.5 if self.lighting.mode == 8 else 1)

    # painting

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        unit, ox, oy = self._unit()
        body = QRectF(ox - unit * 0.35, oy - unit * 0.35, (layout.WIDTH + 0.7) * unit, (layout.HEIGHT + 0.7) * unit)
        p.setPen(QPen(QColor("#2e2e33"), 1))
        p.setBrush(QColor("#121214"))
        p.drawRoundedRect(body, unit * 0.3, unit * 0.3)
        now = time.monotonic()
        if self.mode == "lighting":
            self._typing(now)
        t = now - self.start
        scale = (self.lighting.brightness / BRIGHTEST) if self.lighting else 0
        legend_font = font(1.0)
        for key in KEYS:
            rect = self._rect(key, unit, ox, oy)
            if self.mode == "lighting":
                self._paint_lit_key(p, key, rect, unit, self._glow(key, t) * scale, legend_font)
            else:
                self._paint_binding_key(p, key, rect, unit, legend_font)
        if self.mode == "lighting" and self.lighting and self.lighting.is_map and self.lighting.map in CUSTOM_MAPS:
            p.setPen(QColor("#d8d8de"))
            p.setFont(font(1.05))
            p.drawText(body, Qt.AlignmentFlag.AlignCenter,
                       "Custom map: recorded on the keyboard, so it isn't shown here")

    def _keycap(self, rect, unit):
        inset = unit * 0.07
        return rect.adjusted(inset, inset, -inset, -inset)

    def _paint_lit_key(self, p, key, rect, unit, glow, legend_font):
        colour = QColor(ROW_COLOURS[key.row])
        if glow > 0.02:
            halo = QColor(colour)
            halo.setAlphaF(min(1.0, 0.85 * glow))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(halo)
            p.drawRoundedRect(rect.adjusted(-unit * 0.02, -unit * 0.02, unit * 0.02, unit * 0.02), unit * 0.14, unit * 0.14)
        cap = self._keycap(rect, unit)
        p.setPen(QPen(QColor("#2a2a2f"), 1))
        p.setBrush(QColor("#1b1b1e"))
        p.drawRoundedRect(cap, unit * 0.1, unit * 0.1)
        if glow > 0.02:
            tint = QColor(colour)
            tint.setAlphaF(0.16 * glow)
            p.setBrush(tint)
            p.drawRoundedRect(cap, unit * 0.1, unit * 0.1)
        legend = QColor(colour)
        legend.setAlphaF(0.25 + 0.75 * glow)
        p.setPen(legend)
        legend_font.setPixelSize(max(7, int(unit * (0.26 if len(key.label) <= 2 else 0.2))))
        p.setFont(legend_font)
        p.drawText(cap.adjusted(unit * 0.1, unit * 0.06, -unit * 0.06, -unit * 0.06),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, key.label)

    def _paint_binding_key(self, p, key, rect, unit, legend_font):
        cap = self._keycap(rect, unit)
        binding = self.bindings[key.position] if self.bindings else key.factory
        changed = binding != key.factory
        theme = self.theme
        fill = QColor(theme.raised if key is self.hover and not key.is_fn else theme.surface)
        p.setPen(QPen(QColor(theme.accent if changed else theme.border), 2 if changed else 1))
        p.setBrush(fill)
        p.drawRoundedRect(cap, unit * 0.1, unit * 0.1)
        text = key.label if not changed else short_label(binding)
        colour = QColor(theme.accent if changed else (theme.dim if key.is_fn else theme.text))
        p.setPen(colour)
        legend_font.setPixelSize(max(7, int(unit * (0.26 if len(text) <= 2 else 0.19))))
        p.setFont(legend_font)
        p.drawText(cap.adjusted(unit * 0.06, unit * 0.04, -unit * 0.06, -unit * 0.04),
                   Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)

    # input

    def mouseMoveEvent(self, event):
        key = self.key_at(event.position())
        if self.mode == "keys" and key is not self.hover:
            self.hover = key
            clickable = key is not None and not key.is_fn
            self.setCursor(Qt.CursorShape.PointingHandCursor if clickable else Qt.CursorShape.ArrowCursor)
            self.setToolTip("" if key is None else (
                "Fn is handled by the keyboard and can't be changed" if key.is_fn else
                f"{key.label or 'Space'}: sends {describe(self.bindings[key.position]) if self.bindings else ''}"))
            self.update()

    def leaveEvent(self, _):
        self.hover = None
        self.update()

    def mousePressEvent(self, event):
        key = self.key_at(event.position())
        if key is None:
            return
        if self.mode == "lighting":
            self.presses.append((time.monotonic(), key))
        elif not key.is_fn:
            self.key_clicked.emit(key)


def short_label(binding):
    """A keycap-sized name: the keycap that sends it by default, or the full description."""
    if binding.empty:
        return "—"
    for key in KEYS:
        if key.factory == binding and key.label:
            return key.label
    return describe(binding).replace("Left ", "L").replace("Right ", "R")


# Keyboard access


class Connection:
    """Opens the keyboard on demand and reports what's wrong when it can't."""

    def __init__(self):
        self.keyboard = None
        self.problem = ""

    def get(self):
        if self.keyboard is not None:
            return self.keyboard
        node = find_node()
        if node is None:
            self.problem = "missing"
            return None
        try:
            self.keyboard = Keyboard(node)
        except PermissionError:
            self.problem = "access"
            return None
        except OSError:
            self.problem = "missing"
            return None
        self.problem = ""
        return self.keyboard

    def drop(self):
        if self.keyboard is not None:
            self.keyboard.close()
        self.keyboard = None


# Lighting tab


class LightingTab(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        theme = app.theme
        self.view = KeyboardView(theme, "lighting")
        self.view.setToolTip("A preview of the effect. Click keys to see reactive and ripple effects.")

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        effects = QGridLayout()
        effects.setSpacing(8)
        for index, mode in enumerate(EFFECTS):
            name, about = EFFECT_INFO[mode]
            tile = self._tile(name, about, ("effect", mode))
            effects.addWidget(tile, index // 4, index % 4)
        maps = QGridLayout()
        maps.setSpacing(8)
        for index, number in enumerate(PRESET_MAPS):
            tile = self._tile(f"M{number}", "", ("map", number))
            tile.setToolTip(f"Built-in key map M{number} (Fn + {number})")
            maps.addWidget(tile, 0 if index < 5 else 1, index % 5)
        for index, number in enumerate(CUSTOM_MAPS):
            tile = self._tile(f"CM{index + 1}", "", ("map", number))
            tile.setToolTip(f"Custom map CM{index + 1} (Fn + {9 if index == 0 else 0})")
            maps.addWidget(tile, 1, 3 + index)
        self.custom_hint = dim_label(wrap=True)

        self.speed = QSlider(Qt.Orientation.Horizontal)
        self.speed.setRange(0, SLOWEST)
        self.speed.setPageStep(1)
        self.speed.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.speed.valueChanged.connect(lambda v: self._change(speed=SLOWEST - v))
        self.speed_note = dim_label()
        self.brightness = QSlider(Qt.Orientation.Horizontal)
        self.brightness.setRange(0, BRIGHTEST)
        self.brightness.setPageStep(1)
        self.brightness.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.brightness.valueChanged.connect(lambda v: self._change(brightness=v))
        self.brightness_note = dim_label()

        sliders = QHBoxLayout()
        sliders.setSpacing(40)
        for label, slider, low, high, note in (
                ("Brightness", self.brightness, "Off", "Bright", self.brightness_note),
                ("Speed", self.speed, "Slow", "Fast", self.speed_note)):
            heading = QHBoxLayout()
            title = QLabel(label)
            title.setFont(font(1.1, QFont.Weight.DemiBold))
            heading.addWidget(title)
            heading.addStretch(1)
            heading.addWidget(note)
            track = QHBoxLayout()
            track.addWidget(dim_label(low))
            track.addWidget(slider, 1)
            track.addWidget(dim_label(high))
            column = QVBoxLayout()
            column.addLayout(heading)
            column.addLayout(track)
            sliders.addLayout(column, 1)

        self.effect_about = dim_label(wrap=True)
        page = scroll_page(
            self.view,
            panel("", sliders),
            panel("Effect", effects, self.effect_about),
            panel("Key map", dim_label("Light only some keys. M1–M8 are built in; CM1 and CM2 are yours, "
                                       "recorded on the keyboard.", wrap=True), maps, self.custom_hint),
        )
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(page)
        self.group.idClicked.connect(lambda _: self._pick(self.group.checkedButton().property("choice")))
        self.current = None
        self._ready = False

    def _tile(self, title, about, choice):
        tile = QPushButton(title)
        tile.setObjectName("tile")
        tile.setCheckable(True)
        tile.setCursor(Qt.CursorShape.PointingHandCursor)
        tile.setFont(font(1.05))
        tile.setMinimumHeight(40)
        tile.setProperty("choice", choice)
        if about:
            tile.setToolTip(about)
        self.group.addButton(tile)
        return tile

    def _pick(self, choice):
        if self.current is None:
            return
        kind, number = choice
        self.app.write_lighting(self.current.with_effect(number) if kind == "effect" else self.current.with_map(number))

    def _change(self, **fields):
        if self.current is not None and self._ready:
            self.app.write_lighting(self.current._replace(**fields))

    def show_lighting(self, lighting):
        self._ready = False
        self.current = lighting
        self.view.set_lighting(lighting)
        choice = ("map", lighting.map) if lighting.is_map else ("effect", lighting.mode)
        for tile in self.group.buttons():
            tile.setChecked(tuple(tile.property("choice")) == choice)
        if not self.speed.isSliderDown():
            self.speed.setValue(SLOWEST - lighting.speed)
        if not self.brightness.isSliderDown():
            self.brightness.setValue(lighting.brightness)
        self.brightness_note.setText("Off" if lighting.brightness == 0 else f"{lighting.brightness} of {BRIGHTEST}")
        animated = not lighting.is_map and lighting.mode != 1
        self.speed.setEnabled(animated)
        self.speed_note.setText("" if animated else "Doesn't apply: this lighting doesn't move")
        self.effect_about.setText("" if lighting.is_map else EFFECT_INFO.get(lighting.mode, ("", ""))[1])
        self.effect_about.setVisible(not lighting.is_map)
        if lighting.is_map and lighting.map in CUSTOM_MAPS:
            n, key = (1, "9") if lighting.map == CUSTOM_MAPS[0] else (2, "0")
            self.custom_hint.setText(
                f"To record CM{n}: press Fn + {key}, then Fn + PrtSc (the lock lights blink), press the keys "
                f"that should light up, and press Fn + PrtSc again.")
        else:
            self.custom_hint.setText("")
        self.custom_hint.setVisible(bool(self.custom_hint.text()))
        self._ready = True


# Keys tab


class KeyDialog(QDialog):
    """Choose what a key sends: press a key, pick one from the list, or turn it off."""

    def __init__(self, parent, key, current):
        super().__init__(parent)
        self.setWindowTitle(f"{key.label or 'Space'} key")
        self.key = key
        self.choice = current
        self.capturing = False
        title = QLabel(f"What the {key.label or 'Space'} key sends")
        title.setFont(font(1.15, QFont.Weight.DemiBold))
        self.now = dim_label()
        self.capture = button("Press a key to use…", self._start_capture)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Search keys")
        self.filter.textChanged.connect(self._filter)
        self.list = QListWidget()
        self.list.setMinimumHeight(300)
        self._fill()
        self.list.currentItemChanged.connect(self._picked)
        self.list.itemDoubleClicked.connect(lambda _: self.accept())
        buttons = QDialogButtonBox()
        buttons.addButton("Default", QDialogButtonBox.ButtonRole.ResetRole).clicked.connect(
            lambda: self._set(key.factory, accept=True))
        buttons.addButton("Nothing", QDialogButtonBox.ButtonRole.ActionRole).clicked.connect(
            lambda: self._set(Binding(), accept=True))
        buttons.addButton(QDialogButtonBox.StandardButton.Ok).clicked.connect(self.accept)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.reject)
        box = QVBoxLayout(self)
        box.setSpacing(10)
        box.addWidget(title)
        box.addWidget(self.now)
        box.addWidget(self.capture)
        box.addWidget(self.filter)
        box.addWidget(self.list)
        box.addWidget(buttons)
        self.resize(420, 560)
        self._show_choice()

    def _fill(self):
        self.list.clear()
        entries = [("Modifiers", [Binding(mods=bit) for bit in MODIFIERS])]
        entries += [(group, [Binding(usage=u) for u in usages]) for group, usages in GROUPS]
        for group, bindings in entries:
            header = QListWidgetItem(group)
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            header.setFont(font(0.9, QFont.Weight.DemiBold))
            self.list.addItem(header)
            for binding in bindings:
                item = QListWidgetItem("    " + describe(binding))
                item.setData(Qt.ItemDataRole.UserRole, tuple(binding))
                self.list.addItem(item)

    def _filter(self, text):
        text = text.strip().lower()
        for row in range(self.list.count()):
            item = self.list.item(row)
            data = item.data(Qt.ItemDataRole.UserRole)
            item.setHidden(bool(text) and (data is None or text not in item.text().lower()))

    def _picked(self, item):
        if item is not None and item.data(Qt.ItemDataRole.UserRole) is not None:
            self.choice = Binding(*item.data(Qt.ItemDataRole.UserRole))
            self._show_choice()

    def _set(self, binding, accept=False):
        self.choice = binding
        self._show_choice()
        if accept:
            self.accept()

    def _show_choice(self):
        note = " (default)" if self.choice == self.key.factory else ""
        self.now.setText(f"Sends: {describe(self.choice)}{note}")

    def _start_capture(self):
        self.capturing = True
        self.capture.setText("Press the key now… (Esc cancels)")
        self.grabKeyboard()

    def keyPressEvent(self, event):
        if not self.capturing:
            return super().keyPressEvent(event)
        self.capturing = False
        self.releaseKeyboard()
        self.capture.setText("Press a key to use…")
        if event.key() == Qt.Key.Key_Escape:
            return
        binding = binding_for_code(event.nativeScanCode() - 8)
        if binding is None:
            self.now.setText("That key can't be sent by the keyboard: pick one from the list")
        else:
            self._set(binding)


class KeysTab(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.view = KeyboardView(app.theme, "keys")
        self.view.key_clicked.connect(self._edit)
        self.win_switch = Switch(app.theme)
        self.win_switch.toggled.connect(self._win)
        win_row = QHBoxLayout()
        win_text = QVBoxLayout()
        win_text.addWidget(QLabel("Turn off the Win key"))
        win_text.addWidget(dim_label("Saved with the keys, so it stays off on any computer. Fn + Win on the "
                                     "keyboard switches its own game mode.", wrap=True))
        win_row.addLayout(win_text, 1)
        win_row.addWidget(self.win_switch)
        self.changes = dim_label(wrap=True)
        reset = button("Reset all keys", self._reset)
        reset_row = QHBoxLayout()
        reset_row.addWidget(self.changes, 1)
        reset_row.addWidget(reset)
        page = scroll_page(
            dim_label("Click a key to change what it sends. Changes are saved in the keyboard and work without "
                      "this app, on any computer.", wrap=True),
            self.view,
            panel("", reset_row),
            panel("", win_row),
        )
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(page)
        self.bindings = None

    def show_bindings(self, bindings):
        self.bindings = bindings
        self.view.set_bindings(bindings)
        changed = [k for k in KEYS if bindings[k.position] != k.factory]
        if changed:
            names = ", ".join(f"{k.label or 'Space'} → {describe(bindings[k.position])}" for k in changed[:6])
            more = f" and {len(changed) - 6} more" if len(changed) > 6 else ""
            self.changes.setText(f"Changed: {names}{more}")
        else:
            self.changes.setText("All keys send what's printed on them.")
        self.win_switch.blockSignals(True)
        self.win_switch.setChecked(bindings[WIN_KEY.position].empty)
        self.win_switch.blockSignals(False)

    def _edit(self, key):
        if self.bindings is None:
            return
        dialog = KeyDialog(self, key, self.bindings[key.position])
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.choice != self.bindings[key.position]:
            self._write({key.position: dialog.choice})

    def _win(self, off):
        self._write({WIN_KEY.position: Binding() if off else WIN_KEY.factory})

    def _reset(self):
        if self.bindings is None:
            return
        changed = {k.position: k.factory for k in KEYS if self.bindings[k.position] != k.factory}
        if changed:
            self._write(changed)

    def _write(self, changes):
        bindings = list(self.bindings)
        for position, binding in changes.items():
            bindings[position] = binding
        self.app.write_keymap(bindings)


# Keyboard tab


class KeyboardTab(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.status = QLabel()
        self.status.setFont(font(1.05))
        self.detail = dim_label(wrap=True)
        backup = button("Back up…", app.backup)
        restore = button("Restore…", app.restore)
        backup_row = QHBoxLayout()
        backup_row.addWidget(dim_label("Save the lighting and the keys to a file, and put them back later.", wrap=True), 1)
        backup_row.addWidget(backup)
        backup_row.addWidget(restore)
        shortcuts = QGridLayout()
        shortcuts.setHorizontalSpacing(24)
        shortcuts.setVerticalSpacing(5)
        for row, (combo, action) in enumerate(FN_SHORTCUTS):
            label = QLabel(combo)
            label.setFont(font(0.95, QFont.Weight.DemiBold))
            shortcuts.addWidget(label, row, 0)
            shortcuts.addWidget(dim_label(action, 0.95), row, 1)
        shortcuts.setColumnStretch(2, 1)
        page = scroll_page(
            panel("HATOR Starfall", self.status, self.detail),
            panel("Backup", backup_row),
            panel("Shortcuts on the keyboard", shortcuts,
                  dim_label("Fn + Esc resets lighting and keys to the factory settings.", wrap=True)),
        )
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(page)

    def show_state(self, connected, node="", lighting=None):
        if connected:
            self.status.setText("Connected")
            what = ("map " + (f"M{lighting.map}" if lighting.map in PRESET_MAPS else
                              f"CM{CUSTOM_MAPS.index(lighting.map) + 1}" if lighting.map in CUSTOM_MAPS else
                              str(lighting.map))) if lighting and lighting.is_map else (
                EFFECT_INFO.get(lighting.mode, (str(lighting.mode),))[0] if lighting else "")
            self.detail.setText(f"USB 258a:002a (Sino Wealth), {node}. Lighting: {what}.")
        else:
            self.status.setText("Not connected")
            self.detail.setText("")


# Window


class Banner(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("banner")
        box = QVBoxLayout(self)
        box.setContentsMargins(16, 12, 16, 12)
        self.title = QLabel()
        self.title.setFont(font(1.05, QFont.Weight.DemiBold))
        self.text = dim_label(wrap=True)
        self.text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        box.addWidget(self.title)
        box.addWidget(self.text)

    def show_problem(self, problem):
        if problem == "access":
            self.title.setText("No access to the keyboard")
            self.text.setText("Starfall Control needs a udev rule (the package installs it). To add it by hand, "
                              "run in a terminal and replug the keyboard:\n\n" + UDEV_HINT)
        else:
            self.title.setText("HATOR Starfall not found")
            self.text.setText("Plug in the keyboard. Starfall Control finds it by its USB ID, 258a:002a.")
        self.show()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.theme = Theme()
        QApplication.instance().setStyleSheet(self.theme.stylesheet())
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon.fromTheme("input-keyboard"))
        self.connection = Connection()
        self.lighting = None
        self.bindings = None

        root = QWidget()
        root.setObjectName("root")
        title = QLabel("HATOR Starfall")
        title.setFont(font(1.7, QFont.Weight.Bold))
        self.tabs = Segmented(["Lighting", "Keys", "Keyboard"])
        self.pill = QLabel()
        self.pill.setObjectName("pill")
        header = QHBoxLayout()
        header.setContentsMargins(28, 18, 28, 6)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.tabs)
        header.addStretch(1)
        header.addWidget(self.pill)
        self.banner = Banner()
        self.banner.hide()
        banner_row = QHBoxLayout()
        banner_row.setContentsMargins(28, 4, 28, 0)
        banner_row.addWidget(self.banner)

        self.lighting_tab = LightingTab(self)
        self.keys_tab = KeysTab(self)
        self.keyboard_tab = KeyboardTab(self)
        self.stack = QStackedWidget()
        for tab in (self.lighting_tab, self.keys_tab, self.keyboard_tab):
            self.stack.addWidget(tab)
        self.tabs.changed.connect(self.stack.setCurrentIndex)

        version = button(f"{APP_NAME} {__version__}", self.show_about, "flat")
        version.setFont(font(0.9))
        footer = QHBoxLayout()
        footer.setContentsMargins(22, 4, 22, 10)
        footer.addStretch(1)
        footer.addWidget(version)

        column = QVBoxLayout(root)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addLayout(header)
        column.addLayout(banner_row)
        column.addWidget(self.stack, 1)
        column.addWidget(hline())
        column.addLayout(footer)
        self.setCentralWidget(root)
        self.resize(1080, 820)

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(POLL_MS)
        self.poll_timer.timeout.connect(self.poll)
        self.poll_timer.start()
        self.poll(full=True)

    # keyboard state

    def _set_connected(self, connected):
        for tab in (self.lighting_tab, self.keys_tab):
            tab.setEnabled(connected)
        if connected:
            self.banner.hide()
            self.pill.setText(f'<span style="color:{self.theme.green}">●</span>&nbsp;Connected')
        else:
            self.banner.show_problem(self.connection.problem)
            self.pill.setText(f'<span style="color:{self.theme.dim}">●</span>&nbsp;Not connected')
            self.keyboard_tab.show_state(False)

    def poll(self, full=False):
        """Read the lighting (the keyboard's Fn keys change it too) and, on (re)connect, the keymap."""
        if not self.isActiveWindow() and not full and self.lighting is not None:
            return
        fresh = self.connection.keyboard is None
        keyboard = self.connection.get()
        if keyboard is None:
            self.lighting = self.bindings = None
            self._set_connected(False)
            return
        try:
            lighting = keyboard.lighting()
            if fresh or full or self.bindings is None:
                self.bindings = keyboard.keymap()
                self.keys_tab.show_bindings(self.bindings)
        except OSError:
            self.connection.drop()
            self.lighting = self.bindings = None
            self._set_connected(False)
            return
        if lighting != self.lighting:
            self.lighting = lighting
            self.lighting_tab.show_lighting(lighting)
        self._set_connected(True)
        self.keyboard_tab.show_state(True, keyboard.node, lighting)

    def write_lighting(self, lighting):
        keyboard = self.connection.get()
        if keyboard is None:
            return self._set_connected(False)
        try:
            self.lighting = keyboard.set_lighting(lighting)
        except OSError as err:
            self._failed("Couldn't change the lighting", err)
            self.lighting = None
            return self.poll(full=True)
        self.lighting_tab.show_lighting(self.lighting)
        self.keyboard_tab.show_state(True, keyboard.node, self.lighting)

    def write_keymap(self, bindings):
        keyboard = self.connection.get()
        if keyboard is None:
            return self._set_connected(False)
        try:
            self.bindings = keyboard.set_keymap(bindings)
        except OSError as err:
            self._failed("Couldn't save the keys", err)
            return self.poll(full=True)
        self.keys_tab.show_bindings(self.bindings)

    def _failed(self, what, err):
        self.connection.drop()
        QMessageBox.warning(self, APP_NAME, f"{what}: {err}")

    # backups

    def backup(self):
        if self.lighting is None or self.bindings is None:
            return
        name = f"starfall-backup-{time.strftime('%Y-%m-%d')}.json"
        path, _ = QFileDialog.getSaveFileName(self, "Back up the keyboard", os.path.expanduser(f"~/{name}"),
                                              "Starfall backups (*.json)")
        if not path:
            return
        data = {"starfall_backup": BACKUP_FORMAT, "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "app": __version__, "lighting": list(self.lighting),
                "keymap": b"".join(b.entry() for b in self.bindings).hex()}
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
        except OSError as err:
            QMessageBox.warning(self, APP_NAME, f"Couldn't save the backup: {err}")

    def restore(self):
        path, _ = QFileDialog.getOpenFileName(self, "Restore the keyboard", os.path.expanduser("~"),
                                              "Starfall backups (*.json)")
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
            if data.get("starfall_backup") != BACKUP_FORMAT:
                raise ValueError("this isn't a Starfall Control backup")
            lighting = Lighting(*data["lighting"])
            bindings = parse_keymap(bytes.fromhex(data["keymap"]))
        except (OSError, ValueError, KeyError, TypeError) as err:
            QMessageBox.warning(self, APP_NAME, f"Couldn't read the backup: {err}")
            return
        answer = QMessageBox.question(self, APP_NAME, f"Put the lighting and keys from {os.path.basename(path)} "
                                      "back on the keyboard?")
        if answer == QMessageBox.StandardButton.Yes:
            self.write_keymap(bindings)
            self.write_lighting(lighting)

    def show_about(self):
        box = QMessageBox(self)
        box.setWindowTitle(f"About {APP_NAME}")
        box.setIconPixmap(QIcon.fromTheme("input-keyboard").pixmap(64, 64))
        box.setText(f"<b>{APP_NAME}</b><br>Version {__version__}")
        box.setInformativeText(
            f"Lighting and key settings for the HATOR Starfall keyboard (Sino Wealth, USB 258a:002a).<br><br>"
            f"Author: {__author__} · MIT license<br>Not affiliated with or endorsed by HATOR. The protocol was "
            f"worked out from the keyboard itself.")
        box.exec()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("starfall-control")
    app.setDesktopFileName("starfall-control")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
