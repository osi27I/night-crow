import math
import random
import numpy as np
from panda3d.core import ColorBlendAttrib, Geom, GeomNode, GeomTriangles, GeomVertexArrayFormat, GeomVertexData, GeomVertexFormat, InternalName, OmniBoundingVolume, TransparencyAttrib
from ursina import Entity, Vec3, camera
from engine.assets import tex
from engine.shaders import particle_shader
_QUAD = np.array([(-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5)], dtype=np.float32)
_QUAD_UV = np.array([(0, 0), (1, 0), (0, 1), (1, 1)], dtype=np.float32)
_TRI = np.array([0, 1, 2, 2, 1, 3], dtype=np.uint32)
_VERT_DTYPE = np.dtype([('v', '<f4', 3), ('c', '<f4', 4), ('t', '<f4', 2)])

def _make_format():
    arr = GeomVertexArrayFormat()
    arr.add_column(InternalName.make('vertex'), 3, Geom.NT_float32, Geom.C_point)
    arr.add_column(InternalName.make('color'), 4, Geom.NT_float32, Geom.C_color)
    arr.add_column(InternalName.make('texcoord'), 2, Geom.NT_float32, Geom.C_texcoord)
    fmt = GeomVertexFormat()
    fmt.add_array(arr)
    return GeomVertexFormat.register_format(fmt)

