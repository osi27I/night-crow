import math
import random
from ursina import Entity, Vec3, destroy
from engine.assets import tex
from engine.entities import glow_quad, mk, rgb, shade
from engine.props import bush, dead_tree, distant_dunes, ground, ground_patches, moon, rock, scatter_clutter, soft_path, tent
HUNT_X = -300.0
HUNT_BOUNDS = (HUNT_X - 24.0, HUNT_X + 26.0, -16.0, 34.0)
HUNT_START = (HUNT_X - 20.0, 3.0)
CAMP = (HUNT_X - 19.0, 27.0)
HARE_SPOTS = [(HUNT_X - 6, 8), (HUNT_X + 7, 15), (HUNT_X + 15, -3), (HUNT_X - 3, 25), (HUNT_X + 16, 27), (HUNT_X - 13, -9), (HUNT_X + 3, -8), (HUNT_X + 21, 10)]
HARES_NEEDED = 3
CALM = dict(ambient=Vec3(0.42, 0.4, 0.5), sun=Vec3(1.0, 0.8, 0.56), sun_dir=Vec3(-0.72, 0.5, 0.28), fog=Vec3(0.66, 0.54, 0.5), tint=(1.03, 0.99, 0.94), density=0.0105)

def _mix(a, b, k):
    return a + (b - a) * k

