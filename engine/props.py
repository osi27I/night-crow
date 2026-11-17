import math
import random
from panda3d.core import Point3
from ursina import Entity, Mesh, Vec3, camera, color
from ursina.shaders import unlit_shader
from engine.assets import tex
from engine.entities import blade_model, cylinder_model, glow_quad, mk, rgb, shade, sphere_model, torus_model
WOOD = rgb(112, 74, 44)
DARK_WOOD = rgb(70, 46, 30)
CLOTH_RED = rgb(150, 38, 40)
CLOTH_BLUE = rgb(40, 66, 120)
CLOTH_GOLD = rgb(200, 160, 60)
GOLD = rgb(222, 178, 72)
IRON = rgb(74, 78, 90)
PALM_GREEN = rgb(60, 98, 46)
BONE = rgb(226, 214, 190)

class Sky:

    def __init__(self, S, name='sky_night', radius=420.0, stars=True, star_count=260):
        verts, uvs, tris = ([], [], [])
        rings, segs = (14, 28)
        for i in range(rings + 1):
            elev = math.radians(-10 + 100 * i / rings)
            v = min(1.0, max(0.0, elev / (math.pi / 2)))
            for j in range(segs + 1):
                a = 2 * math.pi * j / segs
                verts.append(Vec3(math.cos(elev) * math.cos(a), math.sin(elev), math.cos(elev) * math.sin(a)))
                uvs.append((j / segs, v))
        for i in range(rings):
            for j in range(segs):
                a = i * (segs + 1) + j
                b = a + segs + 1
                tris += [a, b, a + 1, a + 1, b, b + 1]
        self._geo = (verts, tris, uvs)
        self.entity = Entity(parent=S.root, model=Mesh(vertices=verts, triangles=tris, uvs=uvs), texture=tex(name, filtering='bilinear'), scale=radius, double_sided=True, shader=unlit_shader, add_to_scene_entities=False)
        self.entity.setDepthWrite(False)
        self.entity.setBin('background', 0)
        self.entity.setLightOff()
        self.stars = None
        self._S = S
        self._layers = []
        self._streak = None
        self._streak_wait = random.Random(11).uniform(5.0, 9.0)
        if stars:
            rnd = random.Random(7)
            from ursina import color as ucolor
            self.stars = Entity(parent=S.root, add_to_scene_entities=False)
            for share, size, (b0, b1), speed in ((0.62, 1.6, (0.3, 0.65), 1.3), (0.3, 2.6, (0.55, 0.9), 2.1), (0.08, 4.2, (0.85, 1.0), 2.9)):
                pts, cols = ([], [])
                for _ in range(int(star_count * 3 * share)):
                    elev = math.asin(rnd.uniform(0.05, 1.0))
                    az = rnd.uniform(0, 2 * math.pi)
                    pts.append(Vec3(math.cos(elev) * math.cos(az), math.sin(elev), math.cos(elev) * math.sin(az)) * 0.98)
                    br = rnd.uniform(b0, b1)
                    tint = rnd.random()
                    r_, g_, b_ = (br * 0.88, br * 0.94, br) if tint < 0.62 else (br, br * 0.92, br * 0.7) if tint < 0.88 else (br, br * 0.7, br * 0.62)
                    cols.append((r_, g_, b_, 1))
                layer = Entity(parent=self.stars, model=Mesh(vertices=pts, colors=[ucolor.rgba(*c) for c in cols], mode='point', thickness=size), scale=radius, shader=unlit_shader, add_to_scene_entities=False)
                layer.setDepthWrite(False)
                layer.setBin('background', 1)
                layer.setLightOff()
                self._layers.append((layer, speed, rnd.uniform(0, 6.28)))
        self.t = 0.0

    def fade_to(self, S, name, duration=20.0, stars=None):
        verts, tris, uvs = self._geo
        top = Entity(parent=S.root, model=Mesh(vertices=verts, triangles=tris, uvs=uvs), texture=tex(name, filtering='bilinear'), scale=self.entity.scale * 0.999, double_sided=True, shader=unlit_shader, add_to_scene_entities=False)
        top.setDepthWrite(False)
        top.setBin('background', 1)
        top.setLightOff()
        top.setTransparency(True)
        top.alpha = 0.0
        self._overlay = top

        def finish():
            self.entity.texture = tex(name, filtering='bilinear')
            self._overlay = None
            from ursina import destroy
            destroy(top)
        S.tl.to(top, 'alpha', 1.0, duration, on_done=finish)
    _overlay = None

    def update(self, dt):
        p = camera.world_position
        self.entity.position = p
        if self._overlay is not None:
            self._overlay.position = p
        if self.stars:
            self.stars.position = p
            self.t += dt
            for layer, speed, phase in self._layers:
                layer.alpha = 0.78 + 0.22 * math.sin(self.t * speed + phase)
            if self.stars.enabled:
                self._shooting_star(dt, p)

    def _shooting_star(self, dt, cam):
        S = self._S
        if self._streak is None:
            self._streak_wait -= dt
            if self._streak_wait > 0:
                return
            rnd = random
            az = rnd.uniform(0, 2 * math.pi)
            el = math.radians(rnd.uniform(28, 62))
            start = Vec3(math.cos(el) * math.cos(az), math.sin(el), math.cos(el) * math.sin(az)) * 380
            side = Vec3(-math.sin(az), 0, math.cos(az)) * rnd.choice((-1, 1))
            vel = (side * 1.0 + Vec3(0, -0.45, 0)).normalized() * 330
            sprites = []
            for i in range(7):
                q = glow_quad(S.root, (0, 0, 0), 5.0 * (1.0 - i * 0.11), (0.85, 0.92, 1.0, 0.9 * (1.0 - i * 0.14)), tex('glow'), billboard=True, add=True)
                q.setBin('background', 4)
                sprites.append(q)
            self._streak = {'pos': start, 'vel': vel, 't': 0.0, 'sprites': sprites}
            return
        st = self._streak
        st['t'] += dt
        for i, q in enumerate(st['sprites']):
            q.position = cam + st['pos'] + st['vel'] * (st['t'] - i * 0.03)
            q.alpha = max(0.0, min(1.0, (0.9 - st['t']) * 3.0)) * (1.0 - i * 0.14)
        if st['t'] > 0.9:
            from ursina import destroy
            for q in st['sprites']:
                destroy(q)
            self._streak = None
            self._streak_wait = random.uniform(7.0, 15.0)

    def hide_stars(self):
        if self.stars:
            self.stars.enabled = False

def planets(S, ringed=(-135, 52, 150), red=(105, 74, 165), blue=None, size=1.0):
    out = []
    for where, tname, sz, glow_col in ((ringed, 'planet_ringed', 30, (0.95, 0.85, 0.6)), (red, 'planet_red', 7.5, (1.0, 0.5, 0.3)), (blue, 'planet_blue', 10, (0.5, 0.7, 1.0))):
        if where is None:
            continue
        h = glow_quad(S.root, (where[0], where[1], where[2] - 0.3), sz * size * 2.2, (*glow_col, 0.1), tex('glow'), billboard=True, add=True)
        h.setBin('background', 2)
        q = glow_quad(S.root, where, sz * size, (1, 1, 1, 1), tex(tname), billboard=True, add=False)
        q.setBin('background', 3)
        q.halo = h
        out.extend([h, q])
    return out

def moon(S, pos=(-70, 80, 140), size=40, color=(0.8, 0.84, 0.92, 1.0), halo=0.22, halo_color=(0.55, 0.68, 1.0)):
    h = glow_quad(S.root, (pos[0], pos[1], pos[2] - 0.5), size * 2.6, (*halo_color, halo), tex('glow'), billboard=True, add=True)
    h.setBin('background', 2)
    m = glow_quad(S.root, pos, size, color, tex('moon'), billboard=True, add=False)
    m.setBin('background', 3)
    m.halo = h
    return m

def ground(S, size=160, texture='sand', tile=34, col=None, y=0.0):
    return mk(S.root, 'plane', (0, y, 0), (size, 1, size), col, tex(texture), tex_scale=(tile, tile))

def path_strip(S, x0, z0, x1, z1, width=2.4, texture='dirt', col=None, y=0.012):
    cx, cz = ((x0 + x1) / 2.0, (z0 + z1) / 2.0)
    length = math.hypot(x1 - x0, z1 - z0)
    ang = math.degrees(math.atan2(x1 - x0, z1 - z0))
    e = mk(S.root, 'plane', (cx, y, cz), (width, 1, length), col, tex(texture), tex_scale=(max(1, width / 2.0), max(1, length / 2.0)), rot=(0, ang, 0))
    return e

def torch(S, x, z, h=1.9, y=0.0, color=(1.0, 0.62, 0.28), intensity=1.5, radius=9.0, flame=0.55, smoke=False, embers=False):
    mk(S.root, 'cylinder', (x, y, z), (0.11, h, 0.11), DARK_WOOD)
    mk(S.root, 'cylinder', (x, y + h - 0.05, z), (0.24, 0.22, 0.24), IRON)
    S.fx.fire((x, y + h + 0.14, z), scale=flame)
    if smoke:
        S.fx.smoke((x, y + h + 0.5, z), scale=0.5, rate=2, alpha=0.3)
    if embers:
        S.fx.embers((x, y + h + 0.3, z), scale=0.7, rate=3)
    return S.rig.add((x, y + h + 0.55, z), color=color, intensity=intensity, radius=radius, flicker=0.32)

def brazier(S, x, z, y=0.0, scale=1.0, color=(1.0, 0.55, 0.22), intensity=2.0, radius=11.0):
    mk(S.root, 'cylinder', (x, y, z), (0.9 * scale, 0.5 * scale, 0.9 * scale), IRON)
    mk(S.root, 'cone', (x, y + 0.0, z), (0.6 * scale, 0.5 * scale, 0.6 * scale), shade(IRON, 0.7), rot=(180, 0, 0), origin=(0, 0.5, 0))
    mk(S.root, 'cylinder', (x, y + 0.5 * scale, z), (0.72 * scale, 0.1, 0.72 * scale), rgb(30, 14, 8), emissive=0.4)
    S.fx.fire((x, y + 0.62 * scale, z), scale=1.1 * scale, intensity=1.4)
    S.fx.embers((x, y + 0.9 * scale, z), scale=1.0, rate=6)
    return S.rig.add((x, y + 1.3 * scale, z), color=color, intensity=intensity, radius=radius, flicker=0.3, speed=7.0)

def wall_sconce(S, x, z, nx, nz, y=3.0, color=(1.0, 0.7, 0.38), intensity=1.3, radius=12.0, scale=1.0):
    ang = math.degrees(math.atan2(nx, nz))
    g = Entity(parent=S.root, position=(x, y, z), rotation_y=ang, add_to_scene_entities=False)
    mk(g, 'cube', (0, 0.0, 0.03), (0.3, 0.42, 0.06), IRON)
    mk(g, 'cube', (0, -0.1, 0.2), (0.08, 0.08, 0.34), shade(IRON, 1.1))
    mk(g, 'cylinder', (0, -0.06, 0.38), (0.2 * scale, 0.2 * scale, 0.2 * scale), shade(IRON, 0.8))
    mk(g, 'cone', (0, -0.1, 0.38), (0.15 * scale, 0.2 * scale, 0.15 * scale), IRON, rot=(180, 0, 0))
    mk(g, 'cylinder', (0, 0.09, 0.38), (0.16 * scale, 0.04, 0.16 * scale), rgb(255, 150, 60), emissive=0.9)
    fx_ = x + nx * 0.38
    fz_ = z + nz * 0.38
    S.fx.fire((fx_, y + 0.1, fz_), scale=0.5 * scale, intensity=0.9)
    glow_quad(S.root, (fx_, y + 0.3, fz_), 1.0 * scale, (1.0, 0.65, 0.28, 0.4), tex('glow'))
    return S.rig.add((x + nx * 0.7, y + 0.5, z + nz * 0.7), color=color, intensity=intensity, radius=radius, flicker=0.25, speed=6.0)