class ParticleBatch:

    def __init__(self, parent, texture, blend, bin_sort):
        self.blend = blend
        self.holder = Entity(parent=parent, shader=particle_shader, add_to_scene_entities=False)
        t = tex(texture)
        if t is not None:
            self.holder.setTexture(t._texture, 1)
        self.holder.setLightOff()
        self.holder.setDepthWrite(False)
        self.holder.setBin('fixed', bin_sort)
        self.holder.setTwoSided(True)
        if blend == 'add':
            self.holder.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha, ColorBlendAttrib.OOne))
        else:
            self.holder.setTransparency(TransparencyAttrib.MAlpha)
        self.sorted = blend != 'add'
        self.fmt = _make_format()
        self.cap = 0
        self.dirty_layout = True
        self.node = None
        self.geom_np = None
        self.alloc = 0
        self._init_arrays(0)

    def _init_arrays(self, n):
        f = np.float32
        self.pos = np.zeros((n, 3), f)
        self.vel = np.zeros((n, 3), f)
        self.age = np.zeros(n, f)
        self.life = np.ones(n, f)
        self.alive = np.zeros(n, bool)
        self.seed = np.zeros(n, f)
        self.ang = np.zeros(n, f)
        self.s0 = np.zeros(n, f)
        self.s1 = np.zeros(n, f)
        self.c0 = np.zeros((n, 4), f)
        self.c1 = np.zeros((n, 4), f)
        self.grav = np.zeros(n, f)
        self.drag = np.zeros(n, f)
        self.turb = np.zeros(n, f)
        self.wind = np.zeros((n, 3), f)
        self.inout = np.zeros(n, bool)
        self.oy = np.zeros(n, f)
        self.spin = np.zeros(n, f)
        self.stretch = np.zeros(n, f)

    def register(self, emitter):
        n = emitter.max_particles
        start = self.alloc
        old = (self.pos, self.vel, self.age, self.life, self.alive, self.seed, self.ang, self.s0, self.s1, self.c0, self.c1, self.grav, self.drag, self.turb, self.wind, self.inout, self.oy, self.spin, self.stretch)
        self._init_arrays(start + n)
        new = (self.pos, self.vel, self.age, self.life, self.alive, self.seed, self.ang, self.s0, self.s1, self.c0, self.c1, self.grav, self.drag, self.turb, self.wind, self.inout, self.oy, self.spin, self.stretch)
        for a, b in zip(old, new):
            b[:start] = a
        self.alloc = start + n
        emitter.batch = self
        emitter.sl = slice(start, start + n)
        emitter.apply_params()
        self.seed[emitter.sl] = np.random.rand(n).astype(np.float32) * 100.0
        self.dirty_layout = True

    def _rebuild(self):
        if self.geom_np is not None:
            self.geom_np.removeNode()
            self.geom_np = None
        n = self.alloc
        self.cap = n
        if n == 0:
            self.dirty_layout = False
            return
        self.vdata = GeomVertexData('particles', self.fmt, Geom.UH_dynamic)
        self.vdata.unclean_set_num_rows(n * 4)
        self.buf = np.zeros(n * 4, _VERT_DTYPE)
        self.buf['t'] = np.tile(_QUAD_UV, (n, 1))
        self.prim = GeomTriangles(Geom.UH_dynamic)
        self.prim.set_index_type(Geom.NT_uint32)
        self.idx_base = (np.arange(n, dtype=np.uint32)[:, None] * 4 + _TRI[None, :]).reshape(-1)
        self.prim.modify_vertices().modify_handle().set_data(self.idx_base.tobytes())
        geom = Geom(self.vdata)
        geom.add_primitive(self.prim)
        self.node = GeomNode('particle_batch')
        self.node.add_geom(geom)
        self.node.set_bounds(OmniBoundingVolume())
        self.node.set_final(True)
        self.geom_np = self.holder.attachNewNode(self.node)
        self.dirty_layout = False

    def simulate(self, dt, sl=slice(None)):
        al = self.alive[sl]
        if not al.any():
            return
        age = self.age[sl]
        age += dt * al
        life = self.life[sl]
        dead = al & (age >= life)
        if dead.any():
            al[dead] = False
            self.alive[sl] = al
        vel = self.vel[sl]
        pos = self.pos[sl]
        vel[:, 1] += self.grav[sl] * dt
        d = self.drag[sl]
        if d.any():
            vel *= np.maximum(0.0, 1.0 - d * dt)[:, None]
        tb = self.turb[sl]
        if tb.any():
            k = tb * dt
            sd = self.seed[sl]
            vel[:, 0] += np.sin(sd + age * 3.1) * k
            vel[:, 2] += np.cos(sd * 1.3 + age * 2.7) * k
            vel[:, 1] += np.sin(sd * 0.7 + age * 4.3) * k * 0.4
        pos += (vel + self.wind[sl]) * dt * al[:, None]
        self.ang[sl] += self.spin[sl] * dt

    def build_and_upload(self):
        if self.dirty_layout:
            self._rebuild()
        n = self.cap
        if n == 0:
            return
        al = self.alive
        t = np.clip(self.age / np.maximum(self.life, 0.0001), 0.0, 1.0)
        size = (self.s0 + (self.s1 - self.s0) * t) * al
        col = self.c0 + (self.c1 - self.c0) * t[:, None]
        if self.inout.any():
            col[:, 3] *= np.where(self.inout, np.maximum(np.sin(np.pi * t), 0.0) ** 0.6, 1.0)
        col[:, 3] *= al
        right = np.array(tuple(camera.right), np.float32)
        up = np.array(tuple(camera.up), np.float32)
        if self.stretch.any():
            vx = self.vel @ right
            vy = self.vel @ up
            sp = np.sqrt(vx * vx + vy * vy) + 1e-05
            ux, uy = (vx / sp, vy / sp)
            R = right[None, :] * ux[:, None] + up[None, :] * uy[:, None]
            U = -right[None, :] * uy[:, None] + up[None, :] * ux[:, None]
            stretch = (1.0 + self.stretch * np.minimum(sp, 8.0))[:, None, None]
            along = R[:, None, :] * (_QUAD[None, :, 1:2] * size[:, None, None] * stretch)
            across = U[:, None, :] * (_QUAD[None, :, 0:1] * size[:, None, None])
            mixed = (self.stretch > 0)[:, None, None]
        ca, sa = (np.cos(self.ang)[:, None], np.sin(self.ang)[:, None])
        Rb = right[None, :] * ca + up[None, :] * sa
        Ub = -right[None, :] * sa + up[None, :] * ca
        qx = _QUAD[None, :, 0:1] * size[:, None, None]
        qy = (_QUAD[None, :, 1:2] - self.oy[:, None, None]) * size[:, None, None]
        corners = Rb[:, None, :] * qx + Ub[:, None, :] * qy
        if self.stretch.any():
            corners = np.where(mixed, along + across, corners)
        corners = corners + self.pos[:, None, :]
        v = self.buf['v'].reshape(n, 4, 3)
        v[...] = corners
        self.buf['c'] = np.repeat(col, 4, axis=0)
        self.vdata.modify_array(0).modify_handle().set_data(self.buf.tobytes())
        if self.sorted:
            cam = np.array(tuple(camera.world_position), np.float32)
            depth = ((self.pos - cam) ** 2).sum(axis=1)
            order = np.argsort(-depth).astype(np.uint32)
            idx = (order[:, None] * 4 + _TRI[None, :]).reshape(-1)
            self.prim.modify_vertices().modify_handle().set_data(idx.tobytes())

