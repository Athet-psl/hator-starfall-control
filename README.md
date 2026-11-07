# HATOR Starfall Control

Lighting and key settings for the **HATOR Starfall** keyboard (Rainbow, Outemu Red HTK-608 / Blue HTK-609)
on Linux. Everything is saved in the keyboard, so it stays without the app, on any computer.

- **Lighting:** the keyboard's 8 effects, the 8 built-in key maps M1–M8 and the custom maps CM1/CM2, speed,
  brightness (or off). The window shows a preview of each effect.
- **Keys:** make any key send another key or modifier, or nothing. A switch turns off the Win key.
- **Backup:** save the lighting and keys to a file and restore them.

HATOR's Windows app is for the Starfall **RGB** (a SONiX chip) and can't talk to this keyboard, so the protocol
was worked out from the keyboard itself.

## Install

Download the package from [Releases](https://github.com/Athet-psl/hator-starfall-control/releases/latest): `starfall-control_…_all.deb` for Ubuntu and Debian,
`starfall-control-…noarch.rpm` for Fedora. Or build it from this checkout:

```sh
packaging/build-deb.sh 0.1.0 && sudo apt install ./dist/starfall-control_0.1.0_all.deb
packaging/build-rpm.sh 0.1.0 && sudo dnf install ./dist/starfall-control-0.1.0-1.noarch.rpm   # needs rpm-build
```

Then open **HATOR Starfall Control** from the app menu. The package needs PyQt6 and installs a udev rule for
the keyboard. On Ubuntu it lets the `plugdev` group (the desktop user) change the keyboard's settings. Fedora
has no `plugdev`, so there the rule gives access to the logged-in user.

## How it works

The keyboard is a Sino Wealth chip, USB `258a:002a`. Interface 1 has vendor feature reports:

| Report | Size | Contents |
|---|---|---|
| 10 | 41 | Lighting: `[mode, map, speed, brightness, 0…]` |
| 9 | 504 | Keymap: 126 matrix positions × `[0, modifier bits, HID usage, 0]`, 21 columns of 6 rows |
| 11 | 126 | Unknown. Writing it only sets the map byte of report 10 |
| 12 | 1920 | Unknown, not readable. Probably where custom maps live |
| 5 | 5 | Probably a command channel. Not used |

- **Mode** 1–8 is an effect (static, reactive, breathing, snake, corners, spiral, wave, ripple), and the map byte
  stays 10. Mode 9 lights a key map instead: map 1–8 = M1–M8, 9 = CM1, 10 = CM2.
- **Speed** 0 is the fastest, 4 the slowest. **Brightness** 0 is off, 5 the brightest.
- Reports 9 and 10 read back with GET_FEATURE. Right after a change, report 10 can carry leftovers after byte 4.
- The Fn key is matrix usage `0xb0` and is handled by the keyboard itself.

Feature reports work through a **write-only** handle to the hidraw node, so the Ubuntu udev rule grants write
access only (`MODE="0620"`). Programs can change settings but can't read keystrokes, which the same
interface also sends. Fedora's rule (`uaccess`) gives the logged-in user read access as well.

Custom maps CM1/CM2 are recorded on the keyboard: Fn + 9 (or Fn + 0), Fn + PrtSc, the keys to light, Fn + PrtSc.

## Development

```sh
python3 -m unittest discover tests
bin/starfall-control
```

Every push to `main` runs the tests, builds the .deb on Ubuntu and the .rpm on Fedora and publishes them as
release `v0.1.<commit count>`, with the messages of the commits since the previous release as its notes.

`research/` has the probes used to work out the protocol, and the keyboard's factory readout.

## Disclaimer

Not affiliated with or endorsed by HATOR. Comes without warranty. Fn + Esc resets the keyboard to its
factory settings.

## License

MIT, see [LICENSE](LICENSE).
