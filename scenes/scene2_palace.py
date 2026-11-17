import math
import random
from ursina import Entity, Vec3, color, destroy
from engine.assets import tex
from engine.ai import Follower, Guard
from engine.entities import glow_quad, mk, rgb, shade, torus_model
from engine.props import Sky, arch_gate, banner, bed, blood_pool, brazier, bush, chest, contact_shadow, crate, door_panel, ground, ground_patches, flower_bed, hanging_rope, hedge, house, lantern, throne, light_shaft, moon, palm, pillar, planets, rug, scatter_clutter, stairs, torch, wall_box, weapon_rack
from engine.scene_base import BaseScene
from engine.timing import Clock, ease_in, ease_out
GATE_Z = 21.0
HALL_Z0, HALL_Z1 = (34.0, 50.0)
DOOR_X = -8.0
STAGE_X = 300.0
GUARD = dict(robe=rgb(54, 62, 80), trim=rgb(196, 198, 210), head='helmet', head_color=rgb(128, 134, 148), weapon='spear', build='broad', skin='tan')
NIGHT = dict(ambient=Vec3(0.17, 0.2, 0.33), sun=Vec3(0.34, 0.44, 0.72), sun_dir=Vec3(0.3, 0.8, -0.5), fog=Vec3(0.05, 0.075, 0.15), tint=(0.94, 0.99, 1.08))
DAWN = dict(ambient=Vec3(0.34, 0.34, 0.42), sun=Vec3(0.78, 0.6, 0.5), sun_dir=Vec3(-0.65, 0.55, 0.45), fog=Vec3(0.4, 0.36, 0.4), tint=(1.0, 0.96, 0.95))

