import os
import sys
import wave
import numpy as np
from scipy import signal
SR = 22050
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOUND_DIR = os.path.join(ROOT, 'assets', 'sounds')
MUSIC_DIR = os.path.join(ROOT, 'assets', 'music')
os.makedirs(SOUND_DIR, exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)
RNG = np.random.default_rng(2026)

def t_axis(dur):
    return np.arange(int(dur * SR)) / SR

def sine(freq, dur, phase=0.0):
    return np.sin(2 * np.pi * freq * t_axis(dur) + phase)

def noise(dur):
    return RNG.uniform(-1, 1, int(dur * SR))

def env(n, attack=0.01, decay=0.2, sustain=1.0, release=0.1):
    a, d, r = (int(attack * SR), int(decay * SR), int(release * SR))
    a, d, r = (min(a, n), min(d, max(0, n - a)), min(r, n))
    s = max(0, n - a - d - r)
    return np.concatenate([np.linspace(0, 1, a, endpoint=False) if a else np.zeros(0), np.linspace(1, sustain, d, endpoint=False) if d else np.zeros(0), np.full(s, sustain), np.linspace(sustain, 0, r) if r else np.zeros(0)])[:n]

def expdecay(dur, tau):
    return np.exp(-t_axis(dur) / tau)

def lowpass(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, min(fc, SR / 2 - 100), 'low', fs=SR, output='sos'), x)

def highpass(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc, 'high', fs=SR, output='sos'), x)

def bandpass(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, min(hi, SR / 2 - 100)], 'band', fs=SR, output='sos'), x)

def sweep(f0, f1, dur, curve=1.0):
    t = t_axis(dur)
    k = (t / dur) ** curve
    f = f0 + (f1 - f0) * k
    return np.sin(2 * np.pi * np.cumsum(f) / SR)

def saw(freq, dur):
    return 2.0 * (t_axis(dur) * freq % 1.0) - 1.0