class Emitter:
    quality = 1.0

    def __init__(self, parent, pos, rate=20.0, max_particles=40, life=(0.8, 1.4), speed=(0.5, 1.0), direction=(0, 1, 0), spread=0.3, size=(0.4, 0.1), color0=(1, 0.6, 0.2, 1.0), color1=(1, 0.2, 0.0, 0.0), gravity=0.0, drag=0.0, texture='glow', blend='add', area=(0, 0, 0), turbulence=0.0, wind=(0, 0, 0), origin_y=0.0, in_out=False, bin_sort=40, spin=0.0, stretch=0.0):
        self.parent = parent
        self.pos = Vec3(*pos)
        self.rate = rate
        self.max_particles = max_particles
        self.life, self.speed = (life, speed)
        self.direction = Vec3(*direction).normalized()
        self.spread = spread
        self.size = size
        self.color0, self.color1 = (tuple(color0), tuple(color1))
        self.gravity, self.drag = (gravity, drag)
        self.area = area
        self.turbulence = turbulence
        self.wind = Vec3(*wind)
        self.in_out = in_out
        self.origin_y = origin_y
        self.spin = spin
        self.stretch = stretch
        self.texture, self.blend, self.bin_sort = (texture, blend, bin_sort)
        self.enabled = True
        self.cull = True
        self.culled = False
        self._acc = 0.0
        self.batch = None
        self.sl = None

    def apply_params(self):
        b, sl = (self.batch, self.sl)
        b.s0[sl], b.s1[sl] = self.size
        b.c0[sl] = self.color0
        b.c1[sl] = self.color1
        b.grav[sl] = self.gravity
        b.drag[sl] = self.drag
        b.turb[sl] = self.turbulence
        b.wind[sl] = (self.wind.x, self.wind.y, self.wind.z)
        b.inout[sl] = self.in_out
        b.oy[sl] = self.origin_y
        b.stretch[sl] = self.stretch

    def burst(self, count):
        b = self.batch
        if b is None:
            return
        al = b.alive[self.sl]
        free = np.flatnonzero(~al)
        k = min(int(count), len(free))
        if k <= 0:
            return
        idx = free[:k] + self.sl.start
        ax, ay, az = self.area
        rnd = np.random.rand
        b.pos[idx] = np.stack([self.pos.x + (rnd(k) * 2 - 1) * ax, self.pos.y + (rnd(k) * 2 - 1) * ay, self.pos.z + (rnd(k) * 2 - 1) * az], axis=1)
        d = np.array((self.direction.x, self.direction.y, self.direction.z), np.float32)[None, :] + (np.stack([rnd(k), rnd(k), rnd(k)], axis=1) * 2 - 1) * self.spread
        ln = np.linalg.norm(d, axis=1, keepdims=True)
        d = np.where(ln > 1e-05, d / np.maximum(ln, 1e-05), np.array(self.direction, np.float32)[None, :])
        sp = self.speed[0] + rnd(k) * (self.speed[1] - self.speed[0])
        b.vel[idx] = d * sp[:, None]
        b.life[idx] = self.life[0] + rnd(k) * (self.life[1] - self.life[0])
        b.age[idx] = 0.0
        b.alive[idx] = True
        if self.spin:
            b.ang[idx] = rnd(k) * 6.2832
            b.spin[idx] = (rnd(k) * 2 - 1) * math.radians(self.spin)
        else:
            b.ang[idx] = 0.0
            b.spin[idx] = 0.0

    def _spawn_tick(self, dt):
        if self.enabled and self.rate > 0:
            self._acc += self.rate * Emitter.quality * dt
            n = int(self._acc)
            if n:
                self._acc -= n
                self.burst(n)

    def prewarm(self, seconds=2.0, step=0.1):
        if self.batch is None:
            return
        t = 0.0
        while t < seconds:
            self._spawn_tick(step)
            self.batch.simulate(step, self.sl)
            t += step

    def update(self, dt):
        self._spawn_tick(dt)
        if self.batch is not None:
            self.batch.simulate(dt, self.sl)

    def clear(self):
        if self.batch is not None:
            self.batch.alive[self.sl] = False

    def set_color(self, color0, color1=None):
        self.color0 = tuple(color0)
        if color1 is not None:
            self.color1 = tuple(color1)
        if self.batch is not None:
            self.apply_params()