class Scene2Palace(BaseScene):
    number = 2
    name = 'The Fallen King'
    author = 'Rami Abdo Hezam'

    def build(self):
        g = self.game
        self.phase = 'intro'
        self.checkpoint = (-15.0, 3.4)
        self.kills = 0
        self.guard_home = {}
        self.brazier_parts = []
        self.clue1_done = False
        self.clue2_done = False
        rig = self.rig
        rig.ambient, rig.sun_color, rig.sun_dir, rig.fog_color = (NIGHT['ambient'], NIGHT['sun'], NIGHT['sun_dir'], NIGHT['fog'])
        rig.fog_density = 0.015
        g.post.set(vignette=0.5, bloom=0.8, tint=NIGHT['tint'], grain=0.045, desat=0.0)
        self.cam.pitch, self.cam.distance = (40, 13.5)
        self.cam.set_fov(68)
        self.bounds = (-19.2, 19.2, -0.4, 60.2)
        self.stealth_light = True
        self.sky = Sky(self, 'sky_night', stars=True)
        self.moon = moon(self, (70, 58, 160), size=30)
        planets(self, ringed=(-125, 52, 150), red=(118, 80, 150))
        self._build_courtyard()
        self._build_colonnade()
        self._build_hall()
        self._build_chamber()
        self._build_shadow_stage()
        self._build_people()
        self._build_atmosphere()
        self.trigger(0, GATE_Z + 1.4, 9, 2.2, lambda: self._checkpoint((0.0, GATE_Z + 2.2), 'Checkpoint'))
        self.trigger(0, HALL_Z0 + 1.0, 9, 2.0, lambda: self._checkpoint((0.0, HALL_Z0 + 1.6), 'Checkpoint'))
        self.trigger(DOOR_X, 48.6, 4.2, 2.4, self.on_chamber_door)
        g.audio.music('mus_palace', 0.5, fade=3.0)
        g.audio.loop('amb_wind', 0.22, fade=3.0)

    def _build_courtyard(self):
        stone = rgb(130, 134, 150)
        ground(self, 190, 'stone', 70, stone)
        ground_patches(self, -20, 0, 20, 20, count=46, seed=11, palette=[rgb(52, 82, 56), rgb(44, 70, 52), rgb(70, 94, 66), rgb(40, 62, 50)], alpha=(0.35, 0.6), size=(4.0, 8.0))
        scatter_clutter(self, -19, 0.5, 19, 20, count=46, seed=3, avoid=[(-3, 3, 7, 13)], grass=rgb(60, 92, 62), pebble=rgb(110, 110, 124))
        W = rgb(150, 148, 164)
        h = 5.4
        hs = 2.3
        wall_box(self, -12.0, -1.0, 17.0, 1.2, hs, 'mudbrick', W)
        wall_box(self, 12.0, -1.0, 17.0, 1.2, hs, 'mudbrick', W)
        arch_gate(self, 0, -1.0, width=8.0, h=3.2, depth=1.4, gap=4.0, col=W, lintel=False)
        wall_box(self, 0, 62.4, 43.2, 1.2, h, 'mudbrick', W)
        wall_box(self, -21.0, 30.7, 1.2, 64.8, h, 'mudbrick', W)
        wall_box(self, 21.0, 30.7, 1.2, 64.8, h, 'mudbrick', W)
        for x in range(-20, 21, 2):
            for z in (-1.0, 62.4):
                if z < 0 and abs(x) < 4:
                    continue
                mk(self.root, 'cube', (x, (hs if z < 0 else h) + 0.3, z), (0.8, 0.6, 1.3), shade(W, 0.6 if z < 0 else 0.9))
        for z in range(1, 62, 2):
            for x in (-21.0, 21.0):
                mk(self.root, 'cube', (x, h + 0.35, z), (1.3, 0.7, 0.9), shade(W, 0.95))
        hanging_rope(self, -16.0, -0.36, top_y=hs + 0.6, bottom_y=0.45, hook_z=-1.62)
        wall_box(self, -12.4, GATE_Z, 17.2, 1.2, 2.4, 'mudbrick', W)
        wall_box(self, 12.4, GATE_Z, 17.2, 1.2, 2.4, 'mudbrick', W)
        arch_gate(self, 0, GATE_Z, width=7.6, h=3.4, depth=1.4, gap=3.6, col=shade(W, 1.05), lintel=False)
        banner(self, -2.8, 2.0, GATE_Z - 0.75, 'iron', height=2.4, face='south')
        banner(self, 2.8, 2.0, GATE_Z - 0.75, 'iron', height=2.4, face='south')
        for x0, x1, z in ((-12.5, -4.5, 6.0), (4.5, 12.5, 6.0), (-20.0, -9.0, 13.5), (9.0, 20.0, 13.5)):
            hedge(self, x0, x1, z)
        self._fountain(0.0, 10.0)
        for fx, fz, fw, fd, sd in ((-9.5, 2.6, 5.5, 1.3, 1), (9.5, 2.6, 5.5, 1.3, 2), (-16.0, 8.0, 1.4, 4.0, 3), (16.0, 8.0, 1.4, 4.0, 4)):
            flower_bed(self, fx, fz, fw, fd, seed=sd)
        for bx, bz, bc in ((-17.5, 15.5, (230, 130, 150)), (17.5, 15.5, (240, 230, 190)), (-6.0, 11.5, (210, 90, 110)), (6.0, 11.5, (190, 120, 210))):
            bush(self, bx, bz, 1.1, rgb(46, 78, 52), flowers=bc)
        for x, z in ((-18, 18), (18, 18), (-18, 3), (18, 3), (-14, 10), (14, 10)):
            palm(self, x, z, h=4.4 + abs(x + z) % 3 * 0.3)
        self.brazier_at(-6.0, 17.5)
        self.brazier_at(6.0, 17.5)
        self.brazier_at(0.0, 1.8, scale=0.8, intensity=1.5, radius=9.0)
        self.brazier_at(-18.4, 9.0, scale=0.7, intensity=1.2, radius=8.0)

    def brazier_at(self, x, z, **kw):
        start = len(self.fx.emitters)
        L = brazier(self, x, z, **kw)
        self.brazier_parts.append((L, self.fx.emitters[start:]))
        return L

    def _fountain(self, x, z):
        mk(self.root, 'cylinder', (x, 0, z), (4.0, 0.62, 4.0), rgb(150, 150, 164), tex('stone'))
        mk(self.root, 'cylinder', (x, 0.5, z), (3.5, 0.18, 3.5), rgb(90, 140, 190), emissive=0.35)
        mk(self.root, 'cylinder', (x, 0, z), (0.9, 1.5, 0.9), rgb(150, 150, 164), tex('stone'))
        mk(self.root, 'sphere', (x, 1.7, z), (0.9, 0.5, 0.9), rgb(150, 150, 164))
        mk(self.root, 'cylinder', (x, 1.9, z), (1.9, 0.12, 1.9), rgb(90, 140, 190), emissive=0.3)
        self.world.add_circle(x, z, 2.05)
        contact_shadow(self, x, z, 7.0, 7.0, 0.4)
        self.fx.steam((x, 0.8, z), scale=0.7, rate=3)
        self.tl.every(0.7, lambda: self.fx.magic((x + math.sin(Clock.now) * 1.1, 0.9, z + math.cos(Clock.now * 1.3) * 1.1), color=(0.55, 0.8, 1.0), count=3))

    def _build_colonnade(self):
        W = rgb(150, 148, 164)
        mk(self.root, 'plane', (0, 0.02, 27.5), (20.4, 1, 13.2), rgb(104, 100, 112), tex('tile'), tex_scale=(5, 3.2))
        house(self, -15.6, 27.5, 10.4, 12.4, h=3.8, door='none', texture='mudbrick', col=rgb(140, 138, 156))
        house(self, 15.6, 27.5, 10.4, 12.4, h=3.8, door='none', texture='mudbrick', col=rgb(140, 138, 156))
        for z in (24.0, 28.0, 32.0):
            for x in (-5.0, 5.0):
                pillar(self, x, z, h=4.2, r=0.32, col=rgb(176, 172, 188))
        rug(self, 0, 27.5, 3.2, 12.0, repeat=(1, 3))
        self.brazier_at(-8.6, 22.6, scale=0.8, intensity=1.7, radius=10.0)
        self.brazier_at(8.6, 22.6, scale=0.8, intensity=1.7, radius=10.0)
        torch_l = torch(self, -2.4, 33.4, h=2.3, intensity=1.5, radius=9.0)
        torch_r = torch(self, 2.4, 33.4, h=2.3, intensity=1.5, radius=9.0)
        for g_ in (-8.4, 8.4):
            light_shaft(self, g_, 0.0, 28.0, height=5.4, width=2.2, color=(0.55, 0.7, 1.0, 0.2), tilt=-9 if g_ < 0 else 9)
        barrel_pos = ((-9.2, 31.5), (-9.2, 30.4), (9.2, 25.0))
        for bx, bz in barrel_pos:
            mk(self.root, 'cylinder', (bx, 0, bz), (0.9, 1.0, 0.9), rgb(110, 76, 48), tex('wood'))
            self.world.add_circle(bx, bz, 0.5)
        crate(self, 9.2, 26.0, 0.9)

    def _build_hall(self):
        W = rgb(176, 160, 150)
        H0, H1 = (HALL_Z0, HALL_Z1)
        cz = (H0 + H1) / 2.0
        mk(self.root, 'plane', (0, 0.02, cz), (24.2, 1, H1 - H0), rgb(104, 100, 112), tex('tile'), tex_scale=(6, 4.0))
        rug(self, 0, cz - 1.0, 4.2, 13.0, repeat=(1, 3))
        wall_box(self, -12.0, cz, 0.8, H1 - H0, 5.8, 'plaster', W)
        wall_box(self, 12.0, cz, 0.8, H1 - H0, 5.8, 'plaster', W)
        wall_box(self, -7.0, H0, 10.0, 0.8, 1.0, 'plaster', W)
        wall_box(self, 7.0, H0, 10.0, 0.8, 1.0, 'plaster', W)
        wall_box(self, (-12.0 + DOOR_X - 1.2) / 2.0, H1, DOOR_X - 1.2 + 12.0, 0.8, 5.8, 'plaster', W)
        wall_box(self, (DOOR_X + 1.2 + 12.0) / 2.0, H1, 12.0 - (DOOR_X + 1.2), 0.8, 5.8, 'plaster', W)
        mk(self.root, 'cube', (DOOR_X, 4.7, H1), (2.6, 2.2, 0.8), shade(W, 0.92), tex('plaster'))
        self.chamber_door = door_panel(self, DOOR_X, H1 - 0.05, width=2.4, h=3.5, axis='x')
        for z in (37.5, 41.5, 45.5):
            for x in (-7.0, 7.0):
                pillar(self, x, z, h=4.6, r=0.32, col=rgb(186, 176, 170))
        mk(self.root, 'cube', (3.2, 0.3, 47.6), (9.0, 0.6, 4.4), rgb(150, 70, 60), tex('stone'))
        stairs(self, 3.2, 44.7, 5.0, steps=3, rise=0.2, run=0.5, axis='z')
        throne(self, 3.2, 48.7, ry=180, y=0.6)
        self.world.add_box(3.2, 47.6, 9.0, 4.4, blocks_sight=False)
        for x in (-11.0, -4.6, 0.2, 6.2, 10.8):
            banner(self, x, 3.2, H1 - 0.5, 'iron', height=3.2, face='south')
        self.brazier_at(-2.2, 46.6, scale=0.85, intensity=1.9, radius=11.0)
        self.brazier_at(8.8, 46.6, scale=0.85, intensity=1.9, radius=11.0)
        weapon_rack(self, -11.0, 38.0, rot=90)
        chest(self, 10.8, 36.5, rot=0)

    def _build_chamber(self):
        W = rgb(170, 150, 150)
        z0, z1 = (HALL_Z1, 61.0)
        cx = -8.0
        mk(self.root, 'plane', (cx, 0.02, (z0 + z1) / 2.0), (12.0, 1, z1 - z0), rgb(104, 100, 112), tex('tile'), tex_scale=(3, 3))
        rug(self, cx, 55.6, 7.0, 6.0, rot=0)
        wall_box(self, -14.0, (z0 + z1) / 2.0, 0.8, z1 - z0, 4.6, 'plaster_plain', W)
        wall_box(self, -2.0, (z0 + z1) / 2.0, 0.8, z1 - z0, 4.6, 'plaster_plain', W)
        wall_box(self, cx, z1, 12.8, 0.8, 4.6, 'plaster_plain', W)
        bed(self, -5.2, 59.23, w=1.5, d=2.6, col=rgb(150, 70, 90), head='+z')
        self.curtain_prop = Entity(parent=self.root, position=(-11.2, 0.0, 56.6), add_to_scene_entities=False)
        n_pl = 26
        pw = 6.4 / n_pl
        for i in range(n_pl):
            sh = i % 2
            mk(self.curtain_prop, 'cube', (pw * (i + 0.5), 1.45, 0.07 * sh - 0.035), (pw * 1.04, 2.75 - 0.05 * sh, 0.08), rgb(206, 100, 72) if sh == 0 else rgb(150, 62, 50), emissive=0.62 if sh == 0 else 0.4)
        mk(self.curtain_prop, 'cube', (3.2, 0.1, 0.0), (6.44, 0.2, 0.13), rgb(104, 36, 32), emissive=0.2)
        mk(self.curtain_prop, 'cube', (3.2, 0.26, 0.0), (6.44, 0.06, 0.14), rgb(214, 170, 84), emissive=0.5)
        for i in range(0, n_pl, 2):
            mk(self.curtain_prop, torus_model(0.2), (pw * (i + 0.5), 2.88, 0.0), (0.2, 0.2, 0.2), rgb(214, 170, 84), rot=(0, 0, 90), emissive=0.4)
        mk(self.root, 'cube', (-8.0, 2.88, 56.55), (6.9, 0.1, 0.12), rgb(86, 56, 38), tex('wood'))
        for sx in (-3.5, 3.5):
            mk(self.root, 'sphere', (-8.0 + sx, 2.88, 56.55), (0.2, 0.2, 0.2), rgb(214, 170, 84), emissive=0.4)
        glow_quad(self.root, (-8.0, 1.5, 56.45), (7.4, 3.6), (1.0, 0.62, 0.3, 0.3), tex('glow'), billboard=False, add=True)
        cradle_parts = []
        ccx, ccz = (-11.2, 59.55)
        cradle_parts.append(mk(self.root, 'cube', (ccx, 0.35, ccz), (1.0, 0.45, 0.62), rgb(150, 110, 70), tex('wood')))
        cradle_parts.append(mk(self.root, 'cube', (ccx + 0.18, 0.66, ccz - 0.1), (0.84, 0.12, 0.46), rgb(236, 226, 200), rot=(0, 24, 9)))
        mk(self.root, 'cube', (ccx, 0.08, ccz - 0.3), (1.1, 0.08, 0.1), rgb(110, 76, 48))
        mk(self.root, 'cube', (ccx, 0.08, ccz + 0.3), (1.1, 0.08, 0.1), rgb(110, 76, 48))
        self.world.add_circle(ccx, ccz, 0.65)
        self.toy = Entity(parent=self.root, position=(-9.0, 0.0, 53.4), rotation_y=24, add_to_scene_entities=False)
        mk(self.toy, 'cube', (0, 0.22, 0), (0.46, 0.2, 0.14), rgb(160, 110, 64))
        mk(self.toy, 'cube', (0.2, 0.36, 0), (0.12, 0.24, 0.12), rgb(160, 110, 64))
        mk(self.toy, 'cube', (-0.17, 0.08, 0.04), (0.06, 0.16, 0.06), rgb(110, 76, 48))
        mk(self.toy, 'cube', (0.17, 0.08, 0.04), (0.06, 0.16, 0.06), rgb(110, 76, 48))
        self.chamber_light = lantern(self, -8.0, 59.6, y=2.6, intensity=0.9, radius=8.0)[0]
        self.window_shaft = light_shaft(self, -12.6, 0.0, 55.0, height=4.4, width=2.0, color=(0.6, 0.74, 1.0, 0.24), tilt=-10)

    def _build_shadow_stage(self):
        X, Z = (STAGE_X, 0.0)
        self.stage_root = Entity(parent=self.root, position=(X, 0, Z), add_to_scene_entities=False)
        S = self.stage_root
        mk(S, 'quad', (0, 4.0, 7.0), (60, 22, 1), rgb(6, 5, 8))
        mk(S, 'plane', (0, 0.0, 2.0), (40, 1, 20), rgb(8, 6, 8))
        self.curtain = mk(S, 'quad', (0, 2.1, 4.0), (7.2, 3.9, 1), rgb(236, 150, 70), emissive=1.0)
        for i in range(-6, 7):
            mk(S, 'quad', (i * 0.55, 2.1, 3.97), (0.1, 3.9, 1), rgb(190, 112, 52), emissive=0.9)
        self.curtain_glow = glow_quad(S, (0, 2.1, 3.9), (10.5, 6.2), (1.0, 0.62, 0.28, 0.3), tex('glow'), billboard=False, add=True, bin_sort=30)
        for pos, sc in (((0, 4.12, 3.9), (7.8, 0.28, 0.24)), ((0, 0.02, 3.9), (7.8, 0.2, 0.24)), ((-3.8, 2.1, 3.9), (0.26, 4.2, 0.24)), ((3.8, 2.1, 3.9), (0.26, 4.2, 0.24))):
            mk(S, 'cube', pos, sc, rgb(20, 12, 10))
        self.stage_figures = {}
        self.stage_figures['queen'] = self._silhouette(S, 1.7, 1.0, queen=True)
        self.stage_figures['killer'] = self._silhouette(S, -5.2, 1.12, hood=True, dagger=True)
        self.stage_root.enabled = True

    def _silhouette(self, parent, x, s, hood=False, queen=False, dagger=False):
        black = rgb(3, 2, 4)
        root = Entity(parent=parent, position=(x, 0, 3.55), add_to_scene_entities=False)
        mk(root, 'cone', (0, 0.0, 0), ((1.5 if queen else 1.05) * s, 2.1 * s, 0.03), black)
        mk(root, 'sphere', (0, 1.62 * s, 0), (0.78 * s, 0.34 * s, 0.03), black)
        head = mk(root, 'sphere', (0, 2.06 * s, 0), (0.36 * s, 0.44 * s, 0.03), black)
        if hood:
            mk(root, 'cone', (0, 1.98 * s, 0), (0.66 * s, 0.72 * s, 0.03), black)
        if queen:
            mk(root, 'sphere', (0.0, 1.78 * s, 0), (0.62 * s, 0.95 * s, 0.03), black)
        arms = []
        for side in (-1, 1):
            piv = Entity(parent=root, position=(0.36 * s * side, 1.62 * s, 0), add_to_scene_entities=False)
            mk(piv, 'cylinder', (0, -0.85 * s, 0), (0.13 * s, 0.85 * s, 0.03), black)
            arms.append(piv)
        blade = None
        if dagger:
            blade = mk(arms[1], 'cylinder', (0, -1.0 * s, 0), (0.05, 0.62 * s, 0.03), black)
            mk(arms[1], 'cylinder', (0, -0.86 * s, 0), (0.22 * s, 0.05, 0.03), black, rot=(0, 0, 90))
        root.arm_l, root.arm_r, root.blade = (arms[0], arms[1], blade)
        return root

    def _build_people(self):
        self.abdo = self.add_char((-15.0, 3.4), robe=rgb(66, 54, 52), trim=rgb(150, 56, 40), head='scarf', head_color=rgb(40, 36, 44), skin='tan', cloak=rgb(34, 30, 36))
        self.abdo.face(0, 1)
        self.set_player(self.abdo, speed=3.3, run_speed=5.6)
        self.player.step_sound = 'step_stone'
        self.assassin1 = self.add_char((-16.6, 2.4), robe=rgb(34, 34, 44), trim=rgb(110, 30, 34), head='hood', head_color=rgb(24, 24, 32), skin='light', weapon='dagger')
        self.assassin2 = self.add_char((-13.6, 2.3), robe=rgb(40, 38, 46), trim=rgb(110, 30, 34), head='hood', head_color=rgb(28, 26, 34), skin='olive', build='broad', weapon='dagger')
        for ch in (self.assassin1, self.assassin2):
            ch.face(0, 1)
        self.followers = [Follower(self, self.assassin1, 0.9), Follower(self, self.assassin2, 1.8)]
        for f in self.followers:
            self.actors.append(f)
            self.actors.remove(f.ch)
        spec = [dict(pos=(-9, 3.6), route=[(-9, 3.6), (9, 3.6)], facing=90, pause=2.2), dict(pos=(-6, 19.2), route=[(-6, 19.2), (6, 19.2)], facing=90, pause=2.8, view=9.0), dict(pos=(-8, 26.5), route=[(-8, 26.5), (8, 26.5)], facing=90, pause=2.0, view=9.0), dict(pos=(-5, 38), route=[(-5, 38), (-5, 46)], facing=0, pause=2.0, view=9.5), dict(pos=(7, 42), route=[], facing=270, sweep=44, view=9.5)]
        for sp in spec:
            gd = Guard(self, sp['pos'], route=sp['route'], facing=sp['facing'], speed=1.5, view=sp.get('view', 8.4), fov=74, pause=sp.get('pause', 1.6), sweep=sp.get('sweep', 36), **GUARD)
            gd.alert_mult = 0.85
            self.add_guard(gd)
            self.guard_home[gd] = (sp['pos'], sp['facing'])

    def _build_atmosphere(self):
        self.fx.dust((0, 2.0, 12), area=(34, 3.0, 22), count=46, color=(0.6, 0.72, 1.0), alpha=0.32, size=0.1)
        self.fx.dust((0, 2.0, 41), area=(22, 3.0, 14), count=30, color=(1.0, 0.8, 0.55), alpha=0.32, size=0.1)
        self.fireflies = self.fx.fireflies((0, 1.4, 10), area=(34, 1.2, 18), count=20, color=(0.7, 0.9, 1.0))
        self.fx.smoke((60, 0.0, 70), scale=6.0, rate=2, tone=0.18, alpha=0.2).cull = False

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
        self.shot((-19.0, 6.5, -6.5), (-14.5, 1.0, 3.6), speed=9)
        self.cam.snap()
        g.hud.title_card('FRIDAY NIGHT', 'The Palace of Khaled bin Qusey', '', hold=2.2)
        yield 3.6
        self.shot((-18.2, 2.4, -0.2), (-15.0, 1.3, 3.8), speed=0.8)
        yield from self.talk([('Assassin', 'Over the wall and into the garden. The guard changes at the midnight bell. We have until then.'), ('Abdo', 'Stay in the dark and move when their backs are turned. If one of them sees us, none of us leaves.'), ('Assassin', 'And Khaled?'), ('Abdo', 'Asleep in the north wing. One blade, one night, and we are gone.')], {'Abdo': self.abdo, 'Assassin': self.assassin1})
        self.end_cutscene()
        self.phase = 'abdo'
        self.stealth_active = True
        g.hud.objective('Reach the royal chambers - stay out of sight')
        g.hud.hint('WASD  move      Shift  run (it is loud)      SPACE  silence a guard from BEHIND      Stay in the dark', hold=10)

    def _checkpoint(self, pos, label):
        if self.phase != 'abdo':
            return
        self.checkpoint = pos
        self.game.hud.caption(label, hold=0.6, fade=0.35, size=1.3, tone=(0.75, 0.85, 1.0))

    def reset_section(self):
        cx, cz = self.checkpoint
        self.player.teleport(cx, cz)
        self.abdo.face(0, 1)
        for i, f in enumerate(self.followers):
            f.ch.root.x, f.ch.root.z = (cx - 1.0 - i * 1.0, cz - 1.0)
        for gd, (pos, facing) in self.guard_home.items():
            if gd.alive:
                gd.ch.root.x, gd.ch.root.z = pos
                gd.ch.angle = facing
                gd.ch.root.rotation_y = facing
                gd.wp, gd.wait, gd.look_offset = (0, 0.0, 0.0)
                gd.state, gd.awareness = ('patrol', 0.0)
                gd.spotted_called = False

    def on_action(self):
        if self.phase != 'abdo':
            return
        p = self.player
        for gd in self.guards:
            if gd.alive and gd.state != 'chase' and gd.in_takedown_range(p, 1.9):
                if gd.is_behind(p):
                    self.takedown(gd)
                else:
                    self.game.hud.hint('He is facing you - get behind him first.', hold=2.2)
                return

    def takedown(self, gd):
        g = self.game
        p = self.player
        p.ch.face(gd.x - p.x, gd.z - p.z)
        p.ch.attack()
        gd.kill()
        self.kills += 1
        g.state['palace_kills'] = self.kills
        g.audio.play('thud', 0.8)
        self.fx.dust_puff((gd.x, 0.2, gd.z), 7)
        self.fx.sparks((gd.x, 1.2, gd.z), 8, color0=(0.8, 0.9, 1.0, 1.0), color1=(0.4, 0.5, 0.9, 0.0))
        self.ring_fx((gd.x, 0, gd.z), (0.7, 0.85, 1.0), 3.2, 0.5, y=0.1)
        self.cam.shake(0.08, 0.25)
        Clock.time_scale = 0.35
        self.tl.after(0.1, lambda: setattr(Clock, 'time_scale', 1.0))

    def _interactions(self):
        super()._interactions()
        if self.phase == 'abdo' and self._near is None and (not self.cutscene_active) and (not self.failing):
            for gd in self.guards:
                if gd.alive and gd.state != 'chase' and gd.in_takedown_range(self.player, 1.9) and gd.is_behind(self.player):
                    self.game.hud.prompt('[SPACE]  Silence him')
                    break

    def on_update(self, dt):
        g = self.game
        if self.phase == 'abdo' and self.stealth_active and (not self.failing):
            peak = max((gd.awareness for gd in self.guards if gd.alive), default=0.0)
            vig = g.post.values.get('vignette', 0.5)
            g.post.values['vignette'] = vig + (0.5 + 0.38 * peak - vig) * min(1.0, dt * 6.0)
            self.fireflies.enabled = True
        if self.phase == 'dawn' or self.phase == 'khaled':
            pass

    def on_chamber_door(self):
        if self.phase == 'abdo' and (not self.failing):
            self.tl.run(self.chamber_seq())

    def chamber_seq(self):
        g = self.game
        self.phase = 'chamber'
        self.stealth_active = False
        self.begin_cutscene()
        for gd in self.guards:
            gd.awareness = 0.0
        g.hud.objective(None)
        g.audio.stop('amb_wind', 1.5)
        yield from self.walk(self.abdo, DOOR_X, 49.4, speed=2.2)
        self.abdo.face(0, 1)
        self.go(self.assassin1, DOOR_X - 1.1, 48.2)
        self.go(self.assassin2, DOOR_X + 1.1, 48.2)
        for f in self.followers:
            f.active = False
        self.shot((DOOR_X + 2.8, 2.2, 45.4), (DOOR_X, 1.6, 50.5), speed=1.1)
        yield 1.4
        g.audio.play('door_creak', 0.7)
        self.chamber_door.open(105, 1.5)
        yield 1.7
        self.shot((DOOR_X + 0.6, 1.9, 48.6), (DOOR_X - 0.5, 1.2, 56.4), speed=0.8)
        yield 0.8
        yield from self.talk([('Abdo', 'The bed is empty. Khaled is not here.'), ('Assassin', 'His horse is gone from the stables. It does not matter. The Sheikh said the blow must be felt.'), ('Abdo', 'The order was for Khaled. Only Khaled.'), ('Assassin', 'Behind that curtain sleeps everything he loves. Hold the door.')], {'Abdo': self.abdo, 'Assassin': self.assassin1})
        if g.state.get('abdo_doubt'):
            yield from self.talk([('Abdo', 'No - wait! This was never...')], {'Abdo': self.abdo})
            self.assassin2.arm_r_goal = -70
            yield 0.9
            self.assassin2.arm_r_goal = None
            yield from self.talk([('Assassin', 'Hold the door, farmer.')], {'Assassin': self.assassin2})
        else:
            self.abdo.head_turn = 25
            yield 1.0
        self.go(self.assassin1, DOOR_X - 0.4, 55.4)
        self.go(self.assassin2, DOOR_X + 0.6, 55.4)
        yield 1.6
        yield from self.shadow_play()
        g.audio.play('heartbeat', 0.6)
        yield 3.4
        self.tl.run(self.to_dawn())

    def shadow_play(self):
        g = self.game
        g.audio.stop('mus_palace', 1.0)
        g.hud.fade_to(1.0, 0.8)
        yield 1.0
        self.cam.set_fov(52)
        self.shot((STAGE_X + 0.9, 2.1, -4.2), (STAGE_X + 0.9, 2.0, 4.0), speed=99)
        self.cam.snap()
        g.post.set(vignette=0.8, bloom=0.55, grain=0.06, tint=(1.0, 0.93, 0.86), desat=0.0)
        self.rig.ambient = Vec3(0.02, 0.02, 0.03)
        self.rig.sun_color = Vec3(0, 0, 0)
        self.rig.fog_color = Vec3(0.0, 0.0, 0.0)
        q, k = (self.stage_figures['queen'], self.stage_figures['killer'])
        g.audio.loop('music_box', 0.55, fade=0.6)
        g.hud.fade_to(0.0, 1.2)
        self.shot((STAGE_X + 0.9, 2.1, -1.8), (STAGE_X + 0.9, 2.0, 4.0), speed=0.09)
        flick = {'on': True}

        def lamp(dt):
            if flick['on']:
                self.curtain_glow.alpha = 0.28 + 0.06 * math.sin(Clock.now * 7.0) + 0.04 * math.sin(Clock.now * 17.0)
        self.updaters.append(lamp)
        sway = {'on': True}

        def sway_fn(dt):
            if sway['on']:
                q.rotation_z = math.sin(Clock.now * 1.6) * 2.2
                q.arm_l.rotation_z = 8 + math.sin(Clock.now * 1.6) * 5
                q.arm_r.rotation_z = -8 - math.sin(Clock.now * 1.6) * 5
        self.updaters.append(sway_fn)
        yield 4.0
        self.tl.to(k, 'x', -2.3, 3.2)
        yield 2.2
        sway['on'] = False
        self.tl.to(q, 'rotation_z', 0, 0.4)
        self.tl.to(q, 'x', 1.0, 1.2)
        self.tl.to(q.arm_l, 'rotation_z', 70, 0.8)
        self.tl.to(q.arm_r, 'rotation_z', -70, 0.8)
        yield 1.5
        self.tl.to(k, 'x', -0.7, 1.8)
        yield 1.6
        self.tl.to(k.arm_r, 'rotation_z', -150, 0.9)
        g.audio.play('stinger_soft', 0.8)
        g.post.tween(1.8, vignette=0.85, desat=0.3)
        yield 1.4
        self.tl.to(k, 'x', -0.05, 0.22)
        self.tl.to(k.arm_r, 'rotation_z', -92, 0.2)
        yield 0.22
        g.audio.play('blade', 0.9)
        g.audio.play('thud', 0.5)
        g.post.punch_aberration(0.02)
        self.cam.shake(0.12, 0.4)
        self.tl.to(q, 'rotation_z', 16, 0.25)
        self.tl.to(q.arm_l, 'rotation_z', 150, 0.3)
        self.tl.to(q.arm_r, 'rotation_z', -150, 0.3)
        self._splatter(self.stage_root)
        yield 0.9
        self.tl.to(k.arm_r, 'rotation_z', -120, 0.5)
        self.tl.to(k, 'x', -0.6, 0.9)
        self.tl.to(q, 'rotation_z', 84, 1.5, ease_in)
        self.tl.to(q, 'x', 1.5, 1.5, ease_in)
        self.tl.to(q.arm_l, 'rotation_z', 40, 1.2)
        self.tl.to(q.arm_r, 'rotation_z', -40, 1.2)
        yield 1.9
        self.tl.to(k.arm_r, 'rotation_z', -15, 0.8)
        yield 1.7
        flick['on'] = False
        for a in (0.18, 0.3, 0.08, 0.26, 0.0):
            self.curtain_glow.alpha = a
            g.hud.fade_a = 0.55 * (1.0 - a / 0.3)
            yield 0.13
        g.audio.stop('music_box', 0.05)
        g.hud.black()
        self.updaters.remove(lamp)
        self.updaters.remove(sway_fn)
        yield 0.3

    def _splatter(self, stage):
        rg = random.Random(4)
        base_x, base_y = (1.35, 1.45)
        for i in range(9):
            a = rg.uniform(-0.5, 1.1)
            dist = rg.uniform(0.2, 1.5)
            size = rg.uniform(0.1, 0.36)
            d = glow_quad(stage, (base_x + math.cos(a) * dist * 0.9 + 0.3, base_y + math.sin(a) * dist * 0.7, 3.93), (size, size * rg.uniform(0.8, 1.4)), (0.26, 0.012, 0.02, 0.0), tex('glow'), billboard=False, add=False, bin_sort=33)
            self.tl.to(d, 'alpha', 0.95, 0.12)
        for i, dx in enumerate((0.2, 0.85)):
            r = glow_quad(stage, (base_x + dx, base_y, 3.93), (0.08, 0.08), (0.24, 0.01, 0.02, 0.9), tex('glow'), billboard=False, add=False, bin_sort=33)
            self.tl.to(r, 'y', base_y - 0.9 - i * 0.3, 2.6)
            self.tl.to(r, 'scale_y', 0.7 + i * 0.2, 2.6)

    def to_dawn(self):
        g = self.game
        self.phase = 'dawn'
        self.cam.release()
        self.cam.set_fov(68)
        self.chamber_door.pivot.rotation_y = 105
        for gd in self.guards:
            if gd.alive:
                gd.kill()
        for ch in (self.abdo, self.assassin1, self.assassin2):
            ch.root.enabled = False
        self.abdo.hide_shadow()
        rig = self.rig
        rig.ambient, rig.sun_color, rig.sun_dir, rig.fog_color = (DAWN['ambient'], DAWN['sun'], DAWN['sun_dir'], DAWN['fog'])
        rig.fog_density = 0.011
        self.sky.fade_to(self, 'sky_dawn', duration=0.2)
        self.sky.stars.enabled = False
        self.moon.alpha = 0.0
        self.moon.halo.alpha = 0.0
        self.fireflies.enabled = False
        self.fireflies.clear()
        g.post.set(vignette=0.45, bloom=0.7, grain=0.035, tint=DAWN['tint'], desat=0.18)
        for L, ems in self.brazier_parts:
            L.intensity *= 0.28
            L.flicker = 0.2
            for e in ems:
                e.enabled = False
                e.clear()
        for L, ems in self.brazier_parts:
            self.fx.smoke((L.pos.x, 0.9, L.pos.z), scale=0.9, rate=2, tone=0.22, alpha=0.35)
        self.window_shaft.color = color.rgba(1.0, 0.82, 0.55, 0.3)
        self.chamber_light.intensity = 0.25
        for x in (-2.4, 2.6):
            d = self.add_char((x, 1.0), **GUARD)
            d.set_pose('fall')
            d.face(0.3, 1)
            d.hide_shadow()
        before = set(self.root.children)
        qx, qz = (-8.4, 59.45)
        self.queen_body = self.add_char((qx + 0.85, qz), robe=rgb(150, 56, 88), trim=rgb(222, 190, 120), head='scarf', head_color=rgb(110, 36, 60), skin='tan')
        self.queen_body.angle = 90
        self.queen_body.root.rotation_y = 90
        self.queen_body.set_pose('lie')
        self.queen_body._pose_blend = 1.0
        self.queen_body.update(0.0)
        self.queen_body.root.y = 0.19
        self.queen_body.hide_shadow()
        self.actors.remove(self.queen_body)
        self.queen_body.arm_r.rotation_x = -50
        self.queen_body.freeze()
        blood_pool(self, qx - 0.1, qz - 0.05, r=1.25, alpha=0.97, y=0.046, col=(0.5, 0.02, 0.03))
        rgp = random.Random(11)
        for i, (dx, dz, sx, sz) in enumerate(((0.0, 0.0, 1.0, 0.78), (0.55, 0.3, 0.55, 0.5), (-0.6, 0.15, 0.6, 0.46), (0.1, -0.5, 0.5, 0.52), (-0.2, 0.55, 0.46, 0.4), (0.9, -0.2, 0.34, 0.3))):
            mk(self.root, 'cylinder', (qx - 0.1 + dx, 0.05 + i * 0.001, qz - 0.05 + dz), (sx * 1.9, 0.012, sz * 1.9), rgb(116, 10, 14) if i == 0 else rgb(98, 8, 12), emissive=0.05, rot=(0, rgp.uniform(0, 180), 0))
        for k in range(5):
            blood_pool(self, qx + 1.2 + k * 0.35, qz - 0.7 - 0.12 * k, r=0.2, alpha=0.9, y=0.046, seed=k, col=(0.5, 0.02, 0.03))
        mk(self.root, 'cube', (qx + 1.7, 0.07, qz - 1.25), (0.3, 0.14, 0.22), rgb(150, 112, 70), tex('wood'), rot=(0, 20, 0))
        mk(self.root, 'cube', (qx + 1.7, 0.16, qz - 1.25), (0.3, 0.03, 0.22), rgb(184, 150, 86), rot=(0, 20, 0), origin=(0, 0, 0.1))
        self.queen_things = [c for c in self.root.children if c not in before]
        for c in self.queen_things:
            c.enabled = False
        self.khaled = self.add_char((0.0, -4.5), robe=rgb(150, 34, 40), trim=rgb(222, 180, 74), head='crown', head_color=rgb(236, 230, 214), beard=rgb(30, 24, 22), skin='tan', scale=1.06, cloak=rgb(96, 24, 30), weapon='sword')
        self.khaled.face(0, 1)
        self.player.set_character(self.khaled)
        self.player.step_sound = 'step_stone'
        self.player.speed, self.player.run_speed = (3.0, 5.2)
        self.bounds = (-19.2, 19.2, -9.0, 60.2)
        self.stealth_light = False
        self.shot((-6.0, 3.4, -12.0), (0.0, 1.4, -2.0), speed=9)
        self.cam.snap()
        g.audio.music('mus_dawn', 0.55, fade=3.0)
        g.audio.loop('amb_wind', 0.2, fade=3.0)
        g.hud.fade_to(0.0, 2.2)
        g.hud.title_card('BEFORE SUNRISE', 'The King Returns', '', hold=2.0)
        yield 3.2
        yield from self.walk(self.khaled, 0.0, -0.3, speed=2.0)
        self.shot((0.0, 3.2, -4.4), (0.0, 1.0, 3.0), speed=0.9)
        yield from self.talk([('Khaled', 'The gate stands open... Rashid? Fawaz? Answer me.'), ('Khaled', 'No sentries. No lamps. Why is my house so quiet?')], {'Khaled': self.khaled})
        self.end_cutscene()
        self.phase = 'khaled'
        self.player.locked = False
        g.hud.objective('Search the courtyard for what happened  (0/3)')
        self.clue1 = self.interact(0.0, 7.2, 'Examine the fallen guard', self.on_clue1, radius=3.0)
        self._build_evidence()
        self.fallen = self.add_char((0.0, 7.8), **GUARD)
        self.fallen.set_pose('fall')
        self.fallen.face(0.6, 1.0)
        self.fallen.hide_shadow()
        self.dagger = mk(self.root, 'cylinder', (0.0, 0.07, 27.6), (0.06, 0.6, 0.06), rgb(210, 210, 224), rot=(90, 0, 24))
        mk(self.root, 'cylinder', (0.0, 0.08, 27.45), (0.28, 0.05, 0.05), rgb(214, 170, 70), rot=(0, 0, 90))
        self.dagger_glow = glow_quad(self.root, (0.0, 0.5, 27.6), 1.4, (1.0, 0.85, 0.4, 0.5), tex('glow'))
        self.clue2 = self.interact(0.0, 27.6, 'Pick up the dagger', self.on_clue2, radius=2.4)
        self.clue2.enabled = False

    def on_clue1(self):
        self.tl.run(self._clue1_seq())

    def _clue1_seq(self):
        g = self.game
        self.begin_cutscene(letterbox=True)
        yield from self.walk(self.khaled, 0.0, 5.5, speed=2.4)
        self.turn_to(self.khaled, 0.0, 7.8)
        self.shot((4.6, 2.3, 6.8), (0.0, 0.7, 6.8), speed=1.2)
        yield 0.8
        yield from self.talk([('Khaled', 'Fawaz. Cut down from behind - he never even drew his sword.'), ('Khaled', 'This was no raid. Whoever did this walked through my house like a ghost.')], {'Khaled': self.khaled})
        self.end_cutscene()
        self.clue1_done = True
        self._evidence('fallen')
    EVIDENCE_SPOTS = {'fallen': (0.0, 7.2), 'rope': (-16.0, 1.2), 'rashid': (11.2, 17.0)}

    def _build_evidence(self):
        self.evidence_got = set()
        self.ev_markers = {}
        self.rope_it = self.interact(-16.0, 1.2, 'Examine the rope', self.on_rope, radius=2.8)
        self.rashid = self.add_char((11.2, 17.6), **GUARD)
        self.rashid.set_pose('sit')
        self.rashid.face(-0.7, -1.0)
        self.rashid.hide_shadow()
        blood_pool(self, 11.2, 17.45, r=0.95, alpha=0.9, y=0.046, seed=4, col=(0.5, 0.02, 0.03))
        mk(self.root, 'cylinder', (9.9, 0.07, 17.0), (0.05, 2.2, 0.05), rgb(110, 80, 50), rot=(90, 0, 70))
        self.rashid_it = self.interact(11.2, 17.0, 'Kneel beside the wounded guard', self.on_rashid, radius=2.9)
        for key, (x, z) in self.EVIDENCE_SPOTS.items():
            m = Entity(parent=self.root, position=(x, 2.3 if key != 'rope' else 2.0, z), add_to_scene_entities=False)
            mk(m, 'cube', (0, 0, 0), (0.26, 0.26, 0.26), rgb(255, 214, 110), emissive=1.0, rot=(45, 0, 45))
            glow_quad(m, (0, 0, 0), 1.0, (1.0, 0.8, 0.35, 0.6), tex('glow'))
            self.ev_markers[key] = m

        def spin(dt):
            for k, m in self.ev_markers.items():
                m.rotation_y += 130.0 * dt
        self.updaters.append(spin)
        self.trigger(0.0, 19.6, 12.0, 1.6, self._gate_check, once=False)

    def _evidence(self, key):
        g = self.game
        self.evidence_got.add(key)
        m = self.ev_markers.pop(key, None)
        if m is not None:
            m.enabled = False
        n = len(self.evidence_got)
        if n >= 3:
            self.clue2.enabled = True
            g.hud.objective('Follow the trail through the gate')
        else:
            g.hud.objective(f'Search the courtyard for what happened  ({n}/3)')

    def _gate_check(self):
        if self.phase == 'khaled' and len(self.evidence_got) < 3 and (not self.cutscene_active):
            self.game.hud.hint(f'Not yet. Read the courtyard first  ({len(self.evidence_got)}/3).', hold=3)
            self.player.teleport(self.player.x, 18.0)

    def on_rope(self):
        self.rope_it.enabled = False
        self.tl.run(self._rope_seq())

    def _rope_seq(self):
        k = self.khaled
        self.begin_cutscene(letterbox=True)
        yield from self.walk(k, -14.6, 1.6, speed=2.4)
        self.turn_to(k, -16.4, -0.3)
        self.shot((-10.0, 2.8, 4.6), (-16.4, 1.7, 0.0), speed=1.1)
        yield 0.8
        yield from self.talk([('Khaled', 'A rope, still tied off on my battlements. Two hitches and a loop - a desert knot.'), ('Khaled', 'They climbed into my house over my own wall, and not one sentry heard them.')], {'Khaled': k})
        self.end_cutscene()
        self._evidence('rope')

    def on_rashid(self):
        self.rashid_it.enabled = False
        self.tl.run(self._rashid_seq())

    def _ask(self, question, options):
        res = {'v': None}
        self.game.dialogue.ask('Khaled', question, options, lambda i: res.update(v=i))
        while res['v'] is None:
            yield
        return res['v']

    def _rashid_seq(self):
        g = self.game
        k = self.khaled
        r = self.rashid
        self.begin_cutscene(letterbox=True)
        yield from self.walk(k, 10.0, 16.2, speed=2.4)
        self.turn_to(k, 11.2, 17.6)
        k.set_pose('kneel')
        self.shot((7.0, 2.2, 14.0), (11.2, 0.9, 17.4), speed=1.2)
        yield 0.8
        r.talking = True
        yield from self.talk([('Rashid', '...My king. You came back. Forgive me, I could not hold the gate.'), ('Khaled', 'Hold still, Rashid. Save your breath. Tell me what you saw.')], {'Rashid': r, 'Khaled': k})
        topics = [('Who did this?', [('Rashid', 'No colours, my king. Dark cloth, and silent as the night. They knew where every one of us would be standing.'), ('Khaled', "They knew my sentries' rounds... someone studied my house for weeks.")]), ('How many were there?', [('Rashid', 'Four, five. They moved like one man. But one of them stayed back, my king, always last through the door.'), ('Rashid', 'As if he did not want to be there at all.'), ('Khaled', 'A reluctant man is still a man with a blade.')]), ('Where did they go?', [('Rashid', 'Through the gate to the hall, and then the royal chamber. I tried to follow. I tried...'), ('Khaled', 'Rest. You have done enough.')])]
        left = list(range(len(topics)))
        while left:
            pick = (yield from self._ask('What do you ask him?', [topics[i][0] for i in left]))
            i = left.pop(pick)
            yield from self.talk(topics[i][1], {'Rashid': r, 'Khaled': k})
        yield from self.talk([('Rashid', 'Tell the queen... I am sorry. I tried.')], {'Rashid': r})
        r.talking = False
        yield 0.6
        r.set_pose('fall')
        g.audio.play('stinger_soft', 0.6)
        yield 1.2
        k.set_pose('stand')
        self.end_cutscene()
        self._evidence('rashid')

    def on_clue2(self):
        self.tl.run(self._clue2_seq())

    def _clue2_seq(self):
        g = self.game
        self.begin_cutscene()
        self.turn_to(self.khaled, 0.0, 27.6)
        self.shot((4.2, 2.1, 26.2), (0.0, 0.5, 27.0), speed=1.4)
        yield 0.7
        g.audio.play('pickup', 0.8)
        self.dagger.enabled = False
        self.dagger_glow.enabled = False
        self.fx.sparks((0.0, 0.5, 27.6), 12)
        yield 0.5
        self.ring_fx((0.0, 0.0, 27.6), (1.0, 0.85, 0.4), 4.0, 0.9, y=0.12)
        g.hud.title_card('', 'A dagger with a thunderbolt on its hilt', '', hold=1.6, fade=0.5)
        yield 2.4
        yield from self.talk([('Khaled', "Thunder. Harith's men - in my house."), ('Khaled', 'Then they came for my life, and I was not here to give it. ...Zainab.')], {'Khaled': self.khaled})
        self.end_cutscene()
        self.clue2_done = True
        g.hud.objective('Reach the royal chamber')
        self.chamber_it = self.interact(DOOR_X, 52.2, 'Enter the royal chamber', self.on_enter_chamber, radius=3.4)

    def on_enter_chamber(self):
        self.tl.run(self.final_scene())

    def final_scene(self):
        g = self.game
        k = self.khaled
        self.phase = 'ending'
        self.begin_cutscene()
        g.hud.objective(None)
        g.audio.stop('mus_dawn', 2.5)
        yield from self.walk(k, DOOR_X, 50.6, speed=2.0)
        self.shot((DOOR_X, 1.7, 48.0), (DOOR_X, 1.3, 57.0), speed=0.7)
        yield from self.walk(k, DOOR_X, 53.8, speed=1.2)
        yield 0.6
        yield from self.talk([('Khaled', 'Zainab?')], {'Khaled': k})
        yield 1.0
        k.arm_r_goal = -80
        self.tl.to(self.curtain_prop, 'scale_x', 0.17, 1.6)
        self.tl.to(self.curtain_prop, 'scale_z', 3.4, 1.6)
        yield 1.0
        for c in self.queen_things:
            c.enabled = True
        self.queen_body.root.enabled = True
        yield 0.6
        k.arm_r_goal = None
        self.rig.add((-8.2, 1.7, 57.6), color=(1.0, 0.82, 0.62), intensity=1.5, radius=6.5, flicker=0.05)
        g.audio.play('stinger_soft', 0.8)
        g.post.tween(3.0, desat=0.55, vignette=0.7, bloom=0.6)
        self.shot((-4.4, 1.9, 53.0), (-8.4, 0.3, 59.1), speed=0.5)
        yield 4.0
        self.tl.run(self.walk(k, -9.85, 59.3, speed=0.8))
        yield 3.0
        k.face(1.0, 0.0)
        k.set_pose('kneel')
        g.audio.play('stinger_soft', 0.7)
        self.shot((-5.8, 1.35, 54.6), (-8.7, 0.35, 59.3), speed=0.45)
        yield 3.0
        yield from self.talk([('Khaled', 'Zainab... no. Open your eyes. Please.'), ('Khaled', 'I was at the border, counting banners, while you were here counting on me.')], {'Khaled': k})
        self.fx.dust((DOOR_X, 2.2, 55.5), area=(5, 3, 5), count=40, color=(1.0, 0.85, 0.6), alpha=0.5, size=0.12)
        self.shot((DOOR_X + 0.5, 8.5, 49.5), (DOOR_X, 0.5, 58.0), speed=0.18)
        yield 4.2
        yield from self.talk([('Khaled', 'Harith. You wanted a war between our tribes. You will have one.'), ('Khaled', 'When it is over there will be no Thunder left to name.')], {'Khaled': k})
        g.audio.play('thunder', 1.0)
        g.post.flash((0.85, 0.9, 1.0), 0.95, 1.4)
        g.post.punch_aberration(0.025)
        self.cam.shake(0.3, 0.9)
        g.post.tween(1.2, tint=(1.1, 0.78, 0.74), vignette=0.9)
        yield 1.0
        g.hud.title_card('', 'THE THUNDER TRIBE WILL BURN', '', hold=1.8)
        yield 3.2
        g.hud.fade_to(1.0, 1.6)
        yield 2.0
        g.next_scene()
