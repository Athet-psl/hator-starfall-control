#!/bin/sh
# Builds dist/starfall-control_VERSION_all.deb from this checkout.
set -eu

version=${1:?usage: packaging/build-deb.sh VERSION}
root=$(cd "$(dirname "$0")/.." && pwd)
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
pkg=$stage/starfall-control

"$root/packaging/stage.sh" "$pkg" "$version" deb
mkdir -p "$pkg/DEBIAN"
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
Homepage: https://github.com/Athet-psl/hator-starfall-control
Description: lighting and key settings for the HATOR Starfall keyboard
 HATOR Starfall Control sets the lighting effect, key map, speed and
 brightness of the HATOR Starfall keyboard (Sino Wealth 258a:002a) and
 remaps its keys. Everything is saved in the keyboard itself.
CONTROL

chmod 755 "$pkg/DEBIAN"
mkdir -p "$root/dist"
dpkg-deb --root-owner-group --build "$pkg" "$root/dist/starfall-control_${version}_all.deb"
