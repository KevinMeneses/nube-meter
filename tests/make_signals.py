"""Señales de prueba (48 kHz, float32)."""
import numpy as np, soundfile as sf, pathlib
D = pathlib.Path(__file__).parent / "signals"; D.mkdir(exist_ok=True)
CB = pathlib.Path.home() / "Music/ClaudeBeats"
SR = 48000
def save(name, x): sf.write(D / name, x.astype(np.float32), SR, subtype="FLOAT")
def a(db): return 10 ** (db / 20)
t = np.arange(SR * 10) / SR
s = a(-20) * np.sin(2 * np.pi * 1000 * t); save("s1k_m20.wav", np.stack([s, s], 1))
# premaster de Nube baja (W71) desde el verso 1: es lo que entra al limitador (lo que ve la instancia Antes)
x, sr = sf.read(CB / ".trabajo/x8/pre_W71_copia.wav", start=int(12.8 * SR), frames=45 * SR, always_2d=True); assert sr == SR
save("pre.wav", x[:, :2])
# master oficial X20 (bandas, LUFS, estéreo)
x, sr = sf.read(CB / "Master/Nube baja (master X20).wav", start=30 * SR, frames=60 * SR, always_2d=True); assert sr == SR
save("x20.wav", x[:, :2])
# ruido -30 dBFS, L y R independientes (correlación ~0)
rng = np.random.default_rng(3); save("noise.wav", a(-30) * rng.standard_normal((SR * 20, 2)))
print("señales en", D)