def candle(S, x, z, y=0.0, color=(1.0, 0.7, 0.35), intensity=0.9, radius=4.5, height=0.22, light=True):
    mk(S.root, 'cylinder', (x, y, z), (0.07, height, 0.07), rgb(236, 224, 190))
    S.fx.fire((x, y + height + 0.03, z), scale=0.13, intensity=0.5)
    if light:
        return S.rig.add((x, y + height + 0.25, z), color=color, intensity=intensity, radius=radius, flicker=0.35, speed=11.0)
    return None

def lantern(S, x, z, y=1.6, color=(1.0, 0.72, 0.38), intensity=1.1, radius=7.0):
    mk(S.root, 'cylinder', (x, y + 0.18, z), (0.02, 0.4, 0.02), IRON)
    mk(S.root, 'cube', (x, y, z), (0.22, 0.28, 0.22), rgb(255, 214, 140), emissive=1.0)
    h = glow_quad(S.root, (x, y, z), 1.4, (1.0, 0.7, 0.3, 0.5), tex('glow'))
    L = S.rig.add((x, y - 0.1, z), color=color, intensity=intensity, radius=radius, flicker=0.2, speed=5.0)
    return (L, h)

def light_shaft(S, x, y, z, height=6.0, width=2.0, color=(0.7, 0.8, 1.0, 0.28), tilt=0.0):
    e = glow_quad(S.root, (x, y + height / 2, z), (width, height), color, tex('shaft'), billboard=False, add=True, bin_sort=38)
    e.rotation_z = tilt
    return e

def wall_box(S, cx, cz, w, d, h, texture='mudbrick', col=None, y=0.0, collide=True, sight=True, tile=2.4):
    e = mk(S.root, 'cube', (cx, y + h / 2.0, cz), (w, h, d), col, tex(texture) if texture else None, tex_scale=(max(w, d) / tile, h / tile))
    if collide:
        S.world.add_box(cx, cz, w, d, blocks_sight=sight)
    return e

def wall_line(S, x0, z0, x1, z1, h=3.2, thick=0.5, texture='mudbrick', col=None, y=0.0, collide=True, sight=True):
    cx, cz = ((x0 + x1) / 2.0, (z0 + z1) / 2.0)
    w, d = (max(abs(x1 - x0), thick), max(abs(z1 - z0), thick))
    return wall_box(S, cx, cz, w, d, h, texture, col, y, collide, sight)

def _window(parent, tx, y, nz, ww=0.7, wh=0.95, glow=0.0, seed=0, shutters=True, texture='wood'):
    r = random.Random(seed)
    opening = mk(parent, 'cube', (tx, y, nz + 0.01), (ww, wh, 0.06), rgb(255, 150, 60) if glow > 0 else rgb(14, 12, 14), emissive=glow)
    opening.is_window = True
    frame = shade(DARK_WOOD, 1.15)
    mk(parent, 'cube', (tx, y + wh / 2 + 0.07, nz + 0.05), (ww + 0.34, 0.15, 0.16), frame, tex(texture))
    mk(parent, 'cube', (tx, y - wh / 2 - 0.06, nz + 0.09), (ww + 0.44, 0.1, 0.26), rgb(150, 138, 120), tex('stone'))
    for sx in (-1, 1):
        mk(parent, 'cube', (tx + sx * (ww / 2 + 0.06), y, nz + 0.05), (0.1, wh + 0.1, 0.14), frame, tex(texture))
    for k in (-1, 0, 1):
        if k == 0:
            mk(parent, 'cube', (tx, y, nz + 0.07), (ww, 0.04, 0.04), frame)
        else:
            mk(parent, 'cube', (tx + k * ww * 0.25, y, nz + 0.07), (0.035, wh, 0.04), frame)
    if shutters:
        ang = r.choice((0, 0, 55, 80))
        for sx in (-1, 1):
            piv = Entity(parent=parent, position=(tx + sx * (ww / 2 + 0.12), y, nz + 0.1), rotation_y=sx * ang, add_to_scene_entities=False)
            mk(piv, 'cube', (sx * ww * 0.25, 0, 0.0), (ww * 0.5, wh + 0.04, 0.045), rgb(98, 66, 42), tex(texture))
    return opening

def _clay_pot_at(parent, x, y, z, s=1.0, col=rgb(170, 100, 62)):
    mk(parent, 'sphere', (x, y + 0.3 * s, z), (0.56 * s, 0.62 * s, 0.56 * s), col)
    mk(parent, 'cylinder', (x, y + 0.55 * s, z), (0.26 * s, 0.2 * s, 0.26 * s), shade(col, 0.9))
    mk(parent, 'cylinder', (x, y + 0.73 * s, z), (0.34 * s, 0.05 * s, 0.34 * s), shade(col, 1.1))
    mk(parent, 'cylinder', (x, y, z), (0.28 * s, 0.07 * s, 0.28 * s), shade(col, 0.8))

def _clay_pot(S, x, z, s=1.0, col=rgb(170, 100, 62)):
    _clay_pot_at(S.root, x, 0.0, z, s, col)

def house(S, cx, cz, w, d, h=3.0, door='south', door_w=1.5, texture='mudbrick', col=None, roof=True, roof_col=None, cutaway=False, door_cover='none', thick=0.45, y=0.0, windows=True, window_glow=0.0, awning=None, detail=True, seed=None):
    hw, hd = (w / 2.0, d / 2.0)
    parts = []
    deco = []
    first_child = len(S.root._children)
    base_col = col or rgb(255, 255, 255)
    rr = random.Random(seed if seed is not None else int(cx * 31 + cz * 17 + w * 7))

    def side(name, x0, z0, x1, z1, horizontal, hh):
        if name == door:
            half = door_w / 2.0
            if horizontal:
                for a, b in ((x0, (x0 + x1) / 2 - half), ((x0 + x1) / 2 + half, x1)):
                    parts.append(wall_line(S, a, z0, b, z1, hh, thick, texture, col, y))
                mk(S.root, 'cube', ((x0 + x1) / 2, y + hh - 0.25, z0), (door_w + 0.1, 0.5, thick), shade(base_col, 0.9), texture=tex(texture)) if hh > 2.2 else None
            else:
                for a, b in ((z0, (z0 + z1) / 2 - half), ((z0 + z1) / 2 + half, z1)):
                    parts.append(wall_line(S, x0, a, x1, b, hh, thick, texture, col, y))
                mk(S.root, 'cube', (x0, y + hh - 0.25, (z0 + z1) / 2), (thick, 0.5, door_w + 0.1), shade(base_col, 0.9), texture=tex(texture)) if hh > 2.2 else None
        else:
            parts.append(wall_line(S, x0, z0, x1, z1, hh, thick, texture, col, y))
    south_h = 1.0 if cutaway else h
    side('south', cx - hw, cz - hd, cx + hw, cz - hd, True, south_h)
    side('north', cx - hw, cz + hd, cx + hw, cz + hd, True, h)
    side('west', cx - hw, cz - hd, cx - hw, cz + hd, False, h)
    side('east', cx + hw, cz - hd, cx + hw, cz + hd, False, h)
    contact_shadow(S, cx, cz, w + 3.6, d + 3.6, 0.55, y + 0.02)
    if detail:
        walls = {'south': ((cx, cz - hd - thick / 2), 180, w, south_h), 'north': ((cx, cz + hd + thick / 2), 0, w, h), 'west': ((cx - hw - thick / 2, cz), -90, d, h), 'east': ((cx + hw + thick / 2, cz), 90, d, h)}
        stone = tex('stone')
        for name, ((px, pz), yaw, length, hh) in walls.items():
            piv = Entity(parent=S.root, position=(px, y, pz), rotation_y=yaw, add_to_scene_entities=False)
            deco.append(piv)
            is_door = name == door
            if hh > 1.5:
                if is_door:
                    seg = (length - door_w) / 2.0
                    for sgn in (-1, 1):
                        deco.append(mk(piv, 'cube', (sgn * (door_w / 2 + seg / 2), 0.2, 0.04), (seg + 0.3, 0.4, 0.2), rgb(150, 138, 120), stone, tex_scale=(seg / 1.6, 0.4)))
                else:
                    deco.append(mk(piv, 'cube', (0, 0.2, 0.04), (length + 0.3, 0.4, 0.2), rgb(150, 138, 120), stone, tex_scale=(length / 1.6, 0.4)))
            if is_door and hh > 2.2:
                fr = shade(DARK_WOOD, 1.1)
                for sgn in (-1, 1):
                    deco.append(mk(piv, 'cube', (sgn * (door_w / 2 + 0.02), (hh - 0.5) / 2, -thick / 2 + 0.05), (0.16, hh - 0.5, thick + 0.14), fr, tex('wood')))
                deco.append(mk(piv, 'cube', (0, hh - 0.52, -thick / 2 + 0.05), (door_w + 0.4, 0.16, thick + 0.16), fr, tex('wood')))
                deco.append(mk(piv, 'cube', (0, 0.06, 0.55), (door_w + 0.5, 0.12, 0.8), rgb(138, 126, 110), stone))
                if door_cover == 'plank':
                    dh = hh - 0.58
                    deco.append(mk(piv, 'cube', (0, dh / 2, -thick / 2 + 0.02), (door_w - 0.04, dh, 0.1), WOOD, tex('wood'), tex_scale=(door_w / 0.5, dh / 1.5)))
                    for yy in (0.28, dh - 0.28):
                        deco.append(mk(piv, 'cube', (0, yy, -thick / 2 + 0.085), (door_w - 0.1, 0.1, 0.03), rgb(46, 42, 44)))
                    deco.append(mk(piv, 'cube', (0, dh / 2, -thick / 2 + 0.085), (0.04, dh - 0.1, 0.03), rgb(30, 22, 18)))
                    for sgn in (-1, 1):
                        deco.append(mk(piv, 'sphere', (sgn * 0.17, dh * 0.48, -thick / 2 + 0.12), (0.11, 0.11, 0.05), rgb(150, 124, 70)))
                    wx, wz = walls[name][0]
                    S.world.add_box(wx, wz, door_w if name in ('south', 'north') else thick, thick if name in ('south', 'north') else door_w)
            if windows and hh > 2.2:
                n = 2 if length >= 5.4 else 1
                offs = (-length * 0.27, length * 0.27) if n == 2 else (0.0,)
                for k, off in enumerate(offs):
                    if is_door and abs(off) < door_w / 2 + 0.9:
                        continue
                    deco.append(_window(piv, off, hh * 0.58, 0.0, glow=window_glow, seed=rr.randint(0, 999), shutters=not (is_door and hh < 2.6)))
            if hh > 2.2 and (not cutaway) and (name in ('south', 'north')):
                nb = max(3, int(length / 0.95))
                for i in range(nb):
                    bx = -length / 2 + (i + 0.5) * length / nb
                    deco.append(mk(piv, 'cylinder', (bx, hh - 0.18, -0.06), (0.13, 0.5, 0.13), shade(DARK_WOOD, 1.2), tex('wood'), rot=(90, 0, 0), origin=(0, 0, 0)))
        want_awning = rr.random() < 0.5 if awning is None else awning
        if want_awning and door in ('south', 'north', 'east', 'west') and (h > 2.4):
            wall = walls[door]
            (px, pz), yaw, length, hh = wall
            piv = Entity(parent=S.root, position=(px, y, pz), rotation_y=yaw, add_to_scene_entities=False)
            deco.append(piv)
            cloth = rr.choice((rgb(168, 52, 46), rgb(196, 168, 96), rgb(70, 96, 140), rgb(150, 120, 80)))
            aw = Entity(parent=piv, position=(0, hh - 0.62, 0.08), rotation_x=-14, add_to_scene_entities=False)
            deco.append(aw)
            mk(aw, 'cube', (0, 0, 0.7), (door_w + 1.1, 0.05, 1.45), cloth)
            for k in range(5):
                mk(aw, 'cube', (-(door_w + 1.1) / 2 + (k + 0.5) * (door_w + 1.1) / 5, 0.012, 0.7), ((door_w + 1.1) / 10, 0.05, 1.46), shade(cloth, 0.7 if k % 2 else 1.25))
            for sgn in (-1, 1):
                deco.append(mk(piv, 'cylinder', (sgn * (door_w / 2 + 0.55), 0, 1.45), (0.08, hh - 0.74, 0.08), DARK_WOOD, tex('wood')))
        if rr.random() < 0.65 and door in walls:
            (px, pz), yaw, length, hh = walls[door]
            ang = math.radians(yaw)
            fwd = (math.sin(ang), math.cos(ang))
            side_v = (math.cos(ang), -math.sin(ang))
            k = rr.choice((-1, 1))
            for j in range(2):
                _clay_pot(S, px + fwd[0] * (0.6 + 0.25 * j) + side_v[0] * k * (door_w / 2 + 0.7 + 0.45 * j), pz + fwd[1] * (0.6 + 0.25 * j) + side_v[1] * k * (door_w / 2 + 0.7 + 0.45 * j), s=rr.uniform(0.8, 1.2))
    parts.extend(deco)
    if roof:
        group = Entity(parent=S.root, position=(cx, y + h, cz), add_to_scene_entities=False)
        mk(group, 'cube', (0, 0.12, 0), (w + 0.5, 0.26, d + 0.5), roof_col or rgb(150, 124, 96), tex('mudbrick'), tex_scale=(w / 2.4, d / 2.4))
        if detail:
            rim = shade(roof_col or rgb(150, 124, 96), 1.12)
            rimh = 0.3
            for sx, sz, ww_, dd_ in ((0, -(hd + 0.22), w + 0.6, 0.22), (0, hd + 0.22, w + 0.6, 0.22), (-(hw + 0.22), 0, 0.22, d + 0.2), (hw + 0.22, 0, 0.22, d + 0.2)):
                mk(group, 'cube', (sx, 0.25 + rimh / 2, sz), (ww_, rimh, dd_), rim, tex('plaster'), tex_scale=(max(ww_, dd_) / 2, 0.3))
            if rr.random() < 0.7:
                px_, pz_ = (rr.uniform(-hw * 0.5, hw * 0.5), rr.uniform(-hd * 0.5, hd * 0.5))
                for i in range(4):
                    mk(group, 'cylinder', (px_ + i * 0.07, 0.3, pz_), (0.06, 0.9, 0.06), rgb(106, 78, 50), rot=(90, 28 + i * 6, 0), origin=(0, 0, 0))
            if rr.random() < 0.6:
                _clay_pot_at(group, rr.uniform(-hw * 0.4, hw * 0.4), 0.26, rr.uniform(-hd * 0.4, hd * 0.4), 0.8)
        parts.append(group)
    return _weld_house(S, first_child, roof_group=group if roof else None)