def reverb(x, t60=1.8, wet=0.25, damp=3500):
    n = int(t60 * SR)
    ir = RNG.normal(0, 1, n) * np.exp(-6.9 * np.arange(n) / (t60 * SR))
    ir = lowpass(ir, damp)
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-09
    w = signal.fftconvolve(x, ir)[:len(x) + n // 2]
    out = np.zeros(len(w))
    out[:len(x)] += x * (1 - wet)
    return out + w * wet * 1.6

def normalise(x, peak=0.9):
    m = np.max(np.abs(x)) + 1e-09
    return x / m * peak

def fade_edges(x, ms=6):
    n = max(2, min(int(ms / 1000 * SR), len(x) // 4))
    x = x.copy()
    x[:n] *= np.linspace(0, 1, n)
    x[-n:] *= np.linspace(1, 0, n)
    return x

def pluck(freq, dur, decay=0.995, bright=0.6):
    L = max(2, int(round(SR / freq)))
    n = int(dur * SR)
    blocks = n // L + 2
    out = np.zeros((blocks + 1) * L + 1)
    exc = RNG.uniform(-1, 1, L)
    exc = lowpass(exc, 800 + 6000 * bright, 1) if bright < 0.98 else exc
    out[1:L + 1] = exc
    for b in range(1, blocks):
        i = 1 + b * L
        out[i:i + L] = decay * 0.5 * (out[i - L:i] + out[i - L - 1:i - 1])
    y = out[1:n + 1]
    y = y + 0.35 * bandpass(y, 150, 420, 1)
    return y * np.minimum(1.0, t_axis(dur)[:len(y)] * 400)

def pad(freqs, dur, cutoff=900, attack=1.5, release=1.5, detune=0.004, vol=1.0):
    y = np.zeros(int(dur * SR))
    for f in freqs:
        for d in (-detune, 0, detune):
            y += saw(f * (1 + d), dur)[:len(y)]
    y = lowpass(y, cutoff)
    return y * env(len(y), attack, 0.0, 1.0, release) * vol / (3 * max(1, len(freqs)))

def drum(freq=110, dur=0.35, snap=0.25, drop=0.5):
    body = sweep(freq * 1.6, freq * drop, dur, 0.4) * expdecay(dur, 0.09)
    slap = bandpass(noise(dur), 600, 3000, 1) * expdecay(dur, 0.025) * snap
    return body + slap

def bell(freq, dur=1.5, tau=0.5):
    t = t_axis(dur)
    y = sum((a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t / (tau * m)) for r, a, m in ((1.0, 1.0, 1.0), (2.76, 0.5, 0.6), (5.4, 0.25, 0.4), (8.9, 0.1, 0.25))))
    return y
HIJAZ = [0, 1, 4, 5, 7, 8, 10]
D3 = 146.83

def note(deg, octave=0, tonic=D3):
    o, d = divmod(deg, 7)
    return tonic * 2 ** ((HIJAZ[d] + 12 * (o + octave)) / 12)

class Track:
    TAIL = 5.0

    def __init__(self, length):
        self.length = length
        self.n = int(length * SR)
        self.buf = np.zeros(self.n + int(self.TAIL * SR))

    def put(self, sig, at, gain=1.0):
        i = int(at * SR)
        if i >= len(self.buf):
            return
        j = min(len(self.buf), i + len(sig))
        self.buf[i:j] += sig[:j - i] * gain

    def fold_loop(self):
        out = self.buf[:self.n].copy()
        tail = self.buf[self.n:]
        out[:len(tail)] += tail
        return out

def snap(f, length):
    return round(f * length) / length

def drone(track, freq, gain=0.3, cutoff=500, lfo=0.1):
    f = snap(freq, track.length)
    fl = snap(lfo, track.length)
    t = np.arange(2 * track.n) / SR
    y = sum((np.sin(2 * np.pi * f * k * t + k) / k for k in (1, 2, 3)))
    y *= 1.0 + 0.25 * np.sin(2 * np.pi * fl * t)
    y = lowpass(y, cutoff)[track.n:]
    track.put(y, 0, gain)

def noise_bed(track, lo, hi, gain=0.1, lfo=0.15, depth=0.5):
    xf = 1.5
    raw = bandpass(RNG.uniform(-1, 1, track.n + int(xf * SR)), lo, hi, 2)
    y = make_loop(raw, xf)
    t = t_axis(track.length)
    y *= 1.0 + depth * np.sin(2 * np.pi * snap(lfo, track.length) * t + 1.3)
    track.put(y, 0, gain)

def finish(track, wet=0.25, t60=2.2, peak=0.7):
    x = reverb(track.buf, t60, wet)
    track.buf = x
    track.TAIL = (len(x) - track.n) / SR
    out = track.fold_loop()
    out = out - np.mean(out)
    out = out / (np.sqrt(np.mean(out ** 2)) + 1e-09) * 0.13
    return np.tanh(out * 1.3) / 1.3

def mus_menu():
    T = Track(32.0)
    drone(T, note(0, -1), 0.5, 380)
    drone(T, note(4, -1), 0.25, 380, lfo=0.07)
    T.put(pad([note(0), note(4), note(7)], 16, 650, 3, 3, vol=0.8), 0, 0.5)
    T.put(pad([note(1), note(5), note(8)], 16, 650, 3, 3, vol=0.8), 16, 0.5)
    arps = [[0, 2, 4, 2, 3, 2, 1, 0], [0, 2, 4, 5, 4, 2, 1, 0], [2, 4, 5, 4, 3, 2, 1, 2], [4, 3, 2, 1, 0, 1, 2, 0]]
    for bar in range(8):
        pat = arps[bar % 4]
        for i, d in enumerate(pat):
            at = bar * 4.0 + i * 0.5
            T.put(pluck(note(d, 1), 2.2, 0.996, 0.55), at, 0.5 if i % 4 else 0.7)
    for at, d in ((8, 7), (12, 6), (14, 4), (24, 7), (27, 8), (29, 6), (30.5, 4)):
        T.put(pluck(note(d, 1), 3.0, 0.998, 0.45), at, 0.55)
    for bar in range(8):
        T.put(drum(75, 0.5, 0.1), bar * 4.0, 0.5)
    return finish(T, 0.3, 2.6)

def mus_village():
    T = Track(24.0)
    drone(T, note(0, -1), 0.3, 420)
    T.put(pad([note(0), note(4)], 24, 800, 2, 2, vol=0.5), 0, 0.4)
    beat = 24.0 / 48
    melody = [0, 2, 4, 5, 4, 2, 4, 2, 1, 0, 1, 2, 0, 0, 2, 4, 5, 7, 5, 4, 2, 4, 2, 1]
    for i, d in enumerate(melody):
        T.put(pluck(note(d, 1), 1.4, 0.995, 0.65), i * 1.0, 0.55)
        T.put(pluck(note(d - 7, 0), 1.0, 0.994, 0.5), i * 1.0 + 0.5, 0.3)
    for bar in range(12):
        T.put(drum(95, 0.3, 0.3), bar * 2.0, 0.6)
        T.put(drum(140, 0.2, 0.35), bar * 2.0 + 1.0, 0.35)
        T.put(drum(140, 0.2, 0.35), bar * 2.0 + 1.5, 0.25)
    noise_bed(T, 300, 1800, 0.02, 0.1)
    return finish(T, 0.22, 1.8)

def mus_night():
    T = Track(32.0)
    drone(T, note(0, -2), 0.6, 260)
    drone(T, note(1, -1), 0.18, 300, lfo=0.05)
    T.put(pad([note(0, -1), note(3, -1)], 32, 500, 5, 5, vol=0.6), 0, 0.5)
    noise_bed(T, 200, 1100, 0.05, 0.06, 0.8)
    for at, d in ((3, 0), (7.5, 1), (11, 0), (14.5, 3), (18, 2), (22, 1), (26, 0), (29.5, 2)):
        T.put(pluck(note(d, 0), 3.5, 0.9985, 0.35), at, 0.55)
    for at in np.arange(2.0, 32.0, 4.0):
        T.put(drum(55, 0.6, 0.0), at, 0.35)
    return finish(T, 0.4, 3.2)

def mus_meal():
    T = Track(32.0)
    drone(T, note(0, -2), 0.6, 300)
    drone(T, note(4, -2), 0.3, 300, lfo=0.04)
    T.put(pad([note(0, -1), note(2, -1), note(4, -1)], 8, 700, 2, 2, vol=0.9), 0, 0.35)
    T.put(pad([note(1, -1), note(3, -1), note(5, -1)], 8, 700, 2, 2, vol=0.9), 8, 0.35)
    T.put(pad([note(0, -1), note(2, -1), note(4, -1)], 8, 700, 2, 2, vol=0.9), 16, 0.35)
    T.put(pad([note(1, -1), note(5, -1), note(8, -1)], 8, 800, 2, 2, vol=0.9), 24, 0.35)
    for i in range(32):
        T.put(drum(55, 0.35, 0.0, 0.7), i * 1.0, 0.35 if i % 2 == 0 else 0.2)
    for at, d in ((4, 4), (6, 3), (7, 2), (12, 2), (14, 1), (20, 4), (22, 5), (23, 4), (28, 2), (30, 1)):
        T.put(pluck(note(d, 0), 3.0, 0.9985, 0.4), at, 0.5)
    return finish(T, 0.35, 2.8)

def mus_palace():
    T = Track(32.0)
    drone(T, note(0, -2), 0.55, 240)
    drone(T, note(1, -2), 0.3, 240, lfo=0.09)
    noise_bed(T, 400, 2500, 0.03, 0.08, 0.9)
    T.put(pad([note(3, -1), note(5, -1)], 16, 600, 4, 4, vol=0.6), 0, 0.35)
    T.put(pad([note(4, -1), note(6, -1)], 16, 600, 4, 4, vol=0.6), 16, 0.35)
    for at in np.arange(0.0, 32.0, 2.0):
        T.put(drum(48, 0.5, 0.0, 0.6), at, 0.4)
    for at in (5, 5.5, 13, 21, 21.5, 29):
        T.put(bell(1900 + RNG.uniform(-100, 100), 0.7, 0.12), at, 0.07)
    for at, d in ((8, 2), (10, 1), (18, 0), (26, 1), (28, 2)):
        T.put(pluck(note(d, 0), 3.0, 0.9985, 0.3), at, 0.45)
    return finish(T, 0.35, 3.0)

def mus_dawn():
    T = Track(32.0)
    drone(T, note(0, -1), 0.3, 500)
    T.put(pad([note(0), note(2), note(4), note(7)], 16, 1200, 3, 3, vol=0.9), 0, 0.5)
    T.put(pad([note(-1), note(1), note(3), note(6)], 16, 1200, 3, 3, vol=0.9), 16, 0.5)
    melody = [(0, 4), (2, 3), (4, 2), (5, 5), (4, 3), (2, 2), (1, 4), (0, 6), (7, 3), (6, 2), (4, 4), (5, 3), (4, 2), (2, 4), (1, 3), (0, 5)]
    at = 1.0
    for d, dur in melody:
        T.put(pluck(note(d, 1), dur + 1.5, 0.9985, 0.5), at, 0.5)
        at += dur * 0.9 if at < 28 else 1.0
        if at >= 31:
            break
    for bar in range(4):
        T.put(drum(65, 0.6, 0.0, 0.6), bar * 8.0, 0.4)
    return finish(T, 0.4, 3.5)

def mus_burn():
    T = Track(24.0)
    drone(T, note(0, -2), 0.5, 320)
    drone(T, note(1, -2), 0.25, 320, lfo=0.2)
    noise_bed(T, 120, 900, 0.1, 0.25, 0.6)
    for i in range(48):
        T.put(drum(60 if i % 4 else 48, 0.4, 0.2), i * 0.5, 0.65 if i % 4 == 0 else 0.35)
    for i in range(12):
        T.put(drum(130, 0.2, 0.4), i * 2.0 + 1.0, 0.35)
    for bar in range(6):
        for k, d in enumerate((0, 1, 0, 3) if bar % 2 == 0 else (1, 0, 2, 1)):
            T.put(pluck(note(d, 0), 1.5, 0.996, 0.8), bar * 4.0 + k * 0.5, 0.5)
    for at in (0, 8, 16):
        T.put(pad([note(0, -1), note(1, -1), note(3, -1)], 4, 700, 0.2, 2.5, vol=0.9), at, 0.4)
    return finish(T, 0.3, 2.2)

def mus_ruins():
    T = Track(36.0)
    drone(T, note(0, -2), 0.5, 240)
    drone(T, note(4, -2), 0.2, 260, lfo=0.05)
    noise_bed(T, 150, 1400, 0.08, 0.07, 0.9)
    T.put(pad([note(0, -1), note(4, -1)], 18, 550, 5, 5, vol=0.6), 0, 0.4)
    T.put(pad([note(-1, -1), note(3, -1)], 18, 550, 5, 5, vol=0.6), 18, 0.4)
    for at, d in ((4, 4), (8, 2), (12, 1), (16, 0), (22, 4), (26, 5), (30, 2), (33, 0)):
        T.put(pluck(note(d, 0), 4.5, 0.999, 0.3), at, 0.5)
    for at in (9, 24):
        T.put(bell(note(7, 1), 4.0, 1.4), at, 0.08)
    return finish(T, 0.45, 3.8)

def mus_crow():
    T = Track(32.0)
    drone(T, note(0, -2), 0.55, 260)
    drone(T, note(1, -2), 0.16, 260, lfo=0.07)
    noise_bed(T, 250, 1600, 0.04, 0.05, 0.9)
    T.put(pad([note(0, -1), note(3, -1)], 16, 520, 4, 4, vol=0.6), 0, 0.3)
    T.put(pad([note(1, -1), note(4, -1)], 16, 520, 4, 4, vol=0.6), 16, 0.3)
    for i in range(32):
        T.put(drum(52, 0.4, 0.0, 0.6), i * 1.0, 0.4 if i % 4 == 0 else 0.16)
    for at in (6.5, 14.5, 22.5, 30.0):
        T.put(bell(2100 + RNG.uniform(-80, 80), 0.6, 0.1), at, 0.05)
    for at, d in ((2, 2), (4.5, 1), (10, 3), (12, 2), (18, 4), (20, 3), (26, 1), (28, 0)):
        T.put(pluck(note(d, 0), 3.2, 0.9985, 0.32), at, 0.45)
    return finish(T, 0.4, 3.0)

def mus_legend():
    T = Track(40.0)
    drone(T, note(0, -2), 0.5, 360)
    drone(T, note(4, -2), 0.25, 360, lfo=0.04)
    for k, chord in enumerate(([0, 2, 4, 7], [-1, 1, 3, 6], [0, 2, 4, 7], [1, 3, 5, 8], [0, 2, 4, 7])):
        T.put(pad([note(d) for d in chord], 8.5, 1300, 2.5, 3.0, vol=0.9), k * 8.0, 0.42)
    melody = [(4, 4), (3, 2), (2, 2), (4, 4), (5, 4), (4, 2), (2, 2), (0, 6), (7, 4), (6, 2), (5, 2), (4, 4), (2, 4), (1, 2), (2, 2), (0, 8)]
    at = 2.0
    for d, dur in melody:
        T.put(pluck(note(d, 1), dur + 2.0, 0.9988, 0.5), at, 0.5)
        at += dur * 0.95
        if at > 38:
            break
    for bar in range(5):
        T.put(drum(62, 0.7, 0.0, 0.55), bar * 8.0, 0.5)
    for at in (16.0, 32.0):
        T.put(bell(note(7, 1), 4.5, 1.6), at, 0.07)
    return finish(T, 0.45, 3.8)

def step_sand():
    return normalise(fade_edges(bandpass(noise(0.16), 600, 2600, 1) * expdecay(0.16, 0.045)), 0.5)

def step_stone():
    n = 0.14
    y = highpass(noise(n), 1500, 1) * expdecay(n, 0.012) * 0.7
    y += sine(190, n) * expdecay(n, 0.03) * 0.6
    return normalise(fade_edges(y), 0.55)

def ui_tick():
    return normalise(fade_edges(sine(1500, 0.04) * expdecay(0.04, 0.012)), 0.4)

def ui_select():
    y = np.concatenate([sine(660, 0.09) * expdecay(0.09, 0.05), sine(990, 0.2) * expdecay(0.2, 0.09)])
    return normalise(fade_edges(y), 0.5)

def type_blip():
    return normalise(fade_edges(sine(760, 0.014) * env(int(0.014 * SR), 0.002, 0.01, 0, 0)), 0.22)

def caw():
    dur = 0.5
    f = 760 - 260 * (t_axis(dur) / dur) ** 0.7
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = sum((np.sin(ph * k) / k ** 0.8 for k in range(1, 9)))
    y *= 0.6 + 0.4 * np.sin(2 * np.pi * 70 * t_axis(dur))
    y += 0.25 * bandpass(noise(dur), 900, 3200, 1)
    y = bandpass(y, 500, 3800, 1)
    y *= env(len(y), 0.03, 0.1, 0.8, 0.2)
    return normalise(fade_edges(reverb(y, 0.5, 0.12)), 0.7)

def alert():
    a = (saw(520, 0.16) + 0.5 * saw(523 * 1.5, 0.16)) * env(int(0.16 * SR), 0.005, 0.05, 0.7, 0.05)
    b = (saw(780, 0.34) + 0.5 * saw(784 * 1.5, 0.34)) * env(int(0.34 * SR), 0.005, 0.1, 0.6, 0.18)
    y = lowpass(np.concatenate([a, b]), 3200)
    return normalise(fade_edges(y), 0.6)

def torch_ignite():
    dur = 1.0
    w = bandpass(noise(dur), 300, 2500, 2) * (t_axis(dur) / dur) ** 1.2 * np.exp(-(t_axis(dur) / dur) * 2.5)
    c = highpass(noise(dur), 3000, 1) * (RNG.uniform(0, 1, int(dur * SR)) > 0.992) * expdecay(dur, 0.5)
    return normalise(fade_edges(w + c * 2.0), 0.7)

def splash():
    dur = 0.8
    y = bandpass(noise(dur), 400, 4500, 2) * expdecay(dur, 0.18)
    drops = np.zeros(int(dur * SR))
    for k in range(7):
        s = int(RNG.uniform(0.05, 0.6) * SR)
        d = sweep(RNG.uniform(500, 900), RNG.uniform(1400, 2200), 0.07) * expdecay(0.07, 0.025)
        drops[s:s + len(d)] += d * RNG.uniform(0.2, 0.5)
    return normalise(fade_edges(y + drops), 0.6)

def pickup():
    y = np.concatenate([bell(880, 0.12, 0.08), bell(1320, 0.45, 0.2)])
    return normalise(fade_edges(y), 0.5)

def decode_tick():
    return normalise(fade_edges(highpass(noise(0.03), 1800, 1) * expdecay(0.03, 0.006)), 0.35)

def paper_burn():
    dur = 1.6
    n = int(dur * SR)
    crackle = (RNG.uniform(0, 1, n) > 0.985) * RNG.uniform(0.2, 1, n)
    crackle = bandpass(crackle, 1200, 6000, 1) * np.exp(-np.linspace(0, 2.4, n))
    hiss = bandpass(noise(dur), 2000, 6000, 1) * 0.12 * np.exp(-np.linspace(0, 1.6, n))
    return normalise(fade_edges(crackle * 3 + hiss), 0.65)

def eat():
    parts = []
    for k in range(3):
        d = 0.14
        y = bandpass(noise(d), 200, 1800, 1) * expdecay(d, 0.04) + sine(95, d) * expdecay(d, 0.04) * 0.4
        parts.append(np.concatenate([y, np.zeros(int(0.06 * SR))]))
    return normalise(fade_edges(np.concatenate(parts)), 0.5)

def clink():
    t = t_axis(0.9)
    y = sum((a * np.sin(2 * np.pi * f * t) * np.exp(-t / tau) for f, a, tau in ((2630, 1.0, 0.35), (3950, 0.6, 0.25), (5810, 0.35, 0.12), (1480, 0.4, 0.4))))
    return normalise(fade_edges(y), 0.55)

def clink_soft():
    return clink() * 0.45

def heartbeat():

    def beat(f, dur=0.22):
        return sweep(f * 1.6, f, dur, 0.5) * expdecay(dur, 0.07) * env(int(dur * SR), 0.004, 0.2, 0.2, 0.05)
    y = np.zeros(int(1.0 * SR))
    b1 = beat(58)
    b2 = beat(50) * 0.7
    y[:len(b1)] += b1
    y[int(0.28 * SR):int(0.28 * SR) + len(b2)] += b2
    return normalise(fade_edges(lowpass(y, 200)), 0.85)

def stinger():
    dur = 2.6
    boom = sweep(90, 30, dur, 0.35) * expdecay(dur, 0.7)
    cluster = sum((saw(f, dur) for f in (146.8, 155.6, 185.0, 207.7))) * env(int(dur * SR), 0.9, 0.5, 0.35, 1.0)
    cluster = lowpass(cluster, 900) * 0.15
    hit = drum(55, 0.6, 0.4)
    y = boom * 0.9 + cluster
    y[:len(hit)] += hit
    return normalise(fade_edges(reverb(y, 1.5, 0.3)), 0.85)

def stinger_soft():
    dur = 1.8
    y = pad([note(0, -1), note(1, -1), note(4, -1)], dur, 700, 0.4, 1.2, vol=1.0)
    y += bell(note(4, 1), dur, 1.0) * 0.18
    return normalise(fade_edges(reverb(y, 1.8, 0.35)), 0.55)

def thud():
    dur = 0.35
    y = sweep(110, 45, dur, 0.4) * expdecay(dur, 0.09) + lowpass(noise(dur), 500) * expdecay(dur, 0.03) * 0.5
    return normalise(fade_edges(y), 0.85)

def door_creak():
    dur = 1.9
    f = 140 + 70 * np.sin(2 * np.pi * 0.7 * t_axis(dur)) ** 2 + 40 * (t_axis(dur) / dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = sum((np.sin(ph * k) / k for k in range(1, 12)))
    y *= 0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 9 * t_axis(dur)))
    y += 0.4 * bandpass(noise(dur), 800, 2200, 2) * np.abs(np.sin(2 * np.pi * 3.5 * t_axis(dur)))
    y = bandpass(y, 180, 2600, 1) * env(len(y), 0.15, 0.2, 0.8, 0.5)
    return normalise(fade_edges(reverb(y, 0.9, 0.2)), 0.6)

def music_box():
    seq = [(note(4, 2), 0.0), (note(2, 2), 0.45), (note(1, 2), 0.9), (note(2, 2), 1.35), (note(0, 2), 1.8), (note(1, 2), 2.25), (note(0, 2), 2.7), (note(-1, 2), 3.15)]
    T = Track(4.5)
    for f, at in seq:
        t = t_axis(1.6)
        y = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 3 * t) + 0.15 * np.sin(2 * np.pi * f * 5.1 * t)) * np.exp(-t / 0.35)
        T.put(y, at, 0.6)
    y = reverb(T.buf, 1.6, 0.3)
    return normalise(fade_edges(y), 0.5)

