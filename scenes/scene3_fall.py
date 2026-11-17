import math
import random
from ursina import Entity, Vec3, color, destroy
from engine.ai import Guard
from engine.assets import tex
from engine.entities import glow_quad, mk, rgb, shade
from engine.props import CrowBird, Sky, banner, barrel, blood_pool, bush, cave_mouth, child_things, contact_shadow, crate, dead_tree, distant_dunes, ground, ground_patches, hay, hitch_rail, horse, house, palm, rock, ruin_wall, scatter_clutter, shrouded_body, soft_path, well
from engine.scene_base import BaseScene
from engine.timing import Clock, ease_in, ease_out
from scenes.scene3_hunt import CALM, HUNT_BOUNDS, HUNT_START, HuntMixin
START = (-43.0, 6.0)
FIRE = (31.0, 8.0)
HOME = (24.0, 13.5)
GRAVES = [(31.2, 12.6, 90, 1.7), (31.2, 14.7, 90, 1.6), (31.2, 16.6, 90, 1.45)]
CAVE = (56.0, 22.0)
FAMILY = [(FIRE[0] - 2.4, FIRE[1] + 0.7, 100, 1.65), (FIRE[0], FIRE[1] - 2.4, 175, 1.55), (FIRE[0] + 2.3, FIRE[1] + 1.1, 250, 1.5)]
ROMAN = dict(robe=rgb(150, 40, 36), trim=rgb(226, 190, 90), head='helmet', head_color=rgb(206, 170, 96), weapon='sword', build='broad', skin='olive', cloak=rgb(120, 24, 24))
IRON = dict(robe=rgb(54, 62, 80), trim=rgb(196, 198, 210), head='helmet', head_color=rgb(128, 134, 148), weapon='spear', build='broad', skin='tan')
BURN = dict(ambient=Vec3(0.17, 0.165, 0.25), sun=Vec3(0.26, 0.3, 0.48), sun_dir=Vec3(0.2, 0.7, -0.5), fog=Vec3(0.06, 0.05, 0.09), tint=(1.03, 0.98, 0.95))
ASH = dict(ambient=Vec3(0.36, 0.36, 0.42), sun=Vec3(0.74, 0.64, 0.56), sun_dir=Vec3(-0.6, 0.5, 0.4), fog=Vec3(0.46, 0.44, 0.47), tint=(0.98, 0.96, 0.96))
HOUSES = [(-14.0, 13.5, 6.0, 5.0, 3.0, 'south', 2), (-2.0, 13.5, 7.0, 5.0, 3.2, 'south', 2), (10.0, 13.5, 6.0, 5.0, 3.0, 'south', 1), (-12.0, -2.5, 6.0, 5.0, 3.0, 'north', 2), (0.0, -2.5, 6.0, 5.0, 3.0, 'north', 2), (12.0, -2.5, 6.0, 5.0, 3.0, 'north', 1), (HOME[0], HOME[1], 8.0, 6.0, 3.2, 'south', 1), (34.0, 22.0, 6.0, 5.0, 3.0, 'south', 1), (40.0, 0.0, 6.0, 5.0, 3.0, 'north', 1)]

