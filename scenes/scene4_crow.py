import math
import random
from ursina import Entity, Text, Vec3, camera, color, destroy
from engine.ai import Guard
from engine.assets import FONT, FONT_BOLD, tex
from engine.crow import Abilities
from engine.entities import mk, rgb, shade
from engine.particles import Emitter
from engine.props import CrowBird, Sky, banner, barrel, bed, brazier, candle, chest, contact_shadow, crate, dead_tree, dish, goblet, ground, ground_patches, jug, moon, planets, rock, rug, scatter_clutter, soft_path, torch, wall_box, wall_line, weapon_rack, well
from engine.scene_base import BaseScene
from engine.timing import Clock, ease_in, ease_in_out, ease_out
ROPE_X = -16.0
START_OUT = (ROPE_X, -7.0)
LAND = (ROPE_X, 2.7)
WALL_H = 2.5
COURT_X = 21.0
BARRACKS = (-12.0, 41.5, 18.0, 20.0)
COMMAND = (12.0, 41.5, 18.0, 20.0)
VARRO_POS = (12.0, 45.6)
ZONES = {'court': (-20.0, 20.0, 2.0, 30.5), 'alley': (-2.4, 2.4, 32.5, 50.5), 'barracks': (-20.0, -3.8, 32.8, 50.5), 'hall': (3.8, 20.0, 32.8, 50.5)}
STONE = rgb(150, 152, 170)
PLASTER = rgb(176, 170, 176)
LEGION = dict(robe=rgb(150, 38, 36), trim=rgb(214, 178, 92), head='helmet', head_color=rgb(150, 152, 164), weapon='spear', build='broad', skin='olive')
ELITE = dict(robe=rgb(96, 30, 40), trim=rgb(236, 200, 100), head='helmet', head_color=rgb(214, 176, 90), weapon='sword', build='broad', skin='tan', cloak=rgb(120, 24, 28))
VARRO_LOOK = dict(robe=rgb(160, 40, 40), trim=rgb(240, 206, 110), head='helmet', head_color=rgb(222, 184, 96), weapon='sword', build='broad', skin='olive', cloak=rgb(130, 22, 26), scale=1.08)
CROW_LOOK = dict(robe=rgb(46, 50, 76), trim=rgb(176, 44, 50), head='hood', head_color=rgb(30, 32, 50), cloak=rgb(26, 28, 48), mask=True, weapon='dagger', skin='tan')

