"""Modelo en numpy de lo que mide Nube Meter, con los mismos algoritmos que el JSFX (filtros, bloques, ventanas),
escrito de forma vectorizada. Sirve para:
  - comparar los renders/lecturas de REAPER contra el modelo (tests/check.py),
  - comparar el modelo contra herramientas/analisis.py y techo.py (tests/calib.py),
  - calcular las curvas de referencia y los umbrales que se copian en el JSFX.
Todo a 48 kHz."""
import numpy as np
from scipy import signal as sg

SR = 48000
BANDS = [(30, 60), (60, 120), (120, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000), (8000, 15000)]


# ---------------------------------------------------------------- filtros (RBJ, iguales a los del JSFX)
def biq(kind, f, q, sr=SR):
    w = 2 * np.pi * f / sr; c = np.cos(w); al = np.sin(w) / (2 * q)
    if kind == 'lp': b = [(1 - c) / 2, 1 - c, (1 - c) / 2]
    else: b = [(1 + c) / 2, -(1 + c), (1 + c) / 2]
    a = [1 + al, -2 * c, 1 - al]
    return np.array(b) / a[0], np.array(a) / a[0]


BW4 = (0.5411961001461970, 1.3065629648763766)   # Butterworth de 4o orden = 2 biquads


def bw4(x, kind, f):
    for q in BW4:
        b, a = biq(kind, f, q); x = sg.lfilter(b, a, x, axis=0)
    return x


def bp8(lo, hi, fs=SR):
    """butter(4, [lo, hi], 'bandpass') de scipy en 4 biquads, con la misma aritmética que el JSFX."""
    import cmath
    w1 = 2 * fs * np.tan(np.pi * lo / fs); w2 = 2 * fs * np.tan(np.pi * hi / fs); bw = w2 - w1; w0s = w1 * w2
    secs = []
    for k in (0, 1):
        p = cmath.exp(1j * np.pi * (2 * k + 5) / 8); d = cmath.sqrt((p * bw) ** 2 - 4 * w0s)
        for s in ((p * bw + d) / 2, (p * bw - d) / 2):
            z = (2 * fs + s) / (2 * fs - s); secs.append([1, 0, -1, 1, -2 * z.real, abs(z) ** 2])
    sos = np.array(secs, float)
    W = 2 * np.arctan(np.sqrt(w0s) / (2 * fs)); e = np.exp(-1j * W); H = 1
    for q in sos: H *= (q[0] + q[1] * e + q[2] * e * e) / (q[3] + q[4] * e + q[5] * e * e)
    sos[:, :3] *= abs(H) ** -0.25
    return sos


def band(x, lo, hi): return sg.sosfilt(bp8(lo, hi), x, axis=0)


