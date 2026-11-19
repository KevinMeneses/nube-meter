"""Verifica los renders de tests/out: el audio no cambia, las lecturas del JSFX coinciden con el modelo en numpy
(tests/proto.py, que a su vez coincide con analisis.py y techo.py: ver tests/calib.py) y el retraso medido es la
latencia real de la cadena. Sale con código 1 si algo falla."""
import numpy as np, soundfile as sf, pathlib, sys, re
HERE = pathlib.Path(__file__).parent; sys.path.insert(0, str(HERE))
import proto as P
D = HERE / "out"; S = HERE / "signals"

REF0 = [-9.93, -17.25, -16.88, -16.77, -16.23, -19.07, -24.09, -24.55, -26.84]
VOZ, KICK, DIST = (0.35, 0.80), (0.40, 0.60), (10, 14)
# Nube Limit: latencia = lookahead (muestras) - 1 + 8; Nube Clip con 4x: 24
LAT_LIMIT = lambda ms: int(np.floor(ms * 48 + 0.5)) - 1 + 8
PRESETS = {1: (0, -1, 8, 0), 2: (0, -1, 9, 1), 3: (1, -1, 7, 2), 4: (1, -0.5, 6, 2), 5: (2, -1, 8, 0), 6: (3, -1, 8, 0),
           7: (2, -1, 10, 1), 8: (4, -1, 8, 0), 9: (0, -1, 7, 2), 10: (0, -0.3, 6, 2), 11: (0, -1.5, 10, 1),
           12: (0, -3, 12, 1), 13: (6, -1, 0, 0), 14: (5, -1, 8, 0), 15: (6, -1, 8, 0), 16: (0, -1, 8, 0)}

log = (D / "log.txt").read_text()
CASES = {}
for m in re.finditer(r"^caso (\S+) (.*)$", log, re.M):
    d = {}
    for k, v in re.findall(r"(\w+)=(\S+)", m.group(2)): d[k] = [float(z) for z in v.split(",")]
    CASES[m.group(1)] = d
fails = 0


def ok(name, cond, txt):
    global fails
    fails += not cond; print(f"{'OK ' if cond else 'MAL'} {name:58s} {txt}")


def near(name, got, want, tol):
    ok(name, abs(got - want) <= tol, f"{got:+10.3f}   (esperado {want:+.3f} ± {tol})")


def load(name, d=D): return sf.read(d / f"{name}.wav", always_2d=True)[0]


def par(case, slider): return CASES[case]["P"][slider - 1]


def has(case):
    if case not in CASES: print(f"--  {case}: no se renderizó"); return False
    return True


def verdict(v, k, d):
    if v >= VOZ[1] or k >= KICK[1] or d >= DIST[1]: return 2
    if v > VOZ[0] or k > KICK[0] or d > DIST[0]: return 1
    return 0


print("-- código (tests/lint.py): mayúsculas (a_r pisaba a_R) y variables compartidas entre la gráfica y el audio")
import lint
# lo que la gráfica escribe a propósito: pedidos al audio (req_*), sliders y la caída del medidor del modo Antes
ALLOWED = re.compile(r"la gráfica escribe una variable del audio: (req_\w+|slider\d+|m_peak)$")
probs = [p for p in lint.problems() if not ALLOWED.match(p)]
ok("lint del JSFX", not probs, "; ".join(probs) if probs else "sin problemas")

# REAPER agrega un ruido antidenormales minúsculo a la salida de los JSFX: "igual" = diferencia bajo -180 dB
TOL = 1e-9
print("\n-- el audio no cambia (Nube Meter no toca la señal; igual = diferencia < -180 dB)")
for case, src in (("master", "x20"), ("antes_only", "pre"), ("sine", "s1k_m20")):
    if has(case):
        y = load(case); x = load(src, S)[:len(y)]
        ok(f"{case}: salida = entrada", len(y) == len(x) and np.abs(y - x).max() < TOL, f"diferencia máx {np.abs(y - x).max():.2e}")
if has("lim12") and has("lim_ref"):
    a, b = load("lim12"), load("lim_ref")
    ok("Antes -> Nube Limit -> Medidor = Nube Limit solo", np.abs(a - b).max() < TOL, f"diferencia máx {np.abs(a - b).max():.2e}")