def _weld_house(S, first_child, roof_group):
    from engine.batch import bake
    root = S.root
    made = [e for e in root._children[first_child:] if e]
    windows = []

    def find_windows(e):
        for k in e._children:
            if not k:
                continue
            if getattr(k, 'is_window', False):
                windows.append(k)
            else:
                find_windows(k)
    for e in made:
        if getattr(e, 'is_window', False):
            windows.append(e)
        else:
            find_windows(e)
    for wdw in windows:
        old = wdw._parent
        wdw.wrtReparentTo(root)
        if old is not root and wdw in old._children:
            old._children.remove(wdw)
        wdw._parent = root
        if wdw not in root._children:
            root._children.append(wdw)
    skip = set((id(w) for w in windows))
    body_parts = [e for e in made if id(e) not in skip and e is not roof_group]
    out = [bake(root, body_parts, 'house_body')]
    out.extend(windows)
    if roof_group is not None:
        out.append(bake(root, [roof_group], 'house_roof'))
    return out

def pillar(S, x, z, h=3.6, r=0.38, texture='stone', y=0.0, col=None, collide=True):
    mk(S.root, 'cylinder', (x, y, z), (r * 2.5, 0.28, r * 2.5), col or rgb(170, 160, 140), tex(texture))
    mk(S.root, 'cylinder', (x, y + 0.28, z), (r * 2, h - 0.6, r * 2), col, tex(texture), tex_scale=(2, h / 2))
    mk(S.root, 'cylinder', (x, y + h - 0.32, z), (r * 2.6, 0.32, r * 2.6), col or rgb(170, 160, 140), tex(texture))
    if collide:
        S.world.add_circle(x, z, r * 1.05)

def arch_gate(S, cx, cz, width=5.0, h=4.6, depth=1.2, texture='stone', y=0.0, col=None, gap=2.6, lintel=True):
    px = (gap + (width - gap) / 4.0) / 2.0 + 0.0
    post_w = (width - gap) / 2.0
    for s in (-1, 1):
        wall_box(S, cx + s * (gap / 2.0 + post_w / 2.0), cz, post_w, depth, h, texture, col, y)
    if lintel:
        mk(S.root, 'cube', (cx, y + h + 0.35, cz), (width + 0.4, 0.7, depth + 0.2), col, tex(texture), tex_scale=(width / 2, 0.5))

def stairs(S, x, z, w, steps=5, rise=0.22, run=0.5, axis='z', y=0.0, texture='stone'):
    for i in range(steps):
        if axis == 'z':
            mk(S.root, 'cube', (x, y + rise * (i + 0.5), z + run * i), (w, rise * (i + 1), run), None, tex(texture), tex_scale=(w / 2, 0.5))
        else:
            mk(S.root, 'cube', (x + run * i, y + rise * (i + 0.5), z), (run, rise * (i + 1), w), None, tex(texture), tex_scale=(w / 2, 0.5))

def banner(S, x, y, z, kind='thunder', height=2.6, face='south', sway=True):
    w = height * 0.5
    rot = {'south': 0, 'north': 180, 'east': 90, 'west': -90}[face]
    mk(S.root, 'cube', (x, y + height / 2.0 + 0.08, z), (w + 0.25, 0.08, 0.1) if face in ('south', 'north') else (0.1, 0.08, w + 0.25), DARK_WOOD)
    cloth = mk(S.root, 'quad', (x, y, z - (0.06 if face == 'south' else 0)), (w, height, 1), None, tex(f'banner_{kind}'), rot=(0, rot, 0), double_sided=True, emissive=0.0)
    if sway:
        ph = random.random() * 6.0

        def _sway(dt, e=cloth, ph=ph):
            e.rotation_x = math.sin(Clock_now() * 1.3 + ph) * 3.0
        S.updaters.append(_sway)
    return cloth

def Clock_now():
    from engine.timing import Clock
    return Clock.now

class _TentFlap:

    def __init__(self, S, cx, cz, width, h, col):
        self.S = S
        self.panels = []
        self.is_open = False
        hw = width / 2.0
        mk(S.root, 'cube', (cx, h + 0.1, cz), (width + 0.7, 0.2, 0.34), rgb(92, 62, 40), tex('wood'))
        for sx in (-1, 1):
            mk(S.root, 'cube', (cx + sx * (hw + 0.2), h / 2 + 0.1, cz), (0.22, h + 0.2, 0.3), rgb(92, 62, 40), tex('wood'))
            panel = Entity(parent=S.root, position=(cx + sx * (hw + 0.02), 0.0, cz - 0.02), add_to_scene_entities=False)
            n = 7
            pw = hw / n + 0.02
            for i in range(n):
                k = (i + 0.5) / n
                x = -sx * (hw * k + 0.0)
                z = 0.05 * math.sin(i * 1.9) + (-0.06 if i % 2 else 0.0)
                mk(panel, 'cube', (x, h / 2 - 0.12, z), (pw, h - 0.24, 0.07), shade(col, 0.78 if i % 2 else 1.1))
                mk(panel, 'cube', (x, 0.17, z), (pw, 0.2, 0.09), rgb(214, 170, 70), emissive=0.2)
            mk(panel, 'cube', (-sx * hw * 0.5, h - 0.32, 0.0), (hw + 0.02, 0.22, 0.1), rgb(214, 170, 70), emissive=0.2)
            mk(panel, 'sphere', (-sx * 0.12, 0.9, -0.08), (0.12, 0.2, 0.12), rgb(214, 170, 70), emissive=0.25)
            self.panels.append(panel)

    def open(self, duration=0.9):
        if self.is_open:
            return
        self.is_open = True
        for p_ in self.panels:
            self.S.tl.to(p_, 'scale_x', 0.16, duration)

    def close(self, duration=0.7):
        self.is_open = False
        for p_ in self.panels:
            self.S.tl.to(p_, 'scale_x', 1.0, duration)

def tent_flap(S, cx, cz, width=3.0, h=3.0, col=rgb(96, 52, 126)):
    return _TentFlap(S, cx, cz, width, h, col)

def door_panel(S, x, z, width=1.6, h=2.4, axis='x', hinge='left', y=0.0, texture='wood'):
    pivot = Entity(parent=S.root, position=(x - width / 2.0 if axis == 'x' else x, y, z if axis == 'x' else z - width / 2.0), add_to_scene_entities=False)
    if axis == 'x':
        mk(pivot, 'cube', (width / 2.0, h / 2.0, 0), (width, h, 0.14), WOOD, tex(texture))
    else:
        mk(pivot, 'cube', (0, h / 2.0, width / 2.0), (0.14, h, width), WOOD, tex(texture))

    class _Door:
        angle = 0.0
        is_open = False

        def open(self, amount=100, duration=0.9):
            self.is_open = True
            S.tl.to(pivot, 'rotation_y', amount, duration)

        def close(self, duration=0.7):
            self.is_open = False
            S.tl.to(pivot, 'rotation_y', 0, duration)
    d = _Door()
    d.pivot = pivot
    return d

