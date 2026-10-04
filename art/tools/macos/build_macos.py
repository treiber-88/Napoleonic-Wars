"""
Builds the macOS version of the Napoleonic Wars mod on Windows.

It takes the official "OpenRA - Red Alert.app" out of OpenRA's macOS release image (same engine release as the
Windows build), adds the mod and writes "Napoleonic Wars.app" straight into a .zip with Unix permissions,
because an app bundle copied or zipped through Windows loses its executable bits.

Inputs
  --hfs    raw HFS+ partition of OpenRA-<release>.dmg       (7z x -tdmg OpenRA-...dmg  ->  4.hfs)
  --dll    OpenRA.Mods.Napoleonic.dll built with PlatformTarget=AnyCPU (the Windows build is x64-only)
  --out    output folder

Usage
  7z x -tdmg -oC:/Temp/nw_macos/raw OpenRA-playtest-20260222.dmg
  dotnet build source/OpenRA.Mods.Napoleonic -c Release -p:PlatformTarget=AnyCPU -p:OutputPath=C:/Temp/nw_macos/dll/ -p:IntermediateOutputPath=C:/Temp/nw_macos/obj/
  python art/tools/macos/build_macos.py --hfs C:/Temp/nw_macos/raw/4.hfs --dll C:/Temp/nw_macos/dll/OpenRA.Mods.Napoleonic.dll --out "C:/Users/<you>/Desktop/Napoleonic Wars MacOS"
"""
import argparse
import io
import os
import time
import zipfile

from PIL import Image

from hfs_read import Volume

GAME = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
SOURCE_APP = "OpenRA - Red Alert.app"
APP = "Napoleonic Wars.app"
MOD_ID = "napoleonic"
ZIP_NAME = "Napoleonic Wars macOS.zip"
SETUP = "First time setup.command"
README = "READ ME.txt"

INFO_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "https://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleDevelopmentRegion</key>
	<string>English</string>
	<key>CFBundleDisplayName</key>
	<string>Napoleonic Wars</string>
	<key>CFBundleExecutable</key>
	<string>Launcher</string>
	<key>CFBundleIconFile</key>
	<string>napoleonic.icns</string>
	<key>CFBundleIdentifier</key>
	<string>net.openra.mod.napoleonic</string>
	<key>CFBundleInfoDictionaryVersion</key>
	<string>6.0</string>
	<key>CFBundleName</key>
	<string>Napoleonic Wars</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleShortVersionString</key>
	<string>{version}</string>
	<key>CFBundleSignature</key>
	<string>????</string>
	<key>CFBundleVersion</key>
	<string>{version}</string>
	<key>LSMinimumSystemVersion</key>
	<string>10.15</string>
	<key>NSPrincipalClass</key>
	<string>NSApplication</string>
	<key>LSApplicationCategoryType</key>
	<string>public.app-category.games</string>
	<key>CFBundleURLTypes</key>
	<array>
		<dict>
			<key>CFBundleURLName</key>
			<string>OpenRA Server</string>
			<key>CFBundleURLSchemes</key>
			<array>
				<string>openra-napoleonic-{version}</string>
			</array>
		</dict>
	</array>
	<key>ModId</key>
	<string>napoleonic</string>
	<key>FaqUrl</key>
	<string>https://wiki.openra.net/FAQ</string>
	<key>JoinServerUrlScheme</key>
	<string>openra-napoleonic-{version}</string>
	<key>NSRequiresAquaSystemAppearance</key>
	<false/>
	<key>NSPrefersDisplaySafeAreaCompatibilityMode</key>
	<false/>
</dict>
</plist>
"""

SETUP_SCRIPT = """#!/bin/bash
# Napoleonic Wars - first time setup on a Mac.
# The app is the official OpenRA Red Alert app with the Napoleonic Wars mod added, so Apple's original
# signature no longer matches and macOS refuses to open it until it is signed again on this Mac.
cd "$(dirname "$0")"
APP="Napoleonic Wars.app"
if [ ! -d "$APP" ]; then
	echo "Put this file in the same folder as '$APP' and run it again."
	read -r -p "Press Return to close." _
	exit 1
fi
echo "Removing the download quarantine flag..."
xattr -cr "$APP"
echo "Signing the app for this Mac (ad hoc)..."
codesign --force --deep --sign - "$APP" || echo "Signing failed; trying to open it anyway."
echo "Opening Napoleonic Wars..."
open "$APP"
echo "Done. From now on just double-click '$APP' (you can move it to Applications)."
"""

README_TEXT = """NAPOLEONIC WARS - macOS VERSION
===============================

What this is
    "Napoleonic Wars.app": the official OpenRA Red Alert app for macOS ({release}) with the
    Napoleonic Wars mod added. It runs on Intel Macs and Apple Silicon (M1 and later), macOS 10.15 or newer.

    It was assembled on Windows and has NOT been tested on a Mac.

How to install (on the Mac)
    1. Copy "{zip}" to the Mac and double-click it to unzip. Unzip it ON THE MAC:
       do not unzip it on Windows and copy the folder over, or the app loses the permissions it needs to start.
    2. Double-click "{setup}".
       macOS may refuse because the file was downloaded. If so: right-click it and choose Open, or go to
       System Settings > Privacy & Security and click "Open Anyway", then run it again.
       It removes the download quarantine flag, signs the app for that Mac and opens the game.
    3. After that, open "Napoleonic Wars.app" normally. You can move it to Applications.

    The same thing by hand, in Terminal, from the folder that holds the app:
        xattr -cr "Napoleonic Wars.app"
        codesign --force --deep --sign - "Napoleonic Wars.app"
        open "Napoleonic Wars.app"