print("\n-- volumen, picos, estéreo y bandas contra el modelo (mismo audio)")
for case, src in (("master", "x20"), ("sine", "s1k_m20"), ("noise", "noise")):
    if not has(case): continue
    x = load(src, S); r = P.measure(x)
    print(f"   [{case}]  escala FFT: adelante {par(case, 38):g}, ida y vuelta {par(case, 39):g}")
    near(f"{case}: LUFS integrado", par(case, 12), r["I"], 0.05)
    near(f"{case}: pico real (dBTP)", par(case, 15), r["TP"], 0.02)
    near(f"{case}: PLR", par(case, 16), r["PLR"], 0.06)
    near(f"{case}: LRA", par(case, 17), r["LRA"], 0.3)
    near(f"{case}: correlación", par(case, 18), r["corr"], 0.002)
    near(f"{case}: pérdida en mono (LU)", par(case, 19), r["mono"], 0.05)
    pk, rms, nact = r["probe"]
    near(f"{case}: claude_probe pico (dB)", par(case, 1), pk, 0.01)
    near(f"{case}: claude_probe RMS activo (dB)", par(case, 2), rms, 0.02)
    near(f"{case}: claude_probe bloques activos", par(case, 3), nact, 1)
    if case == "master":
        got = np.array([par(case, 28 + i) for i in range(9)]) + REF0
        for i, (lo, hi) in enumerate(P.BANDS): near(f"{case}: banda {lo}-{hi} Hz (rel. al integrado)", got[i], r["bands"][i], 0.1)
        near(f"{case}: 2-5 kHz sobre el total", par(case, 37), r["r25"], 0.1)
if has("probe"):
    pr = CASES["probe"].get("PROBE")
    if pr and pr[2] > 0:
        near("claude_probe real vs Nube Meter: pico", par("probe", 1), pr[0], 0.01)
        near("claude_probe real vs Nube Meter: RMS activo", par("probe", 2), pr[1], 0.02)
    else:
        print(f"--  claude_probe no registró en el render (lectura {pr}); se compara contra su copia en numpy (arriba)")

print("\n-- limitación: Antes vs Medidor, contra el modelo (mismos archivos)")
pre = load("pre", S)
for case, lat in (("lim12", LAT_LIMIT(3)), ("lim17", LAT_LIMIT(3)), ("lim_la5", LAT_LIMIT(5)), ("clip_lim", LAT_LIMIT(3) + 24), ("enlace2", LAT_LIMIT(3))):
    if not has(case) or (case != "enlace2" and not (D / f"{case}.wav").exists()): continue
    y = load(case if case != "enlace2" else "lim12")
    r = P.limit_metrics(pre, y)
    near(f"{case}: retraso medido (muestras) = latencia", par(case, 26), lat, 0)
    near(f"{case}: retraso en el archivo (REAPER compensa la latencia al renderizar)", r["delay"], 0, 0)
    if case == "enlace2": continue
    near(f"{case}: kicks", par(case, 27), r["kicks"], 3)
    near(f"{case}: voz en kick (dB)", par(case, 20), r["voz_kick"], 0.08)
    near(f"{case}: golpe del kick (dB)", par(case, 21), r["kick"], 0.08)
    near(f"{case}: distorsión (%)", par(case, 22), r["dist"], 1.5)
    near(f"{case}: estado", par(case, 25), verdict(r["voz_kick"], r["kick"], r["dist"]), 0)
    print(f"      modelo: voz {r['voz_kick']:+.2f}  kick {r['kick']:+.2f}  dist {r['dist']:.1f}%  conf {r['conf']:.2f}")
if has("lim12") and has("lim17"):
    ok("más empuje (17 dB, Agresivo) -> peor estado o más distorsión",
       par("lim17", 25) >= par("lim12", 25) and par("lim17", 22) > par("lim12", 22), f"estado {par('lim12', 25):.0f} -> {par('lim17', 25):.0f}, dist {par('lim12', 22):.1f} -> {par('lim17', 22):.1f}%")
for case in ("noantes", "enlace_mal"):
    if has(case):
        ok(f"{case}: sin instancia Antes -> estado -1 y sin retraso", par(case, 25) == -1 and par(case, 26) == -1,
           f"estado {par(case, 25):.0f}, retraso {par(case, 26):.0f}")

print("\n-- presets (curva, techo TP, PLR mínimo, exigencia; Cargar preset vuelve a 0)")
for m in re.finditer(r"^preset (\d+) (.*)$", log, re.M):
    p = int(m.group(1)); v = [float(z) for z in m.group(2).split()]
    ok(f"preset {p}", tuple(v[:4]) == PRESETS[p] and v[4] == 0, f"{v}")

print(f"\n{'TODO BIEN' if not fails else f'{fails} FALLAS'}")
sys.exit(1 if fails else 0)
