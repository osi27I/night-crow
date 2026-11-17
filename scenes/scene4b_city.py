import math
import random
from ursina import Entity, Vec3, destroy
from engine.assets import tex
from engine.crow import Abilities, RoofNet, ladder_model
from engine.entities import mk, rgb, shade
from engine.particles import Emitter
from engine.props import Sky, arch_gate, banner, barrel, brazier, contact_shadow, crate, ground, ground_patches, hay, moon, palm, planets, pillar, wall_box, wall_line
from engine.scene_base import BaseScene
from engine.timing import Clock, ease_in, ease_in_out, ease_out
from scenes.scene4_crow import CROW_LOOK, ELITE, LEGION, Scene4Crow
START = (-19.0, -2.6)
WALL_X = 23.8
ARCHER = dict(robe=rgb(86, 66, 52), trim=rgb(204, 170, 92), head='cap', head_color=rgb(120, 88, 58), weapon='bow', skin='tan', cloak=rgb(58, 44, 40))
MERCHANT = dict(robe=rgb(150, 108, 60), trim=rgb(220, 190, 110), head='cap', head_color=rgb(110, 70, 44), skin='tan', build='broad')
CITIZEN = dict(robe=rgb(96, 110, 150), trim=rgb(200, 190, 150), head='scarf', head_color=rgb(150, 140, 120), skin='olive')
ZONES = {'A': (-23.2, 23.2, -4.5, 27.0), 'B': (-23.2, 23.2, 27.0, 58.6), 'C': (-23.2, 23.2, 58.6, 85.0), 'D': (-23.2, 23.2, 85.0, 98.0)}
PLASTERS = [rgb(188, 176, 168), rgb(172, 164, 176), rgb(196, 178, 160), rgb(164, 170, 182), rgb(184, 168, 170)]

