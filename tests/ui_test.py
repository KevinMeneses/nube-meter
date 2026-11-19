"""Pruebas de la interfaz con el mouse (mueven el mouse real: no usar la Mac mientras corren, ~3 min).
Abre un REAPER PROPIO con tests/ui_host.lua, cierra la ventana de licencia, hace clics / arrastres / rueda / menús
sobre la ventana del Medidor y verifica los parámetros que el anfitrión escribe en tests/out/dump.txt.
Al final mata SOLO ese proceso. Uso: python tests/ui_test.py  (con el candado de comun.md)"""
import subprocess, time, pathlib, sys, re
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "tests/out"; OUT.mkdir(exist_ok=True)
REAPER = "/Applications/REAPER.app/Contents/MacOS/REAPER"
fails = 0


def check(name, got, want, note=""):
    global fails
    ok = want(got) if callable(want) else got == want; fails += not ok
    print(f"{'OK ' if ok else 'MAL'} {name:52s} {got!r}{note}", flush=True)


def retry(name, action, get, want):
    """REAPER 7.86 a veces pierde un evento inyectado (ver README de Nube Clip): si falla, se repite UNA vez y se avisa."""
    action(); got = get(); ok = want(got) if callable(want) else got == want
    if ok: return check(name, got, want)
    action(); check(name, get(), want, "   (2º intento: el 1º se perdió)")