def _frond(parent, rnd, yaw, tone, up=40.0, reach=1.0):
    piv = Entity(parent=parent, rotation_y=yaw, add_to_scene_entities=False)
    cur = piv
    seg_len = 0.78 * reach
    bends = [up, rnd.uniform(15, 22), rnd.uniform(20, 28), rnd.uniform(24, 32), rnd.uniform(26, 34)]
    n_seg = len(bends)
    for si in range(n_seg):
        seg = Entity(parent=cur, position=(0, 0 if si == 0 else seg_len_prev, 0), rotation_x=bends[si], add_to_scene_entities=False)
        L = seg_len * (1.0 - 0.06 * si)
        w = 0.052 * (1.0 - 0.17 * si)
        mk(seg, cylinder_model(5), (0, 0, 0), (w, L * 1.02, w), shade(PALM_GREEN, tone * 0.62))
        stations = 5 if si > 0 else 2
        for k in range(stations):
            f = (k + 0.5) / stations
            u = (si + f) / n_seg
            bl = 0.62 * (0.42 + 0.58 * math.sin(math.pi * min(1.0, 0.18 + 0.82 * u))) * reach
            if si == 0:
                bl *= 0.35
            for side in (-1, 1):
                blade = Entity(parent=seg, position=(0, L * f, 0), add_to_scene_entities=False)
                blade.lookAt(Point3(side * 0.78, L * f + 0.52, -0.4))
                lt = tone * (0.8 + 0.45 * u)
                mk(blade, blade_model(), (0, 0, 0), (0.075, 1.0, bl), shade(PALM_GREEN, lt), rot=(0, 0, side * 20))
        seg_len_prev = L
        cur = seg
    return piv

def palm(S, x, z, h=4.6, lean=6.0, seed=None, collide=True):
    rnd = random.Random(seed if seed is not None else int(x * 31 + z * 17))
    lean_dir = rnd.uniform(0, 360)
    base = Entity(parent=S.root, position=(x, 0, z), rotation_y=lean_dir, add_to_scene_entities=False)
    segs = 5
    seg_h = h / segs
    cur = Entity(parent=base, add_to_scene_entities=False)
    for i in range(segs):
        r = 0.34 - i * 0.035
        mk(cur, 'cylinder', (0, 0, 0), (r, seg_h * 1.08, r), rgb(112, 86, 58), tex('dirt'), tex_scale=(1, 2))
        for k in range(2):
            mk(cur, 'cylinder', (0, seg_h * (0.3 + 0.42 * k), 0), (r * 1.16, 0.045, r * 1.16), rgb(86, 64, 44))
        cur = Entity(parent=cur, position=(0, seg_h, 0), rotation_x=lean / segs, add_to_scene_entities=False)
    crown = Entity(parent=cur, add_to_scene_entities=False)
    mk(crown, 'cylinder', (0, -0.28, 0), (0.3, 0.3, 0.3), rgb(98, 74, 48), tex('dirt'))
    mk(crown, 'sphere', (0, 0.12, 0), (0.42, 0.34, 0.42), rgb(94, 70, 44))
    for i in range(7):
        sk = Entity(parent=crown, position=(0, -0.05, 0), rotation_y=i * 51 + rnd.uniform(-10, 10), rotation_x=118, add_to_scene_entities=False)
        mk(sk, 'cone', (0, 0, 0), (0.1, 0.46, 0.05), rgb(104, 82, 52))
    n = 10
    for i in range(n):
        yaw = i * 360.0 / n + rnd.uniform(-8, 8)
        up = rnd.uniform(24, 44) if i % 2 == 0 else rnd.uniform(48, 66)
        _frond(crown, rnd, yaw, rnd.uniform(0.86, 1.14), up=up, reach=rnd.uniform(0.92, 1.1))
    for bi, yaw in enumerate((rnd.uniform(0, 360), rnd.uniform(0, 360) + 180)):
        st = Entity(parent=crown, position=(0, -0.1, 0), rotation_y=yaw, rotation_x=58, add_to_scene_entities=False)
        mk(st, 'cylinder', (0, 0, 0), (0.05, 0.62, 0.05), rgb(150, 124, 70))
        tip = Entity(parent=st, position=(0, 0.62, 0), rotation_x=48, add_to_scene_entities=False)
        mk(tip, 'cylinder', (0, 0, 0), (0.045, 0.34, 0.045), rgb(150, 124, 70))
        for k in range(5):
            sp = Entity(parent=tip, position=(0, 0.3, 0), rotation_y=k * 72 + 15, rotation_x=34 + k % 2 * 10, add_to_scene_entities=False)
            mk(sp, cylinder_model(5), (0, 0, 0), (0.014, 0.4, 0.014), rgb(170, 140, 78))
            for j in range(3):
                mk(sp, sphere_model((6, 4)), (0.012 * (j % 2), 0.14 + j * 0.1, 0.0), (0.075, 0.11, 0.075), rgb(158, 84, 30) if (j + k) % 2 else rgb(124, 62, 26))
    if collide:
        S.world.add_circle(x, z, 0.38)
    contact_shadow(S, x, z, 3.4, 3.4, 0.38)
    ph = rnd.random() * 6

    def _sway(dt, c=crown, ph=ph):
        c.rotation_z = math.sin(Clock_now() * 0.9 + ph) * 3.0
        c.rotation_x = math.sin(Clock_now() * 0.7 + ph * 1.3) * 2.0
    S.updaters.append(_sway)
    return base

def dead_tree(S, x, z, h=3.6, col=rgb(54, 40, 32), collide=True):
    rnd = random.Random(int(x * 13 + z * 7))
    mk(S.root, 'cylinder', (x, 0, z), (0.34, h, 0.34), col, tex('ash'))
    for i in range(4):
        piv = Entity(parent=S.root, position=(x, h * rnd.uniform(0.55, 0.9), z), rotation_y=rnd.uniform(0, 360), add_to_scene_entities=False)
        br = Entity(parent=piv, rotation_x=rnd.uniform(35, 65), add_to_scene_entities=False)
        mk(br, 'cylinder', (0, 0, 0), (0.14, rnd.uniform(1.0, 1.7), 0.14), col, tex('ash'))
    if collide:
        S.world.add_circle(x, z, 0.35)

def rock(S, x, z, s=1.0, col=rgb(150, 138, 126), texture='rock', collide=True, squash=0.7):
    rnd = random.Random(int(x * 91 + z * 57))
    t = tex(texture) or tex('stone')
    w, d, hgt = (s * rnd.uniform(1.0, 1.4), s * rnd.uniform(0.9, 1.25), s * squash * rnd.uniform(0.9, 1.25))
    yaw = rnd.uniform(0, 360)
    c0 = shade(col, rnd.uniform(0.85, 1.1))
    e = mk(S.root, 'cube', (x, hgt * 0.42, z), (w, hgt, d), c0, t, rot=(rnd.uniform(-9, 9), yaw, rnd.uniform(-9, 9)), tex_scale=(max(1.0, w * 0.8), max(1.0, hgt * 0.8)))
    mk(S.root, 'cube', (x, hgt * 0.4, z), (w * 0.9, hgt * 0.94, d * 0.9), shade(c0, 0.94), t, rot=(rnd.uniform(-12, 12), yaw + 45, rnd.uniform(-12, 12)), tex_scale=(max(1.0, w * 0.8), max(1.0, hgt * 0.8)))
    mk(S.root, 'sphere', (x - s * 0.1, hgt * 0.8, z + s * 0.08), (w * 0.62, hgt * 0.5, d * 0.58), shade(c0, 1.06), t)
    mk(S.root, 'cube', (x + s * 0.7, s * 0.13, z - s * 0.45), (s * 0.45, s * 0.28, s * 0.4), shade(c0, 0.82), t, rot=(0, rnd.uniform(0, 90), rnd.uniform(-10, 10)))
    if collide:
        S.world.add_circle(x, z, s * 0.62)
    contact_shadow(S, x, z, s * 2.1, s * 2.1, 0.28)
    return e

def bush(S, x, z, s=1.0, col=rgb(56, 84, 44), flowers=None):
    rnd = random.Random(int(x * 19 + z * 23))
    leaf = tex('leaves')
    m = max(col.r, col.g, col.b, 0.01)
    tint = (col.r / m, col.g / m, col.b / m)
    for i in range(8):
        a = i * 0.8 + rnd.uniform(-0.2, 0.2)
        rr = (0.3 + 0.12 * (i % 2)) * s if i else 0.0
        k = 0.78 + 0.12 * (i % 3) + rnd.uniform(0, 0.1)
        sz = rnd.uniform(0.62, 0.86) * s
        mk(S.root, sphere_model((10, 6)), (x + math.cos(a) * rr, (0.3 + 0.16 * (i == 0) + 0.04 * (i % 3)) * s, z + math.sin(a) * rr), (sz, sz * 0.78, sz), color.rgba(min(1, tint[0] * k), min(1, tint[1] * k), min(1, tint[2] * k), 1), leaf, tex_scale=(1.4, 1.4))
    for i in range(5):
        a = rnd.uniform(0, 6.28)
        rr = rnd.uniform(0.1, 0.4) * s
        mk(S.root, 'cone', (x + math.cos(a) * rr, rnd.uniform(0.5, 0.62) * s, z + math.sin(a) * rr), (0.15 * s, 0.17 * s, 0.09 * s), shade(col, rnd.uniform(0.95, 1.15)), leaf, rot=(rnd.uniform(-35, 35), rnd.uniform(0, 360), rnd.uniform(-35, 35)))
    if flowers is not None:
        fc = rgb(*flowers) if isinstance(flowers, tuple) else flowers
        for i in range(9):
            a = rnd.uniform(0, 6.28)
            rr = rnd.uniform(0.15, 0.55) * s
            mk(S.root, 'sphere', (x + math.cos(a) * rr, rnd.uniform(0.35, 0.62) * s, z + math.sin(a) * rr), 0.09 * s, shade(fc, rnd.uniform(0.85, 1.15)), emissive=0.1)

def hedge_box(S, cx, cz, w, d, h=1.3, col=rgb(232, 250, 224)):
    leaf = tex('leaves')
    along_x = w >= d
    L, T = (w, d) if along_x else (d, w)
    mk(S.root, 'cube', (cx, 0.09, cz), (w + 0.2, 0.18, d + 0.2), rgb(150, 148, 164), tex('stone'), tex_scale=(max(w, d) / 2.0, 1))
    mk(S.root, 'cube', (cx, 0.18 + (h - 0.45) / 2.0, cz), (w, h - 0.45, d), col, leaf, tex_scale=(L / 1.2, h))
    ytop = h - 0.45 + 0.18
    if along_x:
        mk(S.root, 'cylinder', (cx - L / 2, ytop, cz), (T * 0.98, L, T * 0.98), col, leaf, rot=(0, 0, 90), tex_scale=(3, L / 1.2))
    else:
        mk(S.root, 'cylinder', (cx, ytop, cz - L / 2), (T * 0.98, L, T * 0.98), col, leaf, rot=(90, 0, 0), tex_scale=(3, L / 1.2))
    rnd = random.Random(int(cx * 7 + cz * 3))
    for i in range(max(1, int(L / 1.5))):
        t = -L / 2 + 0.7 + i * 1.5 + rnd.uniform(-0.2, 0.2)
        bx, bz = (cx + t, cz + rnd.uniform(-0.15, 0.15)) if along_x else (cx + rnd.uniform(-0.15, 0.15), cz + t)
        mk(S.root, 'sphere', (bx, h + 0.05, bz), (0.8, 0.5, 0.8), shade(col, rnd.uniform(0.9, 1.2)), leaf)
    S.world.add_box(cx, cz, w, d, blocks_sight=True)