class Scene4bCity(Scene4Crow):
    number = 5
    name = 'The Night Crow  -  Mission II: The Rooftops of Antioch'
    author = 'Group'
    zones = ZONES

    def build(self):
        g = self.game
        self.phase = 'intro'
        self.checkpoint = START
        self._cp_seen = {START}
        self.starts = []
        self.snuffables = []
        self.bodies = []
        self.caw_cd = 0.0
        self.kills = 0
        self.ui = []
        self.varro = self.varro_it = None
        self._eaves_done = False
        self._roof_hint = False
        self.rnd = random.Random(77)
        rig = self.rig
        rig.ambient = Vec3(0.13, 0.15, 0.27)
        rig.sun_color = Vec3(0.24, 0.3, 0.52)
        rig.sun_dir = Vec3(-0.4, 0.8, -0.3)
        rig.fog_color = Vec3(0.035, 0.045, 0.1)
        rig.fog_density = 0.011
        g.post.set(vignette=0.5, bloom=1.0, tint=(0.92, 0.96, 1.08), grain=0.05, desat=0.0)
        self.cam.pitch, self.cam.distance = (51, 13.0)
        self.cam.set_fov(66)
        self.stealth_light = True
        self.bounds = None
        self.sky = Sky(self, 'sky_night', stars=True)
        moon(self, pos=(-80, 82, 160), size=44)
        planets(self, ringed=(135, 58, 160), red=(-140, 92, 130))
        self.nav = RoofNet(self)
        self._build_ground()
        self._build_blocks()
        self._build_market()
        self._build_villa()
        self._build_far_city()
        self._build_people()
        self._build_lanterns()
        self._build_abilities_city()
        for x in (0.0, -19.0, 19.0):
            self.trigger(x, 27.4, 7.0, 1.2, lambda x=x: self._checkpoint((x, 26.2)))
            self.trigger(x, 59.0, 7.0, 1.2, lambda x=x: self._checkpoint((x, 58.0)))
            self.trigger(x, 85.4, 7.0, 1.2, lambda x=x: self._checkpoint((x, 84.4)))
        self.trigger(0.0, 31.0, 8.0, 1.4, self.eavesdrop)
        self.trigger(-19.0, 31.0, 8.0, 1.4, self.eavesdrop)
        self.trigger(0.0, 61.0, 8.0, 1.4, lambda: self.abil.hint_once('archers', 'Lantern Row: archers on the east roofs look across the whole street. Keep to the west roofs or blind them with smoke.', hold=7))
        self.wall_it = self.interact(-9.6, 96.6, 'Throw the grapple', self.on_wall, radius=2.0, once=False)
        self.wall_it.enabled = False
        g.audio.music('mus_crow', 0.5, fade=3.0)
        g.audio.loop('amb_wind', 0.26, fade=3.0)

    def _build_ground(self):
        self.ground = ground(self, 300, 'stone_dark', 150, rgb(104, 108, 136))
        ground_patches(self, -23, -5, 23, 100, count=110, seed=21, palette=[rgb(60, 64, 88), rgb(88, 90, 112), rgb(48, 52, 74)], alpha=(0.25, 0.5), size=(2, 7))
        mk(self.root, 'plane', (0, 0.012, 40.0), (7.0, 1, 98.0), rgb(150, 152, 178), tex('stone'), tex_scale=(3, 36))
        mk(self.root, 'plane', (13.0, 0.014, 43.0), (20.0, 1, 30.0), rgb(146, 146, 172), tex('stone'), tex_scale=(8, 12))
        mk(self.root, 'plane', (0, 0.014, 91.0), (46.0, 1, 14.0), rgb(150, 148, 170), tex('stone'), tex_scale=(18, 6))
        for sx in (-1, 1):
            wall_line(self, sx * (WALL_X + 0.6), -5.0, sx * (WALL_X + 0.6), 100.0, 5.0, 1.2, 'stone', rgb(140, 142, 164))
        wall_line(self, -24.5, -5.4, 24.5, -5.4, 5.0, 1.2, 'stone', rgb(140, 142, 164))
        for z in range(0, 100, 14):
            for sx in (-1, 1):
                wall_box(self, sx * (WALL_X + 0.6), z + 3.0, 2.2, 2.2, 7.0, 'stone', rgb(130, 132, 154))

    def facade(self, x0, x1, z0, z1, h, lit=0.4, doors=()):
        rnd = self.rnd
        rows = [1.9] if h < 4.0 else [1.6, 3.2]
        faces = (('s', z0 - 0.03, x0, x1, False), ('n', z1 + 0.03, x0, x1, False), ('w', x0 - 0.03, z0, z1, True), ('e', x1 + 0.03, z0, z1, True))
        for name, fixed, a0, a1, along_z in faces:
            length = a1 - a0
            n = int((length - 1.4) // 2.7)
            if n <= 0:
                continue
            start = a0 + (length - (n - 1) * 2.7) / 2.0
            for i in range(n):
                u = start + i * 2.7
                if name in doors and i == n // 2:
                    self._door(name, fixed, u)
                    continue
                for ry in rows:
                    on = rnd.random() < lit
                    col = rgb(255, 190, 100) if on else rgb(26, 32, 56)
                    sx_, sz_ = (0.08, 0.0) if along_z else (0.0, 0.08)
                    pos = (fixed, ry, u) if along_z else (u, ry, fixed)
                    size = (0.1, 1.0, 0.78) if along_z else (0.78, 1.0, 0.1)
                    mk(self.root, 'cube', pos, size, col, emissive=0.9 if on else 0.0)
                    fsize = (0.06, 1.18, 0.96) if along_z else (0.96, 1.18, 0.06)
                    fpos = (fixed - (0.02 if name == 'w' else -0.02 if name == 'e' else 0), ry, u) if along_z else (u, ry, fixed - (0.02 if name == 's' else -0.02))
                    mk(self.root, 'cube', fpos, fsize, rgb(78, 56, 40))

    def _door(self, name, fixed, u):
        along_z = name in ('w', 'e')
        size = (0.16, 2.3, 1.3) if along_z else (1.3, 2.3, 0.16)
        pos = (fixed, 1.15, u) if along_z else (u, 1.15, fixed)
        mk(self.root, 'cube', pos, size, rgb(92, 64, 42), tex('wood'))
        fs = (0.12, 2.5, 1.6) if along_z else (1.6, 2.5, 0.12)
        mk(self.root, 'cube', (pos[0] - (0.02 if name == 'w' else -0.02 if name == 'e' else 0), 1.25, pos[2] - (0.02 if name == 's' else -0.02 if name == 'n' else 0)), fs, rgb(60, 44, 32))

    def block(self, x0, x1, z0, z1, h, col, lit=0.4, doors=('e',), roof_col=None, walk=True):
        rnd = self.rnd
        cx, cz, w, d = ((x0 + x1) / 2.0, (z0 + z1) / 2.0, x1 - x0, z1 - z0)
        wall_box(self, cx, cz, w, d, h, 'plaster', col, tile=3.2)
        top = h + 0.28
        rc = roof_col or rgb(150, 104, 90)
        mk(self.root, 'cube', (cx, h + 0.14, cz), (w + 0.4, 0.28, d + 0.4), rc, tex('stone_dark'), tex_scale=(w / 3.0, d / 3.0))
        pc = shade(col, 0.85)
        for px, pz, sx, sz in ((cx, z0 - 0.1, w + 0.4, 0.22), (cx, z1 + 0.1, w + 0.4, 0.22), (x0 - 0.1, cz, 0.22, d), (x1 + 0.1, cz, 0.22, d)):
            mk(self.root, 'cube', (px, top + 0.2, pz), (sx, 0.4, sz), pc, tex('stone'))
        self.facade(x0, x1, z0, z1, h, lit=lit, doors=doors)
        for _ in range(int(w * d / 22)):
            px, pz = (rnd.uniform(x0 + 1.2, x1 - 1.2), rnd.uniform(z0 + 1.2, z1 - 1.2))
            k = rnd.random()
            if k < 0.4:
                mk(self.root, 'cylinder', (px, top, pz), (0.5, 0.55, 0.5), rgb(170, 100, 62), tex('tile'))
            elif k < 0.7:
                mk(self.root, 'cube', (px, top + 0.04, pz), (rnd.uniform(1.2, 2.0), 0.08, rnd.uniform(0.9, 1.4)), rnd.choice([rgb(150, 60, 56), rgb(70, 90, 140), rgb(190, 170, 120)]), rot=(0, rnd.uniform(0, 90), 0))
            else:
                mk(self.root, 'cube', (px, top + 0.1, pz), (0.9, 0.2, 0.9), rgb(96, 70, 48), tex('wood'))
        mk(self.root, 'cube', (x1 - 0.7, top + 0.7, z1 - 0.7), (0.7, 1.4, 0.7), shade(col, 0.8), tex('stone'))
        if walk:
            self.nav.add_roof(cx, cz, w, d, top)
        return top

    def ladder(self, side, x0, x1, z0, z1, h, off=0.0):
        top = h + 0.28
        cx, cz = ((x0 + x1) / 2.0, (z0 + z1) / 2.0)
        if side == 'w':
            gx, gz, rx, rz, yaw = (x0 - 0.5, cz + off, x0 + 1.2, cz + off, 90)
        elif side == 'e':
            gx, gz, rx, rz, yaw = (x1 + 0.5, cz + off, x1 - 1.2, cz + off, -90)
        elif side == 's':
            gx, gz, rx, rz, yaw = (cx + off, z0 - 0.5, cx + off, z0 + 1.2, 0)
        else:
            gx, gz, rx, rz, yaw = (cx + off, z1 + 0.5, cx + off, z1 - 1.2, 180)
        ladder_model(self.root, gx, gz, top + 0.3, yaw)
        gx2 = gx + (-0.55 if side == 'w' else 0.55 if side == 'e' else 0.0)
        gz2 = gz + (-0.55 if side == 's' else 0.55 if side == 'n' else 0.0)
        self.nav.add_ladder(gx2, gz2, rx, rz, top)

    def _build_blocks(self):
        P = PLASTERS
        W0, W1, E0, E1 = (-15.0, -3.5, 3.5, 15.0)
        self.block(W0, W1, -2.0, 9.0, 3.6, P[0])
        self.block(W0, W1, 12.2, 24.0, 4.2, P[1])
        self.block(W0, W1, 27.2, 40.0, 3.7, P[2])
        self.block(W0, W1, 43.2, 57.0, 4.4, P[3])
        self.block(W0, W1, 60.2, 70.0, 3.8, P[4])
        self.block(W0, W1, 73.2, 84.0, 4.2, P[0])
        self.block(E0, E1, -2.0, 9.0, 3.8, P[2], doors=('w',))
        self.block(E0, E1, 12.2, 24.0, 3.5, P[3], doors=('w',))
        self.block(E0, E1, 60.2, 70.0, 3.9, P[1], doors=('w',))
        self.block(E0, E1, 73.2, 84.0, 4.4, P[4], doors=('w',))
        self.ladder('w', W0, W1, -2.0, 9.0, 3.6, off=0.0)
        self.ladder('w', W0, W1, 27.2, 40.0, 3.7, off=-2.0)
        self.ladder('w', W0, W1, 60.2, 70.0, 3.8, off=0.0)
        self.ladder('e', E0, E1, 12.2, 24.0, 3.5, off=-3.0)
        for z in (10.6, 25.6, 41.6, 58.6, 71.6):
            for k in range(2):
                x = -13.0 + k * 6.5
                mk(self.root, 'cube', (x, 3.0, z), (0.03, 0.03, 3.2), rgb(120, 100, 80))
                for j in range(3):
                    mk(self.root, 'cube', (x, 2.7, z - 1.0 + j * 1.0), (0.04, 0.55, 0.55), self.rnd.choice([rgb(190, 70, 60), rgb(220, 210, 190), rgb(70, 100, 160)]))
        for z in (10.6, 25.6, 41.6, 58.6, 71.6):
            barrel(self, -4.2, z - 0.8)
            crate(self, -4.3, z + 0.9, 0.8, rot=self.rnd.uniform(-20, 20))
            crate(self, -14.4, z + 0.5, 0.7, rot=self.rnd.uniform(-20, 20))

    def stall(self, x, z, rot=0, col=rgb(160, 60, 54), goods=True):
        yaw = math.radians(rot)
        c, s = (math.cos(yaw), math.sin(yaw))
        w, d = (3.0, 1.3) if rot % 180 == 0 else (1.3, 3.0)
        wall_box(self, x, z, w, d, 1.05, 'wood', rgb(150, 112, 80), tile=1.4)
        for sx in (-1, 1):
            px, pz = (x + c * sx * 1.4, z - s * sx * 1.4)
            mk(self.root, 'cylinder', (px, 0, pz), (0.12, 2.3, 0.12), rgb(80, 56, 40))
        mk(self.root, 'cube', (x, 2.35, z), (3.4 if rot % 180 == 0 else 1.9, 0.1, 1.9 if rot % 180 == 0 else 3.4), col, rot=(0, 0, 0))
        mk(self.root, 'cube', (x, 2.2, z), (3.4 if rot % 180 == 0 else 1.9, 0.08, 1.9 if rot % 180 == 0 else 3.4), shade(col, 0.7))
        if goods:
            for i in range(5):
                gx = (i - 2) * 0.5
                mk(self.root, 'sphere', (x + c * gx, 1.18, z - s * gx), 0.28, self.rnd.choice([rgb(200, 70, 50), rgb(220, 170, 60), rgb(110, 150, 70)]))
        contact_shadow(self, x, z, w + 1.4, d + 1.4, 0.45)

    def _build_market(self):
        for x, z, rot, col in ((8.0, 34.0, 0, rgb(160, 60, 54)), (17.5, 34.0, 0, rgb(60, 90, 150)), (21.4, 40.0, 90, rgb(190, 150, 60)), (8.0, 51.0, 0, rgb(80, 130, 90)), (17.5, 52.0, 0, rgb(160, 60, 54)), (21.4, 46.0, 90, rgb(60, 90, 150)), (6.2, 44.0, 90, rgb(190, 150, 60))):
            self.stall(x, z, rot, col)
        fx, fz = (14.0, 43.0)
        stone = rgb(170, 172, 190)
        mk(self.root, 'cylinder', (fx, 0, fz), (4.4, 0.5, 4.4), shade(stone, 0.8), tex('stone'))
        mk(self.root, 'cylinder', (fx, 0.5, fz), (3.9, 0.04, 3.9), rgb(70, 125, 185), emissive=0.5)
        for k in range(14):
            a = k * math.tau / 14
            mk(self.root, 'cube', (fx + math.cos(a) * 2.2, 0.4, fz + math.sin(a) * 2.2), (0.9, 0.8, 0.5), stone, tex('stone'), rot=(0, -math.degrees(a) + 90, 0))
        mk(self.root, 'cylinder', (fx, 0.4, fz), (0.55, 2.0, 0.55), stone, tex('stone'))
        mk(self.root, 'cylinder', (fx, 2.2, fz), (1.7, 0.22, 1.7), stone, tex('stone'))
        self.world.add_circle(fx, fz, 2.3)
        jet = Emitter(self.root, (fx, 2.45, fz), rate=26, max_particles=70, life=(0.9, 1.3), speed=(1.4, 2.2), direction=(0, 1, 0), spread=0.55, size=(0.16, 0.05), color0=(0.7, 0.86, 1.0, 0.85), color1=(0.5, 0.7, 1.0, 0.0), gravity=-5.0, texture='glow', blend='add')
        jet.cull = False
        self.fx.add(jet)
        self.fx.steam((fx, 0.9, fz), scale=0.8, rate=3)
        for sx in (-1, 1):
            hay(self, 19.5 + sx * 0.0, 29.5 + (0 if sx < 0 else 0.0), 1.0)
            break
        for x, z in ((22.2, 31.0), (22.2, 56.0), (5.0, 56.2)):
            crate(self, x, z, 0.9, rot=self.rnd.uniform(-25, 25))
            barrel(self, x + 0.9, z + 0.3)
        mk(self.root, 'cube', (2.6, 1.2, 56.0), (0.1, 2.4, 0.1), rgb(80, 56, 40))
        mk(self.root, 'cube', (2.6, 1.9, 56.0), (1.3, 0.9, 0.08), rgb(214, 196, 150))
        self.world.add_box(2.6, 56.0, 0.5, 0.5, blocks_sight=False)
        for z in (6.0, 20.0, 36.0, 64.0, 80.0):
            banner(self, -3.45, 3.0, z, 'roman', height=2.5, face='east')
            banner(self, 3.45, 3.0, z + 2.0, 'roman', height=2.5, face='west')

    def _build_villa(self):
        stone = rgb(150, 152, 176)
        wall_line(self, -24.5, 99.6, -4.6, 99.6, 6.0, 1.6, 'stone', stone)
        wall_line(self, 4.6, 99.6, 24.5, 99.6, 6.0, 1.6, 'stone', stone)
        arch_gate(self, 0.0, 99.6, width=9.4, h=5.6, depth=1.8, gap=3.6, col=stone)
        self.gate_doors = []
        for sx in (-1, 1):
            d = Entity(parent=self.root, position=(sx * 1.8, 0, 99.4), add_to_scene_entities=False)
            mk(d, 'cube', (-sx * 0.9, 1.6, 0), (1.8, 3.2, 0.25), rgb(96, 66, 44), tex('wood'), tex_scale=(1, 2))
            mk(d, 'cube', (-sx * 0.9, 1.6, -0.15), (1.9, 0.18, 0.1), rgb(60, 56, 60))
            mk(d, 'cube', (-sx * 0.9, 2.4, -0.15), (1.9, 0.18, 0.1), rgb(60, 56, 60))
            self.gate_doors.append(d)
        self.world.add_box(0, 99.4, 3.6, 0.5)
        for sx in (-1, 1):
            brazier(self, sx * 5.8, 97.2, scale=0.9, intensity=1.9, radius=10.5)
            brazier(self, sx * 12.0, 88.0, scale=0.8, intensity=1.7, radius=10.0)
            brazier(self, sx * 12.0, 95.0, scale=0.8, intensity=1.7, radius=10.0)
            banner(self, sx * 3.7, 3.2, 98.45, 'roman', height=3.4, face='south')
        for i in range(10):
            mk(self.root, 'sphere', (-9.6 + self.rnd.uniform(-1.0, 1.0), 0.4 + i * 0.55, 98.6), (0.8, 0.5, 0.3), rgb(40, 78, 50) if i % 2 else rgb(50, 94, 56))
        bronze = rgb(150, 116, 70)
        mk(self.root, 'cube', (0, 0.8, 90.5), (2.4, 1.6, 2.4), stone, tex('stone'))
        mk(self.root, 'cube', (0, 1.7, 90.5), (2.7, 0.2, 2.7), shade(stone, 1.1))
        for sx in (-1, 1):
            mk(self.root, 'cylinder', (sx * 0.3, 1.8, 90.5), (0.34, 1.3, 0.34), bronze, emissive=0.12)
        mk(self.root, 'cube', (0, 3.4, 90.5), (1.0, 1.2, 0.55), bronze, emissive=0.12)
        mk(self.root, 'sphere', (0, 4.3, 90.5), 0.5, bronze, emissive=0.12)
        mk(self.root, 'cone', (0, 4.5, 90.5), (0.42, 0.4, 0.42), rgb(200, 60, 50))
        mk(self.root, 'cylinder', (0.9, 1.8, 90.5), (0.07, 3.6, 0.07), rgb(110, 80, 50))
        self.world.add_box(0, 90.5, 2.5, 2.5)
        marble = rgb(214, 206, 204)
        mk(self.root, 'cube', (0, 4.0, 124.0), (50.0, 8.0, 10.0), marble, tex('plaster'), tex_scale=(14, 2.5))
        mk(self.root, 'cube', (0, 8.4, 124.0), (52.0, 0.8, 11.0), rgb(150, 70, 56), tex('tile'), tex_scale=(14, 3))
        for sx in (-1, 1):
            mk(self.root, 'cube', (sx * 27.0, 7.0, 122.0), (7.0, 14.0, 9.0), shade(marble, 0.95), tex('plaster'))
            mk(self.root, 'cube', (sx * 27.0, 14.4, 122.0), (8.0, 0.8, 10.0), rgb(150, 70, 56), tex('tile'))
            brazier(self, sx * 27.0, 116.5, y=0.0, scale=1.0, intensity=1.6, radius=10.0)
        for i in range(9):
            x = -16.0 + i * 4.0
            mk(self.root, 'cylinder', (x, 0, 116.0), (0.9, 8.0, 0.9), marble, tex('plaster'))
            for wy in (2.2, 5.6):
                mk(self.root, 'cube', (x + 2.0, wy, 118.9), (1.1, 1.8, 0.1), rgb(255, 196, 110), emissive=0.9)
        mk(self.root, 'cube', (0, 0.9, 112.0), (50.0, 1.8, 6.0), shade(marble, 0.85), tex('stone'))
        banner(self, 0, 4.2, 113.4, 'roman', height=6.0, face='south', sway=True)
        for x in (-16.0, -9.0, 9.0, 16.0):
            palm(self, x, 106.0, h=4.2, seed=int(x) + 9, collide=False)

    def _build_far_city(self):
        rnd = random.Random(12)
        for side in (-1, 1):
            for i in range(16):
                z = -30 + i * 11.5 + rnd.uniform(-3, 3)
                x = side * rnd.uniform(36, 62)
                w, d, h = (rnd.uniform(8, 16), rnd.uniform(8, 14), rnd.uniform(7, 19))
                mk(self.root, 'cube', (x, h / 2, z), (w, h, d), rgb(30, 34, 58))
                mk(self.root, 'cube', (x, h + 0.3, z), (w + 0.6, 0.6, d + 0.6), rgb(44, 40, 58))
                for k in range(rnd.randint(2, 6)):
                    mk(self.root, 'cube', (x + rnd.uniform(-w / 2.4, w / 2.4), rnd.uniform(2, h - 1), z - d / 2 - 0.05), (0.8, 1.0, 0.1), rgb(255, 190, 100), emissive=0.9)
        for i in range(14):
            x = -80 + i * 11.5
            mk(self.root, 'cube', (x, 9, 170.0), (3.2, 18, 3.2), rgb(34, 38, 62))
            mk(self.root, 'cube', (x + 5.7, 17, 170.0), (8.2, 2.4, 3.2), rgb(40, 44, 68))
        mk(self.root, 'cube', (0, 19.4, 170.0), (170, 1.6, 4.0), rgb(44, 48, 72))

    def _archer(self, pos, route, facing, h, view=11.5, fov=78, pause=2.2, sweep=40, speed=1.1):
        gd = self._guard(pos, route, facing, ARCHER, view=view, fov=fov, pause=pause, sweep=sweep, speed=speed)
        gd.ch.root.y = h
        gd.level_y = h
        return gd

    def _build_people(self):
        self.abdo = self.add_char(START, **CROW_LOOK)
        self.abdo.face(0, 1)
        self.set_player(self.abdo, speed=3.3, run_speed=5.6)
        self.player.step_sound = 'step_stone'
        self.gA1 = self._guard((0.0, 3.0), [(0.0, 3.0), (0.0, 22.0)], 0, LEGION, view=9.0, pause=2.4)
        self.gA2 = self._guard((-19.0, 17.0), [], 0, LEGION, view=8.5, sweep=40)
        self.gA3 = self._guard((-9.2, 25.6), [], 90, LEGION, view=8.0, fov=70, sweep=60)
        self.gB1 = self._guard((2.0, 32.0), [(2.0, 32.0), (20.0, 32.0), (20.0, 54.0), (2.0, 54.0)], 90, LEGION, view=9.0, pause=1.8, speed=1.5)
        self.gB2 = self._guard((8.6, 41.0), [], 90, LEGION, view=8.0, sweep=44)
        self.gB3 = self._guard((-19.0, 30.0), [(-19.0, 30.0), (-19.0, 56.0)], 0, LEGION, view=8.5, pause=2.2)
        self.gB4 = self._guard((0.0, 55.0), [], 180, ELITE, view=9.5, sweep=32)
        self.gC1 = self._archer((9.2, 65.0), [(6.0, 64.0), (12.5, 66.0)], 270, 4.18)
        self.gC2 = self._archer((9.2, 78.0), [(12.5, 77.0), (6.0, 79.0)], 270, 4.68)
        self.gC3 = self._guard((0.0, 62.0), [(0.0, 62.0), (0.0, 83.0)], 0, LEGION, view=9.0, pause=2.8)
        self.gC4 = self._archer((-9.2, 78.0), [(-13.0, 78.0), (-5.5, 78.0)], 0, 4.48, view=9.5, speed=0.9, pause=3.0)
        self.gC5 = self._guard((-19.0, 62.0), [(-19.0, 62.0), (-19.0, 84.0)], 0, LEGION, view=8.5, pause=2.4)
        self.gD1 = self._guard((-16.0, 89.0), [(-16.0, 89.0), (16.0, 89.0)], 90, LEGION, view=9.0, pause=2.2, speed=1.5)
        self.gD2 = self._guard((11.0, 87.0), [(11.0, 87.0), (11.0, 96.0)], 0, LEGION, view=8.5, pause=2.0)
        self.gD3 = self._guard((-11.0, 96.0), [(-11.0, 96.0), (-11.0, 87.0)], 180, LEGION, view=8.5, pause=2.0)
        self.gD4 = self._guard((-3.9, 97.0), [], 180, ELITE, view=9.0, sweep=24)
        self.gD5 = self._guard((3.9, 97.0), [], 180, ELITE, view=9.0, sweep=24)
        for gd in (self.gB4, self.gD4, self.gD5):
            gd.armor = True
        self.sentry_a = self.add_char((-19.0, 4.0), **LEGION)
        self.sentry_b = self.add_char((-19.0, 5.5), **LEGION)
        self.sentry_a.face(0, 1)
        self.sentry_b.face(0, -1)
        self.merchant = self.add_char((6.2, 36.6), **MERCHANT)
        self.talker = self.add_char((7.8, 37.4), **LEGION)
        self.merchant.face(1, 0.3)
        self.talker.face(-1, -0.3)
        for x, z, a in ((11.4, 40.4, 200), (16.8, 39.6, 160)):
            c = self.add_char((x, z), **CITIZEN)
            c.set_pose('sit')
            c.root.rotation_y = a
        self.decor = [self.sentry_a, self.sentry_b]

    def _build_lanterns(self):
        spots = [(-3.2, 4.0), (3.2, 10.6), (-3.2, 17.0), (3.2, 23.5), (-16.2, 8.0), (-16.2, 22.0), (-3.2, 33.0), (-3.2, 50.0), (8.0, 29.0), (20.0, 29.0), (8.0, 57.0), (20.0, 57.0), (-16.2, 36.0), (-16.2, 52.0), (-3.2, 63.0), (3.2, 70.6), (-3.2, 78.0), (3.2, 83.0), (-16.2, 66.0), (-16.2, 80.0)]
        for x, z in spots:
            self.snuffable('torch', x, z, h=2.3, intensity=1.6, radius=9.0, label='Snuff the lantern')
        for x in (-8.0, 8.0):
            brazier(self, x, 92.5, scale=0.8, intensity=1.7, radius=10.0)

    def _build_abilities_city(self):
        self.abil = Abilities(self, knives=4, smokes=2, caw=lambda: (self.caw_cd <= 0, self.caw_cd))
        a = self.abil
        for x, z, kind, y in ((-19.0, 12.0, 'knife', 0.0), (-9.0, 10.8, 'smoke', 0.0), (21.0, 6.0, 'knife', 0.0), (-12.0, 20.0, 'smoke', 4.48), (-9.0, 25.6, 'knife', 0.0), (22.0, 36.0, 'knife', 0.0), (20.5, 50.0, 'smoke', 0.0), (-9.0, 49.0, 'knife', 4.68), (-19.5, 48.0, 'smoke', 0.0), (-9.0, 65.0, 'knife', 4.08), (-9.0, 64.0, 'smoke', 4.08), (20.5, 71.0, 'knife', 0.0), (-20.0, 90.0, 'smoke', 0.0), (20.0, 92.0, 'knife', 0.0), (-20.0, 94.0, 'knife', 0.0)):
            a.add_pickup(x, z, kind, y)
        a.extra_marks = lambda: [(it['x'], 2.4, it['z']) for it in self.snuffables if it['lit']]
        a.add_beacon(-9.6, 96.6, 11.0)

    def start(self):
        self.stealth_active = False
        self.tl.run(self.opening())

    def opening(self):
        g = self.game
        self.begin_cutscene()
        self.shot((-34.0, 16.0, -18.0), (-8.0, 3.0, 22.0), speed=9)
        self.cam.snap()
        g.hud.title_card('MISSION II', 'The Rooftops of Antioch', 'Prefect Marcellus gives a banquet tonight', hold=2.8)
        yield 4.2
        self.shot((-26.0, 12.0, 6.0), (-8.0, 4.0, 40.0), speed=0.32)
        yield 3.0
        self.shot((-22.5, 2.6, -1.0), (-19.0, 1.6, 4.6), speed=0.9)
        yield 1.2
        yield from self.talk([('Legionary', 'A banquet for forty senators, and I am standing in a lane smelling of dye.'), ('Sentry', 'Marcellus doubled every watch in the city. Two Centurions dead on the Antioch road in a month.'), ('Legionary', "Varro is dead too, they say. A crow's feather on his chest."), ('Sentry', 'Keep walking. And keep your eyes on the roofs.')], {'Legionary': self.sentry_a, 'Sentry': self.sentry_b})
        self.go(self.sentry_a, -19.0, 26.0, speed=1.9)
        self.go(self.sentry_b, -19.0, 27.5, speed=1.9)
        self.shot((-23.0, 4.5, -9.0), (-19.0, 1.6, 0.0), speed=1.0)
        yield 1.2
        yield from self.walk(self.abdo, -19.0, 0.6, speed=2.2)
        yield from self.talk([('Abdo', 'Marcellus. Varro was the sword - this man signed the order.'), ('Abdo', 'Every guard in Antioch is on the street tonight. Good. A crow does not need streets.')], {'Abdo': self.abdo})
        self.sentry_a.root.enabled = False
        self.sentry_b.root.enabled = False
        self.end_cutscene()
        self.phase = 'infiltrate'
        self.stealth_active = True
        self.bounds = (-23.2, 23.2, -4.5, 97.8)
        self.abil.enabled = True
        g.hud.objective("Reach the Prefect's villa - over the roofs if you can")
        g.hud.hint('The ladder at the west wall leads up to the roofs.   E  climb      Push against a roof edge to leap the gap      SPACE  drop on a guard below', hold=9)
        self.tl.after(10.5, lambda: self.abil.hint_once('tools2', 'C  Crow Sight (guards glow through walls)     G  smoke bomb     R  throwing knife', hold=8))

    def eavesdrop(self):
        if self._eaves_done or self.phase != 'infiltrate' or self.failing or self.nav.busy:
            return
        self._eaves_done = True
        self.tl.run(self._eavesdrop())

    def _eavesdrop(self):
        g = self.game
        self.phase = 'reveal'
        self.stealth_active = False
        self.abil.sight_off(cooldown=0.0)
        self.begin_cutscene()
        for gd in self.guards:
            gd.awareness = 0.0
        self.shot((1.0, 3.4, 30.5), (7.0, 1.5, 37.0), speed=1.0)
        yield 1.6
        yield from self.talk([('Merchant', "Forty amphorae of Falernian for the Prefect's table. And not a coin for my trouble."), ('Legionary', 'Quiet, old man. Tonight the villa gate opens to nobody. Archers on every roof of Lantern Row.'), ('Merchant', 'Every roof?'), ('Legionary', 'The east side. The west roofs have one lazy sentry. Prefect says nobody walks on rooftops.')], {'Merchant': self.merchant, 'Legionary': self.talker})
        yield 0.3
        self.end_cutscene()
        self.phase = 'infiltrate'
        self.stealth_active = True
        g.hud.objective('The west roofs of Lantern Row are the way in')

    def reset_section(self):
        self.nav.busy = False
        self.player.ch.root.y = 0.0
        super().reset_section()

    def on_update(self, dt):
        if self.caw_cd > 0:
            self.caw_cd = max(0.0, self.caw_cd - dt)
        self._stealth_upkeep(dt)
        p = self.player
        if self.phase == 'infiltrate':
            if p.ch.root.y > 1.0 and (not self._roof_hint):
                self._roof_hint = True
                self.abil.hint_once('roofhint', 'Push against the edge of a roof to leap across.   SPACE at the edge drops you to the street - or onto a guard.', hold=7)
            self.wall_it.enabled = p.z > 90.0 and p.ch.root.y < 1.0

    def on_action(self):
        if self.phase != 'infiltrate':
            return
        p = self.player
        if self.nav.on_roof(p) and self.nav.try_drop(p):
            return
        for gd in self.guards:
            if gd.alive and gd.state != 'chase' and (abs(gd.ch.root.y - p.ch.root.y) < 1.0) and gd.in_takedown_range(p, 1.9):
                if gd.is_behind(p):
                    self.takedown(gd)
                else:
                    self.game.hud.hint('He is facing you - get behind him first.', hold=2.2)
                return

    def _interactions(self):
        BaseScene._interactions(self)
        if self.phase != 'infiltrate' or self.cutscene_active or self.failing or (self._near is not None):
            return
        p = self.player
        txt = self.nav.prompt()
        if txt:
            self.game.hud.prompt(txt)
            return
        for gd in self.guards:
            if gd.alive and gd.state != 'chase' and (abs(gd.ch.root.y - p.ch.root.y) < 1.0) and gd.in_takedown_range(p, 1.9) and gd.is_behind(p):
                self.game.hud.prompt('[SPACE]  Silence him')
                break

    def on_wall(self):
        if self.phase == 'infiltrate' and (not self.failing):
            self.tl.run(self.wall_climb())

    def wall_climb(self):
        g = self.game
        a = self.abdo
        self.phase = 'ending'
        self.stealth_active = False
        self.abil.sight_off(cooldown=0.0)
        self.abil.enabled = False
        self.begin_cutscene()
        g.hud.objective(None)
        for gd in self.guards:
            gd.awareness = 0.0
            gd.frozen = True
            gd.ch.amount = 0.0
        x = -9.6
        yield from self.walk(a, x, 96.2, speed=2.2)
        a.face(0, 1)
        self.shot((x + 3.2, 3.2, 90.0), (x, 3.0, 99.0), speed=1.0)
        yield 0.8
        hook = mk(self.root, 'cube', (x, 1.5, 96.4), (0.16, 0.16, 0.16), rgb(150, 150, 160), emissive=0.2)
        rope = mk(self.root, 'cylinder', (x, 0.0, 98.4), (0.06, 0.1, 0.06), rgb(130, 104, 70))
        a.attack()
        g.audio.play('blade', 0.5, pitch=0.8)
        t = 0.0
        while t < 0.7:
            t += self.dt
            k = min(1.0, t / 0.7)
            hook.position = (x, 1.5 + 4.6 * ease_out(k), 96.4 + 2.0 * k)
            rope.scale_y = 0.1 + 6.0 * ease_out(k)
            yield
        g.audio.play('clink', 0.7)
        yield 0.3
        t = 0.0
        a.face(0, 1)
        while t < 2.4:
            t += self.dt
            k = ease_in_out(min(1.0, t / 2.4))
            a.root.y = 6.0 * k
            a.root.z = 98.0 + 0.0 * k
            a.amount = 0.85
            yield
        a.amount = 0.0
        a.root.z = 98.0
        g.audio.play('wingbeat', 0.6)
        self.shot((x + 1.0, 11.5, 90.0), (x + 2.0, 4.5, 112.0), speed=0.8)
        yield 1.0
        yield from self.talk([('Abdo', 'Torches. Marble. Forty guests singing while the city walks in fear.'), ('Abdo', 'Count your guards, Prefect. It will not be enough.')], {'Abdo': a})
        g.hud.fade_to(1.0, 1.8)
        yield 2.2
        g.next_scene()
