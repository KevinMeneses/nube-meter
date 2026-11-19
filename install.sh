#!/bin/zsh
# Instala Nube Meter en REAPER (macOS) como enlace: los cambios del repo se ven al volver a insertar el FX.
set -e
DST="$HOME/Library/Application Support/REAPER/Effects/Nube Meter"
cd "$(dirname "$0")"
mkdir -p "$DST"
ln -sf "$PWD/nube_meter.jsfx" "$DST/nube_meter.jsfx"
echo "Listo: en REAPER busca \"Nube Meter\" en el navegador de FX (JS: Nube Meter)."