# ---------------------------------------------------------------- REAPER propio
for f in ("dump.txt", "cmd.txt"): (OUT / f).unlink(missing_ok=True)
proc = subprocess.Popen([REAPER, "-new", "-nosplash", str(ROOT / "tests/ui_host.lua")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
PID = proc.pid


def front():
    subprocess.run(["osascript", "-e", f'tell application "System Events" to set frontmost of (first process whose unix id is {PID}) to true'],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(0.3)


def window():
    out = subprocess.run(["swift", str(ROOT / "tests/wins.swift")], capture_output=True, text=True).stdout
    for line in out.splitlines():
        p = line.split(" ", 6)
        if len(p) == 7 and int(p[1]) == PID and "Nube Meter" in p[6]: return float(p[2]), float(p[3]), float(p[4]), float(p[5])
    return None


def kill():
    if "REAPER -new" in subprocess.run(["ps", "-o", "command=", "-p", str(PID)], capture_output=True, text=True).stdout: proc.kill()


win = None
for i in range(60):
    time.sleep(1)
    if i in (8, 12, 16):   # ventana de licencia (modal): Escape
        front(); subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 53'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    win = window()
    if win and (OUT / "dump.txt").exists(): break
if not win: kill(); sys.exit("no apareció la ventana del Medidor")
WX, WY, WW, WH = win; HDR = WH - 700      # cabecera de REAPER sobre el área gráfica (preset, Param...)
print(f"ventana en {WX:.0f},{WY:.0f} ({WW:.0f}x{WH:.0f}), REAPER pid {PID}")


def pt(x, y): return f"{round(WX + x)},{round(WY + HDR + y)}"


def cc(*args): subprocess.run(["cliclick", "-w", "60", *args], check=True); time.sleep(0.4)


def wheel(n): subprocess.run(["swift", str(ROOT / "tests/scroll.swift"), str(n)], check=True); time.sleep(0.6)


def cg(x, y, n=1):
    subprocess.run(["swift", str(ROOT / "tests/click.swift"), str(WX + x), str(WY + HDR + y), str(n)], check=True); time.sleep(0.4)


def flush(): cg(500, 687)   # clic en el pie (sin controles): si quedó un "apretado" pegado, lo suelta


def click(x, y): front(); flush(); cg(x, y)


def dclick(x, y): front(); flush(); cg(x, y, 2)


def drag(x0, y0, x1, y1):
    front(); flush()
    subprocess.run(["swift", str(ROOT / "tests/mouse.swift"), *map(str, (WX + x0, WY + HDR + y0, WX + x1, WY + HDR + y1, 8))], check=True)
    time.sleep(0.4)


def menu(x, y, downs):
    click(x, y); time.sleep(0.7); cc(*(["kp:arrow-down"] * downs), "kp:return"); time.sleep(0.8)


def dump():
    time.sleep(0.6)
    for _ in range(20):
        t = (OUT / "dump.txt").read_text() if (OUT / "dump.txt").exists() else ""
        if t.endswith("done\n"): break
        time.sleep(0.1)
    return {m.group(1): float(m.group(2)) for m in re.finditer(r"^(\w+)\|([-\d.]+)", t, re.M)}


def par(n): return dump()[str(n)]


def cmd(c): (OUT / "cmd.txt").write_text(c + "\n"); time.sleep(1.0)


# ---------------------------------------------------------------- coordenadas (puntos dentro del área gráfica, 1000x700)
MODE, LINK, PRESETS, CURVE, EXIG = (200, 22), (311, 22), (414, 22), (572, 22), (753, 22)
TP_BOX, PLR_BOX = (816, 242), (923, 242)
LOUD = (870, 100)
CAPTURE, CLEAR = (363, 298), (508, 514)

try:
    time.sleep(10)   # que suene un poco (bandas, alineación)
    check("arranca con los valores por defecto (curva, TP, PLR, exig.)", (par(7), par(8), par(9), par(10)), (0, -1, 8, 0))
    # techo de pico real: arrastre, doble clic, rueda
    retry("arrastrar Techo TP hacia abajo baja ~2 dB", lambda: drag(*TP_BOX, TP_BOX[0], TP_BOX[1] + 80), lambda: par(8), lambda v: v < -1.5)
    retry("doble clic en Techo TP = -1", lambda: dclick(*TP_BOX), lambda: par(8), -1.0)
    front(); flush(); cc(f"m:{pt(*TP_BOX)}"); time.sleep(0.4); wheel(3)
    check("rueda +3 sobre Techo TP = -0.7", par(8), lambda v: abs(v + 0.7) < 0.01)
    wheel(-3); check("rueda -3 sobre Techo TP = -1.0", par(8), lambda v: abs(v + 1.0) < 0.01)
    front(); flush(); cc(f"m:{pt(*PLR_BOX)}"); time.sleep(0.4); wheel(2)
    check("rueda +2 sobre PLR min = 9", par(9), 9.0)
    def plr_wheel(): front(); flush(); cc(f"m:{pt(*PLR_BOX)}"); time.sleep(0.4); wheel(-2)
    retry("rueda -2 sobre PLR min baja 1 (9 -> 8)", plr_wheel, lambda: par(9), lambda v: v <= 8.0)
    front(); flush(); cc(f"m:{pt(*PLR_BOX)}"); time.sleep(0.4); wheel(4)
    retry("doble clic en PLR min (10) = 8", lambda: dclick(*PLR_BOX), lambda: par(9), 8.0)
    # menús
    retry("menú Exigencia -> Estricto", lambda: menu(*EXIG, 2), lambda: par(10), 1)
    retry("menú Curva -> Myke", lambda: menu(*CURVE, 3), lambda: par(7), 2)
    menu(*PRESETS, 4); check("menú Presets -> Drill / rage", (par(7), par(8), par(9), par(10)), (1, -0.5, 6, 2))
    menu(*PRESETS, 1); check("menú Presets -> Nube baja (calibrado)", (par(7), par(8), par(9), par(10)), (0, -1, 8, 0))
    # enlace: con el Antes en el enlace 1, el Medidor en el 2 queda sin Antes
    check("con Antes: retraso = latencia de Nube Limit (151)", par(26), 151)
    retry("menú Enlace -> 2", lambda: menu(*LINK, 2), lambda: par(6), 2); time.sleep(1.5)
    check("enlace 2 -> sin Antes (estado -1, sin retraso)", (par(25), par(26)), (-1, -1))
    retry("menú Enlace -> 1", lambda: menu(*LINK, 1), lambda: par(6), 1)
    # modo
    retry("menú Modo -> Antes", lambda: menu(*MODE, 2), lambda: par(5), 1)
    retry("menú Modo -> Medidor", lambda: menu(*MODE, 1), lambda: par(5), 0)
    # capturar referencia (las bandas ya tienen > 9 s)
    click(*CAPTURE); time.sleep(1)
    check("Capturar -> curva Capturada", par(7), 5)
    check("recién capturada: banda más desviada < 1 dB", abs(par(23)), lambda v: v < 1)
    # reiniciar con clic en el panel de loudness
    b0 = par(3); click(*LOUD)
    check("clic en loudness reinicia (bloques del probe)", par(3), lambda v: v < b0 / 2)
    # intentos: 22 s sonando y stop -> una fila; Borrar -> vacía
    n0 = par(40); time.sleep(22); cmd("stop"); time.sleep(1.5)
    check("play de 22 s + stop -> un intento más", par(40), lambda v: v == min(n0 + 1, 10))
    retry("Borrar -> tabla vacía", lambda: click(*CLEAR), lambda: par(40), 0)
    cmd("play")
finally:
    kill()
print("FALLAS:", fails)
sys.exit(1 if fails else 0)
