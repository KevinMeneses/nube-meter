"""Chequeos estáticos del JSFX (los errores que no se ven en los renders):
  1. EEL2 no distingue mayúsculas: dos nombres que solo difieren en eso son la misma variable (a_r pisaba a_R).
  2. @gfx corre en otro hilo: una variable global que escribe la gráfica no puede usarla el audio, y una función
     no puede llamarse desde los dos (sus parámetros y local() se comparten). Lección de Nube Clip.
Devuelve una lista de problemas (vacía = bien). Uso: python tests/lint.py"""
import re, pathlib, collections
SRC = pathlib.Path(__file__).resolve().parent.parent / "nube_meter.jsfx"


def clean(s):
    s = re.sub(r'"[^"]*"', '""', s); s = re.sub(r'//[^\n]*', '', s)
    return re.sub(r'^(slider\d+|in_pin|out_pin|desc|options):.*$', '', s, flags=re.M)


def problems(src=None):
    s = clean(src if src is not None else SRC.read_text()); out = []
    g = collections.defaultdict(set)
    for w in re.findall(r'(?<![#\w])[A-Za-z_]\w*', s): g[w.lower()].add(w)
    out += [f"mayúsculas: {sorted(v)}" for v in g.values() if len(v) > 1]
    gi = s.index('@gfx'); gfx = s[gi:]; audio = s[:gi]
    loc = set(); fn_gfx = set()
    for m in re.finditer(r'function\s+(\w+)\(([^)]*)\)\s*(?:local\(([^)]*)\))?', gfx):
        fn_gfx.add(m.group(1))
        for part in (m.group(2), m.group(3) or ''): loc |= {p.strip() for p in part.split(',') if p.strip()}
    assigned = set(re.findall(r'(?<![\w#.])([A-Za-z_]\w*)\s*(?:[-+*/|&]?=)(?!=)', gfx))
    used_audio = set(re.findall(r'(?<![\w#])([A-Za-z_]\w*)', audio))
    out += [f"la gráfica escribe una variable del audio: {v}" for v in sorted(assigned - loc) if v in used_audio and not v.startswith(('gfx_', 'mouse_'))]
    fn_audio = set(re.findall(r'function\s+(\w+)\(', audio))
    calls_gfx = set(re.findall(r'(?<![\w#])(\w+)\(', gfx))
    out += [f"función del audio llamada desde la gráfica: {f}" for f in sorted(fn_audio & calls_gfx)]
    return out


if __name__ == '__main__':
    p = problems(); print('\n'.join(p) if p else 'sin problemas')
