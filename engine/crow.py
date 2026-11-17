import math
from ursina import Entity, Text, Vec3, camera, color, destroy
from engine.assets import FONT, FONT_BOLD, tex
from engine.entities import glow_quad, mk, rgb
from engine.particles import Emitter
from engine.timing import Clock, ease_in_out, ease_out
SIGHT_TIME = 6.0
SIGHT_COOLDOWN = 7.0
SMOKE_RADIUS = 3.1
SMOKE_TIME = 8.0
KNIFE_RANGE = 12.0
LEAP_MAX = 4.7

def _hide_depth(e):
    e.setDepthTest(False)
    e.setDepthWrite(False)
    return e

class Abilities:

    def __init__(self, scene, knives=3, smokes=2, max_knives=5, max_smokes=3, caw=None):
        self.S = scene
        self.enabled = False
        self.sight_unlocked = self.smoke_unlocked = self.knife_unlocked = True
        self.knives, self.smokes = (knives, smokes)
        self.max_knives, self.max_smokes = (max_knives, max_smokes)
        self.caw_state = caw
        self.sight_on = False
        self.sight_t = 0.0
        self.sight_cd = 0.0
        self._sight_amt = 0.0
        self._markers = {}
        self._marks = []
        self.extra_marks = None
        self.beacons = []
        self.clouds = []
        self.flights = []
        self.pickups = []
        self.smoke_cd = 0.0
        self.knife_cd = 0.0
        self._said = set()
        self._build_hud()

    def _build_hud(self):
        ui = camera.ui
        self.rows = []
        y = -0.285
        for i in range(4):
            t = Text(text='', parent=ui, position=(0.86, y - i * 0.043), origin=(0.5, -0.5), scale=0.95, font=FONT_BOLD, color=color.rgba(0.85, 0.9, 1.0, 0.0), z=-0.3, add_to_scene_entities=False)
            self.rows.append(t)

    def _set_row(self, i, text, ready, visible=True):
        t = self.rows[i]
        if t.text != text:
            t.text = text
        a = (0.95 if ready else 0.42) if visible else 0.0
        t.color = color.rgba(0.82, 0.9, 1.0, a)

    def _update_hud(self):
        vis = self.enabled and (not self.S.cutscene_active)
        if self.sight_unlocked:
            if self.sight_on:
                self._set_row(0, f'[C]  SIGHT  {self.sight_t:0.0f}s', True, vis)
            elif self.sight_cd > 0:
                self._set_row(0, f'[C]  SIGHT  {self.sight_cd:0.0f}s', False, vis)
            else:
                self._set_row(0, '[C]  SIGHT  ready', True, vis)
        else:
            self._set_row(0, '', False, False)
        if self.smoke_unlocked:
            self._set_row(1, f'[G]  SMOKE  x{self.smokes}', self.smokes > 0, vis)
        else:
            self._set_row(1, '', False, False)
        if self.knife_unlocked:
            self._set_row(2, f'[R]  KNIFE  x{self.knives}', self.knives > 0, vis)
        else:
            self._set_row(2, '', False, False)
        if self.caw_state:
            ready, left = self.caw_state()
            self._set_row(3, '[Q]  CAW  ready' if ready else f'[Q]  CAW  {left:0.0f}s', ready, vis)
        else:
            self._set_row(3, '', False, False)

    def hint_once(self, key, text, hold=6.0):
        if key not in self._said:
            self._said.add(key)
            self.S.game.hud.hint(text, hold=hold)

    def can_act(self):
        S = self.S
        return self.enabled and (not S.cutscene_active) and (not S.failing) and (S.player is not None) and (not S.player.locked) and (not S.game.dialogue.active)

    def on_key(self, key):
        if key == 'c':
            self.toggle_sight()
        elif key == 'g':
            self.throw_smoke()
        elif key == 'r':
            self.throw_knife()

    def resupply(self, knives=0, smokes=0):
        self.knives = min(self.max_knives, self.knives + knives)
        self.smokes = min(self.max_smokes, self.smokes + smokes)

    def on_reset(self):
        self.sight_off(cooldown=0.0)
        for c in list(self.clouds):
            self._end_cloud(c)
        for f in list(self.flights):
            destroy(f['e'])
        self.flights.clear()
        self.knives = max(self.knives, 2)
        self.smokes = max(self.smokes, 1)

    def toggle_sight(self):
        if not self.sight_unlocked or not self.can_act():
            return
        if self.sight_on:
            self.sight_off()
        elif self.sight_cd <= 0:
            self.sight_on = True
            self.sight_t = SIGHT_TIME
            S = self.S
            S.game.audio.play('wingbeat', 0.5, pitch=0.8)
            S.game.audio.play('stinger_soft', 0.7)
            S.ring_fx((S.player.x, S.player.z), (0.45, 0.8, 1.0), 16.0, 1.1, y=0.12)
            S.player.speed_mult = 0.65

    def sight_off(self, cooldown=SIGHT_COOLDOWN):
        if self.sight_on:
            self.sight_on = False
            self.sight_cd = cooldown
            if self.S.player:
                self.S.player.speed_mult = 1.0

    def _guard_marker(self, gd):
        m = self._markers.get(id(gd))
        if m is None:
            S = self.S
            orb = _hide_depth(glow_quad(S.root, (0, 0, 0), 0.7, (1.0, 0.8, 0.3, 0.95), tex('glow'), billboard=True, add=True, bin_sort=60))
            ring = _hide_depth(glow_quad(S.root, (0, 0.1, 0), 1.7, (1.0, 0.8, 0.3, 0.8), tex('ring'), billboard=False, add=True, bin_sort=59))
            ring.rotation_x = 90
            orb.enabled = ring.enabled = False
            m = (orb, ring)
            self._markers[id(gd)] = m
        return m

    def _update_sight(self, dt):
        S = self.S
        goal = 1.0 if self.sight_on else 0.0
        self._sight_amt += (goal - self._sight_amt) * min(1.0, dt * 7.0)
        S.game.post.values['sight'] = self._sight_amt
        if self.sight_on:
            self.sight_t -= dt
            if self.sight_t <= 0:
                self.sight_off()
        elif self.sight_cd > 0:
            self.sight_cd = max(0.0, self.sight_cd - dt)
        show = self._sight_amt > 0.15
        t = Clock.now
        for gd in S.guards:
            orb, ring = self._guard_marker(gd)
            on = show and gd.alive
            orb.enabled = ring.enabled = on
            if on:
                gy = gd.ch.root.y
                pulse = 0.9 + 0.12 * math.sin(t * 6.0 + gd.x)
                a = gd.awareness
                if gd.blind_t > 0:
                    col = (0.6, 0.65, 0.75)
                elif gd.state == 'chase':
                    col = (1.0, 0.15, 0.1)
                else:
                    col = (1.0, 0.82 - 0.6 * min(1.0, a * 2), 0.3 - 0.2 * min(1.0, a * 2))
                orb.position = (gd.x, gy + 2.45, gd.z)
                orb.scale = 0.75 * pulse
                orb.color = color.rgba(col[0], col[1], col[2], 0.95 * self._sight_amt)
                ring.position = (gd.x, gy + 0.1, gd.z)
                ring.scale = 1.9 * pulse
                ring.color = color.rgba(col[0], col[1], col[2], 0.85 * self._sight_amt)
        for b in self._markers.keys() - {id(g) for g in S.guards}:
            for e in self._markers.pop(b):
                e.enabled = False
        pts = []
        if show:
            if self.extra_marks:
                pts.extend(self.extra_marks())
            pts.extend(((p['x'], p['y'] + 1.0, p['z']) for p in self.pickups if p['alive']))
        while len(self._marks) < len(pts):
            m = _hide_depth(glow_quad(S.root, (0, 0, 0), 0.5, (0.5, 0.85, 1.0, 0.9), tex('glow'), billboard=True, add=True, bin_sort=58))
            m.enabled = False
            self._marks.append(m)
        for i, m in enumerate(self._marks):
            if i < len(pts):
                m.enabled = True
                m.position = pts[i]
                m.scale = 0.55 + 0.1 * math.sin(t * 5.0 + i)
                m.color = color.rgba(0.5, 0.85, 1.0, 0.9 * self._sight_amt)
            else:
                m.enabled = False
        for b in self.beacons:
            b.enabled = show
            if show:
                b.color = color.rgba(0.45, 0.8, 1.0, 0.5 * self._sight_amt)

    def add_beacon(self, x, z, h=9.0):
        b = _hide_depth(glow_quad(self.S.root, (x, h / 2.0, z), (1.6, h), (0.45, 0.8, 1.0, 0.5), tex('shaft'), billboard=True, add=True, bin_sort=57))
        b.enabled = False
        self.beacons.append(b)
        return b

    def _free_distance(self, want):
        S, p = (self.S, self.S.player)
        a = math.radians(p.ch.angle)
        sx, sz = (math.sin(a), math.cos(a))
        best = 0.8
        d = 0.8
        while d <= want:
            if not S.world.line_of_sight(p.x, p.z, p.x + sx * d, p.z + sz * d):
                break
            best = d
            d += 0.4
        return (best, sx, sz)

    def throw_smoke(self):
        if not self.smoke_unlocked or not self.can_act():
            return
        if self.smokes <= 0:
            self.S.game.hud.hint('No smoke bombs left. Look for bundles - or Crow Sight shows them.', hold=3.0)
            return
        if self.smoke_cd > 0:
            return
        S, p = (self.S, self.S.player)
        d, sx, sz = self._free_distance(5.5)
        tx, tz = (p.x + sx * d, p.z + sz * d)
        self.smokes -= 1
        self.smoke_cd = 0.8
        p.ch.face(sx, sz)
        p.ch.attack()
        S.game.audio.play('blade', 0.35, pitch=0.7)
        S.tl.run(self._smoke_flight(p.x, p.ch.root.y + 1.2, p.z, tx, p.ch.root.y, tz))

    def _smoke_flight(self, x0, y0, z0, x1, y1, z1):
        S = self.S
        ball = mk(S.root, 'sphere', (x0, y0, z0), 0.2, rgb(40, 40, 52))
        T = 0.5
        t = 0.0
        while t < T:
            t += S.dt
            k = min(1.0, t / T)
            ball.position = (x0 + (x1 - x0) * k, y0 + (y1 + 0.15 - y0) * k + math.sin(k * math.pi) * 1.6, z0 + (z1 - z0) * k)
            yield
        destroy(ball)
        self._pop_smoke(x1, y1, z1)

    def _pop_smoke(self, x, y, z):
        S = self.S
        em = Emitter(S.root, (x, y + 0.5, z), rate=36, max_particles=120, life=(2.0, 3.2), speed=(0.2, 0.8), direction=(0, 0.5, 0), spread=1.3, size=(2.0, 3.8), color0=(0.52, 0.55, 0.66, 0.6), color1=(0.32, 0.34, 0.44, 0.0), texture='smoke', blend='alpha', turbulence=1.2, bin_sort=31, spin=30, area=(SMOKE_RADIUS * 0.55, 0.25, SMOKE_RADIUS * 0.55), drag=0.8)
        em.cull = False
        S.fx.add(em)
        em.burst(70)
        S.game.audio.play('snuff', 0.9, pitch=0.6)
        S.game.audio.play('thud', 0.4)
        S.ring_fx((x, z), (0.7, 0.75, 0.9), SMOKE_RADIUS * 2.2, 0.7, y=y + 0.1)
        S.fx.sparks((x, y + 0.5, z), 10, color0=(0.8, 0.85, 1.0, 1.0), color1=(0.4, 0.45, 0.8, 0.0))
        S.cam.shake(0.05, 0.2)
        self.clouds.append({'x': x, 'z': z, 't': SMOKE_TIME, 'em': em, 'y': y})

    def _end_cloud(self, c):
        if c in self.clouds:
            self.clouds.remove(c)
        c['em'].rate = 0
        c['em'].enabled = False
        c['em'].clear()

    def in_cloud(self, x, z, margin=0.0):
        for c in self.clouds:
            if math.hypot(x - c['x'], z - c['z']) < SMOKE_RADIUS + margin:
                return c
        return None

    def _segment_through_cloud(self, ax, az, bx, bz):
        dx, dz = (bx - ax, bz - az)
        L2 = dx * dx + dz * dz
        for c in self.clouds:
            if L2 < 1e-06:
                continue
            t = max(0.0, min(1.0, ((c['x'] - ax) * dx + (c['z'] - az) * dz) / L2))
            if math.hypot(ax + dx * t - c['x'], az + dz * t - c['z']) < SMOKE_RADIUS * 0.8:
                return True
        return False

    def _update_clouds(self, dt):
        for c in list(self.clouds):
            c['t'] -= dt
            if c['t'] < 1.8:
                c['em'].rate = 0
            if c['t'] <= 0:
                self._end_cloud(c)
        if self.clouds:
            for gd in self.S.guards:
                if gd.alive and gd.state != 'chase' and self.in_cloud(gd.x, gd.z):
                    if gd.blind_t <= 0:
                        self.S.fx.sparks((gd.x, gd.ch.root.y + 2.0, gd.z), 4, color0=(0.8, 0.8, 0.9, 1.0), color1=(0.5, 0.5, 0.6, 0.0))
                    gd.blind_t = 0.6

    def _knife_target(self):
        S, p = (self.S, self.S.player)
        a = math.radians(p.ch.angle)
        dx, dz = (math.sin(a), math.cos(a))
        best, best_along = (None, 1000000000.0)
        for gd in S.guards:
            if not gd.alive or gd.state == 'chase':
                continue
            vx, vz = (gd.x - p.x, gd.z - p.z)
            along = vx * dx + vz * dz
            if along < 0.6 or along > KNIFE_RANGE:
                continue
            lateral = abs(vx * dz - vz * dx)
            if lateral > 0.8 + along * 0.05:
                continue
            if abs(gd.ch.root.y - p.ch.root.y) > 1.6:
                continue
            if S.world.line_of_sight(p.x, p.z, gd.x, gd.z) is False and (not self.skip_los(gd, p)):
                continue
            if along < best_along:
                best, best_along = (gd, along)
        return (best, dx, dz)

    def throw_knife(self):
        if not self.knife_unlocked or not self.can_act() or self.knife_cd > 0:
            return
        S, p = (self.S, self.S.player)
        if self.knives <= 0:
            S.game.hud.hint('No knives left. Knife bundles glow in Crow Sight.', hold=3.0)
            return
        gd, dx, dz = self._knife_target()
        self.knives -= 1
        self.knife_cd = 0.45
        p.ch.face(dx, dz)
        p.ch.attack()
        S.game.audio.play('blade', 0.45, pitch=1.5)
        y0 = p.ch.root.y + 1.25
        if gd is not None:
            tx, ty, tz = (gd.x, gd.ch.root.y + 1.3, gd.z)
            hit = True
        else:
            d = KNIFE_RANGE * 0.75
            while d > 1.0 and (not S.world.line_of_sight(p.x, p.z, p.x + dx * d, p.z + dz * d)):
                d -= 0.5
            tx, ty, tz = (p.x + dx * d, y0 - 0.35, p.z + dz * d)
            hit = False
        e = mk(S.root, 'cube', (p.x, y0, p.z), (0.05, 0.05, 0.55), rgb(220, 228, 240), emissive=0.5, rot=(0, math.degrees(math.atan2(dx, dz)), 0))
        dist = math.hypot(tx - p.x, tz - p.z)
        self.flights.append({'e': e, 'x0': p.x, 'y0': y0, 'z0': p.z, 'x1': tx, 'y1': ty, 'z1': tz, 't': 0.0, 'T': max(0.08, dist / 32.0), 'gd': gd, 'hit': hit})

    def fire_knife(self, p0, p1, callback):
        S = self.S
        dx, dz = (p1[0] - p0[0], p1[2] - p0[2])
        e = mk(S.root, 'cube', p0, (0.05, 0.05, 0.55), rgb(220, 228, 240), emissive=0.5, rot=(0, math.degrees(math.atan2(dx, dz)), 0))
        dist = math.hypot(dx, dz)
        self.flights.append({'e': e, 'x0': p0[0], 'y0': p0[1], 'z0': p0[2], 'x1': p1[0], 'y1': p1[1], 'z1': p1[2], 't': 0.0, 'T': max(0.08, dist / 32.0), 'gd': None, 'hit': False, 'cb': callback})

    def _update_flights(self, dt):
        for f in list(self.flights):
            f['t'] += dt
            k = min(1.0, f['t'] / f['T'])
            f['e'].position = (f['x0'] + (f['x1'] - f['x0']) * k, f['y0'] + (f['y1'] - f['y0']) * k, f['z0'] + (f['z1'] - f['z0']) * k)
            if k >= 1.0:
                self.flights.remove(f)
                destroy(f['e'])
                self._knife_lands(f)

    def _knife_lands(self, f):
        S = self.S
        if f.get('cb'):
            f['cb']()
            return
        gd = f['gd']
        pos = (f['x1'], f['y1'], f['z1'])
        if f['hit'] and gd is not None and gd.alive:
            if getattr(gd, 'armor', False):
                S.game.audio.play('clink', 0.8, pitch=1.3)
                S.fx.sparks(pos, 14)
                S.game.hud.hint('Armour! The knife glanced off - he is coming to look.', hold=2.5)
                gd.hear(S.player.x, S.player.z)
            else:
                self.kill_guard(gd, 'knife')
        else:
            S.game.audio.play('clink', 0.5, pitch=1.6)
            S.fx.sparks(pos, 5)
            self.noise(f['x1'], f['z1'], 8.0)

    def kill_guard(self, gd, how='takedown'):
        S = self.S
        gd.kill()
        S.game.audio.play('thud', 0.7)
        S.fx.dust_puff((gd.x, gd.ch.root.y + 0.2, gd.z), 6)
        S.fx.sparks((gd.x, gd.ch.root.y + 1.2, gd.z), 8, color0=(0.8, 0.9, 1.0, 1.0), color1=(0.4, 0.5, 0.9, 0.0))
        S.ring_fx((gd.x, gd.z), (0.6, 0.75, 1.0), 3.0, 0.5, y=gd.ch.root.y + 0.1)
        fn = getattr(S, 'guard_down', None)
        if fn:
            fn(gd, how)

    def noise(self, x, z, radius):
        for gd in self.S.guards:
            if gd.alive and gd.state != 'chase' and (math.hypot(gd.x - x, gd.z - z) < radius) and (abs(gd.ch.root.y - self.S.player.ch.root.y) < 1.6):
                gd.hear(x, z)

    def skip_los(self, gd, p):
        return gd.ch.root.y > 1.5 or p.ch.root.y > 1.5

    def vision_scale(self, gd, p):
        if gd.blind_t > 0:
            return 0.0
        if self.clouds:
            if self.in_cloud(p.x, p.z, -0.3) or self._segment_through_cloud(gd.x, gd.z, p.x, p.z):
                return 0.0
        py, gy = (p.ch.root.y, gd.ch.root.y)
        if py > 1.5 and gy < 1.0:
            return 0.4
        if gy > 1.5 and py < 1.0:
            return 0.9
        return 1.0

    def add_pickup(self, x, z, kind='knife', y=0.0):
        S = self.S
        col = (0.75, 0.85, 1.0) if kind == 'knife' else (0.7, 0.72, 0.85)
        halo = glow_quad(S.root, (x, y + 0.55, z), 1.1, (*col, 0.6), tex('glow'), billboard=True, add=True, bin_sort=40)
        if kind == 'knife':
            body = [mk(S.root, 'cube', (x + dx, y + 0.3, z), (0.05, 0.04, 0.5), rgb(210, 220, 235), emissive=0.4, rot=(0, 20 * i, 0)) for i, dx in enumerate((-0.12, 0.0, 0.12))]
        else:
            body = [mk(S.root, 'sphere', (x + dx, y + 0.2, z + dz), 0.26, rgb(60, 60, 78), emissive=0.15) for dx, dz in ((-0.14, 0.0), (0.14, 0.04), (0.0, -0.14))]
        p = {'x': x, 'z': z, 'y': y, 'kind': kind, 'alive': True, 'halo': halo, 'body': body}
        self.pickups.append(p)
        return p

    def _update_pickups(self, dt):
        S = self.S
        if not self.pickups or S.player is None:
            return
        t = Clock.now
        for p in self.pickups:
            if not p['alive']:
                continue
            p['halo'].scale = 1.0 + 0.15 * math.sin(t * 3.0 + p['x'])
            if math.hypot(S.player.x - p['x'], S.player.z - p['z']) < 1.0 and abs(S.player.ch.root.y - p['y']) < 1.0:
                p['alive'] = False
                p['halo'].enabled = False
                for b in p['body']:
                    b.enabled = False
                if p['kind'] == 'knife':
                    self.resupply(knives=2)
                    msg = '+2 throwing knives'
                else:
                    self.resupply(smokes=1)
                    msg = '+1 smoke bomb'
                S.game.audio.play('pickup', 0.7)
                S.game.hud.caption(msg, hold=0.6, fade=0.3, size=1.3, tone=(0.75, 0.88, 1.0))

    def update(self, dt):
        if self.smoke_cd > 0:
            self.smoke_cd -= dt
        if self.knife_cd > 0:
            self.knife_cd -= dt
        self._update_sight(dt)
        self._update_clouds(dt)
        self._update_flights(dt)
        self._update_pickups(dt)
        nav = getattr(self.S, 'nav', None)
        if nav is not None:
            nav.update(dt)
        self._update_hud()

    def destroy(self):
        for t in self.rows:
            try:
                destroy(t)
            except Exception:
                pass

