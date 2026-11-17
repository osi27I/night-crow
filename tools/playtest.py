import os
import sys
import traceback
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

class PlayTest:

    def __init__(self, scene=0, fixed_dt=1 / 30, size=(1280, 720), safe=False, out_dir=None, mute=True):
        from engine.game import Game
        self.dt = fixed_dt
        self.out = out_dir or os.path.join(HERE, 'screenshots', 'test')
        os.makedirs(self.out, exist_ok=True)
        self.game = Game(start_scene=scene, fixed_dt=fixed_dt, size=size, safe=safe, mute=mute)
        self._gen = None
        self.frame = 0
        self._skip = 0
        self.errors = 0

    def wait(self, frames):
        for _ in range(int(frames)):
            yield

    def seconds(self, s):
        return self.wait(round(s / self.dt))

    def hold_for(self, key, s):
        from ursina import held_keys
        held_keys[key] = 1
        yield from self.seconds(s)
        held_keys[key] = 0

    def hold(self, key, on=True):
        from ursina import held_keys
        held_keys[key] = 1 if on else 0

    def tap(self, key):
        self.game.on_input(key)

    def shot(self, name):
        path = os.path.join(self.out, f'{name}.png')
        base.screenshot(path, defaultFilename=False)
        print('SHOT', name)

    def walk_to(self, x, z, tol=0.45, timeout=40.0, run=False):
        import math
        n = 0
        while n * self.dt < timeout:
            p = self.game.scene.player
            dx, dz = (x - p.x, z - p.z)
            if math.hypot(dx, dz) < tol:
                break
            self.hold('d', dx > 0.25)
            self.hold('a', dx < -0.25)
            self.hold('w', dz > 0.25)
            self.hold('s', dz < -0.25)
            self.hold('left shift', run)
            n += 1
            yield
        for k in ('a', 'd', 'w', 's', 'left shift'):
            self.hold(k, False)

    def read(self, max_seconds=60.0, gap=0.35):
        d = self.game.dialogue
        n = 0
        tick = 0
        while d.active and n * self.dt < max_seconds:
            n += 1
            tick += 1
            if tick * self.dt >= gap and d.mode == 'talk':
                tick = 0
                self.tap('space')
            yield

    def autoplay(self, prefix, until=None, max_seconds=300.0, pick=0, shot_every=5.0, max_shots=60, press_e=True):
        g = self.game
        d = g.dialogue
        n, k, last, age, quiet = (0, 0, None, 0, 0)
        shot_done = False
        per_tap = max(1, int(0.6 / self.dt))
        while n * self.dt < max_seconds and k < max_shots:
            n += 1
            if until and until():
                break
            if d.active:
                quiet = 0
                key = (id(d.lines), d.index, d.mode)
                if key != last:
                    last, age, shot_done = (key, 0, False)
                age += 1
                if d.mode == 'choice':
                    if age * self.dt > 1.0:
                        self.shot(f'{prefix}{k:02d}')
                        k += 1
                        d.pick(pick)
                else:
                    if not shot_done and age * self.dt >= 0.8:
                        self.shot(f'{prefix}{k:02d}')
                        k += 1
                        shot_done = True
                    if age * self.dt >= 1.0 and age % per_tap == 0:
                        self.tap('space')
            else:
                last = None
                quiet += 1
                sc = g.scene
                if press_e and sc is not None and (getattr(sc, '_near', None) is not None) and (quiet % per_tap == 0):
                    self.tap('e')
                if quiet * self.dt >= shot_every:
                    quiet = 0
                    self.shot(f'{prefix}{k:02d}')
                    k += 1
            yield

    def until(self, cond, timeout=60.0):
        n = 0
        while not cond() and n * self.dt < timeout:
            n += 1
            yield

    def run(self, script):
        self._gen = script(self)

        def hook(game):
            self.frame += 1
            if self.frame < 3 or (game.transitioning and False):
                return
            try:
                next(self._gen)
            except StopIteration:
                from ursina import application
                application.quit()
            except Exception:
                traceback.print_exc()
                from ursina import application
                application.quit()
        self.game.frame_hooks.append(hook)
        self.game.run()