def kweight(x, sr=SR):
    f0 = 1681.974450955533; G = 3.999843853973347; Q = 0.7071752369554196
    K = np.tan(np.pi * f0 / sr); Vh = 10 ** (G / 20); Vb = Vh ** 0.4996667741545416
    a0 = 1 + K / Q + K * K
    b = [(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0]
    a = [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0]
    y = sg.lfilter(b, a, x, axis=0)
    K = np.tan(np.pi * 38.13547087602444 / sr); Q = 0.5003270373238773; a0 = 1 + K / Q + K * K
    return sg.lfilter([1, -2, 1], [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0], y, axis=0)


def db(x): return 10 * np.log10(np.maximum(x, 1e-30))


# ---------------------------------------------------------------- volumen (bloques de 100 ms como Nube Limit)
def loudness(x):
    """I (histograma de 0.1 LU como el JSFX), LRA, TP máx, PLR y la pérdida en mono."""
    y = kweight(x); B = SR // 10; n = len(y) // B
    e = (y[:n * B] ** 2).reshape(n, B, 2).mean(1).sum(1)                   # energía por bloque de 100 ms
    ym = kweight(np.repeat(x.mean(1, keepdims=True), 2, 1)); em = (ym[:n * B] ** 2).reshape(n, B, 2).mean(1).sum(1)
    c = np.convolve(e, np.ones(4) / 4)[3:n]; cm = np.convolve(em, np.ones(4) / 4)[3:n]   # M = 400 ms
    L = -0.691 + db(c)
    ok = L > -70; bins = np.clip(np.floor((L + 70) * 10), 0, 799).astype(int)
    I = -70.0; mono = 0.0
    if ok.any():
        rel = -0.691 + db(c[ok].mean()) - 10; bi = int(np.clip(np.ceil((rel + 70) * 10), 0, 799))
        g = ok & (bins >= bi); I = -0.691 + db(c[g].mean())
        Lm = -0.691 + db(cm); okm = Lm > -70; bm = np.clip(np.floor((Lm + 70) * 10), 0, 799).astype(int)
        if okm.any():
            relm = -0.691 + db(cm[okm].mean()) - 10; bim = int(np.clip(np.ceil((relm + 70) * 10), 0, 799))
            mono = I - (-0.691 + db(cm[okm & (bm >= bim)].mean()))
    s = np.convolve(e, np.ones(30) / 30)[29:n]; S = -0.691 + db(s)               # S = 3 s, cada 100 ms
    LRA = 0.0
    so = S[S > -70]
    if len(so):
        rel = -0.691 + db((10 ** ((so + 0.691) / 10)).mean()) - 20; so = so[so > rel]
        if len(so) > 1: LRA = np.percentile(so, 95) - np.percentile(so, 10)
    tp = true_peak(x)
    return dict(I=I, LRA=LRA, TP=tp, PLR=tp - I, mono=mono, S=S)


def tp_coefs():
    h = np.zeros((3, 16))
    for p in range(1, 4):
        t = np.arange(16) - 7 - p / 4; s = np.sinc(t); w = 0.5 + 0.5 * np.cos(np.pi * t / 8.5)
        h[p - 1] = s * w / (s * w).sum()
    return h


def true_peak(x):
    """Igual que Nube Limit: 3 fases de sinc de 16 coef. + la muestra misma."""
    h = tp_coefs(); m = np.abs(x).max()
    for p in range(3):
        m = max(m, np.abs(sg.lfilter(h[p][::-1], [1], x, axis=0)).max())
    return 20 * np.log10(m + 1e-10)


# ---------------------------------------------------------------- claude_probe
def probe(x):
    pk = np.abs(x).max(); m = x.mean(1); B = int(SR * 0.05); n = len(m) // B
    r = (m[:n * B].reshape(n, B) ** 2).mean(1); a = r[r > 1e-6]
    return 20 * np.log10(pk + 1e-9), (10 * np.log10(a.mean()) if len(a) else -150), len(a)


# ---------------------------------------------------------------- estéreo
def stereo(x):
    L, R = x[:, 0], x[:, 1]; n = len(L)
    sl, sr_, sll, srr, slr = L.sum(), R.sum(), (L * L).sum(), (R * R).sum(), (L * R).sum()
    cov = slr - sl * sr_ / n; vl = sll - sl * sl / n; vr = srr - sr_ * sr_ / n
    return cov / np.sqrt(vl * vr + 1e-30)


# ---------------------------------------------------------------- bandas (FFT 16384, Hann, salto 8192 = Welch)
NF = 16384


def spectrum(x):
    """Suma de |X|^2 por bin (mono), tramas de 16384 cada 8192 sin la media (detrend de Welch). Igual que el JSFX."""
    m = x.mean(1); w = sg.get_window('hann', NF); H = NF // 2
    n = (len(m) - NF) // H + 1
    acc = np.zeros(NF // 2 + 1)
    for i in range(n):
        seg = m[i * H:i * H + NF]; X = np.abs(np.fft.rfft((seg - seg.mean()) * w)) ** 2
        acc += X
    return acc, n


def bands_from(acc, n, I):
    """Nivel de cada banda relativo al LUFS integrado (dB), en la escala de analisis.bandas (Welch, densidad)."""
    w = sg.get_window('hann', NF); f = np.arange(NF // 2 + 1) * SR / NF
    P = acc / max(n, 1) * 2 / (SR * (w ** 2).sum())
    return np.array([db(P[(f >= a) & (f < b)].sum()) for a, b in BANDS]) - I


def ratio25(x):
    """2-5 kHz sobre el total (mono, bloques de 0.4 s, solo los que suenan): mediana, como analisis.banda_sobre_total."""
    m = x.mean(1); y = band(m, 2000, 5000); n = int(0.4 * SR); nb = len(m) // n
    b = (y[:nb * n].reshape(nb, n) ** 2).mean(1); t = (m[:nb * n].reshape(nb, n) ** 2).mean(1)
    ok = t > t.max() * 1e-3
    return med(db(b[ok] / t[ok]))


# ---------------------------------------------------------------- limitación (antes vs después)
BK = SR // 100   # bloques de 10 ms


def kicks(x):
    """Igual que techo.kicks_de_mezcla, en tiempo real: banda 50-150 (BW4+BW4), envolventes 2 / 50 ms,
    disparo si la rápida pasa el doble de la lenta y el percentil 70 de la rápida (histograma de 0.25 dB, por bloque)."""
    y = np.abs(band(x.mean(1), 50, 150))
    kf = np.exp(-1 / (0.002 * SR)); ks = np.exp(-1 / (0.05 * SR))
    ef = sg.lfilter([1 - kf], [1, -kf], y); es = sg.lfilter([1 - ks], [1, -ks], y)
    # percentil 70 que va sabiendo el JSFX: histograma de la rápida al final de cada bloque de 10 ms
    nb = len(ef) // BK; v = 20 * np.log10(ef[BK - 1::BK][:nb] + 1e-12)
    hb = np.clip(np.floor((v + 150) * 4), 0, 799).astype(int)
    thr = np.empty(nb); H = np.zeros(800); tot = 0
    for i in range(nb):
        H[hb[i]] += 1; tot += 1
        j = np.searchsorted(np.cumsum(H), 0.7 * tot); thr[i] = 10 ** ((j / 4 - 150) / 20)
    thc = np.r_[0.0, thr[:-1]] if nb else np.zeros(0)
    th = np.repeat(thc, BK); th = np.r_[th, np.full(len(ef) - len(th), thr[-1] if nb else 0.0)]
    on, last = [], -10 ** 9
    trig = (ef > es * 2) & (ef > th)
    for i in np.where(trig[1:] & ~trig[:-1])[0] + 1:
        if i - last > SR * 0.15: on.append(i); last = i
    return np.array(on, int)


def voz_en_kick(x, y, on):
    bx = band(x.mean(1), 1000, 4000); by = band(y.mean(1), 1000, 4000); n = min(len(bx), len(by)) // BK
    ex = np.sqrt((bx[:n * BK].reshape(n, BK) ** 2).mean(1)) + 1e-9; ey = np.sqrt((by[:n * BK].reshape(n, BK) ** 2).mean(1)) + 1e-9
    g = 20 * np.log10(ey / ex); exd = 20 * np.log10(ex)
    # percentil 30 con el mismo histograma que el JSFX (0.1 dB)
    hb = np.clip(np.floor((exd + 200) * 10), 0, 2599).astype(int); c = np.cumsum(np.bincount(hb, minlength=2600))
    p30 = np.searchsorted(c, 0.3 * n) / 10 - 200
    act = exd >= p30
    idx = on // BK; idx = idx[idx < n - 8]
    hm = np.zeros(n, bool); hit = np.zeros(n, bool)
    for i in idx: hm[i:i + 8] = True; hit[i:i + 3] = True
    if not len(idx): return np.nan
    return med(g[act & ~hm]) - med(g[hit])


def med(v):
    """Mediana con el histograma de 0.01 dB del JSFX (entre -40 y +40 dB)."""
    if not len(v): return np.nan
    b = np.clip(np.floor((v + 40) * 100), 0, 7999).astype(int); c = np.cumsum(np.bincount(b, minlength=8000))
    return (np.searchsorted(c, 0.5 * len(v)) + 0.5) / 100 - 40


def golpe_kick(x, y, on):
    ex = band(x.mean(1), 40, 150) ** 2; ey = band(y.mean(1), 40, 150) ** 2
    a = int(0.04 * SR); b = int(0.3 * SR); on = on[on < min(len(ex), len(ey)) - b]
    if not len(on): return np.nan
    cx = np.r_[0, np.cumsum(ex)]; cy = np.r_[0, np.cumsum(ey)]
    rx = db((cx[on + a] - cx[on]) / (cx[on + b] - cx[on] + 1e-20)); ry = db((cy[on + a] - cy[on]) / (cy[on + b] - cy[on] + 1e-20))
    return float(med(rx) - med(ry))


# --- parte lineal de la cadena: FIR de 4096 coef. estimado con el espectro cruzado (tramas de 8192, salto 4096),
# se recalcula cada UPD bloques con lo acumulado hasta ahí (como el JSFX). lin = h * x, alineado con y.
NL = 8192; HL = NL // 2; UPD = 12            # 12 bloques de 4096 = ~1 s


def fir_from(Sxy, Sxx):
    H = Sxy / (Sxx + 1e-9 * Sxx.max() + 1e-30)
    h = np.fft.irfft(H, NL)                                   # circular: centro en 0
    h = np.roll(h, HL // 2)[:HL]                              # 2048 coef. antes y 2047 después del centro
    t = np.arange(HL) - HL // 2; h *= 0.5 + 0.5 * np.cos(np.pi * t / (HL // 2))   # ventana de Hann
    return h


def linear_model(x, y):
    """Devuelve lin (mono) alineado con y (mono): la cadena como si fuera solo un filtro lineal."""
    xm = x.mean(1); ym = y.mean(1); n = min(len(xm), len(ym)); xm = xm[:n]; ym = ym[:n]
    w = np.hanning(NL + 1)[:NL]                              # Hann periódica
    Sxy = np.zeros(NL // 2 + 1, complex); Sxx = np.zeros(NL // 2 + 1)
    nb = n // HL; lin = np.zeros(n + NL); h = np.zeros(HL); h[HL // 2] = 1.0
    xp = np.r_[np.zeros(HL), xm, np.zeros(NL)]; yp = np.r_[np.zeros(HL), ym, np.zeros(NL)]
    for i in range(nb):
        # acumula el espectro cruzado con la trama que termina en este bloque
        fx = np.fft.rfft(xp[i * HL:i * HL + NL] * w); fy = np.fft.rfft(yp[i * HL:i * HL + NL] * w)
        Sxy += fy * np.conj(fx); Sxx += np.abs(fx) ** 2
        if i % UPD == UPD - 1: h = fir_from(Sxy, Sxx)
        # convolución del bloque i de x con h (solapar y sumar): sale retrasado HL//2
        seg = np.fft.irfft(np.fft.rfft(xm[i * HL:(i + 1) * HL], NL) * np.fft.rfft(h, NL), NL)
        lin[i * HL:i * HL + NL] += seg
    lin = lin[HL // 2:HL // 2 + n]                           # quita el retraso del centro del FIR
    return lin, ym


# distorsión: igual que master_sim.distorsion (STFT 1024/512, tercios desde 25 Hz, enmascaramiento -12 dB)
ND = 1024
EDGES = 25 * 2 ** (np.arange(0, 30) / 3); EDGES = EDGES[EDGES < 18000]


def dist_tables():
    f = np.arange(ND // 2 + 1) * SR / ND
    bidx = np.full(len(f), -1)
    for b, (lo, hi) in enumerate(zip(EDGES[:-1], EDGES[1:])): bidx[(f >= lo) & (f < hi)] = b
    nb = len(EDGES) - 1; S = np.zeros((nb, nb))
    for b in range(nb):
        for k in range(nb):
            d = b - k; S[b, k] = 10 ** (-(8 * abs(d) * (1 if d >= 0 else 2)) / 10)
    return bidx, S


def distortion(lin, ym):
    """% de tramas (de las que suenan) con distorsión audible: error y - lin sobre el umbral de enmascaramiento."""
    n = min(len(lin), len(ym)); H = ND // 2; w = np.hanning(ND + 1)[:ND]; bidx, S = dist_tables(); nb = S.shape[0]
    nf = (n - ND) // H + 1; e = ym[:n] - lin[:n]
    fr = np.lib.stride_tricks.sliding_window_view(lin[:n], ND)[::H][:nf] * w
    fe = np.lib.stride_tricks.sliding_window_view(e, ND)[::H][:nf] * w
    X = np.abs(np.fft.rfft(fr, axis=1)) ** 2; E = np.abs(np.fft.rfft(fe, axis=1)) ** 2
    Px = np.zeros((nf, nb)); Pe = np.zeros((nf, nb))
    for b in range(nb):
        k = bidx == b; Px[:, b] = X[:, k].sum(1); Pe[:, b] = E[:, k].sum(1)
    M = Px @ S.T
    nmr = 10 * np.log10((Pe + 1e-14) / (M * 10 ** (-12 / 10) + 1e-14))
    tot = Px.sum(1); worst = nmr.max(1)
    tb = np.clip(np.floor((10 * np.log10(tot + 1e-30) + 200) * 10), 0, 2999).astype(int)
    c = np.cumsum(np.bincount(tb, minlength=3000)); idx = np.searchsorted(c, int(0.2 * nf), side='right')
    loud = tb > idx
    return 100 * np.mean(worst[loud] > 0) if loud.any() else 0.0


def gcc_delay(x, y, n=8192, frames=35):
    """Retraso de y respecto de x con GCC-PHAT: tramas de 8192 cada 4096 en las que los dos suenan (> -60 dB).
    Devuelve (retraso, muestra en la que se decide = desde donde se mide, confianza)."""
    xm = x.mean(1); ym = y.mean(1); H = n // 2; w = np.hanning(n + 1)[:n]; C = np.zeros(n // 2 + 1, complex); k = 0
    for i in range((min(len(xm), len(ym)) - n) // H + 1):
        a_ = xm[i * H:i * H + n]; b_ = ym[i * H:i * H + n]
        if (a_ ** 2).mean() <= 1e-6 or (b_ ** 2).mean() <= 1e-6: continue
        C += np.fft.rfft(b_ * w) * np.conj(np.fft.rfft(a_ * w)); k += 1
        if k == frames:
            r = np.fft.irfft(C / (np.abs(C) + 1e-20), n); d = int(np.argmax(r[:H]))
            return d, i * H + n, float(r[d])
    return None


def limit_metrics(x, y):
    """x = entrada de la instancia Antes (sin alinear), y = salida. Alinea con GCC-PHAT y mide desde ahí, como el JSFX.
    Todo contra la parte lineal de la cadena."""
    g = gcc_delay(x, y)
    if g is None: return dict(kicks=0, voz_kick=np.nan, kick=np.nan, dist=np.nan, delay=-1, start=-1)
    d, st, conf = g; x = x[st - d:]; y = y[st:]
    lin, ym = linear_model(x, y); L = np.stack([lin, lin], 1); Y = np.stack([ym, ym], 1)
    on = kicks(L)
    return dict(kicks=len(on), voz_kick=voz_en_kick(L, Y, on), kick=golpe_kick(L, Y, on), dist=distortion(lin, ym),
                delay=d, start=st, conf=conf)


def measure(y, x=None, ref=None):
    """Todo lo que muestra Nube Meter para la salida y (y la entrada x de la instancia Antes, ya alineada)."""
    r = loudness(y); r['corr'] = stereo(y); acc, n = spectrum(y)
    r['bands'] = bands_from(acc, n, r['I']); r['r25'] = ratio25(y)
    r['probe'] = probe(y)
    if x is not None: r.update(limit_metrics(x, y))
    return r