class ParticleSystem:

    def __init__(self, parent):
        self.parent = parent
        self.emitters = []
        self.batches = {}

    def add(self, emitter):
        key = (emitter.texture, emitter.blend, emitter.bin_sort)
        batch = self.batches.get(key)
        if batch is None:
            batch = self.batches[key] = ParticleBatch(self.parent, *key)
        batch.register(emitter)
        self.emitters.append(emitter)
        return emitter
    cull_distance = 30.0

    def update(self, dt, focus=None):
        for e in self.emitters:
            if focus is not None and e.cull:
                d = math.hypot(e.pos.x - focus.x, e.pos.z - focus.z)
                if d > self.cull_distance:
                    if not e.culled:
                        e.clear()
                        e.culled = True
                    continue
                if e.culled:
                    e.culled = False
                    e.prewarm(0.6)
            e._spawn_tick(dt)
        for b in self.batches.values():
            b.simulate(dt)
            b.build_and_upload()

    def fire(self, pos, scale=1.0, intensity=1.0):
        a = (0.1 * scale, 0, 0.1 * scale)
        outer = Emitter(self.parent, pos, rate=11 * intensity, max_particles=int(18 * max(1, intensity)), life=(0.6, 1.1), speed=(0.35 * scale, 1.0 * scale), direction=(0, 1, 0), spread=0.22, size=(1.25 * scale, 0.16 * scale), color0=(1.0, 0.42, 0.08, 0.8), color1=(0.55, 0.06, 0.02, 0.0), texture='flame', blend='add', turbulence=2.2, origin_y=-0.4, area=(0.14 * scale, 0, 0.14 * scale))
        body = Emitter(self.parent, pos, rate=15 * intensity, max_particles=int(20 * max(1, intensity)), life=(0.45, 0.85), speed=(0.5 * scale, 1.3 * scale), direction=(0, 1, 0), spread=0.14, size=(1.0 * scale, 0.2 * scale), color0=(1.0, 0.82, 0.38, 0.95), color1=(1.0, 0.25, 0.05, 0.0), texture='flame', blend='add', turbulence=1.6, origin_y=-0.4, area=a)
        core = Emitter(self.parent, (pos[0], pos[1] + 0.02 * scale, pos[2]), rate=9 * intensity, max_particles=int(12 * max(1, intensity)), life=(0.28, 0.55), speed=(0.45 * scale, 1.1 * scale), direction=(0, 1, 0), spread=0.08, size=(0.55 * scale, 0.1 * scale), color0=(1.0, 1.0, 0.88, 1.0), color1=(1.0, 0.72, 0.22, 0.0), texture='flame', blend='add', turbulence=0.9, origin_y=-0.35, area=(0.04 * scale, 0, 0.04 * scale))
        halo = Emitter(self.parent, (pos[0], pos[1] + 0.25 * scale, pos[2]), rate=5, max_particles=6, life=(0.5, 0.8), speed=(0.1, 0.3), spread=0.2, size=(2.1 * scale, 0.6 * scale), color0=(1.0, 0.55, 0.2, 0.42), color1=(1.0, 0.3, 0.05, 0.0), texture='glow', blend='add')
        sparks = Emitter(self.parent, (pos[0], pos[1] + 0.3 * scale, pos[2]), rate=3.0 * intensity, max_particles=10, life=(0.7, 1.5), speed=(0.9 * scale, 2.2 * scale), direction=(0, 1, 0), spread=0.7, size=(0.06 * scale, 0.015 * scale), color0=(1.0, 0.85, 0.4, 1.0), color1=(1.0, 0.3, 0.05, 0.0), texture='glow', blend='add', turbulence=3.2, gravity=-0.2, area=a, stretch=0.1)
        out = [outer, body, core, halo, sparks]
        for e in out:
            self.add(e)
            e.prewarm(0.9)
        return out

    def embers(self, pos, scale=1.0, rate=7, area=(0.2, 0, 0.2)):
        e = Emitter(self.parent, pos, rate=rate, max_particles=30, life=(1.2, 2.6), speed=(0.6 * scale, 1.8 * scale), direction=(0, 1, 0), spread=0.55, size=(0.13 * scale, 0.03 * scale), color0=(1.0, 0.65, 0.22, 1.0), color1=(1.0, 0.2, 0.0, 0.0), turbulence=3.0, area=area, gravity=-0.1, stretch=0.12)
        self.add(e)
        e.prewarm(1.5)
        return e

    def smoke(self, pos, scale=1.0, rate=4, tone=0.24, alpha=0.5, wind=(0.25, 0, 0.05)):
        e = Emitter(self.parent, pos, rate=rate, max_particles=int(14 + rate * 3), life=(2.2, 3.8), speed=(0.5, 1.0), direction=(0, 1, 0), spread=0.2, size=(0.8 * scale, 3.2 * scale), color0=(tone, tone * 0.92, tone * 0.9, alpha), color1=(tone * 0.5, tone * 0.5, tone * 0.5, 0.0), texture='smoke', blend='alpha', turbulence=1.4, wind=wind, bin_sort=30, spin=40)
        self.add(e)
        e.prewarm(3.0)
        return e

    def steam(self, pos, scale=1.0, rate=7):
        e = Emitter(self.parent, pos, rate=rate, max_particles=20, life=(1.1, 1.9), speed=(0.25, 0.5), direction=(0, 1, 0), spread=0.25, size=(0.14 * scale, 0.6 * scale), color0=(1, 1, 1, 0.3), color1=(1, 1, 1, 0.0), texture='smoke', blend='alpha', turbulence=0.8, bin_sort=35, spin=30)
        self.add(e)
        e.prewarm(1.5)
        return e

    def dust(self, center, area=(18, 3, 18), count=50, color=(1.0, 0.88, 0.62), alpha=0.5, size=0.12, wind=(0.5, 0.0, 0.1)):
        e = Emitter(self.parent, center, rate=count / 6.0, max_particles=count, life=(5.0, 9.0), speed=(0.05, 0.3), direction=(1, 0.1, 0.2), spread=1.0, size=(size, size * 0.8), color0=(*color, alpha), color1=(*color, 0.0), area=area, turbulence=0.9, wind=wind, in_out=True)
        e.cull = False
        self.add(e)
        e.prewarm(7.0)
        return e

    def fireflies(self, center, area=(18, 1.5, 18), count=22, color=(0.82, 1.0, 0.45)):
        e = Emitter(self.parent, center, rate=count / 5.0, max_particles=count, life=(4.0, 7.0), speed=(0.15, 0.5), direction=(0, 0.2, 0), spread=1.0, size=(0.34, 0.3), color0=(*color, 0.95), color1=(*color, 0.0), area=area, turbulence=2.2, in_out=True)
        e.cull = False
        self.add(e)
        e.prewarm(6.0)
        return e

    def _pooled_emitter(self, key, factory, pos):
        pool = self.__dict__.setdefault('_pooled', {})
        e = pool.get(key)
        if e is None:
            e = factory()
            e.cull = False
            self.add(e)
            pool[key] = e
        e.pos = Vec3(*pos)
        return e

    def sparks(self, pos, count=14, color0=(1.0, 0.85, 0.4, 1.0), color1=(1.0, 0.3, 0.0, 0.0)):
        e = self._pooled_emitter(('sparks', color0, color1), lambda: Emitter(self.parent, pos, rate=0, max_particles=48, life=(0.3, 0.7), speed=(2.5, 6.0), direction=(0, 0.6, 0), spread=1.3, size=(0.16, 0.03), color0=color0, color1=color1, gravity=-9.0, drag=1.2, stretch=0.28), pos)
        e.burst(count)
        return e

    def magic(self, pos, color=(1.0, 0.8, 0.35), count=24, texture='glow', size=(0.3, 0.05)):
        e = self._pooled_emitter(('magic', color, texture, size), lambda: Emitter(self.parent, pos, rate=0, max_particles=64, life=(0.8, 1.6), speed=(0.8, 2.4), direction=(0, 0.4, 0), spread=1.6, size=size, color0=(*color, 1.0), color1=(*color, 0.0), turbulence=2.0, drag=1.0, texture=texture), pos)
        e.burst(count)
        return e

    def blood_free_hit(self, pos):
        self.sparks(pos, 10)
        self.dust_puff(pos, 8)

    def dust_puff(self, pos, count=6, color=(0.75, 0.66, 0.5)):
        e = self._pooled_emitter(('puff', color), lambda: Emitter(self.parent, pos, rate=0, max_particles=48, life=(0.5, 1.0), speed=(0.4, 1.2), direction=(0, 0.3, 0), spread=1.0, size=(0.25, 0.9), color0=(*color, 0.42), color1=(*color, 0.0), texture='smoke', blend='alpha', drag=1.6, bin_sort=33, spin=60), pos)
        e.burst(count)
        return e