def hedge(S, x0, x1, z, h=1.3, depth=1.1, col=rgb(232, 250, 224)):
    hedge_box(S, (x0 + x1) / 2.0, z, x1 - x0, depth, h, col)

def flower_bed(S, cx, cz, w, d, count=34, seed=1, palette=None):
    rnd = random.Random(seed)
    palette = palette or [rgb(214, 70, 92), rgb(236, 208, 90), rgb(170, 100, 200), rgb(240, 240, 232), rgb(238, 130, 60)]
    mk(S.root, 'cube', (cx, 0.05, cz), (w, 0.1, d), rgb(72, 54, 40), tex('dirt'), tex_scale=(w / 2, d / 2))
    for _ in range(count):
        fx, fz = (cx + rnd.uniform(-w / 2 + 0.1, w / 2 - 0.1), cz + rnd.uniform(-d / 2 + 0.1, d / 2 - 0.1))
        hh = rnd.uniform(0.25, 0.55)
        mk(S.root, 'cylinder', (fx, 0.08, fz), (0.025, hh, 0.025), rgb(70, 112, 56))
        mk(S.root, 'cone', (fx + 0.05, 0.08 + hh * 0.35, fz), (0.07, 0.2, 0.03), rgb(66, 104, 52), rot=(0, 0, -50))
        c = rnd.choice(palette)
        mk(S.root, 'sphere', (fx, 0.08 + hh + 0.02, fz), (0.14, 0.09, 0.14), c, emissive=0.12)
        mk(S.root, 'sphere', (fx, 0.08 + hh + 0.06, fz), (0.06, 0.05, 0.06), rgb(250, 220, 110), emissive=0.2)

def hay(S, x, z, s=1.0, collide=True):
    straw = rgb(232, 196, 104)
    mk(S.root, 'sphere', (x, 0.55 * s, z), (1.7 * s, 1.25 * s, 1.7 * s), straw)
    mk(S.root, 'sphere', (x, 1.05 * s, z), (1.2 * s, 0.9 * s, 1.2 * s), shade(straw, 1.08))
    mk(S.root, 'cylinder', (x, 0.38 * s, z), (1.52 * s, 0.07 * s, 1.52 * s), rgb(130, 96, 52))
    if collide:
        S.world.add_circle(x, z, 0.85 * s)
    contact_shadow(S, x, z, 3.0 * s, 3.0 * s, 0.35)

def crop_field(S, cx, cz, w, d, rows=7, col=rgb(118, 168, 70), seed=4):
    rnd = random.Random(seed + int(cx * 7 + cz))
    for i in range(rows):
        z = cz - d / 2.0 + d * (i + 0.5) / rows
        mk(S.root, 'cube', (cx, 0.04, z), (w, 0.08, d / rows * 0.55), rgb(92, 66, 46), tex('dirt'), tex_scale=(w / 2.0, 0.5))
        n = max(4, int(w / 0.85))
        for k in range(n):
            x = cx - w / 2.0 + w * (k + 0.5) / n + rnd.uniform(-0.12, 0.12)
            pz = z + rnd.uniform(-0.08, 0.08)
            hs = rnd.uniform(0.8, 1.25)
            g = Entity(parent=S.root, position=(x, 0.07, pz), rotation_y=rnd.uniform(0, 360), add_to_scene_entities=False)
            for j in range(5):
                piv = Entity(parent=g, rotation_y=j * 72 + rnd.uniform(-14, 14), rotation_x=-rnd.uniform(38, 68), add_to_scene_entities=False)
                mk(piv, blade_model(), (0, 0, 0), (rnd.uniform(0.1, 0.15), 1.0, rnd.uniform(0.5, 0.8) * hs), shade(col, rnd.uniform(0.75, 1.2)))
            if rnd.random() < 0.55:
                hh = rnd.uniform(0.55, 0.85)
                mk(g, cylinder_model(5), (0, 0, 0), (0.022, hh, 0.022), shade(col, 0.9))
                mk(g, sphere_model((6, 4)), (0, hh + 0.05, 0), (0.07, 0.2, 0.07), rgb(206, 170, 80))

def rug(S, cx, cz, w, d, rot=0, y=0.045, repeat=(1, 1)):
    e = mk(S.root, 'plane', (cx, y, cz), (w, 1, d), None, tex('rug'), rot=(0, rot, 0))
    if repeat != (1, 1):
        e.texture_scale = repeat
    e.setDepthOffset(2)
    return e

def low_table(S, cx, cz, w, d, h=0.5, collide=True):
    top = mk(S.root, 'cube', (cx, h, cz), (w, 0.1, d), None, tex('wood'), tex_scale=(w / 1.2, d / 1.2))
    mk(S.root, 'cube', (cx, h + 0.055, cz), (w * 0.96, 0.02, d * 0.96), rgb(168, 152, 122))
    for sx in (-1, 1):
        for sz in (-1, 1):
            mk(S.root, 'cube', (cx + sx * (w / 2 - 0.12), h / 2, cz + sz * (d / 2 - 0.12)), (0.12, h, 0.12), DARK_WOOD)
    if collide:
        S.world.add_box(cx, cz, w, d, blocks_sight=False)
    return h + 0.07

def cushion(S, x, z, col=CLOTH_RED, s=1.0, rot=0):
    mk(S.root, 'cylinder', (x, 0.02, z), (0.8 * s, 0.2 * s, 0.8 * s), col, rot=(0, rot, 0))
    mk(S.root, 'sphere', (x, 0.2 * s, z), (0.8 * s, 0.16 * s, 0.8 * s), shade(col, 1.15))

def goblet(S, x, y, z, col=GOLD, liquid=rgb(120, 26, 36), glow=0.0):
    piv = Entity(parent=S.root, position=(x, y, z), add_to_scene_entities=False)
    mk(piv, 'cylinder', (0, 0, 0), (0.09, 0.02, 0.09), col)
    mk(piv, 'cylinder', (0, 0.02, 0), (0.025, 0.12, 0.025), col)
    mk(piv, 'cylinder', (0, 0.14, 0), (0.11, 0.12, 0.11), col)
    piv.liquid = mk(piv, 'cylinder', (0, 0.235, 0), (0.095, 0.01, 0.095), liquid, emissive=glow)
    piv.glow = glow

    def set_glow(v, piv=piv):
        piv.glow = v
        piv.liquid.set_shader_input('emissive', float(v))
    piv.set_glow = set_glow
    return piv

def dish(S, x, y, z, food=rgb(150, 100, 50), r=0.55, mound=True, steam=False, plate=rgb(214, 206, 188)):
    piv = Entity(parent=S.root, position=(x, y, z), add_to_scene_entities=False)
    mk(piv, 'cylinder', (0, 0, 0), (r, 0.04, r), plate)
    if mound:
        mk(piv, 'sphere', (0, 0.05, 0), (r * 0.7, r * 0.34, r * 0.7), food)
        for i in range(3):
            a = i * 2.1
            mk(piv, 'sphere', (math.cos(a) * r * 0.22, 0.12, math.sin(a) * r * 0.22), (r * 0.22, r * 0.16, r * 0.22), shade(food, 1.1 + 0.08 * i))
    piv.steam = S.fx.steam((x, y + 0.2, z), scale=1.0, rate=5) if steam else None
    return piv

def bowl(S, x, y, z, food=rgb(190, 150, 70), r=0.34):
    piv = Entity(parent=S.root, position=(x, y, z), add_to_scene_entities=False)
    mk(piv, 'cylinder', (0, 0, 0), (r, 0.12, r), rgb(120, 76, 50))
    mk(piv, 'cylinder', (0, 0.11, 0), (r * 0.86, 0.015, r * 0.86), food)
    piv.steam = None
    return piv

def jug(S, x, y, z, col=rgb(150, 96, 60)):
    piv = Entity(parent=S.root, position=(x, y, z), add_to_scene_entities=False)
    mk(piv, 'cylinder', (0, 0, 0), (0.16, 0.26, 0.16), col)
    mk(piv, 'sphere', (0, 0.28, 0), (0.2, 0.2, 0.2), col)
    mk(piv, 'cylinder', (0, 0.36, 0), (0.07, 0.1, 0.07), col)
    return piv

def bed(S, cx, cz, w=1.9, d=1.0, col=rgb(170, 130, 110), collide=True, head=None):
    if head in ('-x', '+x'):
        along_x = True
    elif head in ('-z', '+z'):
        along_x = False
    else:
        along_x = w >= d
    L, Wd = (w, d) if along_x else (d, w)
    ry = {None: 0 if along_x else -90, '-x': 0, '+x': 180, '-z': -90, '+z': 90}[head]
    root = Entity(parent=S.root, position=(cx, 0, cz), rotation_y=ry, add_to_scene_entities=False)
    sheet = rgb(228, 216, 190)
    mk(root, 'cube', (0, 0.26, 0), (L, 0.26, Wd), DARK_WOOD, tex('wood'), tex_scale=(L / 1.2, 1))
    for sx in (-1, 1):
        for sz in (-1, 1):
            mk(root, 'cylinder', (sx * (L / 2 - 0.06), 0.0, sz * (Wd / 2 - 0.06)), (0.13, 0.5, 0.13), shade(DARK_WOOD, 1.15))
    mk(root, 'cube', (-L / 2 - 0.02, 0.55, 0), (0.1, 0.95, Wd + 0.12), shade(DARK_WOOD, 1.1), tex('wood'))
    mk(root, 'cube', (L / 2 + 0.02, 0.45, 0), (0.08, 0.55, Wd + 0.1), shade(DARK_WOOD, 1.1), tex('wood'))
    mk(root, 'cube', (0, 0.46, 0), (L - 0.12, 0.2, Wd - 0.1), sheet)
    mk(root, 'sphere', (0, 0.56, 0), (L - 0.2, 0.26, Wd - 0.16), sheet)
    lb = L - 0.78
    cxb = (-L / 2 + 0.7 + L / 2 + 0.02) / 2.0
    mk(root, 'sphere', (cxb, 0.63, 0), (lb, 0.22, Wd - 0.04), col, tex('rug'), tex_scale=(lb / 0.9, 1))
    for sz in (-1, 1):
        mk(root, 'cube', (cxb, 0.45, sz * (Wd / 2 - 0.03)), (lb - 0.06, 0.4, 0.07), shade(col, 0.85), tex('rug'), tex_scale=(lb / 0.9, 0.5))
    mk(root, 'cube', (L / 2 - 0.01, 0.42, 0), (0.07, 0.4, Wd - 0.06), shade(col, 0.85), tex('rug'), tex_scale=(1, 0.5))
    mk(root, 'cube', (-L / 2 + 0.8, 0.745, 0), (0.34, 0.1, Wd - 0.02), shade(sheet, 0.98))
    for sz in (-1, 1):
        mk(root, 'sphere', (-L / 2 + 0.38, 0.72, sz * Wd * 0.22), (0.46, 0.2, Wd * 0.4), rgb(238, 230, 212))
    if collide:
        S.world.add_box(cx, cz, w, d, blocks_sight=False)

def chest(S, x, z, rot=0, collide=True):
    mk(S.root, 'cube', (x, 0.3, z), (0.9, 0.6, 0.55), WOOD, tex('wood'), rot=(0, rot, 0))
    mk(S.root, 'cube', (x, 0.64, z), (0.92, 0.12, 0.57), shade(WOOD, 0.85), rot=(0, rot, 0))
    mk(S.root, 'cube', (x, 0.5, z), (0.1, 0.18, 0.6), GOLD, rot=(0, rot, 0))
    if collide:
        S.world.add_circle(x, z, 0.5)

