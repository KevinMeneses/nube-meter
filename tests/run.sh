#!/bin/zsh
# Renderiza los casos en un REAPER PROPIO y verifica. Usar con el candado de comun.md:
#   until mkdir /tmp/nube-reaper.lock 2>/dev/null; do sleep 5; done; NUBE_PY=~/Music/ClaudeBeats/.venv/bin/python tests/run.sh; rmdir /tmp/nube-reaper.lock
# NUBE_CASE=a,b -> solo esos casos.  NUBE_SKIP_RENDER=1 -> solo verificar lo que ya está en tests/out.
# Ojo: "REAPER -nonewinst script" manda el script al REAPER que ya está abierto (el del usuario). Aquí se abre una
# instancia nueva con el script, se guarda su PID y al final se cierra SOLO ese proceso (nunca con la acción Salir,
# que podría llegarle al REAPER del usuario).
cd "$(dirname "$0")/.."
PY=${NUBE_PY:-python3}   # numpy, scipy y soundfile
[ -f tests/signals/pre.wav ] || $PY tests/make_signals.py || exit 1
if [ -z "$NUBE_SKIP_RENDER" ]; then
  mkdir -p tests/out; rm -f tests/out/log.txt tests/out/only.txt
  [ -n "$NUBE_CASE" ] && echo "$NUBE_CASE" > tests/out/only.txt
  /Applications/REAPER.app/Contents/MacOS/REAPER -new -nosplash "$PWD/tests/render_cases.lua" >/dev/null 2>&1 &
  RPID=$!
  for i in $(seq 1 600); do grep -q done tests/out/log.txt 2>/dev/null && break; sleep 1; done
  sleep 2
  # cerrar solo el proceso que abrimos (y solo si sigue siendo un REAPER -new)
  ps -o command= -p $RPID 2>/dev/null | grep -q "REAPER -new" && kill $RPID
  grep -q done tests/out/log.txt || { echo "REAPER no terminó (¿diálogo abierto?)"; exit 1; }
  grep -i error tests/out/log.txt
fi
$PY tests/check.py
