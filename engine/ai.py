import math
from ursina import Vec3
from engine.assets import tex
from engine.characters import build_character
from engine.entities import glow_quad, rgb
from engine.timing import Clock

def _angle_diff(a, b):
    return (a - b + 180.0) % 360.0 - 180.0

class Guard:

    def __init__(self, scene, pos, route=None, facing=0.0, speed=1.55, view=8.5, fov=80.0, pause=1.6, sweep=38.0, **look):
        self.S = scene
        self.ch = build_character(scene.root, (pos[0], 0, pos[1]), **look)
        self.ch.angle = facing
        self.ch.root.rotation_y = facing
        self.route = [tuple(p) for p in route or []]
        self.wp = 0
        self.speed = speed
        self.view = view
        self.fov = fov
        self.pause = pause
        self.sweep = sweep
        self.wait = 0.0
        self.state = 'patrol'
        self.awareness = 0.0
        self.alive = True
        self.home_facing = facing
        self.home = (pos[0], pos[1])
        self.look_offset = 0.0
        self.t = 0.0
        self.spotted_called = False
        self.alert_mult = 1.0
        self.chase_speed = 5.2
        self.investigate = None
        self._inv_wait = 0.0
        self.frozen = False
        self.blind_t = 0.0
        self.armor = False
        self.level_y = 0.0
        self.cone_pivot = scene.make_pivot()
        self.cone = glow_quad(self.cone_pivot, (0, 0.05, view / 2), (1, view), (0.3, 1.0, 0.5, 0.32), tex('cone'), billboard=False, add=True, bin_sort=36)
        self.cone.rotation_x = 90
        self.cone_reach = view

    @property
    def x(self):
        return self.ch.root.x

    @property
    def z(self):
        return self.ch.root.z

    @property
    def facing(self):
        return self.ch.angle + self.look_offset

    def vision_amount(self, p):
        S = self.S
        ab = getattr(S, 'abil', None)
        mult = ab.vision_scale(self, p) if ab is not None else 1.0
        if mult <= 0.0:
            return 0.0
        dx, dz = (p.x - self.x, p.z - self.z)
        d = math.hypot(dx, dz)
        if d > self.view:
            return 0.0
        ang = abs(_angle_diff(self.facing, math.degrees(math.atan2(dx, dz))))
        if ang > self.fov / 2.0 and d > 1.3:
            return 0.0
        if not (ab is not None and ab.skip_los(self, p)) and (not S.world.line_of_sight(self.x, self.z, p.x, p.z)):
            return 0.0
        f = (1.25 - d / self.view) * mult
        if S.stealth_light:
            level = S.rig.level_at(p)
            f *= max(0.18, min(1.5, level * 1.35))
        if not p.moving:
            f *= 0.7
        return max(0.0, f)

    def hearing_amount(self, p):
        d = math.hypot(p.x - self.x, p.z - self.z)
        if abs(p.ch.root.y - self.ch.root.y) > 1.5:
            return 0.0
        if p.running and d < 3.6:
            return (1.0 - d / 3.6) * 0.6
        return 0.0

    def hear(self, x, z):
        if self.alive and self.state != 'chase':
            self.investigate = (x, z)
            self._inv_wait = 0.0

    def in_takedown_range(self, p, reach=1.6):
        if not self.alive:
            return False
        return math.hypot(p.x - self.x, p.z - self.z) <= reach

    def is_behind(self, p):
        if self.blind_t > 0:
            return True
        a = math.degrees(math.atan2(p.x - self.x, p.z - self.z))
        return abs(_angle_diff(self.ch.angle, a)) > 115.0

    def kill(self):
        self.alive = False
        self.state = 'dead'
        self.ch.amount = 0.0
        self.ch.set_pose('fall')
        self.cone.enabled = False
        self.ch.hide_shadow()

    def update(self, dt):
        self.t += dt
        if self.blind_t > 0:
            self.blind_t -= dt
            self.ch.amount *= 0.85
            self.awareness = max(0.0, self.awareness - dt * 0.5)
            self.look_offset = math.sin(self.t * 5.0) * 25.0
        elif self.alive and (not self.frozen):
            self._think(dt)
        elif self.frozen:
            self.look_offset *= max(0.0, 1.0 - dt * 6.0)
        self.ch.update(dt)
        self._update_cone()

    def _think(self, dt):
        S = self.S
        p = S.player
        seen = 0.0
        if p is not None and S.stealth_active and (self.state != 'chase'):
            seen = self.vision_amount(p) + self.hearing_amount(p)
        if seen > 0:
            self.awareness = min(1.0, self.awareness + seen * dt * 1.05 * self.alert_mult)
        else:
            self.awareness = max(0.0, self.awareness - dt * 0.28)
        if self.awareness >= 1.0 and (not self.spotted_called) and (self.state != 'chase'):
            self.spotted_called = True
            self.state = 'chase'
            S.on_spotted(self)
        if self.state == 'chase' and p is not None:
            dx, dz = (p.x - self.x, p.z - self.z)
            d = math.hypot(dx, dz)
            if d > 1.1:
                self.ch.root.x += dx / d * self.chase_speed * dt
                self.ch.root.z += dz / d * self.chase_speed * dt
                self.ch.amount = 1.0
            else:
                self.ch.amount = 0.0
            self.ch.face(dx, dz, dt, turn_speed=20)
            self.look_offset = 0.0
            return
        suspicious = self.awareness > 0.25 and p is not None
        if suspicious:
            dx, dz = (p.x - self.x, p.z - self.z)
            self.ch.amount += (0.0 - self.ch.amount) * min(1.0, 8 * dt)
            self.ch.face(dx, dz, dt, turn_speed=4.0)
            self.look_offset += (0.0 - self.look_offset) * min(1.0, 6 * dt)
            return
        if self.investigate is not None:
            tx, tz = self.investigate
            dx, dz = (tx - self.x, tz - self.z)
            d = math.hypot(dx, dz)
            if d > 0.8:
                self.ch.root.x += dx / d * self.speed * 1.6 * dt
                self.ch.root.z += dz / d * self.speed * 1.6 * dt
                self.ch.face(dx, dz, dt, turn_speed=9.0)
                self.ch.amount += (0.8 - self.ch.amount) * min(1.0, 8 * dt)
            else:
                self.ch.amount += (0.0 - self.ch.amount) * min(1.0, 8 * dt)
                self._inv_wait += dt
                self.look_offset = math.sin(self._inv_wait * 2.2) * 55.0
                if self._inv_wait > 3.2:
                    self.investigate = None
                    self._inv_wait = 0.0
            return
        if self.route:
            tx, tz = self.route[self.wp]
            dx, dz = (tx - self.x, tz - self.z)
            d = math.hypot(dx, dz)
            if self.wait > 0:
                self.wait -= dt
                self.ch.amount += (0.0 - self.ch.amount) * min(1.0, 8 * dt)
                self.look_offset = math.sin(self.t * 1.6) * self.sweep
            elif d < 0.25:
                self.wait = self.pause
                self.wp = (self.wp + 1) % len(self.route)
            else:
                self.ch.root.x += dx / d * self.speed * dt
                self.ch.root.z += dz / d * self.speed * dt
                self.ch.face(dx, dz, dt, turn_speed=7.0)
                self.ch.amount += (0.62 - self.ch.amount) * min(1.0, 8 * dt)
                self.look_offset += (0.0 - self.look_offset) * min(1.0, 5 * dt)
        else:
            dx, dz = (self.home[0] - self.x, self.home[1] - self.z)
            d = math.hypot(dx, dz)
            if d > 0.3:
                self.ch.root.x += dx / d * self.speed * dt
                self.ch.root.z += dz / d * self.speed * dt
                self.ch.face(dx, dz, dt, turn_speed=7.0)
                self.ch.amount += (0.62 - self.ch.amount) * min(1.0, 8 * dt)
                self.look_offset += (0.0 - self.look_offset) * min(1.0, 5 * dt)
            else:
                self.ch.amount += (0.0 - self.ch.amount) * min(1.0, 8 * dt)
                hf = math.radians(self.home_facing)
                self.ch.face(math.sin(hf), math.cos(hf), dt, turn_speed=3.0)
                self.look_offset = math.sin(self.t * 0.9 + self.home_facing) * self.sweep

    def _update_cone(self):
        if not self.alive:
            return
        S = self.S
        facing = self.facing
        reach = self.view
        r = math.radians(facing)
        if self.level_y <= 1.5:
            for frac in (1.0, 0.8, 0.6, 0.4, 0.25):
                L = self.view * frac
                if S.world.line_of_sight(self.x, self.z, self.x + math.sin(r) * L, self.z + math.cos(r) * L):
                    reach = L
                    break
                reach = L * 0.5
        self.cone_reach += (reach - self.cone_reach) * 0.35
        width = 2.0 * self.cone_reach * math.tan(math.radians(self.fov / 2.0)) * 0.95
        self.cone_pivot.position = (self.x, self.level_y, self.z)
        self.cone_pivot.rotation_y = facing
        self.cone.position = (0, 0.05, self.cone_reach / 2.0)
        self.cone.scale = (width, self.cone_reach)
        a = self.awareness
        col = (0.3 + 0.7 * min(1, a * 2), 1.0 - 0.75 * max(0.0, a - 0.35) / 0.65, 0.5 - 0.4 * a, 0.28 + 0.4 * a)
        self.cone.color = col

class Follower:

    def __init__(self, scene, character, delay=0.9):
        self.S = scene
        self.ch = character
        self.delay = delay
        self._px, self._pz = (character.root.x, character.root.z)
        self.active = True

    def update(self, dt):
        if self.active:
            s = self.S.player.trail_at(self.delay)
            if s:
                x, z, a = s
                ch = self.ch
                dx, dz = (x - ch.root.x, z - ch.root.z)
                ch.root.x += dx * min(1.0, 10 * dt)
                ch.root.z += dz * min(1.0, 10 * dt)
                speed = math.hypot(ch.root.x - self._px, ch.root.z - self._pz) / max(dt, 0.0001)
                self._px, self._pz = (ch.root.x, ch.root.z)
                goal = min(1.0, speed / 5.0)
                ch.amount += (goal - ch.amount) * min(1.0, 10 * dt)
                if speed > 0.4:
                    ch.face(dx, dz, dt)
                else:
                    ch.amount *= 0.9
        self.ch.update(dt)
