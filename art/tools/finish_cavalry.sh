#!/bin/bash
# Verify renders, build the sheet, wire it in and lint. Usage: finish_cavalry.sh <variant> "<comment>" ACTOR...
set -e
v="$1"; comment="$2"; shift 2
cd "/d/Napoleonic Wars/art"
python -c "
from PIL import Image
import glob, sys
fs=sorted(glob.glob('renders/cav_$v/frame_*.png')); bad=[]
for f in fs:
    try: Image.open(f).load()
    except Exception: bad.append(f)
print(len(fs),'frames, bad:',bad)
sys.exit(0 if len(fs)==248 and not bad else 1)"
python tools/make_sprite_sheet.py "renders/cav_$v" frame "../mods/napoleonic/bits/$v.png" --frame 64
python tools/wire_cavalry.py "$v" "$comment" "$@"
cd .. && ./OpenRA.Utility.exe napoleonic --check-yaml 2>&1 | grep -v "^Testing" | tail -1
