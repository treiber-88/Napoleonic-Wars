#!/bin/sh
# Builds NapoleonicWars.exe (source/NapoleonicWars.Launcher) and installs it in the game folder.
# The game folder is a self-contained .NET 8 install, so the launcher needs a runtimeconfig.json and a
# deps.json describing that bundled runtime: they are RedAlert's, with the application name swapped.
#
# Usage: sh art/tools/make_launcher.sh
set -e
cd "$(dirname "$0")/../.."

dotnet build source/NapoleonicWars.Launcher -c Release --nologo -v q

cp source/NapoleonicWars.Launcher/bin/NapoleonicWars.exe .
cp source/NapoleonicWars.Launcher/bin/NapoleonicWars.dll .
cp source/NapoleonicWars.Launcher/bin/NapoleonicWars.dll.config .
cp RedAlert.runtimeconfig.json NapoleonicWars.runtimeconfig.json
sed 's/RedAlert/NapoleonicWars/g' RedAlert.deps.json > NapoleonicWars.deps.json

ls -la NapoleonicWars.*
