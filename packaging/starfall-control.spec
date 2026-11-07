# Built by packaging/build-rpm.sh, which defines pkg_version and source_root (this checkout).
%global source_date_epoch_from_changelog 0

Name:           starfall-control
Version:        %{pkg_version}
Release:        1
Summary:        Lighting and key settings for the HATOR Starfall keyboard
License:        MIT
URL:            https://github.com/Athet-psl/hator-starfall-control
BuildArch:      noarch
Requires:       python3, python3-pyqt6

%description
HATOR Starfall Control sets the lighting effect, key map, speed and
brightness of the HATOR Starfall keyboard (Sino Wealth 258a:002a) and
remaps its keys. Everything is saved in the keyboard itself.

%install
%{source_root}/packaging/stage.sh %{buildroot} %{version} rpm

%preun
if [ "$1" -eq 0 ]; then
    find /usr/share/starfall-control -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
fi

%postun
if [ "$1" -eq 0 ]; then
    udevadm control --reload >/dev/null 2>&1 || true
fi

%posttrans
python3 -m compileall -q /usr/share/starfall-control/starfall >/dev/null 2>&1 || true
udevadm control --reload >/dev/null 2>&1 || true
udevadm trigger --subsystem-match=hidraw >/dev/null 2>&1 || true

%files
%license /usr/share/doc/starfall-control/copyright
%doc /usr/share/doc/starfall-control/README.md
/usr/bin/starfall-control
/usr/share/starfall-control
/usr/lib/udev/rules.d/70-starfall-control.rules
/usr/share/applications/starfall-control.desktop
