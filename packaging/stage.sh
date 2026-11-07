#!/bin/sh
# Installs HATOR Starfall Control into ROOT (a package's staging tree) as version VERSION.
# FLAVOUR is deb (the udev rule for the plugdev group) or rpm (Fedora's rule, for the logged-in user).
# Used by build-deb.sh and starfall-control.spec.
set -eu

usage="usage: packaging/stage.sh ROOT VERSION deb|rpm"
pkg=${1:?$usage}
version=${2:?$usage}
flavour=${3:?$usage}
root=$(cd "$(dirname "$0")/.." && pwd)
app=$pkg/usr/share/starfall-control
case $flavour in
    deb) rules=$root/data/70-starfall-control.rules ;;
    rpm) rules=$root/data/fedora/70-starfall-control.rules ;;
    *) echo "$usage" >&2; exit 2 ;;
esac

mkdir -p "$app/bin" "$pkg/usr/bin"
cp -r "$root/starfall" "$app/"
find "$app" -name __pycache__ -prune -exec rm -rf {} +
sed -i "s/^__version__ = .*/__version__ = \"$version\"/" "$app/starfall/__init__.py"
install -m 755 "$root/bin/starfall-control" "$app/bin/"
ln -s ../share/starfall-control/bin/starfall-control "$pkg/usr/bin/starfall-control"
install -D -m 644 "$root/data/starfall-control.desktop" "$pkg/usr/share/applications/starfall-control.desktop"
install -D -m 644 "$rules" "$pkg/usr/lib/udev/rules.d/70-starfall-control.rules"
install -D -m 644 "$root/LICENSE" "$pkg/usr/share/doc/starfall-control/copyright"
install -m 644 "$root/README.md" "$pkg/usr/share/doc/starfall-control/"

find "$pkg/usr" -type d -exec chmod 755 {} +
find "$pkg/usr" -type f -exec chmod 644 {} +
chmod 755 "$app/bin/starfall-control"