def thunder():
    dur = 3.8
    t = t_axis(dur)
    rumble = lowpass(noise(dur), 160, 2) * np.exp(-t / 1.4) * (1 + 0.5 * np.sin(2 * np.pi * 3.2 * t))
    crack = highpass(noise(dur), 1500, 1) * expdecay(dur, 0.08) * 1.4
    roll = lowpass(noise(dur), 300, 2) * np.exp(-((t - 1.0) / 0.7) ** 2) * 0.8
    return normalise(fade_edges(rumble * 2.5 + crack + roll), 0.9)

def beam_fall():
    dur = 1.7
    t = t_axis(dur)
    creak = bandpass(noise(0.5), 300, 1600, 2) * np.abs(np.sin(2 * np.pi * 14 * t_axis(0.5))) * env(int(0.5 * SR), 0.05, 0.1, 0.7, 0.25)
    y = np.zeros(len(t))
    y[:len(creak)] += creak * 0.4
    hit = int(0.45 * SR)
    boom = sweep(95, 35, 1.2, 0.35) * expdecay(1.2, 0.3)
    debris = lowpass(noise(1.2), 2500) * expdecay(1.2, 0.35)
    y[hit:hit + len(boom)] += boom * 1.0 + debris * 0.45
    for k in range(9):
        s = hit + int(RNG.uniform(0.1, 1.0) * SR)
        c = bandpass(noise(0.05), 800, 4000, 1) * expdecay(0.05, 0.012)
        if s + len(c) < len(y):
            y[s:s + len(c)] += c * RNG.uniform(0.3, 0.7)
    return normalise(fade_edges(reverb(y, 1.1, 0.18)), 0.9)