def barrel(S, x, z, collide=True):
    mk(S.root, 'cylinder', (x, 0, z), (0.7, 0.9, 0.7), WOOD, tex('wood'))
    for yy in (0.2, 0.7):
        mk(S.root, 'cylinder', (x, yy, z), (0.74, 0.05, 0.74), IRON)
    if collide:
        S.world.add_circle(x, z, 0.38)

def crate(S, x, z, s=0.8, rot=0, collide=True):
    mk(S.root, 'cube', (x, s / 2, z), (s, s, s), WOOD, tex('wood'), rot=(0, rot, 0))
    if collide:
        S.world.add_circle(x, z, s * 0.62)

def throne(S, x, z, ry=0.0, scale=1.0, y=0.0):
    gold = rgb(214, 170, 64)
    dgold = rgb(160, 118, 38)
    wood = rgb(88, 52, 36)
    velvet = rgb(142, 26, 40)
    g = Entity(parent=S.root, position=(x, y, z), rotation_y=ry, scale=scale, add_to_scene_entities=False)
    mk(g, 'cube', (0, 0.1, 0), (2.5, 0.2, 1.9), dgold, emissive=0.12)
    mk(g, 'cube', (0, 0.27, -0.05), (2.15, 0.16, 1.65), gold, emissive=0.16)
    mk(g, 'cube', (0, 0.62, -0.1), (1.7, 0.55, 1.2), wood, tex('wood'))
    mk(g, 'cube', (0, 0.92, 0.0), (1.55, 0.18, 1.2), velvet)
    mk(g, 'cube', (0, 1.03, 0.0), (1.3, 0.06, 0.95), shade(velvet, 1.15))
    for sx in (-1, 1):
        mk(g, 'cube', (sx * 0.82, 1.1, 0.05), (0.2, 0.18, 1.2), gold, emissive=0.2)
        mk(g, 'cube', (sx * 0.82, 0.74, -0.05), (0.18, 0.75, 1.0), wood, tex('wood'))
        mk(g, 'sphere', (sx * 0.82, 1.14, 0.68), 0.22, gold, emissive=0.3)
        mk(g, 'cylinder', (sx * 0.92, 0.2, -0.8), (0.2, 3.35, 0.2), gold, emissive=0.2)
        mk(g, 'sphere', (sx * 0.92, 3.62, -0.8), 0.3, gold, emissive=0.35)
        mk(g, 'cone', (sx * 0.92, 3.8, -0.8), (0.14, 0.3, 0.14), gold, emissive=0.35)
    mk(g, 'cube', (0, 1.95, -0.78), (1.75, 1.9, 0.2), wood, tex('wood'))
    mk(g, 'cylinder', (0, 2.8, -0.88), (1.75, 0.2, 1.75), wood, tex('wood'), rot=(90, 0, 0), origin=(0, 0, 0))
    mk(g, 'cube', (0, 1.95, -0.66), (1.35, 1.65, 0.05), velvet)
    mk(g, 'cylinder', (0, 2.8, -0.685), (1.35, 0.05, 1.35), velvet, rot=(90, 0, 0), origin=(0, 0, 0))
    for k in range(13):
        a_ = math.radians(k * 15.0)
        mk(g, 'sphere', (math.cos(a_) * 0.78, 2.8 + math.sin(a_) * 0.78, -0.655), 0.075, gold, emissive=0.35)
    mk(g, 'cube', (0, 1.15, -0.64), (1.62, 0.07, 0.07), gold, emissive=0.3)
    for sx in (-1, 1):
        mk(g, 'cube', (sx * 0.81, 1.97, -0.64), (0.07, 1.64, 0.07), gold, emissive=0.3)
    mk(g, 'sphere', (0, 3.1, -0.62), (0.26, 0.34, 0.12), rgb(236, 60, 70), emissive=0.8)
    mk(g, 'sphere', (0, 3.55, -0.78), (0.34, 0.34, 0.34), gold, emissive=0.35)
    mk(g, 'cone', (0, 3.7, -0.78), (0.2, 0.4, 0.2), gold, emissive=0.35)
    return g

def hanging_rope(S, x, z_face, top_y, bottom_y=0.35, hook_z=None):
    iron = rgb(58, 54, 56)
    hz = z_face - 1.2 if hook_z is None else hook_z
    mk(S.root, 'cube', (x, top_y + 0.07, (hz + z_face) / 2.0), (0.18, 0.12, abs(z_face - hz) + 0.28), iron)
    for sx in (-1, 1):
        mk(S.root, 'cone', (x + sx * 0.13, top_y + 0.02, hz - 0.1), (0.1, 0.3, 0.1), iron, rot=(180, 0, 0))
    mk(S.root, torus_model(0.22), (x, top_y - 0.04, z_face + 0.04), (0.26, 0.26, 0.26), iron, rot=(90, 0, 0))
    rope = rgb(132, 104, 66)
    n = int((top_y - bottom_y) / 0.13)
    for i in range(n):
        f = i / max(1, n - 1)
        y = top_y - 0.14 - i * 0.13
        zz = z_face + 0.14 + 0.16 * f * f
        mk(S.root, 'cylinder', (x + 0.012 * (i % 2), y - 0.13, zz), (0.07, 0.15, 0.07), shade(rope, 0.85 + 0.25 * (i % 2)), rot=(0, 0, 14 if i % 2 else -14))
        if i % 4 == 2:
            mk(S.root, 'sphere', (x, y - 0.06, zz), (0.13, 0.11, 0.13), shade(rope, 0.7))
    mk(S.root, 'cone', (x, bottom_y - 0.08, z_face + 0.14 + 0.16), (0.13, 0.2, 0.13), shade(rope, 0.75), rot=(180, 0, 0))

def fire_logs(S, x, z, r=0.62, ring=True):
    rnd = random.Random(int(x * 13 + z * 29))
    mk(S.root, 'cylinder', (x, 0.012, z), (r * 2.3, 0.03, r * 2.3), rgb(34, 28, 26), tex('ash'), tex_scale=(2, 1))
    for i in range(5):
        piv = Entity(parent=S.root, position=(x, 0.0, z), rotation_y=i * 72 + rnd.uniform(-8, 8), add_to_scene_entities=False)
        lg = Entity(parent=piv, position=(0, 0.13 + 0.03 * (i % 2), 0.0), rotation_x=84, add_to_scene_entities=False)
        ln = r * 1.5 * rnd.uniform(0.9, 1.15)
        mk(lg, 'cylinder', (0, 0, 0), (0.17, ln, 0.17), rgb(96, 66, 42), tex('wood'), emissive=0.12)
        mk(lg, 'cylinder', (0, 0, 0), (0.18, ln * 0.34, 0.18), rgb(28, 20, 18))
        mk(lg, 'cylinder', (0, ln - 0.03, 0), (0.15, 0.04, 0.15), rgb(210, 170, 110))
    for k in range(7):
        a_ = rnd.uniform(0, 6.28)
        d_ = rnd.uniform(0.05, r * 0.55)
        mk(S.root, 'sphere', (x + math.cos(a_) * d_, 0.07, z + math.sin(a_) * d_), (0.11, 0.05, 0.1), rgb(255, 120, 40), emissive=0.9)
    if ring:
        n = 9
        for a in range(n):
            ang = a * 6.283 / n + rnd.uniform(-0.1, 0.1)
            sz = rnd.uniform(0.2, 0.3)
            mk(S.root, 'sphere', (x + math.cos(ang) * (r + 0.3), sz * 0.28, z + math.sin(ang) * (r + 0.3)), (sz * 1.2, sz * 0.8, sz), rgb(110, 102, 96), tex('stone_dark'), rot=(0, rnd.uniform(0, 180), 0))

def seat_mat(S, x, z, ry=0.0, w=1.15, d=0.95, col=rgb(150, 104, 64)):
    g = Entity(parent=S.root, position=(x, 0.0, z), rotation_y=ry, add_to_scene_entities=False)
    e = mk(g, 'cube', (0, 0.03, 0), (w, 0.05, d), col, tex('dirt'), tex_scale=(2.0, 1.6))
    e.setDepthOffset(1)
    for k in (-0.3, 0.0, 0.3):
        mk(g, 'cube', (0, 0.058, k * d), (w * 0.98, 0.012, d * 0.07), shade(col, 0.55))
    for sx in (-1, 1):
        mk(g, 'cube', (sx * (w / 2 + 0.03), 0.025, 0), (0.07, 0.03, d * 0.92), shade(col, 1.25))
    return g

def log_seat(S, x, z, ry=0.0, ln=1.5, d=0.36):
    g = Entity(parent=S.root, position=(x, 0.0, z), rotation_y=ry, add_to_scene_entities=False)
    mk(g, 'cylinder', (-ln / 2, d / 2, 0), (d, ln, d), rgb(122, 86, 54), tex('wood'), rot=(0, 0, 90))
    mk(g, 'cylinder', (ln / 2 - 0.02, d / 2, 0), (d * 0.9, 0.04, d * 0.9), rgb(206, 170, 118), rot=(0, 0, 90))
    mk(g, 'cylinder', (-ln / 2 + 0.02, d / 2, 0), (d * 0.9, 0.04, d * 0.9), rgb(206, 170, 118), rot=(0, 0, 90))
    S.world.add_box(x, z, ln if abs(math.sin(math.radians(ry))) < 0.7 else d, d if abs(math.sin(math.radians(ry))) < 0.7 else ln, blocks_sight=False)
    return g

def well(S, x, z):
    mk(S.root, 'cylinder', (x, 0, z), (1.6, 0.9, 1.6), None, tex('stone'), tex_scale=(3, 1))
    mk(S.root, 'cylinder', (x, 0.88, z), (1.2, 0.04, 1.2), rgb(8, 14, 24))
    for sx in (-1, 1):
        mk(S.root, 'cube', (x + sx * 0.7, 1.4, z), (0.12, 1.4, 0.12), DARK_WOOD)
    mk(S.root, 'cube', (x, 2.1, z), (1.8, 0.1, 0.5), DARK_WOOD)
    S.world.add_circle(x, z, 0.85)
    contact_shadow(S, x, z, 3.4, 3.4, 0.5)

