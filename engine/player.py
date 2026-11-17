import math
from collections import deque
from ursina import Vec3, held_keys
from engine.timing import Clock

def _held(*names):
    return any((held_keys[n] for n in names))

class Player:

    def __init__(self, scene, character, speed=3.6, run_speed=6.2, radius=0.38):
        self.S = scene
        self.ch = character
        self.speed = speed
        self.run_speed = run_speed
        self.radius = radius
        self.speed_mult = 1.0
        self.locked = False
        self.running = False
        self.moving = False
        self.step_sound = 'step_sand'
        self.step_volume = 0.35
        self.trail = deque(maxlen=260)
        self._trail_t = 0.0
        self._last_step = 0
        self.attack_cooldown = 0.0

    @property
    def x(self):
        return self.ch.root.x

    @property
    def z(self):
        return self.ch.root.z

    @property
    def pos(self):
        return Vec3(self.ch.root.x, 0, self.ch.root.z)

    def teleport(self, x, z):
        self.ch.root.x, self.ch.root.z = (x, z)
        self.trail.clear()

    def set_character(self, ch):
        self.ch.amount = 0.0
        self.ch = ch
        self.trail.clear()

    def update(self, dt):
        ch = self.ch
        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        mx = mz = 0.0
        if not self.locked:
            mx = (1 if _held('d', 'right arrow') else 0) - (1 if _held('a', 'left arrow') else 0)
            mz = (1 if _held('w', 'up arrow') else 0) - (1 if _held('s', 'down arrow') else 0)
        self.moving = bool(mx or mz)
        self.running = self.moving and _held('left shift', 'shift', 'right shift')
        if self.moving:
            yaw = math.radians(self.S.cam.yaw)
            fx, fz = (math.sin(yaw), math.cos(yaw))
            rx, rz = (math.cos(yaw), -math.sin(yaw))
            dx, dz = (fx * mz + rx * mx, fz * mz + rz * mx)
            n = math.hypot(dx, dz)
            dx, dz = (dx / n, dz / n)
            spd = (self.run_speed if self.running else self.speed) * self.speed_mult
            nx, nz = (ch.root.x + dx * spd * dt, ch.root.z + dz * spd * dt)
            nav = getattr(self.S, 'nav', None)
            if nav is not None and nav.on_roof(self):
                nx, nz = nav.resolve(self, ch.root.x, ch.root.z, nx, nz, dx, dz)
            else:
                nx, nz = self.S.world.resolve(nx, nz, self.radius)
            b = self.S.bounds
            if b:
                nx = min(max(nx, b[0]), b[1])
                nz = min(max(nz, b[2]), b[3])
            ch.root.x, ch.root.z = (nx, nz)
            ch.face(dx, dz, dt)
            goal = 1.0 if self.running else 0.72
        else:
            goal = 0.0
        ch.amount += (goal - ch.amount) * min(1.0, 12.0 * dt)
        if ch.amount < 0.02:
            ch.amount = 0.0
        if ch.amount > 0.1:
            n = int(ch.phase / math.pi)
            if n != self._last_step:
                self._last_step = n
                self.S.game.audio.play(self.step_sound, self.step_volume * (1.0 if self.running else 0.7), pitch=1.0, variation=0.12)
                if self.running and self.step_sound == 'step_sand':
                    self.S.fx.dust_puff((ch.root.x, 0.1, ch.root.z), 2)
        self._trail_t += dt
        if self._trail_t >= 0.04 and (self.moving or not self.trail):
            self._trail_t = 0.0
            self.trail.append((Clock.now, ch.root.x, ch.root.z, ch.angle))

    def trail_at(self, delay):
        if not self.trail:
            return None
        target = Clock.now - delay
        for t, x, z, a in reversed(self.trail):
            if t <= target:
                return (x, z, a)
        t, x, z, a = self.trail[0]
        return (x, z, a)