def bat():
    y = np.zeros(int(1.3 * SR))
    for k in range(9):
        s = int(RNG.uniform(0, 1.1) * SR)
        c = sweep(RNG.uniform(3800, 5200), RNG.uniform(6000, 8500), 0.06) * expdecay(0.06, 0.03)
        y[s:s + len(c)] += c * RNG.uniform(0.3, 0.7)
    y += bandpass(noise(1.3), 1200, 4000, 1) * 0.08 * np.abs(np.sin(2 * np.pi * 16 * t_axis(1.3)))
    return normalise(fade_edges(reverb(y, 0.8, 0.2)), 0.5)

def blade():
    dur = 0.38
    y = bandpass(noise(dur), 1800, 7000, 2) * np.sin(np.pi * t_axis(dur) / dur) ** 2
    y += 0.25 * sweep(2600, 1200, dur) * np.sin(np.pi * t_axis(dur) / dur)
    return normalise(fade_edges(y), 0.6)

def snuff():
    dur = 0.7
    puff = lowpass(noise(0.12), 900) * expdecay(0.12, 0.04)
    hiss = bandpass(noise(dur), 3500, 9000, 1) * np.exp(-t_axis(dur) / 0.2) * 0.35
    y = hiss
    y[:len(puff)] += puff * 1.2
    return normalise(fade_edges(y), 0.55)

