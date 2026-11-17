import math
from panda3d.core import ClockObject

class Clock:
    fixed_dt = None
    time_scale = 1.0
    now = 0.0
    raw_dt = 0.016

    @classmethod
    def tick(cls):
        if cls.fixed_dt:
            raw = cls.fixed_dt
        else:
            raw = min(ClockObject.getGlobalClock().getDt(), 0.05)
        cls.raw_dt = raw
        dt = raw * cls.time_scale
        cls.now += dt
        return dt

def linear(t):
    return t

def ease_out(t):
    return 1 - (1 - t) ** 3

def ease_in(t):
    return t * t * t

def ease_in_out(t):
    return t * t * (3 - 2 * t)

def _lerp(a, b, t):
    if isinstance(a, (int, float)):
        return a + (b - a) * t
    if isinstance(a, (tuple, list)):
        return tuple((a[i] + (b[i] - a[i]) * t for i in range(len(a))))
    return a + (b - a) * t

class _Tween:

    def __init__(self, get, set_, target, duration, ease, delay, on_done):
        self.get, self.set, self.target = (get, set_, target)
        self.duration = max(duration, 0.0001)
        self.ease, self.delay, self.on_done = (ease, delay, on_done)
        self.t = 0.0
        self.start = None
        self.dead = False

    def step(self, dt):
        if self.delay > 0:
            self.delay -= dt
            return
        if self.start is None:
            self.start = self.get()
        self.t += dt
        k = min(1.0, self.t / self.duration)
        self.set(_lerp(self.start, self.target, self.ease(k)))
        if k >= 1.0:
            self.dead = True
            if self.on_done:
                self.on_done()

class _Timer:

    def __init__(self, delay, fn, repeat=None):
        self.delay, self.fn, self.repeat = (delay, fn, repeat)
        self.dead = False

    def cancel(self):
        self.dead = True

class _Script:

    def __init__(self, gen):
        self.gen = gen
        self.wait = 0.0
        self.cond = None
        self.dead = False

    def step(self, dt):
        if self.wait > 0:
            self.wait -= dt
            return
        if self.cond is not None:
            if not self.cond():
                return
            self.cond = None
        try:
            y = next(self.gen)
        except StopIteration:
            self.dead = True
            return
        if y is None:
            return
        if callable(y):
            self.cond = y
        else:
            self.wait = float(y)

class Timeline:

    def __init__(self):
        self.tweens, self.timers, self.scripts = ([], [], [])

    def to(self, obj, attr, target, duration=1.0, ease=ease_in_out, delay=0.0, on_done=None):
        tw = _Tween(lambda: getattr(obj, attr), lambda v: setattr(obj, attr, v), target, duration, ease, delay, on_done)
        self.tweens.append(tw)
        return tw

    def to_item(self, mapping, key, target, duration=1.0, ease=ease_in_out, delay=0.0, on_done=None):
        tw = _Tween(lambda: mapping[key], lambda v: mapping.__setitem__(key, v), target, duration, ease, delay, on_done)
        self.tweens.append(tw)
        return tw

    def value(self, getter, setter, target, duration=1.0, ease=ease_in_out, delay=0.0, on_done=None):
        tw = _Tween(getter, setter, target, duration, ease, delay, on_done)
        self.tweens.append(tw)
        return tw

    def after(self, delay, fn):
        t = _Timer(delay, fn)
        self.timers.append(t)
        return t

    def every(self, interval, fn):
        t = _Timer(interval, fn, repeat=interval)
        self.timers.append(t)
        return t

    def run(self, generator):
        s = _Script(generator)
        self.scripts.append(s)
        return s

    def update(self, dt):
        for tw in self.tweens:
            tw.step(dt)
        self.tweens = [t for t in self.tweens if not t.dead]
        for tm in self.timers:
            tm.delay -= dt
            if tm.delay <= 0 and (not tm.dead):
                tm.fn()
                if tm.repeat:
                    tm.delay += tm.repeat
                else:
                    tm.dead = True
        self.timers = [t for t in self.timers if not t.dead]
        for sc in list(self.scripts):
            sc.step(dt)
        self.scripts = [s for s in self.scripts if not s.dead]

    def clear(self):
        self.tweens, self.timers, self.scripts = ([], [], [])

def wave(t, speed=1.0, phase=0.0):
    return 0.5 + 0.5 * math.sin(t * speed + phase)