class Hare:
    SHY_RUN, SHY_WALK, SHY_STILL = (10.0, 4.6, 2.0)
    SPEED = 7.4

    def __init__(self, S, pos, seed=0):
        self.S = S
        self.rnd = random.Random(seed)
        self.root = Entity(parent=S.root, position=(pos[0], 0, pos[1]), scale=1.55, add_to_scene_entities=False)
        self.body = Entity(parent=self.root, add_to_scene_entities=False)
        fur = rgb(166, 128, 90)
        mk(self.body, 'sphere', (0, 0.25, 0.0), (0.34, 0.3, 0.52), fur)
        mk(self.body, 'sphere', (0, 0.29, -0.17), (0.32, 0.36, 0.34), shade(fur, 0.94))
        mk(self.body, 'sphere', (0, 0.17, 0.08), (0.28, 0.16, 0.36), rgb(214, 190, 150))
        mk(self.body, 'sphere', (0, 0.3, -0.36), 0.13, rgb(240, 234, 224))
        for sx in (-1, 1):
            mk(self.body, 'sphere', (sx * 0.13, 0.12, -0.2), (0.1, 0.18, 0.3), shade(fur, 0.88))
        self.head = Entity(parent=self.body, position=(0, 0.4, 0.27), add_to_scene_entities=False)
        mk(self.head, 'sphere', (0, 0, 0), (0.2, 0.2, 0.27), shade(fur, 1.08))
        mk(self.head, 'sphere', (0, -0.03, 0.12), (0.1, 0.09, 0.1), rgb(226, 204, 176))
        mk(self.head, 'sphere', (0, -0.01, 0.17), 0.035, rgb(60, 36, 34))
        self.ears = []
        for sx in (-1, 1):
            e = Entity(parent=self.head, position=(sx * 0.055, 0.07, -0.04), rotation=(-10, 0, sx * 7), add_to_scene_entities=False)
            mk(e, 'cone', (0, 0, 0), (0.07, 0.34, 0.05), fur)
            mk(e, 'cone', (0, 0.02, 0.012), (0.04, 0.26, 0.02), rgb(222, 170, 156))
            self.ears.append(e)
            mk(self.head, 'sphere', (sx * 0.085, 0.035, 0.07), 0.035, rgb(18, 14, 12), emissive=0.2)
        self.mark = Entity(parent=self.root, position=(0, 1.15, 0), add_to_scene_entities=False)
        mk(self.mark, 'cube', (0, 0, 0), (0.2, 0.2, 0.2), rgb(255, 214, 110), emissive=1.0, rot=(45, 0, 45))
        glow_quad(self.mark, (0, 0, 0), 0.8, (1.0, 0.8, 0.35, 0.55), tex('glow'))
        self.mark.enabled = False
        self.state = 'graze'
        self.t = self.rnd.uniform(0.5, 2.5)
        self.hop_t = 0.0
        self.hop_dir = (0.0, 1.0)
        self.flee_dir = (0.0, 1.0)
        self.turn_t = 0.0
        self.wait = 0.0
        self.nibble = 0.0
        self.age = 0.0
        self.face(self.rnd.uniform(-1, 1), self.rnd.uniform(-1, 1))

    @property
    def x(self):
        return self.root.x

    @property
    def z(self):
        return self.root.z

    def face(self, dx, dz):
        if abs(dx) + abs(dz) > 0.0001:
            self.root.rotation_y = math.degrees(math.atan2(dx, dz))

    def heading(self):
        a = math.radians(self.root.rotation_y)
        return (math.sin(a), math.cos(a))

    def alive(self):
        return self.state not in ('dead', 'hide', 'gone')

    def shootable(self):
        return self.state in ('graze', 'alert')

    def _clamp(self, b):
        x0, x1, z0, z1 = b
        hit = False
        if self.root.x < x0 + 1.5 or self.root.x > x1 - 1.5:
            self.root.x = min(max(self.root.x, x0 + 1.5), x1 - 1.5)
            hit = True
        if self.root.z < z0 + 1.5 or self.root.z > z1 - 1.5:
            self.root.z = min(max(self.root.z, z0 + 1.5), z1 - 1.5)
            hit = True
        return hit

    def hit(self):
        self.state = 'dead'
        self.t = 0.0
        self.mark.enabled = False
        self.body.rotation_z = 80
        self.body.y = 0.1
        self.head.rotation_x = 20

    def update(self, dt, p, b, spots):
        self.age += dt
        if self.state == 'gone':
            return
        if self.state == 'dead':
            self.t += dt
            if self.t > 1.0:
                self.state = 'gone'
                self.root.enabled = False
            return
        if self.state == 'hide':
            self.wait -= dt
            if self.wait <= 0:
                self._respawn(p, spots)
            return
        dx, dz = (p.x - self.x, p.z - self.z)
        d = math.hypot(dx, dz)
        shy = self.SHY_RUN if p.running else self.SHY_WALK if p.moving else self.SHY_STILL
        if self.state in ('graze', 'hop') and d < shy:
            self.state = 'alert'
            self.t = 0.6 + self.rnd.uniform(0.0, 0.25)
            self.body.y = 0.0
        if self.state == 'alert':
            self.t -= dt
            self.face(dx, dz)
            self.head.rotation_x = _mix(self.head.rotation_x, -22.0, min(1.0, dt * 14))
            self.body.rotation_x = _mix(self.body.rotation_x, -26.0, min(1.0, dt * 12))
            for e in self.ears:
                e.rotation_x = -2
            if d > shy * 1.4 and p.running is False:
                self.state = 'graze'
                self.t = 1.0
            elif self.t <= 0:
                self.state = 'flee'
                self.t = 2.4 + self.rnd.uniform(0.0, 0.8)
                self.turn_t = 0.0
                self.body.rotation_x = 0.0
                self.head.rotation_x = 0.0
                n = max(d, 0.001)
                self.flee_dir = (-dx / n, -dz / n)
        elif self.state == 'flee':
            self.t -= dt
            self.turn_t -= dt
            if self.turn_t <= 0:
                self.turn_t = self.rnd.uniform(0.35, 0.7)
                a = math.atan2(self.flee_dir[0], self.flee_dir[1]) + math.radians(self.rnd.uniform(-38, 38))
                self.flee_dir = (math.sin(a), math.cos(a))
            self.root.x += self.flee_dir[0] * self.SPEED * dt
            self.root.z += self.flee_dir[1] * self.SPEED * dt
            if self._clamp(b):
                cx, cz = ((b[0] + b[1]) / 2, (b[2] + b[3]) / 2)
                n = max(math.hypot(cx - self.x, cz - self.z), 0.001)
                self.flee_dir = ((cx - self.x) / n, (cz - self.z) / n)
            self.face(*self.flee_dir)
            k = self.age * 9.0 % (2 * math.pi)
            self.body.y = abs(math.sin(k)) * 0.3
            self.body.rotation_x = math.sin(k) * -12
            for e in self.ears:
                e.rotation_x = 52
            if self.t <= 0:
                self.state = 'hide'
                self.wait = 6.0 + self.rnd.uniform(0.0, 3.0)
                self.root.enabled = False
                self.S.fx.dust_puff((self.x, 0.2, self.z), 4, color=(0.7, 0.6, 0.45))
        else:
            self.body.rotation_x = _mix(self.body.rotation_x, 0.0, min(1.0, dt * 10))
            if self.state == 'graze':
                self.t -= dt
                self.nibble += dt
                dip = 34.0 if self.nibble % 1.6 < 1.1 else 4.0
                self.head.rotation_x = _mix(self.head.rotation_x, dip, min(1.0, dt * 9))
                for i, e in enumerate(self.ears):
                    e.rotation_x = -10 + math.sin(self.age * 5 + i * 2.1) * 4 * (1 if self.age * 0.5 % 3 < 0.4 else 0)
                if self.t <= 0:
                    self.state = 'hop'
                    self.hop_t = 0.0
                    a = self.rnd.uniform(0, math.tau)
                    self.hop_dir = (math.sin(a), math.cos(a))
                    cx, cz = ((b[0] + b[1]) / 2, (b[2] + b[3]) / 2)
                    if abs(self.x - cx) > (b[1] - b[0]) * 0.38 or abs(self.z - cz) > (b[3] - b[2]) * 0.38:
                        n = max(math.hypot(cx - self.x, cz - self.z), 0.001)
                        self.hop_dir = ((cx - self.x) / n, (cz - self.z) / n)
                    self.face(*self.hop_dir)
            else:
                self.hop_t += dt
                k = min(1.0, self.hop_t / 0.36)
                self.root.x += self.hop_dir[0] * 3.2 * dt
                self.root.z += self.hop_dir[1] * 3.2 * dt
                self.body.y = math.sin(k * math.pi) * 0.24
                self.body.rotation_x = math.sin(k * math.pi) * -14
                self._clamp(b)
                if k >= 1.0:
                    self.body.y = 0.0
                    self.state = 'graze'
                    self.t = self.rnd.uniform(1.8, 4.2)
        self.mark.rotation_y += 150.0 * dt

    def _respawn(self, p, spots):
        far = [s for s in spots if math.hypot(s[0] - p.x, s[1] - p.z) > 15.0] or spots
        s = self.rnd.choice(far)
        self.root.position = (s[0] + self.rnd.uniform(-1.5, 1.5), 0, s[1] + self.rnd.uniform(-1.5, 1.5))
        self.root.enabled = True
        self.state = 'graze'
        self.t = self.rnd.uniform(1.0, 3.0)
        self.body.rotation_z = 0
        self.body.y = 0.0