def wingbeat():
    dur = 0.6
    y = np.zeros(int(dur * SR))
    for k in range(4):
        s = int(k * 0.13 * SR)
        f = lowpass(noise(0.09), 700) * expdecay(0.09, 0.04)
        y[s:s + len(f)] += f * (1 - 0.15 * k)
    return normalise(fade_edges(y), 0.6)

def banner_fall():
    dur = 1.4
    y = lowpass(noise(dur), 900) * np.sin(np.pi * (t_axis(dur) / dur) ** 0.6) * 0.5
    y[int(1.0 * SR):] += 0
    y += sweep(70, 40, dur, 0.3) * expdecay(dur, 0.12) * 0.2
    return normalise(fade_edges(y), 0.6)

def fanfare():
    dur = 5.0
    T = Track(dur)
    for d, at in ((0, 0.0), (2, 0.5), (4, 1.0)):
        T.put(lowpass(saw(note(d, 0), 2.6), 1500) * env(int(2.6 * SR), 0.05, 0.3, 0.7, 1.4), at, 0.35)
    T.put(pad([note(0, -1), note(4, -1), note(7, -1)], 4.5, 900, 0.8, 2.5, vol=1.0), 0.0, 0.8)
    T.put(drum(55, 0.9, 0.4), 0.0, 0.9)
    T.put(bell(note(4, 1), 4.0, 1.5), 1.0, 0.15)
    return normalise(fade_edges(reverb(T.buf, 3.0, 0.4)), 0.85)

