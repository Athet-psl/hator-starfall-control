#!/bin/sh
# Builds dist/starfall-control_VERSION_all.deb from this checkout.
set -eu

version=${1:?usage: packaging/build-deb.sh VERSION}
root=$(cd "$(dirname "$0")/.." && pwd)
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
pkg=$stage/starfall-control
app=$pkg/usr/share/starfall-control

mkdir -p "$app/bin" "$pkg/usr/bin" "$pkg/DEBIAN"
cp -r "$root/starfall" "$app/"
find "$app" -name __pycache__ -prune -exec rm -rf {} +
sed -i "s/^__version__ = .*/__version__ = \"$version\"/" "$app/starfall/__init__.py"
install -m 755 "$root/bin/starfall-control" "$app/bin/"
ln -s ../share/starfall-control/bin/starfall-control "$pkg/usr/bin/starfall-control"
install -D -m 644 "$root/data/starfall-control.desktop" "$pkg/usr/share/applications/starfall-control.desktop"
install -D -m 644 "$root/data/70-starfall-control.rules" "$pkg/usr/lib/udev/rules.d/70-starfall-control.rules"
install -D -m 644 "$root/README.md" "$pkg/usr/share/doc/starfall-control/README.md"
install -m 755 "$root/packaging/postinst" "$root/packaging/postrm" "$pkg/DEBIAN/"

cat > "$pkg/DEBIAN/control" <<CONTROL
Package: starfall-control
Version: $version
Architecture: all
Maintainer: Athet-psl <186676948+Athet-psl@users.noreply.github.com>
Installed-Size: $(du -sk "$pkg/usr" | cut -f1)
Depends: python3, python3-pyqt6
Section: utils
Priority: optional
Description: lighting and key settings for the HATOR Starfall keyboard
 HATOR Starfall Control sets the lighting effect, key map, speed and
 brightness of the HATOR Starfall keyboard (Sino Wealth 258a:002a) and
 remaps its keys. Everything is saved in the keyboard itself.
CONTROL

find "$pkg" -type d -exec chmod 755 {} +
find "$pkg/usr" -type f -exec chmod 644 {} +
chmod 755 "$app/bin/starfall-control"

mkdir -p "$root/dist"
dpkg-deb --root-owner-group --build "$pkg" "$root/dist/starfall-control_${version}_all.deb"