class HuntMixin:

    def _build_hills(self):
        rnd = random.Random(31)
        hx = HUNT_X
        g = ground(self, 150, 'sand', 46, rgb(146, 168, 88))
        g.x, g.z = (hx, 9.0)
        self.hill_ground = g
        ground_patches(self, hx - 32, -22, hx + 34, 40, count=110, seed=41, palette=[rgb(96, 130, 56), rgb(132, 148, 66), rgb(160, 150, 80), rgb(80, 110, 52)], alpha=(0.3, 0.55), size=(3.0, 8.0))
        scatter_clutter(self, hx - 30, -20, hx + 32, 38, count=200, seed=6, avoid=[(CAMP[0] - 3, CAMP[0] + 3, CAMP[1] - 3, CAMP[1] + 3)], grass=rgb(112, 128, 62), pebble=rgb(130, 118, 104))
        soft_path(self, [(HUNT_START[0] - 3, HUNT_START[1]), (hx - 12, 8), (hx - 4, 14), (hx + 6, 18), (CAMP[0], CAMP[1] - 3)], width=2.0, seed=4, col=rgb(150, 126, 92), alpha=0.5)
        for _ in range(22):
            x, z = (rnd.uniform(hx - 24, hx + 24), rnd.uniform(-14, 32))
            if math.hypot(x - HUNT_START[0], z - HUNT_START[1]) < 5 or math.hypot(x - CAMP[0], z - CAMP[1]) < 5:
                continue
            bush(self, x, z, s=rnd.uniform(0.8, 1.6), col=rgb(*rnd.choice([(66, 98, 48), (96, 108, 52), (78, 90, 46)])), flowers=(228, 204, 96) if rnd.random() < 0.35 else None)
        for x, z, h in ((hx - 12, 16, 4.6), (hx + 10, 5, 3.8), (hx + 22, 22, 4.2), (hx - 6, -10, 3.4)):
            dead_tree(self, x, z, h=h, col=rgb(128, 98, 72))
        for i in range(40):
            side = rnd.choice(('n', 'w', 's', 'e'))
            if side == 'n':
                x, z = (rnd.uniform(hx - 26, hx + 28), rnd.uniform(35, 40))
            elif side == 's':
                x, z = (rnd.uniform(hx - 26, hx + 28), rnd.uniform(-22, -17))
            elif side == 'w':
                x, z = (rnd.uniform(hx - 31, hx - 26), rnd.uniform(-18, 36))
            else:
                x, z = (rnd.uniform(hx + 28, hx + 33), rnd.uniform(-18, 36))
            rock(self, x, z, s=rnd.uniform(1.8, 4.4), col=rgb(*rnd.choice([(206, 188, 170), (190, 176, 166), (216, 196, 172)])), collide=False)
        for x, z in ((hx - 8, 2), (hx + 12, 12), (hx - 15, 13), (hx + 18, -8), (hx + 4, 29)):
            rock(self, x, z, s=rnd.uniform(1.0, 1.7), col=rgb(206, 190, 172), collide=False)
        for x, z, w, h, d in ((hx - 4, 52, 90, 22, 26), (hx - 46, 10, 30, 18, 70), (hx + 52, 20, 26, 14, 70), (hx, -34, 90, 16, 26)):
            mk(self.root, 'sphere', (x, -3.0, z), (w, h, d), rgb(150, 124, 112), tex('rock'), tex_scale=(10, 3))
        distant_dunes(self, hx, 8.0, radius=130.0, count=26, seed=12, col=rgb(88, 66, 66), height=(8.0, 20.0))
        self.hunt_sun = moon(self, (hx - 70, 15, 78), size=34, color=(1.0, 0.66, 0.3, 1.0), halo=0.55, halo_color=(1.0, 0.52, 0.22))
        cx, cz = CAMP
        tent(self, cx - 2.2, cz + 0.6, r=1.9, h=2.2, col=rgb(158, 132, 98), face=(cx + 1.6, cz - 0.4))
        self.fx.fire((cx + 1.6, 0.15, cz - 0.4), scale=0.8, intensity=1.1)
        self.fx.embers((cx + 1.6, 0.6, cz - 0.4), scale=0.7, rate=4)
        self.camp_light = self.rig.add((cx + 1.6, 1.0, cz - 0.4), color=(1.0, 0.62, 0.3), intensity=1.4, radius=8.0, flicker=0.3)
        for a in range(6):
            mk(self.root, 'cylinder', (cx + 1.6 + math.cos(a * 1.05) * 0.5, 0.02, cz - 0.4 + math.sin(a * 1.05) * 0.5), (0.28, 0.24, 0.28), rgb(96, 90, 86), tex('stone_dark'))
        mk(self.root, 'cube', (cx + 0.2, 0.06, cz + 2.4), (1.4, 0.1, 2.2), rgb(146, 82, 62), rot=(0, 20, 0))
        mk(self.root, 'cube', (cx + 0.3, 0.14, cz + 3.2), (0.9, 0.16, 0.5), rgb(210, 190, 150), rot=(0, 20, 0))
        for k in range(3):
            mk(self.root, 'cylinder', (cx + 4.0 + k * 0.7, 0.0, cz + 1.4), (0.07, 1.5, 0.07), rgb(98, 70, 44))
        mk(self.root, 'cube', (cx + 4.7, 1.45, cz + 1.4), (2.0, 0.06, 0.06), rgb(98, 70, 44))
        for k in range(2):
            mk(self.root, 'sphere', (cx + 4.2 + k * 0.9, 1.0, cz + 1.4), (0.26, 0.6, 0.12), rgb(150, 112, 82))
        self.world.add_circle(cx - 2.2, cz + 0.6, 1.7)
        self.hunt_smoke = []
        for k, (dx, dz) in enumerate(((78, 6), (86, 18), (70, 28), (94, 0))):
            e = self.fx.smoke((hx + dx, 0, dz), scale=16.0, rate=6, tone=0.1, alpha=0.82, wind=(0.7, 0.2, 0.05))
            e.cull = False
            e.enabled = False
            self.hunt_smoke.append(e)
        self.hunt_glow = glow_quad(self.root, (hx + 120, 7, 12), (70, 22), (1.0, 0.36, 0.1, 0.0), tex('glow'), billboard=True, add=True, bin_sort=20)

    def _build_hares(self):
        self.hares = [Hare(self, HARE_SPOTS[i], seed=i + 3) for i in range(4)]
        for h, s in zip(self.hares, (HARE_SPOTS[0], HARE_SPOTS[3], HARE_SPOTS[1], HARE_SPOTS[5])):
            h.root.position = (s[0], 0, s[1])
        self.hunt_caught = 0
        self.hunt_arrows = []
        self.hunt_cool = 0.0
        self.quarry.enabled = False

    def mood_now(self):
        rig = self.rig
        t = self.game.post.values.get('tint', (1.0, 1.0, 1.0))
        return dict(ambient=Vec3(rig.ambient), sun=Vec3(rig.sun_color), sun_dir=Vec3(rig.sun_dir), fog=Vec3(rig.fog_color), tint=tuple(t), density=rig.fog_density)

    def set_mood(self, m, k=1.0, base=None):
        b = base or self.mood_now()
        rig = self.rig
        rig.ambient = _mix(b['ambient'], m['ambient'], k)
        rig.sun_color = _mix(b['sun'], m['sun'], k)
        rig.sun_dir = _mix(b['sun_dir'], m['sun_dir'], k)
        rig.fog_color = _mix(b['fog'], m['fog'], k)
        rig.fog_density = _mix(b['density'], m['density'], k)
        self.game.post.set(tint=tuple((_mix(b['tint'][i], m['tint'][i], k) for i in range(3))))

    def hunt_update(self, dt):
        p = self.player
        a = self.abdo
        self.hunt_cool = max(0.0, self.hunt_cool - dt)
        hint_target = None
        for h in self.hares:
            h.update(dt, p, HUNT_BOUNDS, HARE_SPOTS)
            h.mark.enabled = False
        t = self._hunt_target()
        if t is not None and (not self.player.locked) and (not self.cutscene_active):
            t.mark.enabled = True
        for ar in list(self.hunt_arrows):
            ar['t'] += dt
            k = min(1.0, ar['t'] / ar['dur'])
            e = ar['e']
            e.position = ar['p0'] + (ar['p1'] - ar['p0']) * k + Vec3(0, math.sin(k * math.pi) * 0.25, 0)
            if k >= 1.0:
                if ar['hit'] is not None:
                    self.fx.dust_puff((ar['p1'].x, 0.3, ar['p1'].z), 5, color=(0.8, 0.7, 0.55))
                    self.game.audio.play('thud', 0.6)
                    destroy(e)
                else:
                    e.y = max(0.05, e.y)
                    ar['life'] = ar.get('life', 0.0) + dt
                    if ar['life'] > 1.2:
                        destroy(e)
                        self.hunt_arrows.remove(ar)
                        continue
                    continue
                self.hunt_arrows.remove(ar)

    def _hunt_target(self):
        p = self.player
        a = self.abdo
        fx, fz = (math.sin(math.radians(a.root.rotation_y)), math.cos(math.radians(a.root.rotation_y)))
        best, bd = (None, 99.0)
        for h in self.hares:
            if not h.shootable():
                continue
            dx, dz = (h.x - p.x, h.z - p.z)
            d = math.hypot(dx, dz)
            if d > 7.8 or d < 0.5:
                continue
            if (dx * fx + dz * fz) / d < 0.78:
                continue
            if d < bd:
                best, bd = (h, d)
        return best

    def hunt_action(self):
        if self.phase != 'hunt' or self.hunt_cool > 0:
            return
        g = self.game
        p = self.player
        a = self.abdo
        self.hunt_cool = 1.0
        tgt = self._hunt_target()
        p0 = Vec3(p.x, 1.25, p.z)
        if tgt is not None:
            p1 = Vec3(tgt.x, 0.3, tgt.z)
            a.face(tgt.x - p.x, tgt.z - p.z)
        else:
            fx, fz = (math.sin(math.radians(a.root.rotation_y)), math.cos(math.radians(a.root.rotation_y)))
            p1 = Vec3(p.x + fx * 9.0, 0.05, p.z + fz * 9.0)
        e = Entity(parent=self.root, position=p0, add_to_scene_entities=False)
        mk(e, 'cube', (0, 0, 0.35), (0.03, 0.03, 0.8), rgb(176, 140, 96))
        mk(e, 'cube', (0, 0, 0.78), (0.06, 0.06, 0.1), rgb(190, 192, 204), emissive=0.2)
        mk(e, 'cube', (0, 0, -0.02), (0.1, 0.01, 0.12), rgb(230, 224, 210))
        e.look_at(p1)
        dur = max(0.12, (p1 - p0).length() / 38.0)
        self.hunt_arrows.append(dict(e=e, p0=p0, p1=p1, t=0.0, dur=dur, hit=tgt))
        g.audio.play('clink_soft', 0.5, pitch=0.8)
        a.arm_r_goal = -80
        self.tl.run(self._shot_release(tgt, dur))

    def _shot_release(self, tgt, dur):
        yield 0.3
        self.abdo.arm_r_goal = None
        if tgt is None:
            self.game.hud.hint('No hare in front of you. Face one, stay about 4-7 steps away.', hold=3)
            return
        yield max(0.0, dur - 0.3)
        if tgt.shootable():
            tgt.hit()
            self.hunt_caught += 1
            self.quarry.enabled = True
            left = HARES_NEEDED - self.hunt_caught
            if left > 0:
                self.game.hud.objective(f'Hunt hares for supper  ({self.hunt_caught}/{HARES_NEEDED})', announce=False)
                self.game.hud.hint(f'Hare {self.hunt_caught}/{HARES_NEEDED}', hold=2.5)
            else:
                self.phase = 'hunt_done'
                self.tl.run(self.hunt_end())
        else:
            self.game.hud.hint('It bolted just in time.', hold=2.5)

    def hunt_intro(self):
        g = self.game
        self.begin_cutscene()
        self.shot((HUNT_X - 30, 3.2, -6.0), (HUNT_X - 14, 1.2, 8.0), speed=9)
        self.cam.snap()
        g.hud.title_card('THREE DAYS IN THE HILLS', 'The Hunt', '', hold=2.6)
        yield 3.0
        self.shot((HUNT_X - 28, 4.0, -2.0), (HUNT_X - 6, 1.0, 10.0), speed=0.45)
        yield 2.4
        yield from self.talk([('Abdo', 'Three nights out here and the traps are empty. The children are waiting for meat.'), ('Abdo', 'Hares are shy. Walk, never run, and loose the arrow from a few steps away.')], {'Abdo': self.abdo})
        self.end_cutscene()
        self.phase = 'hunt'
        g.hud.objective(f'Hunt hares for supper  (0/{HARES_NEEDED})')
        g.hud.hint('WASD  walk quietly      SPACE  shoot the bow      Hares bolt when you run', hold=10)

    def hunt_end(self):
        g = self.game
        yield 0.9
        self.begin_cutscene()
        self.abdo.face(1, 0.05)
        g.hud.objective('Go home')
        self.shot((HUNT_X + 12, 2.2, 6.0), (HUNT_X + 60, 5.0, 10.0), speed=0.5)
        yield 1.0
        yield from self.talk([('Abdo', 'Three hares. Enough for the whole table tonight.')], {'Abdo': self.abdo})
        g.audio.play('stinger_soft', 0.7)
        for e in self.hunt_smoke:
            e.enabled = True
        self.tl.to(self.hunt_glow, 'alpha', 0.55, 4.0)
        self.tl.run(self._mood_to(self.BURN_MOOD, 5.0))
        self.shot((HUNT_X + 18, 3.6, 6.0), (HUNT_X + 85, 7.0, 10.0), speed=0.35)
        yield 4.2
        yield from self.talk([('Abdo', '...What is that on the horizon? That is not the sunset.')], {'Abdo': self.abdo})
        yield 0.3
        g.hud.fade_to(1.0, 1.2)
        yield 1.5
        self.hunt_leave()
        yield 0.5
        g.hud.fade_to(0.0, 0.9)
        yield from self.village_opening()

    def _mood_to(self, mood, duration):
        base = self.mood_now()
        t = 0.0
        while t < duration:
            t += self.dt
            self.set_mood(mood, min(1.0, t / duration), base=base)
            yield

    def hunt_leave(self):
        g = self.game
        for e in self.hunt_smoke:
            e.enabled = False
        for h in self.hares:
            h.root.enabled = False
        for ar in self.hunt_arrows:
            destroy(ar['e'])
        self.hunt_arrows.clear()
        self.hunt_sun.enabled = False
        self.hunt_sun.halo.enabled = False
        self.camp_light.enabled = False
        self.hunt_glow.enabled = False
        self.set_mood(self.BURN_MOOD, 1.0)
        g.post.set(vignette=0.5, bloom=1.0, grain=0.05)
        self.sky.fade_to(self, 'sky_smoke', duration=0.6)
        self.abdo.arm_r_goal = None
        self.bounds = self.VILLAGE_BOUNDS
        self.player.teleport(*self.VILLAGE_START)
        self.abdo.face(1, 0)
        self.cam.snap()