def make_loop(x, fade=1.5):
    n = int(fade * SR)
    body = x[:-n].copy()
    k = np.linspace(0, 1, n)
    body[:n] = body[:n] * np.sin(k * np.pi / 2) + x[-n:] * np.cos(k * np.pi / 2)
    return body

def amb_wind():
    dur = 22.0
    t = t_axis(dur + 1.5)
    base = bandpass(RNG.uniform(-1, 1, len(t)), 150, 1100, 2)
    gust = 0.55 + 0.45 * np.sin(2 * np.pi * 0.11 * t + 1) * np.sin(2 * np.pi * 0.23 * t + 2)
    whistle = bandpass(RNG.uniform(-1, 1, len(t)), 900, 1400, 2) * (0.25 + 0.25 * np.sin(2 * np.pi * 0.17 * t))
    y = base * gust + whistle * 0.35
    return normalise(make_loop(y), 0.6)

def amb_hall():
    dur = 16.0
    t = t_axis(dur + 1.5)
    y = lowpass(RNG.uniform(-1, 1, len(t)), 280, 2) * 0.8
    y += sine(55, dur + 1.5) * 0.18 + sine(82.4, dur + 1.5) * 0.08
    y += bandpass(RNG.uniform(-1, 1, len(t)), 800, 2400, 1) * 0.04 * (1 + np.sin(2 * np.pi * 0.2 * t))
    return normalise(make_loop(y), 0.5)

