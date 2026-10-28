"""
Builds the macOS package of the Napoleonic Wars mod on Windows, as loose files for the Napoleonic-Wars-MacOS
git repository (GitHub's "Download ZIP" of that repository is what a Mac user gets).

The official OpenRA app for macOS is used UNMODIFIED, so Apple's signature and notarisation stay valid, nothing
has to be signed on the Mac and no file needs to be anywhere near GitHub's 100 MB limit. (An earlier version put
the mod inside a copy of the app: that breaks the signature, and an app that passes through Windows or git also
loses its executable permissions, so macOS refused to launch it.) The mod is loaded from outside the app:

  * the start script copies the mod folder and its DLL to /Users/Shared/NapoleonicWars,
  * it starts the official launcher with  Engine.ModSearchPaths=<app>/Contents/Resources/mods,/Users/Shared/NapoleonicWars/mods
    and  Game.Mod=napoleonic  (the launcher passes arguments through; later arguments override its own Game.Mod),
  * the Mac copy of mod.yaml names the DLL by absolute path: the engine joins assembly names to its binary
    folder with Path.Combine, which returns an absolute second argument unchanged.

The only file that should be executable is the start script. Git on Windows does not record that by itself:
    git add --chmod=+x "Play Napoleonic Wars.command"
(The READ ME also explains how to start it with `bash`, which works without the permission.)

Usage
  dotnet build source/OpenRA.Mods.Napoleonic -c Release -p:PlatformTarget=AnyCPU -p:OutputPath=C:/Temp/nw_macos/dll/ -p:IntermediateOutputPath=C:/Temp/nw_macos/obj/
  python art/tools/macos/build_macos.py --dll C:/Temp/nw_macos/dll/OpenRA.Mods.Napoleonic.dll --out "<path to the Napoleonic-Wars-MacOS repository>"
"""
import argparse
import os
import shutil
import time

GAME = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
MOD_ID = "napoleonic"
INSTALL_DIR = "/Users/Shared/NapoleonicWars"
DLL = "OpenRA.Mods.Napoleonic.dll"
SCRIPT = "Play Napoleonic Wars.command"
README = "README.md"
OPENRA_RELEASES = "https://github.com/OpenRA/OpenRA/releases/tag/{engine}"
OPENRA_DMG = "https://github.com/OpenRA/OpenRA/releases/download/{engine}/OpenRA-{engine}.dmg"

PLAY_SCRIPT = """#!/bin/bash
# Napoleonic Wars for macOS.
# Starts the official, unmodified OpenRA app with the Napoleonic Wars mod loaded from outside the app,
# so nothing has to be signed and macOS has nothing to object to.
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="{install_dir}"
ENGINE="{engine}"

pause() {{ echo; read -r -p "Press Return to close this window." _; }}

APP=""
for c in "/Applications/OpenRA - Red Alert.app" "$HOME/Applications/OpenRA - Red Alert.app" "$HERE/OpenRA - Red Alert.app" "$HOME/Desktop/OpenRA - Red Alert.app" "$HOME/Downloads/OpenRA - Red Alert.app"; do
	if [ -d "$c" ]; then APP="$c"; break; fi
done

if [ -z "$APP" ]; then
	echo "OpenRA is not installed yet."
	echo
	echo "Download OpenRA $ENGINE for macOS:"
	echo "  {dmg_url}"
	echo "Open the .dmg, drag 'OpenRA - Red Alert' into Applications, open it once, quit it, then run this again."
	pause
	exit 1
fi

VERSION="$(cat "$APP/Contents/Resources/VERSION" 2>/dev/null)"
if [ "$VERSION" != "$ENGINE" ]; then
	echo "Warning: this mod was built for OpenRA $ENGINE, but '$APP' is version '$VERSION'."
	echo "It may not start. Install OpenRA $ENGINE from {releases_url}"
	echo
fi

if [ ! -f "$HERE/files/{dll}" ] || [ ! -d "$HERE/files/mods/{mod}" ]; then
	echo "The 'files' folder is missing. Keep this script in the folder it came in."
	pause
	exit 1
fi

echo "Installing the mod files to $DEST ..."
mkdir -p "$DEST" || {{ echo "Could not create $DEST"; pause; exit 1; }}
rm -rf "$DEST/mods"
cp -R "$HERE/files/mods" "$DEST/mods" && cp "$HERE/files/{dll}" "$DEST/{dll}" || {{ echo "Copying the mod files failed."; pause; exit 1; }}
xattr -cr "$DEST" 2>/dev/null

echo "Starting Napoleonic Wars with $APP ..."
open -n "$APP" --args "Engine.ModSearchPaths=$APP/Contents/Resources/mods,$DEST/mods" "Game.Mod={mod}" || {{ echo "macOS could not open OpenRA."; pause; exit 1; }}
echo "Started. You can close this window."
"""

