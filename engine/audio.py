import random
from panda3d.core import Filename
from engine.assets import sound_path

class Audio:

    def __init__(self, enabled=True):
        self.enabled = enabled
        self.master = 1.0
        self.muted = False
        self._pool = {}
        self._pool_i = {}
        self._loops = {}
        self.music_name = None
        self._missing = set()

    def _load(self, name):
        if name in self._missing:
            return None
        p = sound_path(name)
        if p is None:
            self._missing.add(name)
            print(f"[audio] (silent) no file for '{name}'")
            return None
        try:
            return base.loader.loadSfx(Filename.fromOsSpecific(str(p)))
        except Exception as exc:
            print(f'[audio] could not load {p}: {exc}')
            self._missing.add(name)
            return None

    def toggle_mute(self):
        self.muted = not self.muted
        for d in self._loops.values():
            d['snd'].setVolume(0.0 if self.muted else d['vol'] * self.master)

    def play(self, name, volume=1.0, pitch=1.0, variation=0.0):
        if not self.enabled or self.muted:
            return
        pool = self._pool.get(name)
        if pool is None:
            snd = self._load(name)
            pool = [snd] if snd else []
            if snd:
                for _ in range(2):
                    extra = self._load(name)
                    if extra:
                        pool.append(extra)
            self._pool[name] = pool
            self._pool_i[name] = 0
        if not pool:
            return
        i = self._pool_i[name] = (self._pool_i[name] + 1) % len(pool)
        snd = pool[i]
        snd.setVolume(max(0.0, min(1.0, volume * self.master)))
        snd.setPlayRate(pitch * (1.0 + random.uniform(-variation, variation)))
        snd.play()

    def loop(self, name, volume=0.5, fade=1.5):
        if not self.enabled:
            return
        d = self._loops.get(name)
        if d:
            d['target'], d['kill'], d['rate'] = (volume, False, abs(volume - d['vol']) / max(fade, 0.05))
            return
        snd = self._load(name)
        if not snd:
            return
        snd.setLoop(True)
        snd.setVolume(0.0)
        snd.play()
        self._loops[name] = {'snd': snd, 'vol': 0.0, 'target': volume, 'kill': False, 'rate': volume / max(fade, 0.05)}

    def stop(self, name, fade=1.0):
        d = self._loops.get(name)
        if d:
            d['target'], d['kill'], d['rate'] = (0.0, True, max(d['vol'], 0.01) / max(fade, 0.05))

    def stop_all(self, fade=1.0, keep=()):
        for name in list(self._loops):
            if name not in keep:
                self.stop(name, fade)
        if self.music_name not in keep:
            self.music_name = None

    def music(self, name, volume=0.55, fade=2.0):
        if name == self.music_name:
            return
        if self.music_name:
            self.stop(self.music_name, fade)
        self.music_name = name
        if name:
            self.loop(name, volume, fade)

    def update(self, dt):
        for name in list(self._loops):
            d = self._loops[name]
            if d['vol'] < d['target']:
                d['vol'] = min(d['target'], d['vol'] + d['rate'] * dt)
            elif d['vol'] > d['target']:
                d['vol'] = max(d['target'], d['vol'] - d['rate'] * dt)
            d['snd'].setVolume(0.0 if self.muted else d['vol'] * self.master)
            if d['kill'] and d['vol'] <= 0.001:
                d['snd'].stop()
                del self._loops[name]