class Scene4Crow(BaseScene):
    number = 4
    name = 'The Night Crow  -  Mission I: The Fort'
    author = 'Yusra Abdelaseim Elsayed'

    def build(self):
        g = self.game
        self.phase = 'intro'
        self.checkpoint = LAND
        self.starts = []
        self.snuffables = []
        self.bodies = []
        self.caw_cd = 0.0
        self.kills = 0
        self.ui = []
        rig = self.rig
        rig.ambient = Vec3(0.125, 0.145, 0.255)
        rig.sun_color = Vec3(0.24, 0.3, 0.5)
        rig.sun_dir = Vec3(-0.45, 0.8, -0.35)
        rig.fog_color = Vec3(0.03, 0.04, 0.09)
        rig.fog_density = 0.012
        g.post.set(vignette=0.52, bloom=1.0, tint=(0.9, 0.96, 1.1), grain=0.05, desat=0.0)
        self.cam.pitch, self.cam.distance = (46, 12.5)
        self.cam.set_fov(66)
        self.stealth_light = True
        self.bounds = None
        self.sky = Sky(self, 'sky_night', stars=True)
        moon(self, pos=(-70, 78, 150), size=42)
        planets(self, ringed=(125, 54, 150), red=(-130, 88, 120))
        self._build_outside()
        self._build_fort()
        self._build_courtyard()
        self._build_barracks()
        self._build_hall()
        self._build_people()
        self._build_ui()
        self._build_abilities()
        self.trigger(0.0, 31.8, 5.0, 1.2, lambda: self._checkpoint((0.0, 31.0)))
        self.trigger(-12.0, 32.4, 2.4, 1.0, lambda: self._checkpoint((-12.0, 31.0)))
        self.trigger(3.6, 40.0, 1.6, 2.4, self.on_hall)
        self.trigger(12.0, 32.8, 3.0, 1.2, self.on_hall)
        g.audio.music('mus_crow', 0.5, fade=3.0)
        g.audio.loop('amb_wind', 0.28, fade=3.0)

    def _build_outside(self):
        self.ground = ground(self, 260, 'sand', 130, rgb(92, 100, 130))
        ground_patches(self, -50, -60, 50, 0, count=70, seed=44, palette=[rgb(40, 46, 70), rgb(66, 70, 96), rgb(30, 34, 52)], alpha=(0.25, 0.5), size=(3, 9))
        scatter_clutter(self, -50, -60, 50, -2, count=70, seed=9, grass=rgb(60, 70, 70), pebble=rgb(80, 84, 104))
        soft_path(self, [(0, -70), (0, -40), (2, -14), (0, -2)], width=4.0, col=rgb(96, 100, 126), alpha=0.5)
        rnd = random.Random(31)
        for i in range(14):
            rock(self, rnd.uniform(-45, 45), rnd.uniform(-45, -6), s=rnd.uniform(0.8, 2.4), col=rgb(84, 90, 116), collide=False)
        for x, z in ((-28, -12), (24, -20), (-34, -30), (36, -8)):
            dead_tree(self, x, z, h=rnd.uniform(3.2, 4.4))
        for x, z, sx, sy in ((-90, 120, 90, 22), (-30, 150, 120, 30), (60, 130, 110, 26), (130, 90, 80, 20), (-140, 60, 70, 16), (20, -150, 160, 18)):
            mk(self.root, 'sphere', (x, -2, z), (sx, sy, sx * 0.6), rgb(22, 26, 44))
        mk(self.root, 'cylinder', (ROPE_X, 0.0, -0.8), (0.07, WALL_H + 0.2, 0.07), rgb(120, 96, 64), tex('wood'))
        mk(self.root, 'cube', (ROPE_X, WALL_H + 0.05, -0.55), (0.35, 0.12, 0.5), rgb(70, 70, 80))
        self.fx.smoke((ROPE_X, 0, -6), scale=4, rate=1, tone=0.1, alpha=0.2, wind=(0.3, 0.1, 0.1)).cull = False

    def _build_fort(self):
        h = 4.8
        mk(self.root, 'plane', (0, 0.01, 26.0), (2 * COURT_X, 1, 53.5), rgb(150, 152, 176), tex('stone_dark'), tex_scale=(7, 9))
        ground_patches(self, -20, 1, 20, 31, count=40, seed=5, palette=[rgb(60, 64, 80), rgb(86, 88, 104)], alpha=(0.25, 0.45), size=(2, 6), y=0.02)
        gate_half = 1.9
        for a, b in ((-COURT_X - 1.2, -gate_half), (gate_half, COURT_X + 1.2)):
            wall_line(self, a, 0.0, b, 0.0, WALL_H, 1.2, 'stone', STONE)
        mk(self.root, 'cube', (0, 1.7, 0), (2 * gate_half, 3.4, 0.6), rgb(96, 66, 44), tex('wood'), tex_scale=(2, 1))
        self.world.add_box(0, 0, 2 * gate_half, 0.8)
        for x in range(-21, 22, 2):
            if abs(x) > gate_half + 0.2:
                mk(self.root, 'cube', (x + 0.3, WALL_H + 0.3, 0.0), (1.0, 0.6, 1.2), STONE, tex('stone'))
        for sx in (-1, 1):
            wall_box(self, sx * 4.2, 0.0, 3.4, 3.4, 5.6, 'stone', STONE)
            brazier(self, sx * 4.2, 0.0, y=5.6, scale=0.8, intensity=1.5, radius=9.0)
        for sx in (-1, 1):
            wall_line(self, sx * (COURT_X + 0.6), 0.0, sx * (COURT_X + 0.6), 32.0, h, 1.2, 'stone', STONE)
        for sx in (-1, 1):
            wall_box(self, sx * (COURT_X + 0.6), 0.0, 4.2, 4.2, 7.2, 'stone', STONE)
            wall_box(self, sx * (COURT_X + 0.6), 52.0, 4.2, 4.2, 7.2, 'stone', STONE)
            brazier(self, sx * (COURT_X + 0.6), 52.0, y=7.2, scale=0.7, intensity=1.2, radius=8.0)
        wall_box(self, 0.0, 51.5, 6.4, 0.6, 4.2, 'stone', STONE)

    def _wall_run(self, x0, z0, x1, z1, hh, thick, col):
        if max(abs(x1 - x0), abs(z1 - z0)) > 0.05:
            wall_line(self, x0, z0, x1, z1, hh, thick, 'plaster', col)

    def building(self, cx, cz, w, d, h, doors, south_h=1.25, col=PLASTER, floor=rgb(122, 112, 116)):
        hw, hd = (w / 2.0, d / 2.0)
        thick = 0.5
        sides = {'south': (cx - hw, cz - hd, cx + hw, cz - hd, True, south_h), 'north': (cx - hw, cz + hd, cx + hw, cz + hd, True, h), 'west': (cx - hw, cz - hd, cx - hw, cz + hd, False, h), 'east': (cx + hw, cz - hd, cx + hw, cz + hd, False, h)}
        for name, (x0, z0, x1, z1, horiz, hh) in sides.items():
            a0, a1 = (x0, x1) if horiz else (z0, z1)
            mid = (a0 + a1) / 2.0
            cur = a0
            for off, wd in sorted(((o, wdt) for s, o, wdt in doors if s == name)):
                g0, g1 = (mid + off - wd / 2.0, mid + off + wd / 2.0)
                self._seg(horiz, x0, z0, cur, g0, hh, thick, col)
                if hh > 2.6:
                    ox, oz = ((g0 + g1) / 2.0, z0) if horiz else (x0, (g0 + g1) / 2.0)
                    lh = hh - 2.4
                    mk(self.root, 'cube', (ox, 2.4 + lh / 2.0, oz), (g1 - g0 + 0.1, lh, thick) if horiz else (thick, lh, g1 - g0 + 0.1), shade(col, 0.9), tex('plaster'))
                cur = g1
            self._seg(horiz, x0, z0, cur, a1, hh, thick, col)
        mk(self.root, 'plane', (cx, 0.02, cz), (w - 0.7, 1, d - 0.7), floor, tex('stone'), tex_scale=(w / 5.0, d / 5.0))

    def _seg(self, horiz, x0, z0, a, b, hh, thick, col):
        if b - a < 0.05:
            return
        if horiz:
            wall_line(self, a, z0, b, z0, hh, thick, 'plaster', col)
        else:
            wall_line(self, x0, a, x0, b, hh, thick, 'plaster', col)

    def snuffable(self, kind, x, z, label='Snuff the torch', **kw):
        n0 = len(self.fx.emitters)
        if kind == 'torch':
            L = torch(self, x, z, **kw)
        elif kind == 'brazier':
            L = brazier(self, x, z, **kw)
        else:
            L = candle(self, x, z, **kw)
        ems = self.fx.emitters[n0:]
        for e in ems:
            e.cull = False
        item = dict(light=L, emitters=ems, x=x, z=z, lit=True)
        it = self.interact(x, z, label, lambda it=item: self.snuff(it), radius=1.9 if kind != 'candle' else 1.5)
        item['interact'] = it
        self.snuffables.append(item)
        return item

    def snuff(self, item):
        if not item['lit']:
            return
        item['lit'] = False
        item['light'].enabled = False
        for e in item['emitters']:
            e.enabled = False
            e.clear()
        self.game.audio.play('snuff', 0.8)
        self.fx.smoke((item['x'], 1.9, item['z']), scale=0.7, rate=0, tone=0.35, alpha=0.5).burst(10)
        self.fx.dust_puff((item['x'], 1.8, item['z']), 5, color=(0.6, 0.6, 0.65))

    def _build_courtyard(self):
        for x, z in ((-20.0, 8.0), (-20.0, 18.0), (-20.0, 28.0), (20.0, 8.0), (20.0, 18.0), (20.0, 28.0)):
            self.snuffable('torch', x, z, h=2.0, intensity=1.7, radius=9.5)
        for x in (-14.6, -9.4, 9.4, 14.6):
            self.snuffable('torch', x, 30.7, h=2.0, intensity=1.6, radius=9.0)
        for x, z in ((-2.3, 36.0), (2.3, 45.0)):
            self.snuffable('torch', x, z, h=2.0, intensity=1.5, radius=8.5)
        brazier(self, -5.4, 3.6, scale=0.9, intensity=1.8, radius=10.0)
        brazier(self, 5.4, 3.6, scale=0.9, intensity=1.8, radius=10.0)
        well(self, 0.0, 14.5)
        for cx, cz, w, d in ((-17.0, 11.0, 2.6, 1.4), (-15.0, 22.0, 1.4, 2.6), (-7.0, 19.0, 2.4, 1.4), (7.0, 10.0, 2.4, 1.4), (16.5, 15.0, 1.4, 2.8), (13.0, 26.0, 2.8, 1.4), (-5.0, 27.0, 2.4, 1.3)):
            self.cover(cx, cz, w, d)
        crate(self, -18.6, 5.0, 0.9, rot=12)
        crate(self, -18.7, 6.0, 0.8, rot=-6)
        crate(self, 18.6, 4.6, 0.9, rot=-14)
        barrel(self, -19.0, 14.5)
        barrel(self, -19.0, 15.5)
        crate(self, 19.0, 22.0, 0.9, rot=18)
        crate(self, 18.0, 22.8, 0.8, rot=-8)
        mk(self.root, 'cylinder', (9.5, 0.0, 22.0), (0.35, 1.7, 0.35), rgb(96, 70, 48), tex('wood'))
        mk(self.root, 'cube', (9.5, 1.35, 22.0), (1.2, 0.14, 0.14), rgb(96, 70, 48))
        self.world.add_circle(9.5, 22.0, 0.4)
        weapon_rack(self, -20.2, 24.5, rot=90)
        mk(self.root, 'cube', (3.8, 0.7, 24.0), (2.6, 0.18, 1.3), rgb(104, 76, 52), tex('wood'))
        for sx in (-1, 1):
            mk(self.root, 'cylinder', (3.8 + sx * 1.0, 0.45, 23.3), (0.9, 0.12, 0.9), rgb(60, 44, 32), rot=(0, 0, 90))
        self.world.add_box(3.8, 24.0, 2.6, 1.3, blocks_sight=False)
        self.decor = []
        for x in (-10.0, -8.6, 9.0, 14.5):
            s = self.add_char((x, 0.0), robe=rgb(120, 34, 34), trim=rgb(214, 178, 92), head='helmet', head_color=rgb(150, 152, 164), weapon='spear', build='broad', skin='olive')
            s.root.y = WALL_H
            s.face(0, 1)
            self.decor.append(s)
        for z in (13.0, 23.0):
            banner(self, -20.9, 3.0, z, 'roman', height=2.4, face='east')
            banner(self, 20.9, 3.0, z, 'roman', height=2.4, face='west')

    def cover(self, cx, cz, w, d):
        wall_box(self, cx, cz, w, d, 1.5, 'wood', rgb(150, 120, 100), tile=1.2)
        for i in range(int(max(w, d) // 0.9)):
            ox = (i - (max(w, d) // 0.9 - 1) / 2.0) * 0.9
            px, pz = (cx + ox, cz) if w >= d else (cx, cz + ox)
            mk(self.root, 'cube', (px, 1.75, pz), (0.7, 0.5, 0.7), rgb(140, 108, 80), tex('wood'), rot=(0, 10 * i, 0))
        contact_shadow(self, cx, cz, w + 1.2, d + 1.2, 0.5)

    def _build_barracks(self):
        cx, cz, w, d = BARRACKS
        self.building(cx, cz, w, d, 3.6, [('south', 0.0, 2.0), ('east', -1.5, 2.0)])
        self.sleepers = []
        for i, bx in enumerate((-18.4, -15.4, -12.4, -9.4)):
            bed(self, bx, 49.6, 1.9, 1.0, col=rgb(130, 90, 90), collide=True)
            if i % 2 == 0:
                s = self.add_char((bx, 49.6), robe=rgb(110, 36, 36), trim=rgb(214, 178, 92), head='bare', skin='olive', build='broad')
                s.set_pose('lie')
                s.root.rotation_y = 90
                s.root.y = 0.62
                s.root.x = bx - 0.3
                self.sleepers.append(s)
        for bz in (45.5, 42.5):
            bed(self, -19.6, bz, 1.0, 1.9, col=rgb(130, 90, 90), collide=True)
        mk(self.root, 'cube', (-20.4, 1.0, 38.0), (0.9, 2.0, 2.4), rgb(70, 64, 70), tex('stone'))
        mk(self.root, 'cube', (-19.95, 0.5, 38.0), (0.1, 0.7, 1.4), rgb(30, 12, 8), emissive=0.6)
        self.fx.fire((-19.8, 0.45, 38.0), scale=0.8, intensity=1.0)
        self.fx.embers((-19.8, 0.9, 38.0), scale=0.6, rate=4)
        self.rig.add((-18.6, 1.0, 38.0), color=(1.0, 0.55, 0.22), intensity=1.4, radius=8.0, flicker=0.3, speed=7.0)
        self.mess_table(-9.0, 39.0)
        self.snuffable('candle', -9.0, 39.0, label='Pinch out the candle', y=0.99, intensity=1.1, radius=5.5, height=0.22)
        chest(self, -4.6, 33.4, rot=20)
        barrel(self, -20.0, 33.6)

    def mess_table(self, x, z):
        mk(self.root, 'cube', (x, 0.88, z), (3.0, 0.1, 1.2), rgb(120, 90, 62), tex('wood'))
        for sx in (-1, 1):
            for sz in (-1, 1):
                mk(self.root, 'cube', (x + sx * 1.35, 0.44, z + sz * 0.5), (0.12, 0.88, 0.12), rgb(80, 60, 44))
        self.world.add_box(x, z, 3.0, 1.2, blocks_sight=False)
        goblet(self, x + 0.8, 0.93, z + 0.2)
        goblet(self, x - 1.1, 0.93, z - 0.3)
        dish(self, x + 0.1, 0.93, z + 0.35, r=0.3)
        jug(self, x - 0.5, 0.93, z - 0.2)

    def _build_hall(self):
        cx, cz, w, d = COMMAND
        self.building(cx, cz, w, d, 3.8, [('south', 0.0, 2.4), ('west', -1.5, 2.0)], col=rgb(186, 176, 176), floor=rgb(104, 96, 104))
        rug(self, 12.0, 39.5, 5.0, 11.0, rot=0, repeat=(1, 2))
        tx, tz = (12.0, 47.2)
        mk(self.root, 'cube', (tx, 0.92, tz), (4.4, 0.14, 1.5), rgb(110, 80, 56), tex('wood'))
        for sx in (-1, 1):
            for sz in (-1, 1):
                mk(self.root, 'cube', (tx + sx * 2.0, 0.46, tz + sz * 0.6), (0.14, 0.92, 0.14), rgb(70, 52, 40))
        mk(self.root, 'plane', (tx, 1.0, tz), (3.8, 1, 1.2), rgb(214, 196, 150))
        for i in range(7):
            mk(self.root, 'cube', (tx - 1.5 + i * 0.5, 1.04, tz + math.sin(i * 1.7) * 0.3), (0.12, 0.08, 0.12), rgb(180, 40, 40) if i % 2 else rgb(50, 70, 150))
        self.world.add_box(tx, tz, 4.4, 1.5, blocks_sight=False)
        self.varro_candle = candle(self, tx - 1.7, tz, y=0.99, intensity=1.5, radius=7.5, height=0.3)
        candle(self, tx + 1.7, tz, y=0.99, light=False, height=0.3)
        self.snuffable('brazier', 6.4, 43.0, label='Put out the fire', scale=0.8, intensity=1.5, radius=8.5)
        self.snuffable('brazier', 17.6, 43.0, label='Put out the fire', scale=0.8, intensity=1.5, radius=8.5)
        banner(self, 12.0, 3.0, 51.05, 'roman', height=2.8, face='south')
        banner(self, 6.0, 3.0, 51.05, 'roman', height=2.2, face='south')
        banner(self, 18.0, 3.0, 51.05, 'roman', height=2.2, face='south')
        weapon_rack(self, 20.4, 36.0, rot=90)
        chest(self, 20.0, 49.8, rot=-30)
        self.standard = Entity(parent=self.root, position=(17.4, 0, 49.2), add_to_scene_entities=False)
        mk(self.standard, 'cylinder', (0, 0, 0), (0.14, 3.0, 0.14), rgb(96, 70, 48))
        mk(self.standard, 'cube', (0, 2.6, 0), (0.9, 0.08, 0.08), rgb(214, 176, 80), emissive=0.3)
        for i in range(3):
            mk(self.standard, 'cylinder', (0, 1.3 + i * 0.35, 0), (0.42, 0.06, 0.42), rgb(220, 184, 90), emissive=0.25)
        mk(self.standard, 'sphere', (0, 3.15, 0), (0.45, 0.4, 0.3), rgb(230, 190, 90), emissive=0.35)
        for sx in (-1, 1):
            mk(self.standard, 'cube', (sx * 0.4, 3.15, 0), (0.7, 0.08, 0.3), rgb(230, 190, 90), emissive=0.35, rot=(0, 0, sx * -20))
        mk(self.standard, 'cone', (0, 3.45, 0.1), (0.14, 0.24, 0.14), rgb(240, 200, 90), emissive=0.35, rot=(90, 0, 0))
        self.world.add_circle(17.4, 49.2, 0.4)

    def _guard(self, pos, route, facing, look, view=9.0, fov=74, pause=2.0, sweep=34, speed=1.4, alert=1.0):
        gd = Guard(self, pos, route=route, facing=facing, speed=speed, view=view, fov=fov, pause=pause, sweep=sweep, **look)
        gd.alert_mult = alert
        self.add_guard(gd)
        self.starts.append((gd, pos, facing))
        return gd

    def _build_people(self):
        self.abdo = self.add_char(START_OUT, **CROW_LOOK)
        self.abdo.face(0, 1)
        self.set_player(self.abdo, speed=3.3, run_speed=5.6)
        self.player.step_sound = 'step_stone'
        self.mist = self.fx.smoke((START_OUT[0], 0.15, START_OUT[1]), scale=0.7, rate=5, tone=0.03, alpha=0.5, wind=(0.0, 0.15, 0.0))
        self.mist.cull = False
        self.g1 = self._guard((-10.0, 6.0), [(-10.0, 6.0), (-10.0, 25.0)], 0, LEGION, pause=2.4)
        self.g2 = self._guard((12.0, 26.0), [(12.0, 26.0), (12.0, 8.0)], 180, LEGION, pause=2.0)
        self.g3 = self._guard((0.0, 19.0), [], 270, LEGION, view=9.5, sweep=48)
        self.g5 = self._guard((0.0, 34.0), [(0.0, 34.0), (0.0, 49.0)], 0, LEGION, view=8.5, pause=2.6)
        self.b1 = self._guard((-9.0, 37.4), [], 0, LEGION, view=7.5, fov=70, sweep=30, alert=0.8)
        self.e1 = self._guard((7.6, 44.4), [], 135, ELITE, view=9.0, sweep=40)
        self.e2 = self._guard((6.5, 36.0), [(6.5, 36.0), (17.5, 36.0)], 90, ELITE, pause=2.2)
        self.e3 = self._guard((12.0, 29.4), [], 180, LEGION, view=8.0, sweep=34)
        self.varro = self._guard(VARRO_POS, [], 0, VARRO_LOOK, view=5.5, fov=60, sweep=12, alert=1.6)
        self.varro_it = self.interact(VARRO_POS[0], VARRO_POS[1], 'Assassinate Varro', self.on_assassinate, radius=2.0, once=False)
        self.varro_it.enabled = False

    def _build_ui(self):
        pass

    def _build_abilities(self):
        self.abil = Abilities(self, knives=3, smokes=2, caw=lambda: (self.caw_cd <= 0, self.caw_cd))
        self._cp_seen = {(LAND[0], LAND[1])}
        for gd in (self.e1, self.e2, self.varro):
            gd.armor = True
        for x, z, kind in ((-18.4, 9.2, 'knife'), (17.6, 12.0, 'smoke'), (-4.6, 24.0, 'knife'), (-15.8, 33.4, 'smoke'), (2.0, 41.0, 'knife'), (19.0, 46.0, 'knife')):
            self.abil.add_pickup(x, z, kind)
        self.abil.extra_marks = lambda: [(it['x'], 2.0, it['z']) for it in self.snuffables if it['lit']]
        self.abil.add_beacon(VARRO_POS[0], VARRO_POS[1], 10.0)

    def start(self):
        self.stealth_active = False
        self.tl.run(self.opening())

    def talk(self, lines, who):

        def on_line(i, line):
            for n, c in who.items():
                c.talking = n == line[0]
        yield from self.say(lines, on_line=on_line)
        for c in who.values():
            c.talking = False

    def opening(self):
        g = self.game
        self.begin_cutscene()
        self.shot((-34.0, 6.0, -26.0), (-4.0, 3.0, 6.0), speed=9)
        self.cam.snap()
        g.hud.title_card('THREE MONTHS LATER', 'The Roman Frontier', 'A fort on the edge of the desert', hold=2.6)
        yield 4.0
        self.shot((-24.0, 5.0, -14.0), (-4.0, 2.5, 2.0), speed=0.35)
        yield 2.0
        sa = self.decor[0]
        sb = self.decor[1]
        self.shot((-12.5, 3.8, -5.0), (-9.3, 3.3, 0.0), speed=0.8)
        yield 1.4
        yield from self.talk([('Sentry A', 'Another officer found on the Antioch road. Third this month.'), ('Sentry B', "They say there is always a feather. A black crow's feather, laid on the chest."), ('Sentry A', 'Quiet. Do not say that name on watch. They say he hears it.'), ('Sentry B', 'Varro doubled the guard tonight because of it. Pray he is wrong.')], {'Sentry A': sa, 'Sentry B': sb})
        self.shot((ROPE_X + 2.5, 1.5, -10.0), (ROPE_X, 1.4, -5.0), speed=0.9)
        yield 1.4
        yield from self.walk(self.abdo, ROPE_X, -4.0, speed=2.0)
        yield from self.talk([('Abdo', 'Varro. The third name on my list. The first two died without ever knowing why.'), ('Abdo', 'Tonight he will know.')], {'Abdo': self.abdo})
        yield from self.climb()
        self.end_cutscene()
        self.phase = 'infiltrate'
        self.stealth_active = True
        self.bounds = (-20.6, 20.6, 0.9, 51.0)
        g.hud.objective('Find Centurion Varro - stay in the dark')
        self.abil.enabled = True
        g.hud.hint('E  snuff a torch      Q  caw (calls guards away)      SPACE  silence a guard from behind      Shift  run (loud)', hold=8)
        self.tl.after(9.5, lambda: self.abil.hint_once('tools', 'NEW  C  Crow Sight (see guards through walls)     G  smoke bomb     R  throwing knife', hold=9))

    def climb(self):
        a = self.abdo
        g = self.game
        yield from self.walk(a, ROPE_X, -1.1, speed=2.2)
        a.face(0, 1)
        self.shot((ROPE_X + 2.2, 0.9, -5.2), (ROPE_X, 1.8, 0.0), speed=1.3)
        t = 0.0
        while t < 1.8:
            t += self.dt
            k = ease_in_out(min(1.0, t / 1.8))
            a.root.y = (WALL_H + 0.05) * k
            a.amount = 0.8
            yield
        t = 0.0
        while t < 0.7:
            t += self.dt
            a.root.z = -1.1 + 1.0 * (t / 0.7)
            yield
        a.amount = 0.0
        g.audio.play('wingbeat', 0.5)
        self.shot((ROPE_X, 6.5, -3.5), (ROPE_X, 1.0, 5.0), speed=1.3)
        yield 0.6
        t = 0.0
        while t < 0.45:
            t += self.dt
            k = ease_in(min(1.0, t / 0.45))
            a.root.y = (WALL_H + 0.05) * (1.0 - k)
            a.root.z = -0.1 + (LAND[1] + 0.1) * k
            yield
        a.root.y = 0.0
        g.audio.play('thud', 0.5)
        self.fx.dust_puff((LAND[0], 0.1, LAND[1]), 8, color=(0.55, 0.56, 0.65))
        self.cam.shake(0.08, 0.2)
        yield 0.5

    def _checkpoint(self, pos, zone=None):
        if self.phase == 'infiltrate':
            self.checkpoint = pos
            self.game.hud.caption('Checkpoint', hold=0.5, fade=0.3, size=1.3, tone=(0.7, 0.8, 1.0))
            if pos not in self._cp_seen:
                self._cp_seen.add(pos)
                self.abil.resupply(knives=1, smokes=1)

    def reset_section(self):
        self.abil.on_reset()
        self.player.teleport(*self.checkpoint)
        for gd, pos, facing in self.starts:
            if gd.alive:
                gd.ch.root.x, gd.ch.root.z = pos
                gd.ch.angle = facing
                gd.ch.root.rotation_y = facing
                gd.wp, gd.wait, gd.look_offset = (0, 0.0, 0.0)
                gd.state, gd.awareness, gd.investigate = ('patrol', 0.0, None)
                gd.spotted_called = False
    zones = ZONES

    def zone_of(self, x, z):
        for name, (x0, x1, z0, z1) in self.zones.items():
            if x0 <= x <= x1 and z0 <= z <= z1:
                return name
        return None

    def on_key(self, key):
        if key == 'q':
            self.caw()
            return
        super().on_key(key)

    def caw(self):
        if self.phase != 'infiltrate' or self.cutscene_active or self.failing or self.player.locked:
            return
        if self.caw_cd > 0:
            return
        p = self.player
        zone = self.zone_of(p.x, p.z)
        if zone is None:
            return
        x0, x1, z0, z1 = self.zones[zone]
        a = math.radians(p.ch.angle)
        tx = min(max(p.x + math.sin(a) * 9.0, x0 + 0.5), x1 - 0.5)
        tz = min(max(p.z + math.cos(a) * 9.0, z0 + 0.5), z1 - 0.5)
        self.caw_cd = 7.0
        g = self.game
        g.audio.play('caw', 0.9)
        crow = CrowBird(self.root, scale=0.7)
        crow.root.position = (p.x, 1.6, p.z)
        sx, sz = (p.x, p.z)
        t0 = {'t': 0.0}
        landing = Vec3(tx, 2.4, tz)

        def fly(dt, c=crow):
            t0['t'] += dt
            t = t0['t']
            if t < 1.0:
                k = ease_out(t)
                c.root.x = sx + (tx - sx) * k
                c.root.z = sz + (tz - sz) * k
                c.root.y = 1.6 + (landing.y - 1.6) * k + math.sin(k * math.pi) * 1.2
                c.root.rotation_y = math.degrees(math.atan2(tx - sx, tz - sz))
                c.speed = 12.0
            elif t < 3.3:
                c.speed = 0.0
                c.wing_l.rotation_z, c.wing_r.rotation_z = (-70, 70)
                if t0.get('cawed') is None and t > 1.05:
                    t0['cawed'] = True
                    g.audio.play('caw', 0.7, pitch=1.1)
            elif t < 4.6:
                c.speed = 13.0
                c.root.y += 6.0 * dt
                c.root.x += 1.5 * dt
            else:
                if not t0.get('done'):
                    t0['done'] = True
                    destroy(c.root)
                    self.tl.after(0.0, lambda: fly in self.updaters and self.updaters.remove(fly))
                return
            c.update(Clock.now)
        self.updaters.append(fly)
        self.fx.sparks((tx, 2.2, tz), 8, color0=(0.5, 0.6, 1.0, 1.0), color1=(0.2, 0.3, 0.8, 0.0))
        for gd in self.guards:
            if gd.alive and gd is not self.varro and (gd.state != 'chase') and (self.zone_of(gd.x, gd.z) == zone) and (math.hypot(gd.x - tx, gd.z - tz) < 18.0):
                gd.hear(tx, tz)
        self.tl.after(1.0, lambda: self.game.hud.hint('They heard it. Slip past while they look.', hold=2.5))

    def on_action(self):
        if self.phase != 'infiltrate':
            return
        p = self.player
        for gd in self.guards:
            if gd is self.varro:
                continue
            if gd.alive and gd.state != 'chase' and gd.in_takedown_range(p, 1.9):
                if gd.is_behind(p):
                    self.takedown(gd)
                else:
                    self.game.hud.hint('He is facing you - get behind him first.', hold=2.2)
                return

    def takedown(self, gd):
        p = self.player
        p.ch.face(gd.x - p.x, gd.z - p.z)
        p.ch.attack()
        self.abil.kill_guard(gd, 'takedown')
        self.cam.shake(0.08, 0.25)
        Clock.time_scale = 0.35
        self.tl.after(0.1, lambda: setattr(Clock, 'time_scale', 1.0))

    def guard_down(self, gd, how):
        self.kills += 1
        self.bodies.append([gd.x, gd.z, set()])

    def _interactions(self):
        super()._interactions()
        if self.phase == 'infiltrate' and self._near is None and (not self.cutscene_active) and (not self.failing):
            for gd in self.guards:
                if gd is not self.varro and gd.alive and (gd.state != 'chase') and gd.in_takedown_range(self.player, 1.9) and gd.is_behind(self.player):
                    self.game.hud.prompt('[SPACE]  Silence him')
                    break

    def on_update(self, dt):
        p = self.player
        self.mist.pos = Vec3(p.x, 0.2 + p.ch.root.y, p.z)
        if self.caw_cd > 0:
            self.caw_cd = max(0.0, self.caw_cd - dt)
        self._stealth_upkeep(dt)

    def _stealth_upkeep(self, dt):
        g = self.game
        if self.phase == 'infiltrate' and self.stealth_active and (not self.failing):
            peak = max((gd.awareness for gd in self.guards if gd.alive), default=0.0)
            vig = g.post.values.get('vignette', 0.5)
            g.post.values['vignette'] = vig + (0.52 + 0.36 * peak - vig) * min(1.0, dt * 6.0)
            for gd in self.guards:
                if not gd.alive or gd is self.varro or gd.state == 'chase' or (gd.investigate is not None):
                    continue
                for body in self.bodies:
                    if gd in body[2]:
                        continue
                    dx, dz = (body[0] - gd.x, body[1] - gd.z)
                    d = math.hypot(dx, dz)
                    if d < gd.view * 0.8:
                        ang = abs((gd.facing - math.degrees(math.atan2(dx, dz)) + 180.0) % 360.0 - 180.0)
                        if ang < gd.fov / 2.0 and self.world.line_of_sight(gd.x, gd.z, body[0], body[1]):
                            body[2].add(gd)
                            gd.hear(body[0], body[1])
                            g.hud.hint('A guard has found a body!', hold=2.2)

    def on_hall(self):
        if self.phase == 'infiltrate' and (not self.failing):
            self.tl.run(self.reveal())

    def reveal(self):
        g = self.game
        self.phase = 'reveal'
        self.stealth_active = False
        self.abil.sight_off(cooldown=0.0)
        self.begin_cutscene()
        for gd in self.guards:
            gd.awareness = 0.0
        vx, vz = VARRO_POS
        self.shot((vx - 7.5, 4.8, vz - 8.5), (vx, 1.3, vz), speed=1.1)
        yield 2.0
        yield from self.talk([('Varro', 'Double the watch on the east road. Whoever is killing my officers is no ghost.'), ('Legionary', 'Sir... the men say he is a crow. A shadow that walks through walls.'), ('Varro', 'Then we shall see how a shadow bleeds. Any soldier who whispers that name is flogged.')], {'Varro': self.varro.ch, 'Legionary': self.e1.ch})
        yield 0.4
        self.checkpoint = (min(max(self.player.x, 4.2), 19.8), min(max(self.player.z, 33.4), 40.0))
        self.end_cutscene()
        self.phase = 'infiltrate'
        self.stealth_active = True
        self.varro_it.enabled = True
        g.hud.objective('Kill Varro - from behind. Pull the guards away with Q, or blind them with smoke')
        g.hud.hint('Varro looks at the map. Get behind him and press E. Two elite guards watch the room.', hold=8)

    def on_assassinate(self):
        if self.phase != 'infiltrate' or self.failing:
            return
        v = self.varro
        p = self.player
        if not v.alive:
            return
        if not v.is_behind(p) or v.awareness > 0.4:
            self.game.hud.hint('He would see you. Get behind him, out of the light of his candle.', hold=2.5)
            return
        for gd in self.guards:
            if gd.alive and gd is not v and (gd.awareness > 0.35):
                self.game.hud.hint('A guard is watching you. Wait.', hold=2.2)
                return
        self.tl.run(self.finale())

    def finale(self):
        g = self.game
        v = self.varro
        n = self.abdo
        self.phase = 'kill'
        self.stealth_active = False
        self.abil.sight_off(cooldown=0.0)
        self.abil.enabled = False
        self.begin_cutscene()
        g.hud.objective(None)
        self.varro_it.enabled = False
        for gd in self.guards:
            gd.awareness = 0.0
            gd.investigate = None
            gd.ch.amount = 0.0
            gd.alive, gd.state = (False, 'dead')
            gd.cone.enabled = False
        yield from self.walk(n, v.x, v.z - 1.05, speed=1.8)
        n.face(0, 1)
        g.audio.stop_all(fade=1.2)
        self.shot((v.x - 2.6, 1.4, v.z - 3.2), (v.x, 1.4, v.z + 0.3), speed=1.3)
        g.post.tween(1.4, vignette=0.85, desat=0.3, bloom=1.2)
        yield 1.7
        Clock.time_scale = 0.2
        n.attack()
        g.audio.play('blade', 1.0)
        yield 0.22
        g.post.flash((1.0, 1.0, 1.0), 0.7, 2.6)
        g.post.punch_aberration(0.025)
        self.fx.sparks((v.x, 1.3, v.z), 26, color0=(1.0, 0.95, 0.8, 1.0), color1=(1.0, 0.4, 0.2, 0.0))
        self.ring_fx((v.x, v.z), (0.8, 0.9, 1.0), 7.0, 0.9, y=0.1)
        self.flash_light((v.x, 1.6, v.z), (0.8, 0.9, 1.0), 3.5, 10, 0.7)
        self.cam.shake(0.25, 0.5)
        v.ch.set_pose('kneel')
        yield 0.5
        Clock.time_scale = 1.0
        g.audio.play('thud', 0.9)
        g.audio.play('stinger', 0.8)
        yield 1.2
        yield from self.talk([('Varro', 'Who... who are you?'), ('Abdo', 'A man you left alive. There is nothing left of him now but a crow.'), ('Varro', '...a crow... in the dark...')], {'Abdo': n, 'Varro': v.ch})
        v.ch.set_pose('fall')
        g.audio.play('thud', 0.7)
        self.tl.to(self.standard, 'rotation_z', -78, 1.4, ease_in)
        self.tl.after(1.0, lambda: g.audio.play('banner_fall', 0.9))
        self.tl.to(self.varro_candle, 'scale', 0.0, 1.2)
        self.shot((v.x + 1.8, 3.4, v.z - 5.0), (v.x + 1.0, 1.2, v.z + 0.5), speed=0.9)
        yield 1.6
        g.audio.play('alert', 0.9)
        e1, e2 = (self.e1.ch, self.e2.ch)
        self.go(e1, n.x + 3.0, n.z - 0.4, speed=3.6)
        self.go(e2, n.x - 3.2, n.z - 1.0, speed=3.6)
        yield 1.0
        yield from self.talk([('Legionary', 'The Centurion! Sound the alarm! Seal the gates!')], {'Legionary': e1})
        yield from self.flock_exit()
        yield from self.handoff()

    def flock_exit(self):
        g = self.game
        n = self.abdo
        cx, cz = (n.x, n.z)
        self.shot((cx - 3.8, 2.6, cz - 4.6), (cx, 1.3, cz), speed=1.4)
        flock = []
        for i in range(22):
            b = CrowBird(self.root, scale=random.uniform(0.55, 0.85))
            b.root.position = (cx, -3.0, cz)
            flock.append((b, i))
        feathers = Emitter(self.root, (cx, 1.2, cz), rate=0, max_particles=60, life=(2.0, 4.0), speed=(0.2, 1.2), direction=(0, 0.4, 0), spread=1.4, size=(0.2, 0.14), color0=(0.03, 0.03, 0.05, 0.95), color1=(0.03, 0.03, 0.05, 0.0), gravity=-0.9, drag=0.4, turbulence=2.6, texture='smoke', blend='alpha', bin_sort=34)
        feathers.cull = False
        self.fx.add(feathers)
        t0 = Clock.now
        state = {'spread': 0.0, 'lift': 0.0, 'on': True}

        def swirl(dt):
            if not state['on']:
                return
            t = Clock.now - t0
            for b, i in flock:
                a = t * (2.8 + 0.04 * i) + i * 0.62
                r = 0.7 + state['spread'] * (1.8 + i % 4 * 0.7)
                rise = min(t, 2.0) * 0.9 + i % 5 * 0.32 + math.sin(a * 0.7 + i) * 0.25 + state['lift'] * (3.0 + i % 6 * 1.4)
                drift = state['lift'] * (6.0 + i % 4 * 2.0)
                b.root.position = (cx + math.cos(a) * r - drift * 0.4, 0.2 + rise, cz + math.sin(a) * r + drift)
                b.root.rotation_y = -math.degrees(a)
                b.speed = 12.0
                b.update(Clock.now)
        self.updaters.append(swirl)
        g.audio.play('wingbeat', 0.9)
        g.audio.play('caw', 0.9)
        g.audio.play('caw', 0.8, pitch=0.9)
        yield 0.5
        for L in list(self.rig.lights):
            self.tl.to(L, 'scale', 0.05, 1.2)
        g.post.tween(1.6, vignette=0.9, desat=0.0, bloom=1.0, tint=(0.8, 0.88, 1.15))
        g.audio.play('wingbeat', 1.0)
        yield 1.5
        for _ in range(3):
            feathers.burst(14)
            yield 0.15
        g.post.flash((0.0, 0.0, 0.0), 1.0, 2.4)
        n.root.enabled = False
        self.mist.enabled = False
        self.cam.shake(0.3, 0.8)
        g.audio.play('stinger', 0.9)
        self.tl.to_item(state, 'spread', 1.0, 1.6)
        yield 1.4
        self.shot((cx - 2.0, 4.0, cz - 7.0), (cx, 5.0, cz + 2.0), speed=0.9)
        self.tl.to_item(state, 'lift', 1.0, 5.5, ease_in)
        feathers.burst(18)
        yield 2.2
        self.shot((cx - 4.0, 6.0, cz - 14.0), (cx + 2.0, 12.0, cz + 10.0), speed=0.6)
        yield 2.6
        for L in list(self.rig.lights):
            self.tl.to(L, 'scale', 1.0, 2.0)
        g.audio.music('mus_legend', 0.55, fade=2.0)
        g.audio.play('fanfare', 0.8)
        yield 2.4
        state['on'] = False
        self.updaters.remove(swirl)
        for b, i in flock:
            b.root.enabled = False

    def handoff(self):
        g = self.game
        self.phase = 'ending'
        self.shot((0.0, 11.0, -34.0), (0.0, 7.0, 30.0), speed=0.4)
        self.cam.set_fov(56)
        g.hud.fade_to(0.0, 0.5)
        g.hud.caption('Rome lost its Centurion that night.', hold=3.0, fade=1.0, size=1.9)
        yield 4.6
        g.hud.caption('The soldiers swore a crow circled the fort before the bells rang.', hold=3.2, fade=1.0, size=1.7)
        yield 4.8
        g.hud.caption("On Varro's war table, one name was circled in red: Prefect Marcellus, of Antioch.", hold=3.6, fade=1.0, size=1.7)
        yield 5.2
        self.shot((0.0, 4.0, -34.0), (25.0, 52.0, 140.0), speed=0.35)
        g.hud.title_card('THREE NAMES DOWN', 'THE NIGHT CROW', 'Mission II  -  The Rooftops of Antioch', hold=3.4, fade=1.2)
        yield 5.6
        g.hud.fade_to(1.0, 1.6)
        yield 2.0
        g.next_scene()

    def destroy(self):
        for e in self.ui:
            try:
                destroy(e)
            except Exception:
                pass
        super().destroy()