def amb_fire():
    dur = 18.0
    n = int((dur + 1.5) * SR)
    roar = lowpass(RNG.uniform(-1, 1, n), 420, 2) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.31 * np.arange(n) / SR + 0.5))
    pops = (RNG.uniform(0, 1, n) > 0.9975) * RNG.uniform(0.3, 1.0, n)
    pops = bandpass(pops, 900, 6500, 1)
    hiss = bandpass(RNG.uniform(-1, 1, n), 3000, 8000, 1) * 0.07
    y = roar * 1.0 + pops * 2.6 + hiss
    return normalise(make_loop(y), 0.7)
SOUNDS = {'step_sand': step_sand, 'step_stone': step_stone, 'ui_tick': ui_tick, 'ui_select': ui_select, 'type_blip': type_blip, 'caw': caw, 'alert': alert, 'torch_ignite': torch_ignite, 'splash': splash, 'pickup': pickup, 'decode_tick': decode_tick, 'paper_burn': paper_burn, 'eat': eat, 'clink': clink, 'clink_soft': clink_soft, 'heartbeat': heartbeat, 'stinger': stinger, 'stinger_soft': stinger_soft, 'thud': thud, 'door_creak': door_creak, 'music_box': music_box, 'thunder': thunder, 'beam_fall': beam_fall, 'bat': bat, 'blade': blade, 'snuff': snuff, 'wingbeat': wingbeat, 'banner_fall': banner_fall, 'fanfare': fanfare, 'amb_wind': amb_wind, 'amb_hall': amb_hall, 'amb_fire': amb_fire}
MUSIC = {'mus_menu': mus_menu, 'mus_village': mus_village, 'mus_night': mus_night, 'mus_meal': mus_meal, 'mus_palace': mus_palace, 'mus_dawn': mus_dawn, 'mus_burn': mus_burn, 'mus_ruins': mus_ruins, 'mus_crow': mus_crow, 'mus_legend': mus_legend}

def extra_music():
    return {}

def save(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())

def trim_tail(x, thr=0.004):
    idx = np.nonzero(np.abs(x) > thr)[0]
    return x if len(idx) == 0 else x[:min(len(x), idx[-1] + int(0.05 * SR))]

def main(names):
    todo = []
    for table, folder in ((SOUNDS, SOUND_DIR), (MUSIC, MUSIC_DIR), (extra_music(), MUSIC_DIR)):
        for name, fn in table.items():
            if not names or name in names:
                todo.append((name, fn, folder))
    for name, fn, folder in todo:
        x = fn()
        if folder == SOUND_DIR and (not name.startswith('amb_')):
            x = fade_edges(trim_tail(x), 20)
        path = os.path.join(folder, name + '.wav')
        save(path, x)
        peak = float(np.max(np.abs(x)))
        rms = float(np.sqrt(np.mean(x ** 2)))
        print(f'  {name:14s} {len(x) / SR:5.1f}s  peak {peak:.2f}  rms {rms:.3f}  {os.path.getsize(path) // 1024} KB')
if __name__ == '__main__':
    main(set(sys.argv[1:]))