Why step 2 is needed
    The official app is signed by the OpenRA developers. Adding the mod changes the app, so that signature
    no longer matches and macOS reports the app as "damaged" or from an unidentified developer.
    Signing it again on the Mac itself ("ad hoc") fixes that. Nothing is sent anywhere.

First start
    The mod uses some original Red Alert files (sounds, terrain). On a Mac that does not have them yet the game
    shows OpenRA's content installer first, which can download them. They are stored in
    ~/Library/Application Support/OpenRA, not inside the app.

Multiplayer with Windows players
    Everyone needs the same version of the mod. This build was made {date} from the Windows copy of that day.
    After changing the mod on Windows, build this again:  python art/tools/macos/build_macos.py  (see its header).

Contents of this folder
    {zip}      the app, to be unzipped on a Mac
    {readme}   this file
"""


class Bundle:
    """Collects the files of the app; written as a zip with Unix permissions and no Windows detour."""

    def __init__(self):
        self.files = {}     # arcname -> (bytes, mode)
        self.dirs = {}      # arcname -> mode

    def add_dir(self, name, mode=0o755):
        parts = name.strip("/").split("/")
        for i in range(1, len(parts) + 1):
            self.dirs.setdefault("/".join(parts[:i]), 0o755)
        self.dirs[name.strip("/")] = mode or 0o755

    def add(self, name, data, mode=0o644):
        self.add_dir(os.path.dirname(name))
        self.files[name] = (data, mode or 0o644)

    def write(self, path):
        stamp = time.localtime()[:6]
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for d in sorted(self.dirs):
                if not d:
                    continue
                zi = zipfile.ZipInfo(d + "/", stamp)
                zi.create_system = 3
                zi.external_attr = ((0o040000 | self.dirs[d]) << 16) | 0x10
                z.writestr(zi, b"")
            for name in sorted(self.files):
                data, mode = self.files[name]
                zi = zipfile.ZipInfo(name, stamp)
                zi.create_system = 3
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = (0o100000 | mode) << 16
                z.writestr(zi, data)


def make_icns():
    """App icon from the mod's own French line infantry portrait (the same picture as the Windows launcher icon)."""
    src = Image.open(os.path.join(GAME, "art", "renders", "icons", "fr_line.png")).convert("RGBA")
    side = 1024
    bg = Image.new("RGBA", (side, side), (32, 44, 72, 255))
    im = src.resize((int(src.width * side / src.height), side), Image.LANCZOS)
    bg.alpha_composite(im, ((side - im.width) // 2, 0))
    buf = io.BytesIO()
    bg.save(buf, format="ICNS")
    return buf.getvalue()


def mod_version():
    for line in open(os.path.join(GAME, "mods", MOD_ID, "mod.yaml"), encoding="utf-8"):
        if line.strip().startswith("Version:"):
            return line.split(":", 1)[1].strip()
    return "dev"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hfs", required=True)
    ap.add_argument("--dll", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    vol = Volume(open(args.hfs, "rb"))
    b = Bundle()
    release = "unknown release"
    skipped = 0
    for rel, e in vol.walk(SOURCE_APP):
        # The original signature covers the original contents; it is recreated on the Mac.
        if rel.startswith("Contents/_CodeSignature") or rel in ("Contents/CodeResources", "Contents/Info.plist"):
            skipped += 1
            continue
        name = APP + "/" + rel
        if e.kind == "dir":
            b.add_dir(name, e.mode)
        elif e.kind == "file":
            data = vol.read(e)
            if rel == "Contents/Resources/VERSION":
                release = data.decode().strip()
            b.add(name, data, e.mode)
        else:
            raise SystemExit("unexpected %s in the official app: %s" % (e.kind, rel))

    # The mod itself, exactly as in the Windows game folder.
    mod_root = os.path.join(GAME, "mods", MOD_ID)
    mod_files = 0
    for folder, _, files in os.walk(mod_root):
        for f in files:
            full = os.path.join(folder, f)
            rel = os.path.relpath(full, mod_root).replace(os.sep, "/")
            b.add(f"{APP}/Contents/Resources/mods/{MOD_ID}/{rel}", open(full, "rb").read())
            mod_files += 1

    # The mod's code, next to the engine, for both processor types.
    dll = open(args.dll, "rb").read()
    for arch in ("arm64", "x86_64"):
        b.add(f"{APP}/Contents/MacOS/{arch}/OpenRA.Mods.Napoleonic.dll", dll)

    version = mod_version()
    b.add(f"{APP}/Contents/Info.plist", INFO_PLIST.format(version=version).encode("utf-8"))
    b.add(f"{APP}/Contents/Resources/napoleonic.icns", make_icns())
    b.add(SETUP, SETUP_SCRIPT.replace("\r\n", "\n").encode("utf-8"), 0o755)

    os.makedirs(args.out, exist_ok=True)
    zip_path = os.path.join(args.out, ZIP_NAME)
    b.write(zip_path)
    text = README_TEXT.format(release=release, zip=ZIP_NAME, setup=SETUP, readme=README, date=time.strftime("%Y-%m-%d"))
    with open(os.path.join(args.out, README), "w", encoding="utf-8", newline="\r\n") as f:
        f.write(text)
    print(f"engine {release}; official files {len(b.files) - mod_files - 5}, signature files left out {skipped}, mod files {mod_files}")
    print(f"wrote {zip_path} ({os.path.getsize(zip_path) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