def tent(S, x, z, r=2.2, h=2.4, col=rgb(150, 124, 92), collide=True, face=None):
    ang = 0.0 if face is None else math.degrees(math.atan2(face[0] - x, face[1] - z))
    g = Entity(parent=S.root, position=(x, 0.0, z), rotation_y=ang, add_to_scene_entities=False)
    cloth = tex('plaster')
    mk(g, 'cone', (0, 0, 0), (r * 2, h, r * 2), col, cloth, tex_scale=(3, 1))
    for k, yy in enumerate((0.26, 0.52)):
        dia = 2.0 * r * (1.0 - yy) * 1.02
        mk(g, torus_model(0.05), (0, h * yy, 0), (dia, dia * 0.85, dia), shade(col, 0.62))
    mk(g, torus_model(0.06), (0, 0.07, 0), (r * 2.04, r * 1.5, r * 2.04), shade(col, 0.58))
    mk(g, 'cylinder', (0, h - 0.05, 0), (0.07, 0.55, 0.07), rgb(88, 62, 40), tex('wood'))
    mk(g, 'sphere', (0, h + 0.5, 0), (0.14, 0.14, 0.14), rgb(214, 170, 84), emissive=0.2)
    slope = math.degrees(math.atan2(r, h))
    slant = math.hypot(r, h)
    door = Entity(parent=g, position=(0, 0.0, r * 0.985), rotation_x=-slope, add_to_scene_entities=False)
    dw, dh = (1.2, slant * 0.66)
    mk(door, 'cone', (0, 0.0, 0.0), (dw, dh, 0.05), rgb(18, 12, 9))
    mk(door, 'cone', (0, 0.0, 0.01), (dw * 0.8, dh * 0.8, 0.04), rgb(52, 34, 22))
    for sx in (-1, 1):
        fl = Entity(parent=door, position=(sx * (dw * 0.5 + 0.05), 0.0, 0.03), rotation_z=-sx * 12, add_to_scene_entities=False)
        mk(fl, 'cone', (0, 0, 0), (0.78, dh * 1.04, 0.07), shade(col, 1.12), cloth)
        mk(fl, 'cylinder', (-sx * 0.05, dh * 0.3, 0.05), (0.07, 0.07, 0.07), rgb(120, 86, 52), rot=(0, 0, 90))
        mk(fl, 'sphere', (-sx * 0.05, dh * 0.3, 0.07), (0.1, 0.1, 0.1), rgb(120, 86, 52))
    mk(g, 'cube', (0, 0.03, r + 0.55), (1.5, 0.05, 1.0), rgb(120, 78, 56), tex('rug'), tex_scale=(1, 1)).setDepthOffset(1)
    for k in range(4):
        a_ = math.radians(45 + k * 90 + 180)
        px, pz = (math.sin(a_) * (r + 1.1), math.cos(a_) * (r + 1.1))
        mk(g, 'cone', (px, 0.0, pz), (0.09, 0.28, 0.09), rgb(98, 70, 44))
        ln = math.hypot(r + 1.1, h * 0.95)
        rope = Entity(parent=g, position=(px, 0.28, pz), add_to_scene_entities=False)
        mk(rope, 'cylinder', (0, 0, 0), (0.025, ln, 0.025), rgb(150, 120, 80), rot=(90, 0, 0), origin=(0, 0, 0))
        rope.lookAt(Point3(0, h * 0.95, 0))
    if collide:
        S.world.add_circle(x, z, r * 0.95)

def scroll_item(S, x, y, z, col=rgb(236, 216, 160)):
    piv = Entity(parent=S.root, position=(x, y, z), add_to_scene_entities=False)
    mk(piv, 'cylinder', (0, 0, 0), (0.12, 0.6, 0.12), col, rot=(0, 0, 90), origin=(0, 0.5, 0), emissive=0.35)
    mk(piv, 'cylinder', (-0.16, 0.0, 0), (0.15, 0.06, 0.15), rgb(120, 40, 36), rot=(0, 0, 90), emissive=0.2)
    halo = glow_quad(piv, (0, 0, 0), 1.3, (1.0, 0.82, 0.4, 0.6), tex('glow'))
    glint = glow_quad(piv, (0, 0.1, 0), 0.6, (1.0, 0.95, 0.7, 0.8), tex('star'))
    S.light_scroll = S.rig.add((x, y + 0.6, z), color=(1.0, 0.8, 0.4), intensity=0.9, radius=4.0, flicker=0.2)
    piv.base_y = y

    def _bob(dt, p=piv, h=halo, g=glint):
        t = Clock_now()
        p.y = p.base_y + math.sin(t * 2.2) * 0.07
        p.rotation_y = t * 40
        h.scale = 1.2 + math.sin(t * 3) * 0.12
        g.rotation_z = t * 90
    S.updaters.append(_bob)
    return piv

def weapon_rack(S, x, z, rot=0):
    mk(S.root, 'cube', (x, 0.9, z), (1.6, 0.1, 0.14), DARK_WOOD, rot=(0, rot, 0))
    for i in range(3):
        mk(S.root, 'cylinder', (x - 0.5 + i * 0.5, 0.0, z), (0.05, 1.7, 0.05), shade(IRON, 1.2), rot=(0, rot, 0))
        mk(S.root, 'cone', (x - 0.5 + i * 0.5, 1.7, z), (0.1, 0.25, 0.1), rgb(180, 184, 196), rot=(0, rot, 0))

def ruin_wall(S, cx, cz, w, d, h, col=rgb(60, 48, 42)):
    e = wall_box(S, cx, cz, w, d, h, 'ash', col, tile=2.0)
    for _ in range(3):
        mk(S.root, 'cube', (cx + random.uniform(-w / 2, w / 2), h + 0.1, cz + random.uniform(-d / 2, d / 2)), (random.uniform(0.3, 0.7), random.uniform(0.3, 0.9), random.uniform(0.3, 0.7)), shade(col, 0.8), tex('ash'), rot=(random.uniform(-20, 20), random.uniform(0, 90), random.uniform(-20, 20)))
    return e

def cave_mouth(S, x, z, width=6.0, h=4.5):
    mk(S.root, 'cube', (x, h / 2, z + 1.4), (width * 0.7, h, 2.8), rgb(10, 10, 14))
    for i in range(9):
        a = math.pi * i / 8
        rx = x + math.cos(a) * width * 0.52
        ry = math.sin(a) * h * 0.78
        mk(S.root, 'sphere', (rx, ry, z), (rnd(1.4, 2.2), rnd(1.4, 2.2), rnd(1.3, 2.0)), rgb(76, 72, 74), tex('stone_dark'), rot=(rnd(-15, 15), rnd(0, 360), rnd(-15, 15)))
    S.world.add_box(x - width * 0.52, z, 1.6, 2.5)
    S.world.add_box(x + width * 0.52, z, 1.6, 2.5)

def rnd(a, b):
    return random.uniform(a, b)

class CrowBird:

    def __init__(self, parent, scale=1.0, col=rgb(10, 10, 14)):
        self.root = Entity(parent=parent, scale=scale, add_to_scene_entities=False)
        mk(self.root, 'sphere', (0, 0, 0), (0.46, 0.34, 1.0), col)
        mk(self.root, 'sphere', (0, 0.07, 0.52), (0.27, 0.25, 0.3), col)
        mk(self.root, 'cone', (0, 0.04, 0.72), (0.1, 0.3, 0.1), rgb(30, 28, 30), rot=(90, 0, 0))
        mk(self.root, 'cube', (0, 0.0, -0.62), (0.3, 0.04, 0.5), col, rot=(0, 0, 0))
        self.wing_l = Entity(parent=self.root, position=(-0.18, 0.06, 0.05), add_to_scene_entities=False)
        self.wing_r = Entity(parent=self.root, position=(0.18, 0.06, 0.05), add_to_scene_entities=False)
        mk(self.wing_l, 'cube', (-0.62, 0, 0), (1.25, 0.035, 0.55), col)
        mk(self.wing_r, 'cube', (0.62, 0, 0), (1.25, 0.035, 0.55), col)
        self.phase = random.random() * 6.28
        self.speed = random.uniform(7.0, 9.5)

    def update(self, t):
        a = math.sin(t * self.speed + self.phase) * 38.0
        self.wing_l.rotation_z = -a
        self.wing_r.rotation_z = a

def contact_shadow(S, x, z, w, d, alpha=0.5, y=0.02, rot=0):
    e = glow_quad(S.root, (x, y, z), (w, d), (0, 0, 0, alpha), tex('shadow'), billboard=False, add=False, bin_sort=4)
    e.rotation_x = 90
    e.rotation_y = rot
    return e

def ground_patches(S, x0, z0, x1, z1, count=80, seed=3, palette=None, size=(3.0, 9.0), alpha=(0.16, 0.34), y=0.006):
    from panda3d.core import TransparencyAttrib
    rnd = random.Random(seed)
    palette = palette or [rgb(232, 206, 168), rgb(196, 160, 120), rgb(240, 222, 190), rgb(170, 140, 112), rgb(214, 180, 140), rgb(150, 150, 120)]
    for _ in range(count):
        c = rnd.choice(palette)
        a = rnd.uniform(*alpha)
        s = rnd.uniform(*size)
        col = (c.r, c.g, c.b, a)
        e = mk(S.root, 'quad', (rnd.uniform(x0, x1), y + rnd.random() * 0.002, rnd.uniform(z0, z1)), (s * rnd.uniform(1.0, 1.7), s, 1), col, tex('glow'), rot=(90, rnd.uniform(0, 180), 0), double_sided=True)
        e.setTransparency(TransparencyAttrib.MAlpha)
        e.setDepthWrite(False)
        e.setBin('fixed', 3)

def scatter_clutter(S, x0, z0, x1, z1, count=70, seed=5, avoid=None, grass=rgb(110, 118, 60), pebble=rgb(120, 108, 98)):
    rnd = random.Random(seed)
    for _ in range(count):
        x, z = (rnd.uniform(x0, x1), rnd.uniform(z0, z1))
        if avoid and any((a[0] <= x <= a[1] and a[2] <= z <= a[3] for a in avoid)):
            continue
        if rnd.random() < 0.45:
            s = rnd.uniform(0.12, 0.34)
            mk(S.root, 'sphere', (x, s * 0.25, z), (s * 1.3, s * 0.7, s), shade(pebble, rnd.uniform(0.75, 1.15)), rot=(0, rnd.uniform(0, 180), 0))
        else:
            for k in range(rnd.randint(5, 8)):
                a = rnd.uniform(0, 6.28)
                mk(S.root, 'cone', (x + math.cos(a) * 0.12, 0, z + math.sin(a) * 0.12), (0.045, rnd.uniform(0.28, 0.66), 0.045), shade(grass, rnd.uniform(0.7, 1.25)), rot=(rnd.uniform(-20, 20), 0, rnd.uniform(-20, 20)))

def soft_path(S, points, width=2.4, col=rgb(176, 146, 114), alpha=0.5, y=0.01, spacing=0.9, seed=1):
    from panda3d.core import TransparencyAttrib
    rnd = random.Random(seed)
    for (x0, z0), (x1, z1) in zip(points[:-1], points[1:]):
        length = math.hypot(x1 - x0, z1 - z0)
        n = max(2, int(length / spacing))
        for i in range(n + 1):
            k = i / n
            x = x0 + (x1 - x0) * k + rnd.uniform(-0.25, 0.25)
            z = z0 + (z1 - z0) * k + rnd.uniform(-0.25, 0.25)
            w = width * rnd.uniform(1.15, 1.6)
            e = mk(S.root, 'quad', (x, y + rnd.random() * 0.002, z), (w, w * rnd.uniform(0.9, 1.3), 1), (col.r, col.g, col.b, alpha * rnd.uniform(0.6, 1.0)), tex('glow'), rot=(90, rnd.uniform(0, 180), 0), double_sided=True)
            e.setTransparency(TransparencyAttrib.MAlpha)
            e.setDepthWrite(False)
            e.setBin('fixed', 3)