class Roof:

    def __init__(self, cx, cz, w, d, h):
        self.x0, self.x1 = (cx - w / 2.0, cx + w / 2.0)
        self.z0, self.z1 = (cz - d / 2.0, cz + d / 2.0)
        self.h = h

    def contains(self, x, z, m=0.0):
        return self.x0 + m <= x <= self.x1 - m and self.z0 + m <= z <= self.z1 - m

class Ladder:

    def __init__(self, gx, gz, rx, rz, h):
        self.gx, self.gz, self.rx, self.rz, self.h = (gx, gz, rx, rz, h)
        self.up = self.down = None

class RoofNet:
    MARGIN = 0.3

    def __init__(self, scene):
        self.S = scene
        self.roofs = []
        self.ladders = []
        self.busy = False
        self.edge_t = 0.0
        self._prompt = None

    def add_roof(self, cx, cz, w, d, h):
        r = Roof(cx, cz, w, d, h)
        self.roofs.append(r)
        return r

    def add_ladder(self, gx, gz, rx, rz, h, label_up='Climb up', label_down='Climb down'):
        L = Ladder(gx, gz, rx, rz, h)
        S = self.S
        L.up = S.interact(gx, gz, label_up, lambda L=L: self.climb(L, True), radius=1.5, once=False)
        L.down = S.interact(rx, rz, label_down, lambda L=L: self.climb(L, False), radius=1.4, once=False)
        L.up.enabled = True
        L.down.enabled = False
        self.ladders.append(L)
        return L

    def roof_at(self, x, z, m=None):
        m = self.MARGIN if m is None else m
        best = None
        for r in self.roofs:
            if r.contains(x, z, m) and (best is None or r.h > best.h):
                best = r
        return best

    def on_roof(self, p):
        return p.ch.root.y > 0.4 or self.busy

    def resolve(self, p, ox, oz, nx, nz, dx, dz):
        if self.busy:
            return (ox, oz)
        if self.roof_at(nx, nz):
            self.edge_t = 0.0
            return (nx, nz)
        blocked_x = abs(nx - ox) > 1e-06 and (not self.roof_at(nx, oz))
        blocked_z = abs(nz - oz) > 1e-06 and (not self.roof_at(ox, nz))
        out_x = ox if blocked_x else nx
        out_z = oz if blocked_z else nz
        if blocked_x and abs(dx) > 0.35 or (blocked_z and abs(dz) > 0.35):
            self.edge_t += self.S.dt
            if self.edge_t > 0.3:
                land = self._landing(p, ox, oz, dx, dz)
                if land:
                    self.edge_t = 0.0
                    self.S.tl.run(self._leap(p, *land))
        return (out_x, out_z)

    def _landing(self, p, ox, oz, dx, dz):
        cur = self.roof_at(ox, oz, 0.0)
        ch = cur.h if cur else p.ch.root.y
        d = 1.5
        while d <= LEAP_MAX:
            lx, lz = (ox + dx * d, oz + dz * d)
            r = self.roof_at(lx, lz, 0.5)
            if r and abs(r.h - ch) <= 2.4:
                return (lx, lz, r.h, d)
            d += 0.35
        return None

    def update(self, dt):
        S = self.S
        p = S.player
        if p is None:
            return
        on = self.on_roof(p)
        if not self.busy:
            if on:
                r = self.roof_at(p.x, p.z, -0.2)
                if r is not None:
                    p.ch.root.y += (r.h - p.ch.root.y) * min(1.0, 9.0 * dt)
            for L in self.ladders:
                L.up.enabled = not on
                L.down.enabled = on and math.hypot(p.x - L.rx, p.z - L.rz) < 2.5
        else:
            for L in self.ladders:
                L.up.enabled = L.down.enabled = False
        S.cam.height_offset += (1.2 + p.ch.root.y * 0.85 - S.cam.height_offset) * min(1.0, 4.0 * dt)
        if self.edge_t > 0 and (not p.moving):
            self.edge_t = max(0.0, self.edge_t - dt)
        self._prompt = self._compute_prompt(p) if on and (not self.busy) and (not S.cutscene_active) else None

    def prompt(self):
        return self._prompt

    def climb(self, L, up):
        if self.busy or self.S.failing:
            return
        self.S.tl.run(self._climb(L, up))

    def _climb(self, L, up):
        S, p = (self.S, self.S.player)
        ch = p.ch
        self.busy = True
        p.locked = True
        S.game.hud.prompt(None)
        sx, sz = (L.gx, L.gz) if up else (L.rx, L.rz)
        ex, ez = (L.rx, L.rz) if up else (L.gx, L.gz)
        y0, y1 = (0.0, L.h) if up else (L.h, 0.0)
        for _ in range(40):
            dx, dz = (sx - p.x, sz - p.z)
            d = math.hypot(dx, dz)
            if d < 0.15:
                break
            step = min(d, 3.6 * S.dt)
            ch.root.x += dx / d * step
            ch.root.z += dz / d * step
            ch.face(dx, dz, S.dt)
            ch.amount = 0.8
            yield
        ch.face(ex - sx, ez - sz)
        t, T = (0.0, 0.55 + L.h * 0.28)
        while t < T:
            t += S.dt
            ch.root.y = y0 + (y1 - y0) * ease_in_out(min(1.0, t / T))
            ch.amount = 0.85
            yield
        t = 0.0
        while t < 0.4:
            t += S.dt
            k = ease_out(min(1.0, t / 0.4))
            ch.root.x = sx + (ex - sx) * k
            ch.root.z = sz + (ez - sz) * k
            yield
        ch.amount = 0.0
        ch.root.y = y1
        S.game.audio.play('step_stone', 0.5)
        self.busy = False
        p.locked = False

    def _leap(self, p, lx, lz, h, dist):
        S, ch = (self.S, p.ch)
        self.busy = True
        p.locked = True
        x0, z0, y0 = (ch.root.x, ch.root.z, ch.root.y)
        T = 0.34 + dist * 0.1
        S.game.audio.play('wingbeat', 0.35, pitch=1.3)
        t = 0.0
        ch.face(lx - x0, lz - z0)
        while t < T:
            t += S.dt
            k = min(1.0, t / T)
            ch.root.x = x0 + (lx - x0) * k
            ch.root.z = z0 + (lz - z0) * k
            ch.root.y = y0 + (h - y0) * k + math.sin(k * math.pi) * (0.9 + dist * 0.18)
            ch.amount = 1.0
            yield
        ch.root.y = h
        ch.amount = 0.0
        S.game.audio.play('thud', 0.4)
        S.fx.dust_puff((lx, h + 0.1, lz), 4, color=(0.6, 0.58, 0.62))
        S.cam.shake(0.04, 0.15)
        self.busy = False
        p.locked = False

    def _drop_guard(self, p):
        best, bd = (None, 2.6)
        for gd in self.S.guards:
            if not gd.alive or gd.state == 'chase' or gd.ch.root.y > 1.0 or getattr(gd, 'armor', False):
                continue
            d = math.hypot(gd.x - p.x, gd.z - p.z)
            if d < bd:
                best, bd = (gd, d)
        return best

    def _edge_point(self, p):
        a = math.radians(p.ch.angle)
        sx, sz = (math.sin(a), math.cos(a))
        if self.roof_at(p.x + sx * 0.9, p.z + sz * 0.9, 0.0):
            return None
        for d in (1.4, 1.8, 2.3):
            x, z = (p.x + sx * d, p.z + sz * d)
            if self.roof_at(x, z, -0.2):
                continue
            rx, rz = self.S.world.resolve(x, z, 0.4)
            if math.hypot(rx - x, rz - z) < 0.25:
                return (x, z)
        return None

    def _compute_prompt(self, p):
        if self._drop_guard(p) is not None:
            return '[SPACE]  Drop on him'
        if self._edge_point(p) is not None:
            return '[SPACE]  Drop to the street'
        return None

    def try_drop(self, p):
        if self.busy or not self.on_roof(p):
            return False
        gd = self._drop_guard(p)
        if gd is not None:
            self.S.tl.run(self._drop(p, gd.x, gd.z, gd))
            return True
        pt = self._edge_point(p)
        if pt:
            self.S.tl.run(self._drop(p, pt[0], pt[1], None))
            return True
        return False

    def _drop(self, p, tx, tz, gd):
        S, ch = (self.S, p.ch)
        self.busy = True
        p.locked = True
        S.game.hud.prompt(None)
        x0, z0, y0 = (ch.root.x, ch.root.z, ch.root.y)
        if gd is not None:
            gx, gz = (gd.x, gd.z)
            tx, tz = (gx - (gx - x0) * 0.25, gz - (gz - z0) * 0.25)
        T = 0.42
        t = 0.0
        ch.face(tx - x0, tz - z0)
        while t < T:
            t += S.dt
            k = min(1.0, t / T)
            ch.root.x = x0 + (tx - x0) * k
            ch.root.z = z0 + (tz - z0) * k
            ch.root.y = y0 * (1.0 - k * k)
            yield
        ch.root.y = 0.0
        ch.amount = 0.0
        if gd is not None and gd.alive:
            ch.attack()
            S.abil.kill_guard(gd, 'drop')
            Clock.time_scale = 0.35
            S.tl.after(0.12, lambda: setattr(Clock, 'time_scale', 1.0))
        else:
            S.game.audio.play('thud', 0.55)
            S.abil.noise(tx, tz, 5.0)
        S.fx.dust_puff((tx, 0.1, tz), 7)
        S.cam.shake(0.08, 0.2)
        self.busy = False
        p.locked = False

def ladder_model(parent, x, z, h, yaw=0.0, col=rgb(112, 84, 56)):
    root = Entity(parent=parent, position=(x, 0, z), rotation=(0, yaw, 0), add_to_scene_entities=False)
    for sx in (-0.28, 0.28):
        mk(root, 'cube', (sx, h / 2.0, 0.0), (0.07, h + 0.4, 0.08), col)
    n = int(h / 0.42)
    for i in range(n):
        mk(root, 'cube', (0, 0.4 + i * 0.42, 0.0), (0.56, 0.05, 0.06), shade_col(col, 0.85))
    return root

def shade_col(c, k):
    return (c[0] * k, c[1] * k, c[2] * k, c[3] if len(c) > 3 else 1.0)