class Scene3Fall(HuntMixin, BaseScene):
    number = 3
    name = 'The Last Survivor'
    author = 'Amro'
    BURN_MOOD = dict(ambient=BURN['ambient'], sun=BURN['sun'], sun_dir=BURN['sun_dir'], fog=BURN['fog'], tint=BURN['tint'], density=0.017)
    VILLAGE_BOUNDS = (-46.0, 62.0, -14.0, 32.0)
    VILLAGE_START = START

    def build(self):
        g = self.game
        self.phase = 'intro'
        self.checkpoint = START
        self.house_parts = []
        self.torches = []
        self.chasers = []
        self.hazards_done = set()
        self.hazard_objs = {}
        self.chase_triggers = []
        self.markers = []
        rig = self.rig
        rig.ambient, rig.sun_color, rig.sun_dir, rig.fog_color = (BURN['ambient'], BURN['sun'], BURN['sun_dir'], BURN['fog'])
        rig.fog_density = 0.017
        g.post.set(vignette=0.5, bloom=1.0, tint=BURN['tint'], grain=0.05, desat=0.0)
        self.cam.pitch, self.cam.distance = (38, 13.0)
        self.cam.set_fov(68)
        self.bounds = (-46.0, 62.0, -14.0, 32.0)
        self.stealth_light = True
        self.sky = Sky(self, 'sky_dusk', stars=False)
        self._build_ground()
        self._build_village()
        self._build_aftermath()
        self._build_ridge_and_cave()
        self._build_people()
        self._build_atmosphere()
        self._build_hills()
        self._build_hares()
        self.set_mood(CALM)
        g.post.set(vignette=0.38, bloom=0.7, grain=0.03)
        self.bounds = HUNT_BOUNDS
        self.player.teleport(*HUNT_START)
        self.abdo.face(1, 0.2)
        self.trigger(-26.0, 8.0, 2.4, 50, self.on_vista)
        self.trigger(-8.0, 8.0, 2.4, 50, lambda: self._checkpoint((-8.0, 6.0)))
        self.trigger(16.0, 8.0, 2.4, 50, lambda: self._checkpoint((16.0, 7.0)))
        self.trigger(2.0, 8.0, 2.0, 50, lambda: self.tl.run(self.hazard(6.0, 6.0, 1.5)))
        self.trigger(FIRE[0] - 3.4, FIRE[1] + 0.2, 4.0, 5.0, self.on_home)
        self.trigger(CAVE[0], CAVE[1] + 0.4, 6.0, 4.0, self.on_cave)
        self.rig.add((CAVE[0] - 2.0, 3.5, CAVE[1] - 7.0), color=(1.0, 0.5, 0.22), intensity=1.1, radius=17.0, flicker=0.2, speed=4.0)
        for gx, gz in ((-32.0, 6.0), (-40.0, 10.0)):
            self.rig.add((gx, 3.0, gz), color=(1.0, 0.42, 0.18), intensity=0.9, radius=20.0, flicker=0.25, speed=5.0)
        g.audio.music('mus_burn', 0.5, fade=3.0)
        g.audio.loop('amb_fire', 0.4, fade=3.0)

    def _build_ground(self):
        self.ground = ground(self, 240, 'sand', 120, rgb(176, 146, 124))
        ground_patches(self, -44, -14, 62, 32, count=120, seed=21, palette=[rgb(52, 40, 36), rgb(86, 62, 48), rgb(40, 34, 34), rgb(110, 84, 62)], alpha=(0.25, 0.5), size=(3.0, 9.0))
        scatter_clutter(self, -44, -14, 62, 32, count=90, seed=2, avoid=[(-10, 36, -6, 20)], grass=rgb(96, 84, 52), pebble=rgb(110, 100, 94))
        soft_path(self, [(-44, 6), (-24, 6), (-8, 6), (8, 6), (22, 6), (34, 8), (46, 14), (54, 20)], width=3.2, seed=1, col=rgb(120, 100, 84), alpha=0.55)
        soft_path(self, [(-16, 20), (30, 20)], width=2.0, seed=2, col=rgb(110, 92, 76), alpha=0.4)
        soft_path(self, [(-16, -8), (30, -8)], width=2.0, seed=3, col=rgb(110, 92, 76), alpha=0.4)

    def _build_village(self):
        for cx, cz, w, d, h, door, level in HOUSES:
            parts = house(self, cx, cz, w, d, h=h, door=door, door_w=1.4, texture='mudbrick', col=rgb(166, 150, 140), window_glow=0.9 if level >= 2 else 0.55)
            L, fx = (None, [])
            if level:
                L, fx = self._burn(cx, cz, w, d, h, level)
            self.house_parts.append((parts, level, L, fx, (cx, cz, w, d, h)))
        for x, z in ((-20.0, 9.5), (-6.5, 9.0), (6.0, 2.5), (18.0, 10.0), (28.0, 4.0), (-24.0, 2.5)):
            crate(self, x, z, 0.9, rot=random.Random(int(x * 3 + z)).uniform(0, 90))
        for x, z in ((-19.5, 8.6), (7.2, 9.4), (-5.0, 2.8)):
            barrel(self, x, z)
        for x, z in ((-8.0, 24.0), (14.0, 24.0), (-18.0, -12.0), (20.0, -12.0)):
            hay(self, x, z, 1.0)
        for x, z in ((-22.0, 16.0), (4.0, 24.0), (26.0, -6.0)):
            palm(self, x, z, h=4.2)
        well(self, 20.0, 3.0)
        mk(self.root, 'cylinder', (FIRE[0], 0.0, FIRE[1]), (1.9, 0.07, 1.9), rgb(80, 66, 58), tex('ash'), tex_scale=(2, 2))
        mk(self.root, 'cylinder', (FIRE[0], 0.06, FIRE[1]), (1.15, 0.06, 1.15), rgb(255, 250, 244), tex('ash'), emissive=0.18)
        pr = random.Random(5)
        for i in range(10):
            a_ = i / 10.0 * 2 * math.pi
            mk(self.root, 'cube', (FIRE[0] + math.cos(a_) * 0.86, 0.1, FIRE[1] + math.sin(a_) * 0.86), (0.36, 0.22, 0.3), rgb(128, 118, 110), tex('rock'), rot=(0, -math.degrees(a_) + pr.uniform(-12, 12), pr.uniform(-6, 6)))
        for i in range(3):
            mk(self.root, 'cylinder', (FIRE[0] + (i - 1) * 0.18, 0.14, FIRE[1] + (i - 1) * 0.1), (0.13, 0.9, 0.13), rgb(30, 24, 22), rot=(90, 30 + i * 55, 0), origin=(0, 0.5, 0))
        self.family_embers = self.fx.embers((FIRE[0], 0.3, FIRE[1]), scale=0.5, rate=2)
        self.family_light = self.rig.add((FIRE[0], 0.8, FIRE[1]), color=(1.0, 0.5, 0.2), intensity=0.6, radius=6.0, flicker=0.3)
        self.bread = mk(self.root, 'cube', (FIRE[0] - 1.2, 0.08, FIRE[1] - 0.6), (0.5, 0.06, 0.4), rgb(210, 190, 150), rot=(0, 24, 0))
        self.bread_loaf = mk(self.root, 'sphere', (FIRE[0] - 1.2, 0.18, FIRE[1] - 0.6), (0.34, 0.16, 0.26), rgb(196, 140, 74), rot=(0, 24, 0))
        mk(self.root, 'cylinder', (6.0, 0.0, 9.0), (0.12, 4.6, 0.12), rgb(60, 44, 36))
        banner(self, 6.0, 3.4, 8.9, 'iron', height=2.4, face='south')

    def _fallen(self, x, z, yaw, stain=True, **look):
        look.setdefault('head', 'shemagh')
        sy, cy = (math.sin(math.radians(yaw)), math.cos(math.radians(yaw)))
        ch = self.add_char((x + sy * 0.85, z + cy * 0.85), **look)
        ch.angle = yaw
        ch.root.rotation_y = yaw
        ch.set_pose('lie')
        ch._pose_blend = 1.0
        ch.update(0.0)
        ch.root.y = 0.19
        ch.hide_shadow()
        if ch in self.actors:
            self.actors.remove(ch)
        ch.freeze()
        if stain:
            blood_pool(self, x - sy * 0.15, z - cy * 0.15, r=0.62)
        return ch

    def _build_aftermath(self):
        before = set(self.root.children)
        fx, fz = FIRE
        looks = [dict(robe=rgb(122, 110, 90), trim=rgb(150, 100, 60), head='shemagh', head_color=rgb(232, 226, 210), beard=rgb(170, 170, 170), skin='olive'), dict(robe=rgb(96, 98, 108), trim=rgb(150, 150, 160), head='scarf', head_color=rgb(110, 110, 120), scale=0.97), dict(robe=rgb(150, 60, 90), trim=rgb(220, 190, 120), head='scarf', head_color=rgb(120, 40, 70))]
        for (bx, bz, byaw, blen), look in zip(FAMILY, looks):
            self._fallen(bx, bz, byaw, **look)
        mk(self.root, 'cylinder', (fx + 1.6, 0.2, fz - 0.7), (0.5, 0.36, 0.5), rgb(60, 52, 50), rot=(80, 20, 0), origin=(0, 0, 0))
        mk(self.root, 'cube', (fx - 2.8, 0.12, fz - 1.4), (0.7, 0.24, 0.5), rgb(120, 76, 44), rot=(0, 30, 20))
        mk(self.root, 'sphere', (fx + 2.7, 0.08, fz - 0.6), (0.34, 0.16, 0.3), rgb(190, 140, 80))
        mk(self.root, 'sphere', (fx - 0.9, 0.06, fz - 1.8), (0.26, 0.12, 0.22), rgb(190, 140, 80))
        child_things(self, fx - 3.6, fz + 2.2, 20)
        old = dict(robe=rgb(120, 112, 96), trim=rgb(90, 70, 50), head='turban', head_color=rgb(210, 204, 190), beard=rgb(200, 196, 190))
        man = dict(robe=rgb(110, 92, 70), trim=rgb(70, 54, 40), head='shemagh', head_color=rgb(222, 214, 196))
        man2 = dict(robe=rgb(80, 96, 112), trim=rgb(60, 70, 80), head='cap', head_color=rgb(60, 50, 44))
        woman = dict(robe=rgb(140, 72, 84), trim=rgb(210, 180, 120), head='scarf', head_color=rgb(120, 40, 56))
        woman2 = dict(robe=rgb(76, 94, 128), trim=rgb(200, 190, 150), head='scarf', head_color=rgb(60, 70, 100))
        for x, z, yaw, covered, look in ((-33.5, 3.6, 20, False, man), (-29.5, 8.6, 70, True, None), (-21.5, 4.4, -70, False, woman), (-15.2, 10.1, 175, False, man2), (-9.4, 4.0, 120, True, None), (-3.0, 10.0, 100, False, woman2), (3.6, 8.4, 40, False, man), (9.2, 9.6, 200, True, None), (-11.2, 1.1, 200, False, old), (0.6, 1.2, 160, False, woman), (12.6, 1.0, 90, False, old), (16.8, 4.0, 15, False, man2), (28.6, 4.2, 250, True, None), (36.0, 18.5, 140, False, woman2)):
            if covered:
                shrouded_body(self, x, z, yaw, cloth=random.Random(int(x * 3 + z)).choice([rgb(150, 140, 118), rgb(120, 112, 106), rgb(126, 98, 90)]), stain=random.Random(int(z * 7)).uniform(0.4, 0.9))
            else:
                self._fallen(x, z, yaw, **look)
        child_things(self, -20.4, 3.2, 70)
        child_things(self, 1.8, 0.3, -30)
        hitch_rail(self, -35.0, 12.3, 4.2, 0)
        horse(self, -36.4, 11.2, 8, col=rgb(110, 70, 42), saddle=rgb(60, 70, 96), seed=1)
        horse(self, -34.0, 11.2, -6, col=rgb(54, 40, 34), saddle=rgb(60, 70, 96), seed=2)
        horse(self, -32.9, 14.6, 40, col=rgb(170, 140, 100), saddle=rgb(150, 36, 34), seed=3)
        for x, z, yaw, col in ((-26.5, -3.2, 80, rgb(120, 82, 52)), (-24.0, -5.4, 250, rgb(74, 58, 48)), (13.5, 9.0, 160, rgb(150, 112, 74))):
            horse(self, x, z, yaw, col=col, pose='dead', seed=int(x))
        for k in range(7):
            mk(self.root, 'cube', (-29.0 + k * 1.15, 0.55, -1.0 + random.Random(k).uniform(-0.15, 0.15)), (1.0, 0.1, 0.1), rgb(70, 46, 30), rot=(0, random.Random(k).uniform(-8, 8), random.Random(k + 9).uniform(-6, 6)))
        for k in range(0, 7, 2):
            mk(self.root, 'cylinder', (-29.0 + k * 1.15, 0, -1.0), (0.14, 1.0, 0.14), rgb(60, 40, 28), rot=(random.Random(k).uniform(-10, 10), 0, 0))
        self.remains = [c for c in self.root.children if c not in before]

    def _burn(self, cx, cz, w, d, h, level):
        fx = []
        if level >= 2:
            for dx in (-0.26, 0.26):
                fx += self.fx.fire((cx + dx * w, h + 0.45, cz), scale=1.7, intensity=1.2)
            fx += self.fx.fire((cx, 1.1, cz - d / 2.0 - 0.15), scale=1.0, intensity=0.9)
            fx.append(self.fx.embers((cx, h + 1.0, cz), scale=2.0, rate=7, area=(w * 0.35, 0, d * 0.35)))
            fx.append(self.fx.smoke((cx, h + 1.2, cz), scale=4.4, rate=3, tone=0.14, alpha=0.5, wind=(0.9, 0.4, 0.2)))
            L = self.rig.add((cx, h * 0.9, cz), color=(1.0, 0.46, 0.16), intensity=2.5, radius=14.0, flicker=0.4, speed=8.0)
        else:
            fx += self.fx.fire((cx, h + 0.25, cz), scale=0.95, intensity=0.9)
            fx.append(self.fx.smoke((cx, h + 1.0, cz), scale=3.0, rate=2, tone=0.16, alpha=0.4, wind=(0.8, 0.3, 0.1)))
            L = self.rig.add((cx, h * 0.8, cz), color=(1.0, 0.5, 0.2), intensity=1.5, radius=10.0, flicker=0.35, speed=7.0)
        return (L, fx)

    def _build_ridge_and_cave(self):
        rnd = random.Random(8)
        for i in range(16):
            rock(self, rnd.uniform(-46, -32), rnd.uniform(-12, 22), s=rnd.uniform(0.9, 2.2), collide=False)
        dead_tree(self, -38.0, 11.0, h=4.2)
        dead_tree(self, -40.5, 0.0, h=3.6)
        cx, cz = CAVE
        for i in range(9):
            a = math.pi * i / 8
            mk(self.root, 'sphere', (cx + math.cos(a) * 4.0, math.sin(a) * 4.1 + 0.2, cz), (rnd.uniform(1.5, 2.2), rnd.uniform(1.4, 2.0), rnd.uniform(1.4, 2.0)), rgb(150, 138, 134), tex('rock'), rot=(rnd.uniform(-15, 15), rnd.uniform(0, 360), rnd.uniform(-15, 15)))
        mk(self.root, 'sphere', (cx, 0.0, cz + 10.0), (21.0, 12.0, 17.0), rgb(120, 112, 112), tex('rock'), tex_scale=(7, 4))
        for i in range(22):
            side = -1 if i % 2 else 1
            rock(self, cx + side * rnd.uniform(5.6, 10.0), cz + rnd.uniform(0.5, 9.0), s=rnd.uniform(1.5, 3.0), col=rgb(140, 126, 120), collide=False)
        for sx in (-1, 1):
            mk(self.root, 'cube', (cx + sx * 4.9, 2.6, cz - 0.4), (1.5, 5.2, 1.6), rgb(150, 140, 136), tex('rock'), tex_scale=(1, 2), rot=(0, sx * 8, sx * 3))
        self.world.add_box(cx - 4.6, cz, 1.8, 3.0)
        self.world.add_box(cx + 4.6, cz, 1.8, 3.0)
        cz0, cz1 = (cz + 0.6, cz + 12.0)
        ln = cz1 - cz0
        mk(self.root, 'plane', (cx, 0.03, (cz0 + cz1) / 2), (8.0, 1, ln), rgb(120, 114, 124), tex('dirt'), tex_scale=(3, ln / 3))
        for sx in (-1, 1):
            mk(self.root, 'cube', (cx + sx * 4.4, 2.4, (cz0 + cz1) / 2), (1.2, 4.8, ln), rgb(120, 114, 124), tex('rock'), tex_scale=(ln / 2.6, 2))
        mk(self.root, 'cube', (cx, 4.9, (cz0 + cz1) / 2 + 1.0), (10.0, 0.8, ln), rgb(96, 92, 102), tex('rock'), tex_scale=(4, ln / 3))
        mk(self.root, 'cube', (cx, 2.4, cz1 + 0.4), (9.0, 4.8, 0.8), rgb(100, 96, 106), tex('rock'), tex_scale=(3, 2))
        for i in range(10):
            rock(self, cx + rnd.uniform(-3.4, 3.4), rnd.uniform(cz0 + 1.5, cz1 - 1.0), s=rnd.uniform(0.25, 0.6), collide=False, col=rgb(100, 96, 104))
        rock(self, cx + 1.2, cz + 5.0, s=2.2, collide=False, col=rgb(118, 112, 118))
        rock(self, cx + 2.1, cz + 5.6, s=1.5, collide=False, col=rgb(108, 102, 110))
        for i in range(5):
            mk(self.root, 'cylinder', (cx + rnd.uniform(-3, 3), 0.05, cz + rnd.uniform(3, 10)), (0.07, 0.5, 0.07), rgb(220, 208, 184), rot=(90, rnd.uniform(0, 180), 0), origin=(0, 0, 0))
        for i in range(8):
            mk(self.root, 'cone', (cx + rnd.uniform(-3.4, 3.4), 4.5, rnd.uniform(cz0 + 2, cz1 - 1)), (0.35, rnd.uniform(0.7, 1.4), 0.35), rgb(70, 66, 72), rot=(180, 0, 0), origin=(0, 0.5, 0))
        self.cave_light = self.rig.add((cx, 2.6, cz + 8.0), color=(0.45, 0.55, 1.0), intensity=0.5, radius=9.0, flicker=0.1)
        self.cave_light.enabled = False
        self.bats = []
        for i in range(7):
            b = CrowBird(self.root, scale=0.38, col=rgb(18, 14, 18))
            b.root.position = (cx + rnd.uniform(-3, 3), rnd.uniform(3.2, 4.2), rnd.uniform(cz0 + 3, cz1 - 2))
            b.vx = rnd.uniform(-1.6, 1.6)
            self.bats.append(b)
        self.bat_t = 0.0
        self.bats_flee = False

    def _build_people(self):
        self.abdo = self.add_char(START, robe=rgb(140, 100, 64), trim=rgb(170, 50, 40), head='shemagh', head_color=rgb(236, 228, 208), skin='tan', weapon='bow')
        self.abdo.face(1, 0)
        self.set_player(self.abdo, speed=3.3, run_speed=5.7)
        self.player.step_sound = 'step_sand'
        self.quarry = Entity(parent=self.abdo.body, position=(0.34, 1.0, -0.32), rotation_z=-14, add_to_scene_entities=False)
        mk(self.quarry, 'sphere', (0, 0, 0), (0.46, 0.26, 0.26), rgb(176, 138, 96))
        mk(self.quarry, 'sphere', (0.26, 0.05, 0), (0.22, 0.2, 0.18), rgb(186, 148, 104))
        mk(self.quarry, 'cone', (0.3, 0.2, 0.05), (0.07, 0.24, 0.05), rgb(150, 118, 84), rot=(0, 0, 8))
        spec = [dict(pos=(-18.0, 6.0), route=[(-18.0, 6.0), (-5.0, 6.0)], facing=90, pause=2.2, view=9.5), dict(pos=(4.0, 6.0), route=[(4.0, 6.0), (13.0, 6.0)], facing=90, pause=2.0, view=9.5, look=ROMAN), dict(pos=(-14.0, 20.0), route=[(-14.0, 20.0), (12.0, 20.0)], facing=90, pause=1.6, view=9.0), dict(pos=(-6.0, -8.0), route=[(-6.0, -8.0), (16.0, -8.0)], facing=90, pause=2.0, view=9.0), dict(pos=(34.0, -6.0), route=[(34.0, -6.0), (34.0, -0.5)], facing=0, pause=2.4, view=8.5, look=ROMAN)]
        self.home_guards = []
        for sp in spec:
            look = dict(sp.get('look', IRON))
            gd = Guard(self, sp['pos'], route=sp['route'], facing=sp['facing'], speed=1.55, view=sp['view'], fov=72, pause=sp['pause'], sweep=36, **look)
            gd.alert_mult = 0.9
            self.add_guard(gd)
            self.attach_torch(gd)
            self.home_guards.append((gd, sp['pos'], sp['facing']))
        self.centurion = self.add_char((10.0, 8.0), scale=1.1, **ROMAN)
        self.soldier = self.add_char((10.0, 6.4), **IRON)
        for c in (self.centurion, self.soldier):
            c.root.enabled = False

    def _torch_prop(self, ch):
        arm = ch.arm_l
        stick = mk(arm, 'cylinder', (0.0, -0.7, 0.1), (0.07, 0.5, 0.07), rgb(70, 48, 32))
        rag = mk(arm, 'sphere', (0.0, -0.19, 0.1), (0.13, 0.16, 0.13), rgb(38, 28, 22))
        tip = Entity(parent=arm, position=(0.0, -0.12, 0.1), add_to_scene_entities=False)
        ch.arm_l_goal = -42.0
        return (stick, rag, tip)

    def attach_torch(self, gd):
        gd.torch_stick, gd.torch_rag, gd.torch_tip = self._torch_prop(gd.ch)
        tip = gd.torch_tip.world_position
        L = self.rig.add((tip.x, tip.y + 0.3, tip.z), color=(1.0, 0.62, 0.28), intensity=1.5, radius=8.0, flicker=0.35, speed=9.0)
        ems = self.fx.fire((tip.x, tip.y, tip.z), scale=0.5, intensity=0.6)
        for e in ems:
            e.cull = False
        self.torches.append((gd, L, ems))

    def _follow_torches(self):
        for gd, L, ems in self.torches:
            if not gd.alive:
                L.enabled = False
                for e in ems:
                    e.enabled = False
                continue
            tip = gd.torch_tip.world_position
            L.pos = Vec3(tip.x, tip.y + 0.3, tip.z)
            for e in ems:
                e.pos = Vec3(tip.x, tip.y + (0.0 if e is ems[0] else 0.22), tip.z)

    def _build_atmosphere(self):
        self.ash = self.fx.dust((10, 3, 6), area=(36, 4, 18), count=90, color=(1.0, 0.6, 0.34), alpha=0.55, size=0.1, wind=(0.9, -0.2, 0.2))
        self.ash2 = self.fx.dust((46, 3, 14), area=(20, 4, 14), count=40, color=(1.0, 0.6, 0.34), alpha=0.5, size=0.1, wind=(0.9, -0.2, 0.2))
        glow_quad(self.root, (10, 6, 70), (160, 24), (1.0, 0.36, 0.1, 0.38), tex('glow'), billboard=False, add=True, bin_sort=20)
        distant_dunes(self, 10.0, 6.0, radius=120.0, count=30, seed=5, col=rgb(56, 46, 54))
        for x in (-30, -6, 20, 46):
            self.fx.smoke((x, 0, 60), scale=9.0, rate=2, tone=0.1, alpha=0.5, wind=(1.0, 0.3, 0.1)).cull = False

    def start(self):
        self.stealth_active = False
        self.phase = 'hunt_intro'
        self.cam.pitch, self.cam.distance = (36, 12.0)
        self.tl.run(self.hunt_intro())

    def on_action(self):
        self.hunt_action()

    def talk(self, lines, who):

        def on_line(i, line):
            for n, c in who.items():
                c.talking = n == line[0]
        yield from self.say(lines, on_line=on_line)
        for c in who.values():
            c.talking = False

    def village_opening(self):
        g = self.game
        self.phase = 'intro'
        self.cam.pitch, self.cam.distance = (38, 13.0)
        self.begin_cutscene()
        self.shot((-47.0, 2.4, -3.0), (-36.0, 3.0, 8.0), speed=9)
        self.cam.snap()
        g.hud.title_card('THAT EVENING', 'The Hunter Returns', '', hold=2.2)
        yield 3.6
        self.shot((-45.5, 2.0, 1.5), (-14.0, 5.5, 7.0), speed=0.45)
        yield 3.2
        yield from self.talk([('Abdo', 'That smoke... that is not a cooking fire.'), ('Abdo', 'The whole valley is glowing. No... no. My family.')], {'Abdo': self.abdo})
        self.end_cutscene()
        self.phase = 'walk'
        g.hud.objective('Get home')

    def _checkpoint(self, pos):
        if self.phase == 'stealth':
            self.checkpoint = pos
            self.game.hud.caption('Checkpoint', hold=0.5, fade=0.3, size=1.3, tone=(1.0, 0.8, 0.6))

    def on_vista(self):
        if self.phase == 'walk':
            self.tl.run(self.vista())

    def vista(self):
        g = self.game
        self.begin_cutscene()
        self.shot((-30.0, 9.0, -5.0), (4.0, 2.0, 8.0), speed=0.8)
        yield 3.0
        g.audio.play('stinger_soft', 0.7)
        yield from self.talk([('Abdo', 'Iron Tribe banners. They are burning everything.'), ('Abdo', 'Keep to the dark. If they see me, I will never reach the house.')], {'Abdo': self.abdo})
        self.end_cutscene()
        self.phase = 'stealth'
        self.stealth_active = True
        self.checkpoint = (-24.0, 6.0)
        g.hud.objective('Reach your house - stay out of the torchlight')
        g.hud.hint('WASD  move      Shift  run      Soldiers carry torches - hide behind houses and crates', hold=9)

    def reset_section(self):
        cx, cz = self.checkpoint
        self.player.teleport(cx, cz)
        if self.phase == 'chase':
            for gd in list(self.chasers):
                self._discard(gd)
            self.chasers.clear()
            self._spawn_chasers()
            self.hazards_done.clear()
            for tr in self.chase_triggers:
                tr.enabled = True
                tr.inside = False
        else:
            for gd, pos, facing in self.home_guards:
                if gd.alive:
                    gd.ch.root.x, gd.ch.root.z = pos
                    gd.ch.angle = facing
                    gd.ch.root.rotation_y = facing
                    gd.wp, gd.wait, gd.look_offset = (0, 0.0, 0.0)
                    gd.state, gd.awareness = ('patrol', 0.0)
                    gd.spotted_called = False

    def hazard(self, x, z, delay=1.4, radius=1.7):
        key = (round(x), round(z))
        if key in self.hazards_done:
            return
        self.hazards_done.add(key)
        self._clear_hazard(key)
        g = self.game
        ring = glow_quad(self.root, (x, 0.12, z), radius * 2.4, (1.0, 0.12, 0.06, 0.0), tex('ring'), billboard=False, add=True, bin_sort=37)
        ring.rotation_x = 90
        yaw = random.Random(int(x * 7 + z)).uniform(0, 180)
        beam = mk(self.root, 'cube', (x, 9.0, z), (0.55, 0.55, 5.6), rgb(96, 40, 20), tex('ash'), rot=(0, yaw, 0), emissive=0.45)
        flames = self.fx.fire((x, 9.4, z), scale=0.8, intensity=0.8)
        for e in flames:
            e.cull = False
        g.audio.play('alert', 0.35)
        t = 0.0
        while t < delay:
            t += self.dt
            k = min(1.0, t / delay)
            ring.alpha = (0.35 + 0.5 * k) * (0.6 + 0.4 * math.sin(Clock.now * (10 + 14 * k)))
            size = radius * 2.4 * (1.0 - 0.15 * k)
            ring.scale = Vec3(size, size, 1)
            beam.y = 9.0 - 0.4 * k
            yield
        t = 0.0
        y0 = beam.y
        while t < 0.2:
            t += self.dt
            k = min(1.0, t / 0.2)
            beam.y = y0 + (0.3 - y0) * ease_in(k)
            for e in flames:
                e.pos = Vec3(x, beam.y + 0.4, z)
            yield
        for e in flames:
            e.pos = Vec3(x, 0.55, z)
        glow = self.rig.add((x, 1.2, z), color=(1.0, 0.5, 0.2), intensity=1.4, radius=7.0, flicker=0.4, speed=8.0)
        g.audio.play('beam_fall', 0.9)
        self.cam.shake(0.35, 0.5)
        self.fx.dust_puff((x, 0.3, z), 12, color=(0.5, 0.4, 0.34))
        self.fx.sparks((x, 0.6, z), 24)
        self.flash_light((x, 1.5, z), (1.0, 0.5, 0.2), 3.2, 11, 0.7)
        ring.alpha = 0.0
        p = self.player
        if math.hypot(p.x - x, p.z - z) < radius and (not self.failing) and (self.phase in ('stealth', 'chase')):
            self.caught('Crushed by a burning beam')
        self.world.add_box(x, z, 1.0, 4.0, blocks_sight=False)
        self.hazard_objs[key] = (beam, flames, glow, self.world.boxes[-1])
        self.fx.smoke((x, 0.5, z), scale=1.4, rate=2, tone=0.12, alpha=0.4)

    def _clear_hazard(self, key):
        old = self.hazard_objs.pop(key, None)
        if not old:
            return
        beam, flames, glow, box = old
        destroy(beam)
        for e in flames:
            e.enabled = False
            e.clear()
        self.rig.remove(glow)
        if box in self.world.boxes:
            self.world.boxes.remove(box)

    def on_update(self, dt):
        g = self.game
        self._follow_torches()
        if self.phase in ('hunt', 'hunt_done', 'hunt_intro'):
            self.hunt_update(dt)
        if self.phase == 'stealth' and self.stealth_active and (not self.failing):
            peak = max((gd.awareness for gd in self.guards if gd.alive), default=0.0)
            vig = g.post.values.get('vignette', 0.5)
            g.post.values['vignette'] = vig + (0.5 + 0.35 * peak - vig) * min(1.0, dt * 6.0)
        if self.phase == 'chase' and (not self.failing):
            p = self.player
            for gd in self.chasers:
                if gd.alive and math.hypot(gd.x - p.x, gd.z - p.z) < 1.2:
                    self.caught('They caught you')
                    break
        self.bat_t += dt
        for i, b in enumerate(self.bats):
            if self.bats_flee:
                b.root.rotation_y = 180 + b.vx * 8
                b.root.z -= (8.0 + i) * dt
                b.root.x += b.vx * dt
                b.root.y = max(1.5, b.root.y - 0.2 * dt)
                if b.root.z < CAVE[1] - 30:
                    b.root.enabled = False
            else:
                b.root.x += math.sin(self.bat_t * 0.9 + i) * 0.4 * dt
            b.speed = 16.0
            b.update(self.bat_t)

    def on_home(self):
        if self.phase == 'stealth':
            self.tl.run(self.home_seq())

    def home_seq(self):
        g = self.game
        a = self.abdo
        fx, fz = FIRE
        self.phase = 'home'
        self.stealth_active = False
        self.begin_cutscene()
        for gd in list(self.guards):
            gd.awareness = 0.0
            if gd not in self.chasers and math.hypot(gd.x - fx, gd.z - fz) < 14.0:
                self._discard(gd)
        g.hud.objective(None)
        g.audio.stop('mus_burn', 2.0)
        self.shot((fx - 8.0, 3.0, fz - 5.0), (fx, 0.6, fz + 0.4), speed=0.7)
        yield from self.walk(a, fx - 4.2, fz - 0.9, speed=1.8)
        a.face(1, 0.35)
        yield 0.9
        yield from self.talk([('Abdo', 'Mother? Father? ...Leila?')], {'Abdo': a})
        self.shot((fx + 3.4, 3.8, fz - 6.4), (fx, 0.0, fz + 0.4), speed=0.5)
        g.audio.play('heartbeat', 0.5)
        yield 3.2
        self.tl.run(self.walk(a, fx - 2.9, fz - 0.2, speed=1.2))
        yield 1.4
        yield from self.talk([('Abdo', 'No...')], {'Abdo': a})
        yield 0.6
        self.shot((fx - 3.6, 2.4, fz - 4.4), (fx - 1.0, 0.5, fz + 0.5), speed=0.8)
        self.tl.run(self.walk(a, fx - 1.5, fz - 0.6, speed=1.0))
        yield 1.4
        g.audio.play('pickup', 0.8)
        self.bread.enabled = False
        self.bread_loaf.enabled = False
        self.quarry.enabled = False
        yield 0.7
        yield from self.talk([('Abdo', 'The bread is still warm.'), ('Abdo', 'Still warm... They were sitting right here. Right here.')], {'Abdo': a})
        a.set_pose('kneel')
        g.post.tween(2.5, desat=0.5, vignette=0.7)
        g.audio.play('heartbeat', 0.6)
        yield 3.0
        self.centurion.root.enabled = True
        self.soldier.root.enabled = True
        self.centurion.root.x, self.centurion.root.z = (fx - 13.0, fz - 1.8)
        self.soldier.root.x, self.soldier.root.z = (fx - 14.2, fz - 0.4)
        self._cent_lit = []
        for c in (self.centurion, self.soldier):
            stick, rag, tip = self._torch_prop(c)
            L = self.rig.add((0, 1.4, 0), color=(1.0, 0.6, 0.28), intensity=1.6, radius=8.5, flicker=0.35, speed=9.0)
            ems = self.fx.fire((0, 1.1, 0), scale=0.5, intensity=0.6)
            for e in ems:
                e.cull = False
            self._cent_lit.append((tip, L, ems))
        self._cent_torch = self._cent_lit[0][1]

        def carry(dt):
            for tip, L, ems in self._cent_lit:
                if not L.enabled:
                    continue
                p = tip.world_position
                L.pos = Vec3(p.x, p.y + 0.3, p.z)
                for e in ems:
                    e.pos = Vec3(p.x, p.y + (0.0 if e is ems[0] else 0.22), p.z)
        self.updaters.append(carry)
        self._carry = carry
        self.shot((fx + 3.2, 2.5, fz - 4.8), (fx - 4.5, 1.3, fz + 0.2), speed=0.8)
        self.go(self.centurion, fx - 6.0, fz - 1.2, speed=1.7)
        self.go(self.soldier, fx - 7.2, fz - 0.2, speed=1.7)
        yield 3.8
        yield from self.talk([('Centurion', 'Search every cellar. The king wants no one left to remember the name Thunder.'), ('Soldier', "These three never left their supper, sir. A man from this house went hunting three days ago. Sheikh Harith's best man, they say."), ('Centurion', 'Then he comes home to ashes. Find him before dawn.')], {'Centurion': self.centurion, 'Soldier': self.soldier})
        g.audio.play('clink', 0.8)
        self.tl.run(self.walk(self.centurion, fx - 4.2, fz - 0.9, speed=0.8))
        a.set_pose('stand')
        yield 0.5
        yield from self.talk([('Soldier', 'There! By the fire!'), ('Centurion', 'Take him alive. I want to know who else is hiding.')], {'Soldier': self.soldier, 'Centurion': self.centurion})
        g.audio.play('alert', 0.9)
        g.post.flash((1.0, 0.2, 0.1), 0.5, 1.6)
        self.cam.shake(0.18, 0.4)
        self.end_cutscene()
        yield from self.begin_chase()

    def begin_chase(self):
        g = self.game
        self.phase = 'chase'
        self.stealth_active = False
        self.centurion.root.enabled = False
        self.soldier.root.enabled = False
        for tip, L, ems in self._cent_lit:
            L.enabled = False
            for e in ems:
                e.enabled = False
        self.checkpoint = (FIRE[0] + 2.4, FIRE[1] - 1.8)
        self.player.teleport(*self.checkpoint)
        self._spawn_chasers()
        g.audio.music('mus_burn', 0.6, fade=1.0)
        g.hud.objective('RUN to the cave - hold SHIFT')
        g.hud.hint('Hold  SHIFT  to run      Watch the red rings: a burning beam is about to fall', hold=8)
        self.hazards_done.clear()
        self.chase_triggers = [self.trigger(30.0, 11.0, 2.0, 40, lambda: self.tl.run(self.hazard(36.5, 12.9, 1.25))), self.trigger(42.0, 16.0, 2.0, 40, lambda: self.tl.run(self.hazard(48.5, 18.9, 1.25)))]
        yield 0.0

    def _spawn_chasers(self):
        fx, fz = self.checkpoint
        spots = [(fx - 9.0, fz + 0.5, ROMAN), (fx - 10.5, fz - 1.5, IRON), (fx - 11.5, fz + 2.2, IRON)]
        for x, z, look in spots:
            gd = Guard(self, (x, z), route=[], facing=90, speed=1.5, view=12.0, fov=90, **look)
            gd.state = 'chase'
            gd.spotted_called = True
            gd.chase_speed = 4.7
            gd.cone.enabled = False
            self.add_guard(gd)
            self.attach_torch(gd)
            self.chasers.append(gd)

    def _discard(self, gd):
        gd.alive = False
        gd.cone.enabled = False
        gd.ch.root.enabled = False
        if gd in self.guards:
            self.guards.remove(gd)
        if gd in self.actors:
            self.actors.remove(gd)

    def on_cave(self):
        if self.phase == 'chase':
            self.tl.run(self.cave_seq())

    def _throw_torch(self, gd, tx, tz, dur=0.95):
        entry = next((e for e in self.torches if e[0] is gd), None)
        if entry is None:
            return
        self.torches.remove(entry)
        _, L, ems = entry
        hand = gd.torch_tip.world_position
        gd.torch_stick.enabled = False
        gd.torch_rag.enabled = False
        stick = mk(self.root, 'cylinder', (hand.x, hand.y, hand.z), (0.07, 0.5, 0.07), rgb(70, 48, 32), origin=(0, 0.25, 0))
        gd.ch.arm_l_goal = -150.0
        sx, sy, sz = (hand.x, hand.y, hand.z)
        t = 0.0
        while t < dur:
            t += self.dt
            k = min(1.0, t / dur)
            x, z = (sx + (tx - sx) * k, sz + (tz - sz) * k)
            y = sy + (0.1 - sy) * k + math.sin(k * math.pi) * 1.8
            stick.position = Vec3(x, y, z)
            stick.rotation_x = k * 600.0
            L.pos = Vec3(x, y + 0.3, z)
            for e in ems:
                e.pos = Vec3(x, y + 0.1, z)
            if t > 0.25:
                gd.ch.arm_l_goal = -20.0
            yield
        gd.ch.arm_l_goal = None
        stick.position = Vec3(tx, 0.07, tz)
        stick.rotation = Vec3(90, 25, 0)
        L.pos = Vec3(tx, 0.8, tz)
        L.radius = 12.0
        for i, e in enumerate(ems):
            e.pos = Vec3(tx, 0.18 + 0.2 * i, tz)
        self.fx.sparks((tx, 0.2, tz), 18)
        self.fx.dust_puff((tx, 0.1, tz), 6, color=(0.4, 0.36, 0.34))
        self.game.audio.play('clink', 0.7)

    def cave_seq(self):
        g = self.game
        a = self.abdo
        self.phase = 'cave'
        self.begin_cutscene()
        g.hud.objective(None)
        cx, cz = CAVE
        cen, s1, s2 = self.chasers
        for gd in self.chasers:
            gd.frozen = True
        g.post.tween(1.6, vignette=0.82, desat=0.25, tint=(0.97, 0.99, 1.03))
        self.rig.ambient = Vec3(0.06, 0.07, 0.12)
        self.rig.fog_color = Vec3(0.03, 0.035, 0.07)
        self.cave_light.enabled = True
        self.tl.run(self.walk(a, cx + 2.8, cz + 7.0, speed=5.2))
        for gd, (px, pz) in zip(self.chasers, [(cx - 0.6, cz - 4.4), (cx + 2.2, cz - 5.4), (cx - 2.8, cz - 6.2)]):
            self.go(gd.ch, px, pz, speed=4.6)
        yield 2.6
        a.face(-0.5, -1.0)
        a.set_pose('kneel')
        self.shot((cx - 2.4, 1.0, cz + 10.6), (cx + 0.4, 1.3, cz - 3.0), speed=99)
        self.cam.snap()
        g.audio.play('heartbeat', 0.8)
        yield 1.4
        who = {'Centurion': cen.ch, 'Soldier': s1.ch}
        yield from self.talk([('Soldier', 'He ran in here, sir. I saw his shadow.')], who)
        yield from self.talk([('Centurion', 'Then go in and drag him out.')], who)
        yield from self.talk([('Soldier', 'Sir... this is the old burial cave. The elders say the dead walk in there.')], who)
        yield from self.talk([('Centurion', 'Then throw a torch in. If he is in there he will come out coughing.')], who)
        self.tl.run(self._throw_torch(s1, cx - 1.4, cz + 3.6))
        yield 1.1
        self.bats_flee = True
        g.audio.play('caw', 0.5)
        self.cam.shake(0.14, 0.7)
        yield 2.2
        for gd in (s1, s2):
            self.go(gd.ch, gd.x, gd.z - 1.4, speed=2.2)
        yield 1.6
        yield from self.talk([('Soldier', 'Bats... nothing but bats and bones.'), ('Centurion', 'Leave it. Let the desert finish him. The king will want to hear that Thunder is dead.')], who)
        for gd in self.chasers:
            self.go(gd.ch, gd.x - 14.0, gd.z - 7.0, speed=2.6)
        yield 3.4
        for gd in list(self.chasers):
            self._discard(gd)
        self.chasers.clear()
        self.shot((cx + 0.8, 1.2, cz + 9.8), (cx + 2.4, 0.8, cz + 7.0), speed=0.6)
        g.post.tween(2.0, vignette=0.7, desat=0.5)
        yield 2.5
        if g.state.get('abdo_doubt'):
            second = ('Abdo', 'I doubted at that table, and still I said yes. Harith. The king. Me. Which of us lit the fire?')
        else:
            second = ('Abdo', 'I said I would do it. I did. And they paid the bill - every one of them.')
        yield from self.talk([('Abdo', 'They are gone. Everyone is gone.'), second, ('Abdo', 'Abdo bin Suhail died tonight. Someone else will walk out of this cave.')], {'Abdo': a})
        g.hud.fade_to(1.0, 2.0)
        yield 2.4
        self.tl.run(self.to_ruins())

    def to_ruins(self):
        g = self.game
        self.phase = 'skip'
        g.audio.stop_all(fade=1.0)
        yield 0.5
        g.hud.caption('ONE MONTH LATER', hold=2.2, fade=0.9, size=2.4)
        rig = self.rig
        rig.ambient, rig.sun_color, rig.sun_dir, rig.fog_color = (ASH['ambient'], ASH['sun'], ASH['sun_dir'], ASH['fog'])
        rig.fog_density = 0.009
        g.post.set(vignette=0.5, bloom=0.65, grain=0.04, tint=ASH['tint'], desat=0.38)
        self.sky.fade_to(self, 'sky_dawn', duration=0.2)
        charcoal = color.rgba(0.3, 0.26, 0.25, 1)
        for parts, level, L, fx, (cx, cz, w, d, h) in self.house_parts:
            if L:
                L.enabled = False
            for e in fx:
                e.enabled = False
                e.clear()
            for p in parts[:-1]:
                p.color = charcoal
            if parts and parts[-1] is not None:
                parts[-1].enabled = False
            self.fx.smoke((cx, h * 0.5, cz), scale=1.4, rate=1, tone=0.2, alpha=0.3, wind=(0.4, 0.2, 0.05))
        self.ground.color = color.rgba(0.62, 0.58, 0.56, 1)
        for p in self.remains:
            p.enabled = False
        for parts, level, L, fx, box in self.house_parts:
            for p in parts:
                if getattr(p, 'is_window', False):
                    p.set_shader_input('emissive', 0.0)
        for i, (gx, gz, gyaw, glen) in enumerate(GRAVES):
            mound = Entity(parent=self.root, position=(gx, 0, gz), rotation_y=gyaw, add_to_scene_entities=False)
            mk(mound, 'sphere', (0, 0.0, 0), (0.85, 0.34, glen), rgb(120, 98, 82), tex('dirt'))
            for k in range(8):
                a_ = k / 8.0 * 2 * math.pi
                mk(mound, 'sphere', (math.sin(a_) * 0.52, 0.05, math.cos(a_) * glen * 0.52), (0.16, 0.12, 0.16), rgb(150, 142, 132))
            mk(mound, 'cube', (0, 0.27, glen * 0.5 + 0.05), (0.38, 0.5, 0.1), rgb(168, 150, 124), tex('mudbrick'))
            mk(mound, 'cylinder', (0, 0.52, glen * 0.5), (0.38, 0.1, 0.38), rgb(168, 150, 124), tex('mudbrick'), rot=(90, 0, 0), origin=(0, 0, 0))
        self.family_embers.enabled = False
        self.family_light.enabled = False
        for gd in list(self.guards):
            self._discard(gd)
        for gd, L, ems in self.torches:
            L.enabled = False
            for e in ems:
                e.enabled = False
        self.rig.add((FIRE[0], 1.4, FIRE[1]), color=(1.0, 0.62, 0.34), intensity=0.9, radius=9.0, flicker=0.2, speed=4.0)
        self.ash.color0 = (0.62, 0.6, 0.6, 0.5)
        self.ash.color1 = (0.62, 0.6, 0.6, 0.0)
        self.ash2.enabled = False
        self.bats_flee = True
        self.abdo.root.enabled = False
        self.night = self.add_char((CAVE[0] - 1.0, CAVE[1] - 3.0), robe=rgb(26, 24, 32), trim=rgb(110, 30, 34), head='hood', head_color=rgb(18, 18, 24), cloak=rgb(16, 16, 22), skin='tan', weapon='dagger')
        self.night.face(-1, -0.3)
        self.player.set_character(self.night)
        self.player.step_sound = 'step_sand'
        self.player.speed, self.player.run_speed = (3.2, 5.4)
        self.cam.release()
        self.shot((CAVE[0] - 6.0, 4.0, CAVE[1] - 14.0), (CAVE[0] - 1.0, 1.4, CAVE[1] - 3.0), speed=9)
        self.cam.snap()
        g.audio.music('mus_ruins', 0.55, fade=3.0)
        g.audio.loop('amb_wind', 0.3, fade=3.0)
        g.hud.fade_to(0.0, 2.4)
        yield 3.0
        self.end_cutscene()
        self.phase = 'ruins'
        self.player.locked = False
        g.hud.objective("Return to your family's fire")
        self.vow_it = self.interact(FIRE[0], FIRE[1], 'Kneel at the fire', self.on_vow, radius=3.0)
        self.bounds = (-46.0, 62.0, -14.0, 32.0)
        yield 0.0

    def on_vow(self):
        self.tl.run(self.vow())

    def vow(self):
        g = self.game
        n = self.night
        self.phase = 'vow'
        self.begin_cutscene()
        g.hud.objective(None)
        yield from self.walk(n, FIRE[0] - 1.6, FIRE[1] - 0.3, speed=2.0)
        n.face(1, 0.1)
        n.set_pose('kneel')
        self.shot((FIRE[0] + 4.0, 1.5, FIRE[1] - 3.4), (FIRE[0] - 1.0, 1.0, FIRE[1] - 0.2), speed=0.7)
        yield 1.5
        seats = [(bx, bz) for bx, bz, _, _ in FAMILY]
        for sx, sz in seats:
            self.fx.magic((sx, 0.9, sz), color=(1.0, 0.82, 0.5), count=26)
            self.flash_light((sx, 1.0, sz), (1.0, 0.8, 0.5), 1.4, 5, 3.0)
        g.audio.play('stinger_soft', 0.6)
        yield 2.2
        yield from self.talk([('Abdo', 'I broke bread with the men who sold your lives. I carried their knife into a house I had never seen.'), ('Abdo', 'Harith sent me to kill. The king sent soldiers to burn. And a Roman called Varro stood at my fire and gave the order.')], {'Abdo': n})
        post = mk(self.root, 'cylinder', (FIRE[0] + 3.0, 0.0, FIRE[1] + 1.4), (0.3, 2.3, 0.3), rgb(24, 18, 16))
        crow = CrowBird(self.root, scale=0.9)
        crow.root.position = (FIRE[0] + 12.0, 9.0, FIRE[1] + 8.0)
        crow.root.rotation_y = -125

        def fly(dt, c=crow):
            c.update(Clock.now)
        self.updaters.append(fly)
        self.tl.to(crow.root, 'position', Vec3(FIRE[0] + 3.0, 2.4, FIRE[1] + 1.4), 2.4, ease_out)
        self.tl.to(crow.root, 'rotation_y', -150, 2.4)
        g.audio.play('caw', 0.7)
        yield 2.7
        crow.speed = 0.0
        crow.wing_l.rotation_z, crow.wing_r.rotation_z = (-60, 60)
        self.updaters.remove(fly)
        yield 0.8
        yield from self.talk([('Abdo', 'Abdo bin Suhail is dead. Let the crows have his name.'), ('Abdo', 'Thunder, Iron, Rome. I will take every one of you apart, one shadow at a time. Varro first.')], {'Abdo': n})
        yield from self.transformation()
        g.hud.title_card('', 'THE NIGHT CROW', '', hold=2.4)
        yield 3.6
        g.hud.fade_to(1.0, 1.8)
        yield 2.2
        g.next_scene()

    def transformation(self):
        g = self.game
        n = self.night
        n.set_pose('stand')
        self.shot((FIRE[0] + 3.4, 2.8, FIRE[1] - 5.0), (FIRE[0] - 1.6, 1.4, FIRE[1] - 0.3), speed=1.4)
        yield 0.6
        flock = []
        for i in range(16):
            b = CrowBird(self.root, scale=random.uniform(0.55, 0.85))
            b.root.position = (FIRE[0] - 1.6, -3.0, FIRE[1] - 0.3)
            flock.append((b, i))
        t0 = Clock.now
        state = {'on': True, 'spread': 0.0}

        def swirl(dt):
            if not state['on']:
                return
            t = Clock.now - t0
            for b, i in flock:
                a = t * (2.6 + 0.04 * i) + i * 0.62
                r = 0.7 + state['spread'] * (1.8 + i % 4 * 0.6)
                rise = min(t, 2.0) * 0.9 + i % 5 * 0.32 + state['spread'] * (1.0 + i % 3 * 0.8) + math.sin(a * 0.7 + i) * 0.25
                b.root.position = (FIRE[0] - 1.6 + math.cos(a) * r, 0.2 + rise, FIRE[1] - 0.3 + math.sin(a) * r)
                b.root.rotation_y = -math.degrees(a)
                b.speed = 12.0
                b.update(Clock.now)
        self.updaters.append(swirl)
        g.audio.play('caw', 0.9)
        g.audio.play('stinger', 0.8)
        g.post.tween(1.8, desat=0.0, vignette=0.7, bloom=1.0, tint=(0.85, 0.9, 1.1))
        yield 1.8
        g.post.flash((0.0, 0.0, 0.0), 1.0, 2.2)
        self.night.root.enabled = False
        self.crow = self.add_char((FIRE[0] - 1.6, FIRE[1] - 0.3), robe=rgb(18, 18, 26), trim=rgb(120, 30, 34), head='hood', head_color=rgb(14, 14, 20), cloak=rgb(12, 12, 18), mask=True, weapon='dagger')
        self.crow.face(1, 0.3)
        self.cam.shake(0.25, 0.8)
        self.ring_fx((FIRE[0] - 1.6, FIRE[1] - 0.3), (0.5, 0.6, 1.0), 9.0, 1.2, y=0.1)
        self.tl.to_item(state, 'spread', 1.0, 2.0)
        yield 2.6
        self.shot((FIRE[0] - 5.0, 1.0, FIRE[1] - 3.4), (FIRE[0] - 1.6, 1.7, FIRE[1] - 0.3), speed=1.0)
        yield 2.4
        state['on'] = False
        self.updaters.remove(swirl)
        for b, i in flock:
            b.root.enabled = False
