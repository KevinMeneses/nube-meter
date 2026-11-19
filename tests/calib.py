"""Calibración de Nube Meter contra las herramientas de ClaudeBeats (correr con ClaudeBeats/.venv-ai/bin/python).
  calib.py techo     -> los 5 masters de la calibración de techo.py: métricas del modelo vs techo.py
  calib.py analisis  -> masters de Nube baja y referencias: modelo vs analisis.py (LUFS, TP, PLR, corr, bandas, 2-5k)
  calib.py curvas    -> curvas de referencia (bandas relativas al LUFS integrado) para copiar en el JSFX
Escribe también tests/out/calib_*.json con los números."""
import sys, os, json, pathlib
import numpy as np, soundfile as sf
from scipy import signal as sg
HERE = pathlib.Path(__file__).parent; sys.path.insert(0, str(HERE))
CB = pathlib.Path.home() / 'Music/ClaudeBeats'; sys.path.insert(0, str(CB / 'herramientas'))
import proto as P

OUT = HERE / 'out'; OUT.mkdir(exist_ok=True)


def leer(fn):
    x, sr = sf.read(str(fn), always_2d=True)
    if x.shape[1] == 1: x = np.repeat(x, 2, 1)
    if sr != P.SR: x = sg.resample_poly(x, P.SR, sr, axis=0)
    return x[:, :2]


def casos_techo():
    import master_sim as M
    pre = leer(CB / '.trabajo/x8/pre_W71_copia.wav')
    post = M.glue(M.eq_master(M.intro_gain(pre, -2, 12.8)))
    post1 = M.glue(M.eq_master(M.intro_gain(pre, -1.9, 12.8)))
    return [('W71 limitador -14.5 (le gusta)', post, M.cadena_limitador(post, 13.3, -1.2, 30), 'limpio'),
            ('limitador -15 ("todavía bien")', post, M.cadena_limitador(post, 13.8, -1.2, 30), 'limpio/limite'),
            ('limitador -16 ("se empieza a dañar")', post, M.cadena_limitador(post, 14.8, -1.2, 30), 'se daña'),
            ('X1v -9.0 ("suena muy bien")', post1, M.cadena_x1(post1, 15.8), 'limpio'),
            ('X1c -8.5 ("se distorsiona un poco")', post1, M.cadena_x1(post1, 16.34), 'al limite')]


def techo():
    import techo as T, master_sim as M
    res = []
    for nom, post, y, oido in casos_techo():
        k = T.kicks_de_mezcla(post)
        lin = M.rotar(post) if nom.startswith('X1') else post
        rt = T.medir(post, y, lin, k, None)
        r = P.limit_metrics(post, y); L = P.loudness(y)
        print(f'{nom:40s} LUFS {L["I"]:6.2f} PLR {L["PLR"]:5.2f} | kicks {r["kicks"]:4d} (techo {len(k)})  '
              f'voz/kick {r["voz_kick"]:+.2f} ({rt["voz_kick"]:+.2f})  kick {r["kick"]:+.2f} ({rt["kick"]:+.2f})  '
              f'dist {r["dist"]:4.1f}% ({rt["dist"]:4.1f}%)   [{oido}]', flush=True)
        res.append(dict(caso=nom, oido=oido, I=L['I'], PLR=L['PLR'], **{k_: float(v) for k_, v in r.items()},
                        techo=dict(voz_kick=rt['voz_kick'], kick=rt['kick'], dist=rt['dist'])))
    json.dump(res, open(OUT / 'calib_techo.json', 'w'), indent=1)


MASTERS = [CB / 'Master/Nube baja (master X20).wav', CB / 'Master/Nube baja (version Nube plugins).wav',
           CB / 'referencias/eladio_mbappe_-14LUFS.wav', CB / 'referencias/myke_te_imagino_-14LUFS.wav']


def analisis():
    import analisis as A
    for fn in MASTERS:
        x = leer(fn); r = P.measure(x)
        Ia = A.lufs(x, P.SR); tpa = A.true_peak(x); ba = A.bandas(x, P.SR) - Ia
        print(f'{fn.name}')
        print(f'  LUFS {r["I"]:.2f} ({Ia:.2f})  TP {r["TP"]:.2f} ({tpa:.2f})  PLR {r["PLR"]:.2f} ({tpa - Ia:.2f})  '
              f'corr {r["corr"]:.3f} ({A.corr(x):.3f})  mono {r["mono"]:.2f} ({A.perdida_mono(x, P.SR):.2f})  '
              f'2-5k {r["r25"]:.2f} ({A.banda_sobre_total(x, P.SR, 2000, 5000)[0]:.2f})  LRA {r["LRA"]:.1f}')
        print('  bandas - analisis: ' + ' '.join(f'{v:+.2f}' for v in r['bands'] - ba))


REFS = {'eladio': CB / 'referencias/eladio_mbappe.flac', 'myke': CB / 'referencias/myke_te_imagino.flac',
        'seanpaul': CB / 'referencias/seanpaul_like_glue.flac', 'x20': CB / 'Master/Nube baja (master X20).wav'}


def curvas():
    out = {}
    for k, fn in REFS.items():
        x = leer(fn); r = P.measure(x)
        out[k] = dict(bands=[round(float(v), 2) for v in r['bands']], r25=round(r['r25'], 2), corr=round(r['corr'], 3),
                      I=round(r['I'], 2), PLR=round(r['PLR'], 2), mono=round(r['mono'], 2))
        print(k, out[k], flush=True)
    out['eladio_myke'] = dict(bands=[round((a + b) / 2, 2) for a, b in zip(out['eladio']['bands'], out['myke']['bands'])],
                              r25=round((out['eladio']['r25'] + out['myke']['r25']) / 2, 2),
                              corr=round((out['eladio']['corr'] + out['myke']['corr']) / 2, 3))
    print('eladio_myke', out['eladio_myke'])
    json.dump(out, open(OUT / 'calib_curvas.json', 'w'), indent=1)


if __name__ == '__main__':
    {'techo': techo, 'analisis': analisis, 'curvas': curvas}[sys.argv[1]]()