README_TEXT = """# Napoleonic Wars for macOS

The Napoleonic Wars mod, running on the official OpenRA app for macOS (`{engine}`).
The OpenRA app itself is not changed, so there is nothing to sign and no "damaged app" warning.
Works on Intel Macs and Apple Silicon (M1 and later), macOS 10.15 or newer.

> Put together on Windows and **not yet tested on a Mac**.

## Install

1. **Install OpenRA `{engine}`.** Download [OpenRA-{engine}.dmg]({dmg_url})
   (from the [official release page]({releases_url})), open it and drag **OpenRA - Red Alert** into Applications.
   Open it once so macOS asks its usual "downloaded from the internet" question, then quit it.
2. **Download this repository on the Mac**: the green **Code** button, then **Download ZIP**, and double-click the zip.
   Do the download and unzip on the Mac itself, not on Windows.
3. **Start the game**: in the unzipped folder, double-click **{script}**.

macOS will not open a downloaded script by double-click the first time. Any one of these gets past that:

- right-click the script and choose **Open**, then **Open** again; or
- **System Settings > Privacy & Security**, scroll down and click **Open Anyway**; or
- open **Terminal**, type `bash` and a space, drag the script into the Terminal window and press Return.
  This last way always works, including when macOS says the file "could not be executed".

## Playing

Start the game with **{script}** every time. It copies the mod to `{install_dir}` and starts OpenRA
with the mod. Starting "OpenRA - Red Alert" directly gives you plain Red Alert.

The first start may show OpenRA's content installer: the mod uses some original Red Alert files (sounds, terrain),
and the installer can download them.

## If something goes wrong

The script prints what it is doing in the Terminal window: send that text.
If the game itself crashes, its logs are in `~/Library/Application Support/OpenRA/Logs`.

## Multiplayer with Windows players

Everyone needs the same version of the mod. This build was made {date} from the Windows copy of that day.

## What is in this repository

| Path | What it is |
|---|---|
| `{script}` | starts the game |
| `files/mods/napoleonic/` | the mod |
| `files/{dll}` | the mod's code |
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dll", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    engine = open(os.path.join(GAME, "VERSION"), encoding="utf-8").read().strip()
    fmt = dict(engine=engine, install_dir=INSTALL_DIR, dll=DLL, mod=MOD_ID, script=SCRIPT, date=time.strftime("%Y-%m-%d"),
               dmg_url=OPENRA_DMG.format(engine=engine), releases_url=OPENRA_RELEASES.format(engine=engine))

    out = args.out
    files_dir = os.path.join(out, "files")
    if os.path.isdir(files_dir):
        shutil.rmtree(files_dir)                      # only ever this script's own output
    mod_out = os.path.join(files_dir, "mods", MOD_ID)

    mod_root = os.path.join(GAME, "mods", MOD_ID)
    count = 0
    for folder, _, names in os.walk(mod_root):
        for n in names:
            full = os.path.join(folder, n)
            rel = os.path.relpath(full, mod_root)
            dest = os.path.join(mod_out, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            data = open(full, "rb").read()
            if rel == "mod.yaml":
                # The DLL lives outside the app on the Mac: name it by absolute path.
                text = data.decode("utf-8")
                old = f"Assemblies: OpenRA.Mods.Common.dll, OpenRA.Mods.Cnc.dll, {DLL}"
                if text.count(old) != 1:
                    raise SystemExit("mod.yaml: Assemblies line not found as expected")
                data = text.replace(old, f"Assemblies: OpenRA.Mods.Common.dll, OpenRA.Mods.Cnc.dll, {INSTALL_DIR}/{DLL}").encode("utf-8")
            open(dest, "wb").write(data)
            count += 1

    shutil.copyfile(args.dll, os.path.join(files_dir, DLL))
    with open(os.path.join(out, SCRIPT), "w", encoding="utf-8", newline="\n") as f:
        f.write(PLAY_SCRIPT.format(**fmt))
    with open(os.path.join(out, README), "w", encoding="utf-8", newline="\n") as f:
        f.write(README_TEXT.format(**fmt))

    biggest = max((os.path.getsize(os.path.join(d, n)), os.path.relpath(os.path.join(d, n), out)) for d, _, ns in os.walk(files_dir) for n in ns)
    print(f"engine {engine}; mod files {count}; largest file {biggest[0] / 1e6:.1f} MB ({biggest[1]})")
    print(f"wrote {out}")
    print(f'remember:  git add --chmod=+x "{SCRIPT}"')


if __name__ == "__main__":
    main()