def blood_pool(S, x, z, r=0.8, alpha=0.8, y=0.024, seed=0, col=(0.26, 0.012, 0.02)):
    from panda3d.core import TransparencyAttrib
    rg = random.Random(seed + int(x * 7 + z * 13))
    out = []
    for i in range(6):
        a, dist = (rg.uniform(0, 6.28), rg.uniform(0, r * 0.5))
        sz = r * rg.uniform(0.85, 1.5)
        e = mk(S.root, 'quad', (x + math.cos(a) * dist, y + i * 0.0015, z + math.sin(a) * dist), (sz, sz * rg.uniform(0.7, 1.2), 1), (col[0], col[1], col[2], alpha * rg.uniform(0.7, 1.0)), tex('glow'), rot=(90, rg.uniform(0, 180), 0), double_sided=True)
        e.setTransparency(TransparencyAttrib.MAlpha)
        e.setDepthWrite(False)
        e.setBin('fixed', 4)
        out.append(e)
    return out

def shrouded_body(S, x, z, yaw=0.0, cloth=rgb(176, 166, 142), length=1.65, width=0.5, stain=0.0, y=0.0, scale=1.0):
    from panda3d.core import TransparencyAttrib
    root = Entity(parent=S.root, position=(x, y, z), rotation_y=yaw, scale=scale, add_to_scene_entities=False)
    L = length
    e = mk(root, 'quad', (0.0, 0.012, 0.0), (width + 0.9, L + 0.7, 1), (cloth.r * 0.8, cloth.g * 0.8, cloth.b * 0.8, 0.85), tex('glow'), rot=(90, 0, 0), double_sided=True)
    e.setTransparency(TransparencyAttrib.MAlpha)
    e.setDepthWrite(False)
    e.setBin('fixed', 3)
    mk(root, 'sphere', (0, 0.16, L * 0.06), (width * 0.92, 0.32, L * 0.78), cloth)
    mk(root, 'sphere', (0, 0.15, -L * 0.26), (width * 0.7, 0.27, L * 0.5), shade(cloth, 0.96))
    mk(root, 'sphere', (0, 0.17, L * 0.3), (width * 1.04, 0.31, 0.42), shade(cloth, 1.03))
    mk(root, 'sphere', (0, 0.14, L * 0.47), (0.31, 0.27, 0.34), shade(cloth, 1.06))
    for sx in (-1, 1):
        mk(root, 'sphere', (sx * 0.1, 0.09, -L * 0.47), (0.16, 0.14, 0.26), shade(cloth, 0.9), rot=(-10, sx * 9, 0))
    for fx_, fz_, fl in ((0.13, L * 0.06, 0.55), (-0.15, -L * 0.02, 0.6), (0.06, -L * 0.3, 0.45)):
        mk(root, 'sphere', (fx_, 0.285 if fz_ > -0.2 else 0.25, fz_), (0.07, 0.07, fl), shade(cloth, 0.8), rot=(0, 8 * (1 if fx_ > 0 else -1), 0))
    mk(root, 'sphere', (0.1, 0.2, L * 0.1), (0.18, 0.12, 0.5), shade(cloth, 1.08), rot=(0, 10, 12))
    if stain > 0:
        st = mk(root, 'quad', (0.04, 0.318, L * 0.1), (0.52 * stain + 0.2, 0.62 * stain + 0.22, 1), (0.4, 0.02, 0.03, 0.92), tex('glow'), rot=(90, 12, 0), double_sided=True)
        st.setTransparency(TransparencyAttrib.MAlpha)
        st.setDepthWrite(False)
        st.setBin('fixed', 4)
        wx, wz = (x + math.sin(math.radians(yaw)) * L * 0.05, z + math.cos(math.radians(yaw)) * L * 0.05)
        blood_pool(S, wx + math.cos(math.radians(yaw)) * 0.4, wz - math.sin(math.radians(yaw)) * 0.4, r=0.6 + 0.45 * stain, alpha=0.85)
    return root

def child_things(S, x, z, yaw=0.0):
    root = Entity(parent=S.root, position=(x, 0, z), rotation_y=yaw, add_to_scene_entities=False)
    for sx, rot in ((-1, 12), (1, -20)):
        mk(root, 'cube', (sx * 0.1, 0.02, 0.0 if sx < 0 else 0.15), (0.09, 0.03, 0.2), rgb(120, 82, 52), rot=(0, rot, 0))
    mk(root, 'cube', (0.55, 0.08, 0.1), (0.1, 0.12, 0.26), rgb(150, 104, 62), rot=(0, 25, 0))
    mk(root, 'cube', (0.58, 0.18, 0.2), (0.07, 0.14, 0.07), rgb(150, 104, 62), rot=(0, 25, 0))
    mk(root, 'cube', (0.55, 0.012, 0.1), (0.2, 0.02, 0.1), rgb(110, 76, 46), rot=(0, 25, 0))

def horse(S, x, z, yaw=0.0, col=rgb(112, 72, 44), mane=None, saddle=None, pose='stand', collide=True, seed=0):
    mane = mane or shade(col, 0.42)
    rg = random.Random(seed + int(x * 5 + z * 11))
    root = Entity(parent=S.root, position=(x, 0, z), rotation_y=yaw, add_to_scene_entities=False)
    m = Entity(parent=root, add_to_scene_entities=False)
    mk(m, 'sphere', (0, 1.2, 0), (0.62, 0.72, 2.0), col)
    mk(m, 'sphere', (0, 1.28, 0.74), (0.6, 0.84, 0.74), shade(col, 1.04))
    mk(m, 'sphere', (0, 1.3, -0.76), (0.64, 0.82, 0.84), shade(col, 0.97))
    mk(m, 'sphere', (0, 1.0, 0.0), (0.55, 0.34, 1.5), shade(col, 1.2))
    legs = []
    for sx in (-1, 1):
        for sz in (-1, 1):
            lg = Entity(parent=m, position=(sx * 0.2, 1.0, sz * 0.66), add_to_scene_entities=False)
            mk(lg, 'cylinder', (0, -0.52, 0), (0.19, 0.55, 0.19), shade(col, 0.96))
            mk(lg, 'sphere', (0, -0.5, 0.0), (0.15, 0.14, 0.15), shade(col, 0.8))
            mk(lg, 'cylinder', (0, -1.0, 0), (0.11, 0.5, 0.11), shade(col, 0.8))
            mk(lg, 'cylinder', (0, -1.0, 0.01), (0.16, 0.1, 0.17), rgb(30, 24, 22))
            legs.append(lg)
    th = 34.0
    neck = Entity(parent=m, position=(0, 1.45, 0.92), add_to_scene_entities=False)
    mk(neck, 'cylinder', (0, 0, 0), (0.36, 1.0, 0.36), shade(col, 1.02), rot=(th, 0, 0), origin=(0, 0, 0))
    ct, st_ = (math.cos(math.radians(th)), math.sin(math.radians(th)))
    for i in range(8):
        u = 0.1 + 0.85 * i / 7.0
        mk(neck, 'cube', (0, u * ct + 0.15, u * st_ - 0.2), (0.07, 0.22, 0.15), mane, rot=(th, 0, 0))
    head = Entity(parent=neck, position=(0, 1.0 * ct, 1.0 * st_), add_to_scene_entities=False)
    mk(head, 'sphere', (0, -0.02, 0.1), (0.3, 0.36, 0.6), shade(col, 1.0), rot=(50, 0, 0))
    mk(head, 'sphere', (0, -0.2, 0.36), (0.22, 0.26, 0.3), shade(col, 0.8), rot=(50, 0, 0))
    for sx in (-1, 1):
        mk(head, 'cone', (sx * 0.1, 0.2, -0.05), (0.08, 0.22, 0.08), shade(col, 0.9), rot=(10, 0, sx * 10))
        mk(head, 'sphere', (sx * 0.15, 0.05, 0.1), 0.06, rgb(14, 10, 10))
    tail = Entity(parent=m, position=(0, 1.5, -1.12), add_to_scene_entities=False)
    mk(tail, 'cylinder', (0, 0, 0), (0.16, 0.95, 0.16), mane, rot=(-160, 0, 0), origin=(0, 0, 0))
    mk(tail, 'sphere', (0, -0.7, -0.4), (0.22, 0.5, 0.24), mane)
    if saddle:
        mk(m, 'cube', (0, 1.66, 0.0), (0.72, 0.07, 0.8), saddle)
        mk(m, 'cube', (0, 1.74, -0.05), (0.48, 0.14, 0.5), rgb(92, 58, 34))
        mk(m, 'cube', (0, 1.84, -0.3), (0.46, 0.18, 0.1), rgb(84, 52, 30))
        for sx in (-1, 1):
            mk(m, 'cube', (sx * 0.38, 1.34, -0.05), (0.04, 0.55, 0.1), rgb(70, 50, 34))
    contact_shadow(S, x, z, 2.8, 3.4, 0.45, rot=yaw)
    if pose == 'dead':
        m.rotation_z = 90
        m.position = (1.2, 0.0, 0.0)
        neck.rotation_x = -25
        for i, lg in enumerate(legs):
            lg.rotation_x = rg.uniform(-35, 35)
            lg.rotation_z = rg.uniform(-14, 14)
        head.rotation_x = 20
        blood_pool(S, x + math.cos(math.radians(yaw)) * 0.3, z - math.sin(math.radians(yaw)) * 0.2, r=1.1, alpha=0.8)
        if collide:
            for off in (-0.7, 0.7):
                S.world.add_circle(x + math.sin(math.radians(yaw)) * off, z + math.cos(math.radians(yaw)) * off, 0.7)
        return root
    if collide:
        for off in (-0.6, 0.6):
            S.world.add_circle(x + math.sin(math.radians(yaw)) * off, z + math.cos(math.radians(yaw)) * off, 0.55)
    ph = rg.uniform(0, 6.28)

    def _idle(dt, ph=ph):
        t = Clock_now() + ph
        m.y = math.sin(t * 1.5) * 0.008
        tail.rotation_z = math.sin(t * 2.1) * 9.0
        tail.rotation_x = math.sin(t * 1.1) * 4.0
        neck.rotation_x = math.sin(t * 0.8) * 3.0 + max(0.0, math.sin(t * 0.23)) ** 6 * 22.0
        head.rotation_x = math.sin(t * 0.8 + 1.0) * 3.0
        legs[1].rotation_x = max(0.0, math.sin(t * 0.37)) ** 10 * 18.0
    S.updaters.append(_idle)
    return root

def hitch_rail(S, x, z, length=3.0, yaw=0.0):
    c, s = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw)))
    for sgn in (-1, 1):
        mk(S.root, 'cylinder', (x + c * sgn * length / 2, 0, z - s * sgn * length / 2), (0.16, 1.35, 0.16), DARK_WOOD, tex('wood'))
    mk(S.root, 'cube', (x, 1.15, z), (length, 0.1, 0.1), WOOD, tex('wood'), rot=(0, yaw, 0))
    mk(S.root, 'cube', (x, 0.82, z), (length, 0.08, 0.08), WOOD, tex('wood'), rot=(0, yaw, 0))

def distant_dunes(S, cx, cz, radius=150.0, count=26, seed=2, col=rgb(60, 46, 44), height=(9.0, 22.0)):
    rg = random.Random(seed)
    for i in range(count):
        a = 2 * math.pi * i / count + rg.uniform(-0.08, 0.08)
        r = radius * rg.uniform(0.95, 1.15)
        hgt = rg.uniform(*height)
        wid = rg.uniform(34.0, 60.0)
        mk(S.root, 'sphere', (cx + math.cos(a) * r, -hgt * 0.35, cz + math.sin(a) * r), (wid, hgt * 1.3, wid * rg.uniform(0.7, 1.1)), shade(col, rg.uniform(0.85, 1.15)), rot=(0, rg.uniform(0, 180), 0))
