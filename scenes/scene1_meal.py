import math
import textwrap
from ursina import Entity, Text, Vec3, camera, color, destroy
from engine.assets import FONT, FONT_BOLD, tex
from engine.entities import glow_quad, mk, rgb, shade
from engine.props import CrowBird, contact_shadow, Sky, banner, ground_patches, scatter_clutter, soft_path, bowl, brazier, candle, crop_field, cushion, dish, fire_logs, goblet, ground, hay, house, log_seat, seat_mat, tent_flap, jug, lantern, light_shaft, moon, palm, path_strip, planets, rock, rug, torch, well, low_table, wall_box, bed
from engine.scene_base import BaseScene
from engine.timing import Clock, ease_out
HX = 200.0
DUSK = dict(ambient=Vec3(0.36, 0.37, 0.54), sun=Vec3(1.0, 0.78, 0.55), sun_dir=Vec3(-0.75, 0.62, 0.25), fog=Vec3(0.5, 0.4, 0.44), tint=(1.02, 0.99, 0.97))
NIGHT = dict(ambient=Vec3(0.11, 0.13, 0.24), sun=Vec3(0.14, 0.19, 0.36), sun_dir=Vec3(0.25, 0.8, -0.3), fog=Vec3(0.05, 0.07, 0.15), tint=(0.9, 0.98, 1.1))
SCROLL_TEXT = "TONIGHT. SHEIKH HARITH'S TENT, BEYOND THE PALMS. COME ALONE. TELL NO ONE. BURN THIS."

def _mix(a, b, k):
    return a + (b - a) * k

def caesar(text, shift=3):
    out = []
    for ch in text:
        if 'A' <= ch <= 'Z':
            out.append(chr((ord(ch) - 65 + shift) % 26 + 65))
        else:
            out.append(ch)
    return ''.join(out)

class Scene1Meal(BaseScene):
    number = 1
    name = 'The Secret Meal'
    author = 'Obada Alahmar'

    def build(self):
        g = self.game
        self.tod = 0.0
        self.has_water = False
        self.family_done = False
        self.scroll_taken = False
        self.scroll_ready = False
        self.scroll_open = False
        self.in_hall = False
        self.wood = 0
        self.wood_items = []
        self.torches = []
        self.birds = []
        self.hall_ok = False
        self.bounds = (-30, 62, -14, 17)
        rig = self.rig
        rig.ambient, rig.sun_color, rig.sun_dir, rig.fog_color = (DUSK['ambient'], DUSK['sun'], DUSK['sun_dir'], DUSK['fog'])
        rig.fog_density = 0.0105
        g.post.set(vignette=0.38, bloom=0.7, tint=DUSK['tint'], grain=0.03)
        self.cam.set_fov(70)
        self.sky = Sky(self, 'sky_dusk', stars=True)
        self.sky.stars.enabled = False
        self.sun = moon(self, (-150, 14, 60), size=34, color=(1.0, 0.62, 0.26, 1.0), halo=0.55, halo_color=(1.0, 0.5, 0.2))
        self.moon = moon(self, (60, 55, 150), size=26)
        self.moon.alpha = 0.0
        self.planet_sprites = [(q, q.alpha) for q in planets(self, ringed=(-120, 48, 150), red=(110, 74, 150))]
        for q, _ in self.planet_sprites:
            q.alpha = 0.0
        self._build_village()
        self._build_hall()
        self.abdo = self.add_char((-19, 1), robe=rgb(140, 100, 64), trim=rgb(170, 50, 40), head='shemagh', head_color=rgb(236, 228, 208), skin='tan')
        self.abdo.face(1, 0)
        self.set_player(self.abdo)
        self.player.step_sound = 'step_sand'
        fire = (-9.0, 3.6)
        self.wife = self._sitter(-10.6, 3.0, fire, robe=rgb(150, 60, 90), trim=rgb(220, 190, 120), head='scarf', head_color=rgb(120, 40, 70), skin='tan')
        self.mother = self._sitter(-9.0, 5.3, fire, robe=rgb(96, 98, 108), trim=rgb(150, 150, 160), head='scarf', head_color=rgb(110, 110, 120), skin='tan', scale=0.97)
        self.father = self._sitter(-7.2, 3.1, fire, robe=rgb(122, 110, 90), trim=rgb(150, 100, 60), head='shemagh', head_color=rgb(232, 226, 210), beard=rgb(170, 170, 170), skin='olive')
        self.vill1 = self._sitter(21.0, 6.4, (22.5, 7.3), robe=rgb(110, 90, 70), trim=rgb(140, 90, 60), head='shemagh', head_color=rgb(220, 214, 196), skin='dark')
        self.vill2 = self._sitter(24.0, 7.2, (22.5, 7.3), robe=rgb(70, 86, 100), trim=rgb(140, 120, 70), head='turban', head_color=rgb(160, 150, 130), beard=rgb(60, 50, 44), skin='tan')
        self.vill1.talking = True
        self.sentry1 = self.add_char((52.0, 1.3), robe=rgb(70, 44, 96), trim=rgb(220, 190, 80), head='turban', head_color=rgb(60, 40, 84), weapon='spear', build='broad', skin='dark')
        self.sentry2 = self.add_char((56.0, 1.3), robe=rgb(70, 44, 96), trim=rgb(220, 190, 80), head='turban', head_color=rgb(60, 40, 84), weapon='spear', build='broad', skin='tan')
        self.sentry1.face(0.3, 1)
        self.sentry2.face(-0.3, 1)
        self.fx.dust((10, 2, 2), area=(40, 2.5, 14), count=60, color=(1.0, 0.82, 0.55), alpha=0.5, size=0.11)
        self.fireflies = self.fx.fireflies((20, 1.5, 2), area=(40, 1.2, 14), count=24)
        self.fireflies.enabled = False
        self.fireflies.clear()
        self.well_it = self.interact(-5.0, -3.0, 'Draw water from the well', self.on_well, radius=3.2)
        self.trigger(-9.0, 3.8, 9.5, 8.0, self.on_family_area, once=False)
        self._build_villagers()
        self._build_firewood()
        g.audio.music('mus_village', 0.5, fade=3.0)
        g.audio.loop('amb_wind', 0.28, fade=3.0)

    def _build_villagers(self):
        self.villagers = {}
        fire = (22.5, 7.3)

        def person(x, z, face_to, **look):
            ch = self.add_char((x, z), **look)
            ch.face(face_to[0] - x, face_to[1] - z)
            self.world.add_circle(x, z, 0.5)
            return ch

        def add(key, chars, at, label, first, again, night, radius=2.7, sitting=None):
            m = Entity(parent=self.root, position=(at[0], 2.5, at[1]), add_to_scene_entities=False)
            mk(m, 'cube', (0, 0, 0), (0.3, 0.3, 0.3), rgb(255, 214, 110), emissive=1.0, rot=(45, 0, 45))
            glow_quad(m, (0, 0, 0), 1.1, (1.0, 0.8, 0.35, 0.6), tex('glow'))
            self.villagers[key] = dict(chars=chars, at=at, first=first, again=again, night=night, visits=0, marker=m, sitting=sitting, base_y=2.5)
            self.interact(at[0], at[1], label, lambda k=key: self.tl.run(self._chat_seq(k)), radius=radius, once=False)
        idris = person(-16.8, -0.6, (-19, 1), robe=rgb(120, 98, 70), trim=rgb(150, 110, 70), head='cap', head_color=rgb(176, 160, 130), beard=rgb(176, 176, 172), skin='olive', scale=0.96)
        add('idris', {'Idris': idris}, (-16.8, -0.6), 'Talk to Idris', first=[('Idris', 'Abdo! There you are. I have not forgotten last week, you know.'), ('Abdo', 'Last week?'), ('Idris', 'My cart, in the ditch. You and those shoulders. Thank you, my boy. I would be out there still.'), ('Abdo', 'Any neighbour would have done the same, Idris.'), ('Idris', 'Any neighbour would have said he was busy. Go on, your wife has the fire lit.')], again=[('Idris', 'Go on, Abdo. Your wife keeps the bread warm for nobody else.')], night=[('Idris', 'Walk carefully tonight, Abdo. The air feels wrong, like the hour before a storm.')])
        nadia = person(-1.4, -5.2, (-5, -3), robe=rgb(132, 74, 84), trim=rgb(214, 176, 100), head='scarf', head_color=rgb(96, 72, 104), skin='tan')
        add('nadia', {'Nadia': nadia}, (-1.4, -5.2), 'Talk to Nadia', first=[('Nadia', 'Abdo! Wait. Thank you for mending the well rope. My arms were ready to give up on it.'), ('Abdo', 'It only needed a new knot, Nadia.'), ('Nadia', 'In this village a new knot is a great kindness. Fill your jar before the light goes.')], again=[('Nadia', 'The water is cold and sweet tonight. Take all you need.')], night=[('Nadia', 'You are going out in the dark? Then follow the torches, and take care.')])
        add('fire', {'Harun': self.vill1, 'Salim': self.vill2}, (22.5, 4.7), 'Talk to the men by the fire', first=[('Harun', 'Abdo! Sit, warm your hands. You are the man who mended our roof before the rains.'), ('Salim', 'And carried my grain home when my son was away. We have not thanked you enough.'), ('Abdo', 'You thank me with every cup of tea, Salim.'), ('Harun', 'Then another is owed. ...I will say this, though. Strangers at the big tent. Purple banners, spears.'), ('Salim', 'The elders go in at dusk and come out quiet. When elders go quiet, farmers should worry.'), ('Abdo', 'I will keep my eyes open. Good night to you both.')], again=[('Harun', 'Go well, Abdo. The fire will be here when you want it.')], night=[('Harun', 'Out so late, Abdo? Take care on that road. Those torches are lit for someone tonight.')], radius=3.8, sitting=fire)
        samir = person(38.6, 4.6, (36, 1.5), robe=rgb(86, 108, 92), trim=rgb(190, 150, 80), head='cap', head_color=rgb(200, 190, 160), skin='tan', scale=1.03)
        add('samir', {'Samir': samir}, (38.6, 4.6), 'Talk to Samir', first=[('Samir', 'Abdo! I have waited all week to say it. Thank you for lending me your ox in spring. My field would still be dust.'), ('Abdo', 'Bring him back fed, that is all I ask.'), ('Samir', 'He is fatter than I am. ...Do you know what is going on at that big tent? Spears at the door. Nobody tells us anything.'), ('Abdo', "Perhaps it is only the elders' business."), ('Samir', "Elders' business has a way of becoming everyone's business. Go well, Abdo.")], again=[('Samir', 'Careful on the road. I do not like those banners.')], night=[('Samir', 'The torches are lit all the way to the tent. Somebody important is expected. I hope it is good news.')], radius=3.0)
        hajar = person(13.4, -4.4, (11, -2), robe=rgb(84, 90, 112), trim=rgb(176, 150, 96), head='scarf', head_color=rgb(70, 74, 92), skin='olive', scale=0.94)
        hajar.set_pose('sit')
        add('hajar', {'Hajar': hajar}, (13.4, -4.4), 'Talk to old Hajar', first=[('Hajar', 'Abdo, come here, let me look at you. You are the one who split my firewood all winter.'), ('Abdo', 'It was no trouble, Hajar.'), ('Hajar', 'Trouble is what you do not count, and you never count. My bones remember kindness, my boy.'), ('Hajar', 'Now go home and eat. A man who works like you should not skip his supper.')], again=[('Hajar', 'Eat well, Abdo. Rest well. The world can wait one night.')], night=[('Hajar', 'Be careful, my boy. When the elders light a road, someone always walks it with a heavy heart.')], radius=3.2)

        def bob(dt):
            for v in self.villagers.values():
                v['marker'].y = v['base_y'] + math.sin(Clock.now * 2.6 + v['at'][0]) * 0.08
                v['marker'].rotation_y += 90.0 * dt
        self.updaters.append(bob)

    def _chat_seq(self, key):
        v = self.villagers[key]
        a = self.abdo
        self.begin_cutscene(letterbox=False)
        first = v['visits'] == 0
        lines = v['first'] if first else v['night'] if self.scroll_taken else v['again']
        v['visits'] += 1
        chars = v['chars']
        c0 = list(chars.values())[0]
        for c in chars.values():
            self.turn_to(c, a.root.x, a.root.z)
        self.turn_to(a, c0.root.x, c0.root.z)
        mx, mz = ((a.root.x + c0.root.x) / 2.0, (a.root.z + c0.root.z) / 2.0)
        dx, dz = (c0.root.x - a.root.x, c0.root.z - a.root.z)
        ln = max(0.01, math.hypot(dx, dz))
        px, pz = (-dz / ln, dx / ln)
        if pz > 0:
            px, pz = (-px, -pz)
        self.shot((mx + px * 4.2, 1.9, mz + pz * 4.2), (mx, 1.25, mz), speed=1.8)
        who = dict(chars)
        who['Abdo'] = a

        def on_line(i, line):
            for n, c in who.items():
                c.talking = n == line[0]
        v['marker'].enabled = False
        yield 0.35
        yield from self.say(lines, on_line=on_line)
        for c in who.values():
            c.talking = False
        if v.get('sitting'):
            for c in chars.values():
                self.turn_to(c, v['sitting'][0], v['sitting'][1])
            self.vill1.talking = True
        self.end_cutscene()

    def _sitter(self, x, z, look_at, **look):
        ch = self.add_char((x, z), **look)
        ch.set_pose('sit')
        ch.face(look_at[0] - x, look_at[1] - z)
        self.world.add_circle(x, z, 0.5)
        return ch

    def _make_torch(self, x, z, lit=True):
        start = len(self.fx.emitters)
        L = torch(self, x, z, h=2.0, intensity=1.7, radius=10.5, flame=0.6, smoke=True, embers=True)
        ems = self.fx.emitters[start:]
        t = {'light': L, 'emitters': ems, 'x': x, 'z': z, 'lit': lit}
        if not lit:
            L.scale = 0.0
            for e in ems:
                e.enabled = False
                e.clear()
        self.torches.append(t)
        return t

    def _ignite(self, t):
        t['lit'] = True
        self.game.audio.play('torch_ignite', 0.6)
        self.tl.to(t['light'], 'scale', 1.0, 0.7)
        for e in t['emitters']:
            e.enabled = True
            e.prewarm(0.5)
        self.fx.sparks((t['x'], 2.2, t['z']), 10)
        self.flash_light((t['x'], 2.4, t['z']), (1.0, 0.7, 0.4), 2.4, 12, 0.5)

    def _build_village(self):
        ground(self, 170, 'sand', 110, rgb(196, 188, 176))
        ground_patches(self, -34, -16, 66, 20, count=110, seed=3)
        footprints = [(-17.0, -8.0, 5.8, 12.2), (-30.0, -12.0, -12.0, -2.0), (-24.2, -17.3, 6.0, 11.2), (45.8, 62.2, 3.0, 13.0)]
        for hx, hz, hw_, hd_ in ((8, 12.5, 6.2, 5.0), (19, 14.0, 5.6, 4.8), (31, 12.8, 6.4, 5.4), (11, -8.8, 5.6, 4.6), (33, -10, 6.0, 4.8), (-26, 14, 4.8, 4.2)):
            footprints.append((hx - hw_ / 2 - 0.9, hx + hw_ / 2 + 0.9, hz - hd_ / 2 - 0.9, hz + hd_ / 2 + 0.9))
        scatter_clutter(self, -32, -14, 64, 18, count=130, seed=5, avoid=footprints)
        soft_path(self, [(-13, 5.5), (-13, 1.5), (-5, 1.5), (54, 1.5), (54, 3.2)], width=2.6, seed=1)
        soft_path(self, [(-5, 1.5), (-5, -3.2)], width=1.5, seed=2)
        soft_path(self, [(-9, 1.5), (-9, 3.6)], width=2.2, col=rgb(160, 130, 100), seed=3)
        crop_field(self, -22, -7, 11, 8)
        crop_field(self, -20.6, 8.9, 6.0, 4.6, rows=4)
        self.abdo_house = house(self, -13, 9, 7.2, 5.0, h=3.0, door='south', door_w=1.5, door_cover='plank')
        mk(self.root, 'quad', (-9.9, 1.7, 6.48), (0.9, 0.8, 1), rgb(255, 196, 120), emissive=1.0, rot=(0, 0, 0))
        mk(self.root, 'quad', (-16.1, 1.7, 6.48), (0.9, 0.8, 1), rgb(255, 196, 120), emissive=1.0)
        self.rig.add((-13, 1.8, 5.6), color=(1.0, 0.72, 0.4), intensity=0.9, radius=6.5, flicker=0.15)
        well(self, -5, -3)
        for x, z, s in ((-27, 4, 1.0), (-25, 6.4, 0.9), (-2, 9, 0.9)):
            hay(self, x, z, s)
        for x, z in ((-19, 12.5), (-5.5, 12.0), (-1, 7.5), (-27, -2), (-9, -9), (6, 11), (13.5, 7.5), (40, 9), (46, 12), (38, -7), (28, -9), (-1, -8)):
            palm(self, x, z, h=4.0 + abs(x * 3 + z) % 3 * 0.4)
        for x, z, s in ((3, 5, 0.9), (30, 5.5, 0.8), (-16, -3.5, 1.1), (36, -3, 1.0), (9, -4, 0.8)):
            rock(self, x, z, s)
        self.fx.fire((-9.0, 0.15, 3.6), scale=0.9, intensity=1.2)
        self.fx.embers((-9.0, 0.6, 3.6), scale=0.8, rate=5)
        self.fire_light = self.rig.add((-9.0, 1.1, 3.6), color=(1.0, 0.6, 0.28), intensity=1.9, radius=9, flicker=0.3)
        fire_logs(self, -9.0, 3.6)
        for sx, sz in ((-10.6, 3.0), (-9.0, 5.3), (-7.2, 3.1)):
            seat_mat(self, sx, sz, ry=math.degrees(math.atan2(-9.0 - sx, 3.6 - sz)))
        log_seat(self, -9.6, 1.4, ry=0, ln=1.6)
        self.world.add_circle(-9, 3.6, 1.0)
        for cx, cz, w, d, h in ((8, 12.5, 6.2, 5.0, 3.0), (19, 14.0, 5.6, 4.8, 2.8), (31, 12.8, 6.4, 5.4, 3.2), (11, -8.8, 5.6, 4.6, 2.8), (33, -10, 6.0, 4.8, 3.0), (-26, 14, 4.8, 4.2, 2.6)):
            house(self, cx, cz, w, d, h=h, door='south' if cz > 0 else 'north', door_w=1.4, door_cover='plank')
            mk(self.root, 'quad', (cx + 1.2, 1.7, cz - d / 2 - 0.03), (0.8, 0.75, 1), rgb(255, 196, 120), emissive=1.0)
            self.rig.add((cx, 1.8, cz - d / 2 - 0.8), color=(1.0, 0.72, 0.4), intensity=0.6, radius=5, flicker=0.2)
        fire_logs(self, 22.5, 7.3, r=0.5)
        for sx, sz in ((21.0, 6.4), (24.0, 7.2)):
            seat_mat(self, sx, sz, ry=math.degrees(math.atan2(22.5 - sx, 7.3 - sz)))
        self.fx.fire((22.5, 0.15, 7.3), scale=0.8, intensity=1.1)
        self.rig.add((22.5, 1.0, 7.3), color=(1.0, 0.6, 0.28), intensity=1.6, radius=8, flicker=0.3)
        self.world.add_circle(22.5, 7.3, 0.7)
        for x in (4, 12, 20, 28, 36, 44):
            self._make_torch(x, 3.4, lit=False)
        house(self, 54, 8, 15, 9, h=4.4, door='south', door_w=3.0, texture='plaster', col=rgb(190, 170, 200), roof_col=rgb(72, 44, 86))
        self.tent_flap = tent_flap(self, 54.0, 3.55, width=3.0, h=3.25)
        banner(self, 50.2, 2.9, 3.42, 'thunder', height=3.0, face='south')
        banner(self, 57.8, 2.9, 3.42, 'thunder', height=3.0, face='south')
        brazier(self, 51.0, 1.9, scale=0.9, intensity=2.0, radius=12)
        brazier(self, 57.0, 1.9, scale=0.9, intensity=2.0, radius=12)
        self.hall_door_it = None

    def _build_hall(self):
        H = HX
        mk(self.root, 'plane', (H, 0, 0), (22, 1, 14), None, tex('tile'), tex_scale=(7, 4.5))
        rug(self, H, 0.3, 14.0, 7.2)
        wall_box(self, H, 5.4, 22, 0.7, 4.4, 'plaster', rgb(210, 186, 160), collide=False)
        wall_box(self, H - 11, -0.5, 0.7, 13, 4.4, 'plaster', rgb(210, 186, 160), collide=False)
        wall_box(self, H + 11, -0.5, 0.7, 13, 4.4, 'plaster', rgb(210, 186, 160), collide=False)
        wall_box(self, H, -6.6, 22, 0.7, 0.9, 'plaster', rgb(210, 186, 160), collide=False)
        mk(self.root, 'cube', (H, 4.2, 5.0), (22, 0.4, 0.5), rgb(120, 76, 48), tex('wood'))
        for dx in (-7, 0, 7):
            banner(self, H + dx, 2.5, 4.98, 'thunder', height=3.0, face='south')
        lantern(self, H - 8.5, 4.3, y=2.6)
        lantern(self, H + 8.5, 4.3, y=2.6)
        brazier(self, H + 8.4, 3.0, scale=0.85, intensity=1.5, radius=9)
        brazier(self, H - 8.4, 3.0, scale=0.85, intensity=1.5, radius=9)
        light_shaft(self, H - 4.5, 0.0, 3.4, height=5.2, width=2.4, color=(0.55, 0.7, 1.0, 0.22), tilt=-12)
        self.table_top = low_table(self, H, 0.5, 5.6, 1.6, h=0.5, collide=False)
        for x in (-2.2, 0.0, 2.2):
            cushion(self, H + x, 2.35, rgb(120, 40, 60), 1.3)
            cushion(self, H + x, -1.25, rgb(40, 70, 110), 1.3)
        start = len(self.fx.emitters)
        self.candle_lights = []
        for i, (x, z) in enumerate(((-1.3, 0.5), (1.3, 0.5), (-0.1, 0.9), (0.1, 0.1))):
            L = candle(self, H + x, z, y=self.table_top, light=i < 2, intensity=1.0, radius=7.5)
            if L:
                self.candle_lights.append(L)
        self.candle_emitters = self.fx.emitters[start:]
        self.table_light = self.rig.add((H, 1.6, 0.5), color=(1.0, 0.68, 0.36), intensity=0.7, radius=8, flicker=0.15)
        T = self.table_top
        self.course1 = [dish(self, H - 1.6, T, 0.5, rgb(206, 156, 84), 0.5), bowl(self, H - 0.7, T, 0.15, rgb(90, 44, 32)), bowl(self, H - 0.2, T, 0.85, rgb(84, 92, 44))]
        self.course2 = [dish(self, H + 0.9, T, 0.5, rgb(160, 84, 50), 0.62, steam=True), dish(self, H + 1.9, T, 0.45, rgb(240, 230, 196), 0.5, steam=True)]
        self.goblets = [goblet(self, H + gx, T, gz) for gx, gz in ((-2.2, 1.05), (0.0, 1.05), (2.2, 1.05), (-2.2, -0.05), (0.0, -0.05), (2.2, -0.05))]
        jug(self, H - 1.0, T, 0.5)
        jug(self, H + 1.0, T, 0.9)
        for grp in self.course1 + self.course2 + self.goblets:
            if grp is not None:
                grp.enabled = False
        for d in self.course2:
            if d.steam:
                d.steam.enabled = False
                d.steam.clear()

        def seat(x, z, face_z, name, **look):
            ch = self.add_char((H + x, z), **look)
            ch.set_pose('sit')
            ch.face(0, face_z)
            return ch
        self.harith = seat(0.0, 2.4, -1, 'harith', robe=rgb(84, 50, 110), trim=rgb(232, 200, 80), head='turban', head_color=rgb(70, 40, 92), beard=rgb(150, 150, 150), skin='dark')
        self.qais = seat(-2.2, 2.4, -1, 'qais', robe=rgb(150, 66, 44), trim=rgb(226, 190, 80), head='shemagh', head_color=rgb(160, 52, 40), beard=rgb(30, 24, 22), skin='olive', build='broad')
        self.jabir = seat(2.2, 2.4, -1, 'jabir', robe=rgb(186, 182, 166), trim=rgb(140, 96, 60), head='turban', head_color=rgb(236, 232, 220), beard=rgb(236, 236, 236), skin='tan', scale=0.97)
        self.assassin1 = seat(-2.2, -1.5, 1, 'a1', robe=rgb(34, 34, 44), trim=rgb(110, 30, 34), head='hood', head_color=rgb(24, 24, 32), skin='light')
        self.assassin2 = seat(2.2, -1.5, 1, 'a2', robe=rgb(40, 38, 46), trim=rgb(110, 30, 34), head='hood', head_color=rgb(28, 26, 34), skin='olive', build='broad')
        self.diners = [self.harith, self.qais, self.jabir, self.assassin1, self.assassin2]

    def start(self):
        g = self.game
        self.cam.pitch, self.cam.distance = (35, 13.0)
        self.tl.run(self.opening())

    def opening(self):
        g = self.game
        self.begin_cutscene()
        self.shot((-6, 4.5, -11), (-17, 1.5, 3), speed=99)
        self.cam.snap()
        yield 0.5
        d = g.hud.title_card('SCENE 1', 'The Secret Meal', 'Obada Alahmar  ·  TP083450', hold=2.4)
        yield 1.2
        self.shot((-14, 3.0, -8), (-17, 1.3, 1), speed=0.5)
        yield (d - 0.8)
        self.end_cutscene()
        g.hud.objective('Draw water from the well, and gather firewood (0/3)')
        g.hud.hint('WASD  move       Shift  run       E  interact       Space  action       Esc  pause', hold=9)
    WOOD_SPOTS = ((-24.5, 1.6), (-12.0, -5.6), (1.2, 9.6))

    def _build_firewood(self):
        for i, (x, z) in enumerate(self.WOOD_SPOTS):
            grp = Entity(parent=self.root, position=(x, 0, z), rotation_y=i * 57, add_to_scene_entities=False)
            bark = rgb(196, 140, 86)
            for k, (ox, oz, ry, ln) in enumerate(((0.0, 0.0, 0, 1.5), (0.0, 0.32, 6, 1.4), (0.0, -0.32, -5, 1.45), (0.0, 0.0, 3, 1.3))):
                lift = 0.15 if k < 3 else 0.42
                mk(grp, 'cylinder', (-ln / 2 + ox, lift, oz), (0.27, ln, 0.27), shade(bark, 0.9 + 0.08 * k), rot=(0, ry, 90), emissive=0.22)
            mk(grp, 'cylinder', (0.35, 0.25, 0.0), (0.66, 0.09, 0.66), rgb(222, 196, 128), rot=(0, 0, 90))
            gem = Entity(parent=grp, position=(0, 1.5, 0), add_to_scene_entities=False)
            mk(gem, 'cube', (0, 0, 0), (0.24, 0.24, 0.24), rgb(255, 214, 110), emissive=1.0, rot=(45, 0, 45))
            glow_quad(gem, (0, 0, 0), 0.9, (1.0, 0.8, 0.35, 0.55), tex('glow'))
            contact_shadow(self, x, z, 1.8, 1.4, 0.3)
            it = self.interact(x, z, 'Gather firewood', lambda n=i: self.tl.run(self._wood_seq(n)), radius=2.0)
            self.wood_items.append(dict(grp=grp, gem=gem, it=it, taken=False))

        def spin(dt):
            for w in self.wood_items:
                if not w['taken']:
                    w['gem'].rotation_y += 120.0 * dt
                    w['gem'].y = 1.5 + math.sin(Clock.now * 2.6 + w['grp'].x) * 0.07
        self.updaters.append(spin)

    def _wood_seq(self, n):
        g = self.game
        a = self.abdo
        w = self.wood_items[n]
        if w['taken']:
            return
        w['taken'] = True
        self.player.locked = True
        self.turn_to(a, w['grp'].x, w['grp'].z)
        a.arm_r_goal = a.arm_l_goal = -55
        yield 0.35
        g.audio.play('pickup', 0.7)
        self.fx.dust_puff((w['grp'].x, 0.3, w['grp'].z), 5, color=(0.8, 0.7, 0.55))
        w['grp'].enabled = False
        yield 0.25
        a.arm_r_goal = a.arm_l_goal = None
        self.wood += 1
        if not hasattr(self, 'wood_pack'):
            self.wood_pack = Entity(parent=a.body, position=(0.0, 1.2, -0.34), add_to_scene_entities=False)
        for k in range(3):
            mk(self.wood_pack, 'cylinder', (-0.35, 0.0 + 0.1 * k + 0.06 * self.wood, 0.02 * k - 0.04), (0.14, 0.7, 0.14), rgb(170, 120, 74), rot=(0, 0, 90))
        self.player.locked = False
        left = len(self.wood_items) - self.wood
        if left > 0:
            g.hud.hint(f'Firewood  {self.wood}/{len(self.wood_items)}', hold=3)
        else:
            g.hud.hint('Firewood  3/3  -  that should keep the fire alive till morning.', hold=4)
        self._refresh_objective()

    def _refresh_objective(self):
        g = self.game
        if self.family_done:
            return
        need_w = not self.has_water
        need_f = self.wood < len(self.wood_items)
        if need_w and need_f:
            g.hud.objective(f'Draw water from the well, and gather firewood ({self.wood}/{len(self.wood_items)})')
        elif need_w:
            g.hud.objective('Draw water from the well')
        elif need_f:
            g.hud.objective(f'Gather firewood for the fire  ({self.wood}/{len(self.wood_items)})')
        else:
            g.hud.objective('Bring the water and firewood to your family by the fire')

    def on_well(self):
        self.tl.run(self._well_seq())

    def _well_seq(self):
        g = self.game
        a = self.abdo
        self.player.locked = True
        self.turn_to(a, -5, -3)
        a.arm_r_goal = -70
        a.arm_l_goal = -70
        yield 0.5
        g.audio.play('splash', 0.7)
        for _ in range(3):
            self.fx.dust_puff((-5, 1.0, -3), 4, color=(0.7, 0.85, 1.0))
            self.fx.sparks((-5, 1.0, -3), 8, color0=(0.7, 0.9, 1.0, 1.0), color1=(0.3, 0.6, 1.0, 0.0))
            yield 0.25
        a.arm_r_goal = a.arm_l_goal = None
        self.jar = jug(self, 0, 0, 0)
        self.jar.parent = a.body
        self.jar.position = (0.52, 1.02, 0.12)
        self.jar.rotation_z = -6
        self.player.locked = False
        self.has_water = True
        self._refresh_objective()

    def on_family_area(self):
        if self.family_done:
            return
        ready = self.has_water and self.wood >= len(self.wood_items)
        if ready:
            self.family_done = True
            self.tl.run(self.family_seq())
        elif not self.has_water and self.wood >= len(self.wood_items):
            self.game.hud.hint('The water jar is still at the well.', hold=3)
        elif self.has_water:
            self.game.hud.hint(f'The fire is dying. Gather firewood first  ({self.wood}/{len(self.wood_items)}).', hold=3)
        else:
            self.game.hud.hint('Your family needs water and firewood.', hold=3)

    def family_seq(self):
        g = self.game
        a = self.abdo
        self.begin_cutscene()
        yield from self.walk(a, -8.0, 0.9, speed=2.6)
        self.turn_to(a, -9, 3.6)
        self.shot((-14.5, 3.4, -3.4), (-9, 1.0, 3.8), speed=1.2)
        if hasattr(self, 'jar'):
            destroy(self.jar)
        if hasattr(self, 'wood_pack'):
            destroy(self.wood_pack)
            for k in range(5):
                mk(self.root, 'cylinder', (-8.4 + 0.18 * k, 0.12 + 0.07 * (k % 2), 4.5 + 0.12 * k), (0.2, 0.9, 0.2), rgb(150, 104, 64), rot=(0, 20 * k, 90))
        self.turn_to(self.wife, -8, 0.9)
        self.wife.head_turn = 0
        lines = [('Wife', 'Abdo, there you are. Sit - the fire is warm and the bread is still soft.'), ('Mother', 'He works like a man with a debt to pay. Let him breathe, child.'), ('Father', 'The elders have met every night this week, my son. Something is coming.'), ('Abdo', 'Elders always meet, Father. We are farmers. Nothing comes for farmers.')]
        who = {'Wife': self.wife, 'Mother': self.mother, 'Father': self.father, 'Abdo': self.abdo}

        def on_line(i, line):
            for n, c in who.items():
                c.talking = n == line[0]
        yield from self.say(lines, on_line=on_line)
        for c in who.values():
            c.talking = False
        yield 0.6
        g.audio.play('caw', 0.8)
        self.shot((-20, 3.0, 0), (-12, 7, 4), speed=1.5)
        yield 0.6
        yield from self.crow_delivery()
        g.hud.objective('Pick up the scroll the crow dropped')
        self.end_cutscene()
        self.scroll_it = self.interact(self.scroll_pos[0], self.scroll_pos[2], 'Pick up the scroll', self.on_scroll, radius=2.4)

    def crow_delivery(self):
        g = self.game
        b = CrowBird(self.root, scale=0.65)
        self.birds.append(b)
        P0, P1, P2, P3 = (Vec3(-38, 13, 10), Vec3(-24, 9, -2), Vec3(-12, 5.5, 0.5), Vec3(-5.8, 1.5, 5.6))
        dur = 4.6
        t = 0.0
        prev = P0
        self.scroll_pos = (-6.0, 0.35, 5.6)
        while t < dur:
            t += self.dt
            k = min(1.0, t / dur)
            k = k * k * (3 - 2 * k) * 0.35 + k * 0.65
            m = 1.0 - k
            pos = P0 * (m * m * m) + P1 * (3 * m * m * k) + P2 * (3 * m * k * k) + P3 * (k * k * k)
            d = pos - prev
            prev = pos
            b.root.position = pos
            if d.length() > 0.0001:
                b.root.rotation_y = math.degrees(math.atan2(d.x, d.z))
                b.root.rotation_x = -math.degrees(math.atan2(d.y, math.hypot(d.x, d.z)))
            b.update(Clock.now)
            self.shot((-1.5, 2.3, -4.0), (pos.x, pos.y + 0.2, pos.z), speed=3.0)
            yield
        g.audio.play('caw', 0.9)
        self.scroll_prop = None
        self.scroll_model_drop()
        self.shot((-11, 2.8, 1.5), (-6, 0.6, 5.5), speed=2.0)
        yield 1.1
        t = 0.0
        pos0 = Vec3(b.root.x, b.root.y, b.root.z)
        prev = pos0
        while t < 3.0:
            t += self.dt
            k = t / 3.0
            pos = pos0 + Vec3(26 * k, 22 * k * k + 3 * k, -5 * k)
            d = pos - prev
            prev = pos
            b.root.position = pos
            if d.length() > 0.0001:
                b.root.rotation_y = math.degrees(math.atan2(d.x, d.z))
                b.root.rotation_x = -math.degrees(math.atan2(d.y, math.hypot(d.x, d.z)))
            b.update(Clock.now)
            yield
        b.root.enabled = False

    def scroll_model_drop(self):
        from engine.props import scroll_item
        x, y, z = self.scroll_pos
        self.scroll_prop = scroll_item(self, x, 2.6, z)
        self.tl.to(self.scroll_prop, 'base_y', y + 0.15, 0.7, ease_out)
        self.tl.after(0.75, lambda: (self.fx.dust_puff((x, 0.2, z), 6), self.fx.sparks((x, 0.3, z), 12, color0=(1.0, 0.9, 0.5, 1.0))))

    def on_scroll(self):
        self.tl.run(self.scroll_seq())

    def scroll_seq(self):
        g = self.game
        a = self.abdo
        self.begin_cutscene(letterbox=False)
        yield from self.walk(a, -6.8, 4.6, speed=2.6)
        self.turn_to(a, -6, 5.6)
        g.audio.play('pickup', 0.8)
        if self.scroll_prop:
            self.scroll_prop.enabled = False
            self.rig.remove(self.light_scroll)
        self.scroll_taken = True
        g.audio.stop('amb_wind', 2)
        yield 0.3
        yield from self.show_scroll()
        lines = [('Wife', 'Who is it from? You have gone pale, Abdo.'), ('Abdo', 'The elders. A small matter about the harvest. I will be back before dawn.'), ('Wife', 'You never could lie to me... Come back to us.'), ('Mother', 'Take the bread with you. A man should never walk in the dark on an empty stomach.')]
        who = {'Wife': self.wife, 'Mother': self.mother, 'Abdo': self.abdo}

        def on_line(i, line):
            for n, c in who.items():
                c.talking = n == line[0]
        self.shot((-14.5, 3.4, -3.4), (-9, 1.0, 3.8), speed=1.6)
        yield from self.say(lines, on_line=on_line)
        for c in who.values():
            c.talking = False
        self.end_cutscene()
        g.audio.loop('amb_wind', 0.25, fade=2)
        g.hud.objective("Follow the torch-lit road to Sheikh Harith's tent")
        self.begin_night()
        self.hall_door_it = self.interact(54.0, 1.1, 'Enter the tent', self.enter_hall, radius=2.8)
        self.trigger(10, 1.5, 3, 6, lambda: g.hud.hint('The torches will light your way.', hold=4))

    def show_scroll(self):
        g = self.game
        ui = camera.ui
        self.scroll_open = True
        self.scroll_ready = False
        parts = []
        glow = Entity(parent=ui, model='quad', texture=tex('glow'), color=color.rgba(1, 0.7, 0.3, 0.0), scale=(1.5, 1.1), z=-0.35, add_to_scene_entities=False)
        edge = Entity(parent=ui, model='quad', color=color.rgba(0.35, 0.2, 0.1, 0.0), scale=(0.93, 0.64), z=-0.4, add_to_scene_entities=False)
        paper = Entity(parent=ui, model='quad', color=color.rgba(0.86, 0.76, 0.56, 0.0), scale=(0.9, 0.61), z=-0.42, add_to_scene_entities=False)
        head = Text(text='-  FROM THE THUNDER TRIBE  -', parent=ui, position=(0, 0.2), origin=(0, 0), scale=1.15, font=FONT_BOLD, color=color.rgba(0.4, 0.15, 0.1, 0.0), z=-0.45, add_to_scene_entities=False)
        body = Text(text='', parent=ui, position=(0, 0.04), origin=(0, 0), scale=1.7, font='VeraMono.ttf', color=color.rgba(0.2, 0.1, 0.06, 0.0), z=-0.45, add_to_scene_entities=False)
        foot = Text(text='', parent=ui, position=(0, -0.22), origin=(0, 0), scale=1.0, font=FONT, color=color.rgba(0.4, 0.15, 0.1, 0.0), z=-0.45, add_to_scene_entities=False)
        parts = [glow, edge, paper, head, body, foot]
        lines_plain = textwrap.wrap(SCROLL_TEXT, 24)
        plain = '\n'.join(lines_plain)
        cipher = caesar(plain)
        n = len(plain)
        t = 0.0
        while t < 0.7:
            t += self.dt
            k = min(1.0, t / 0.7)
            paper.color = color.rgba(0.86, 0.76, 0.56, k)
            edge.color = color.rgba(0.35, 0.2, 0.1, k)
            head.color = color.rgba(0.4, 0.15, 0.1, k)
            body.color = color.rgba(0.2, 0.1, 0.06, k)
            glow.color = color.rgba(1, 0.7, 0.3, 0.35 * k)
            body.text = cipher
            yield
        yield 0.5
        from ursina import held_keys
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        gold = color.rgba(0.62, 0.32, 0.1, 1)
        dim = color.rgba(0.4, 0.2, 0.1, 0.75)
        x0, step = (-0.325, 0.026)
        strip = []
        for i, L in enumerate(letters):
            strip.append(Text(text=L, parent=ui, position=(x0 + i * step, -0.135), origin=(0, 0), scale=0.85, font='VeraMono.ttf', color=dim, z=-0.45, add_to_scene_entities=False))
        marker = Entity(parent=ui, model='quad', color=color.rgba(0.85, 0.45, 0.1, 0.95), scale=(0.022, 0.003), position=(x0, -0.158), z=-0.46, add_to_scene_entities=False)
        wheel = Text(text='', parent=ui, position=(0, -0.185), origin=(0, 0), scale=0.95, font='VeraMono.ttf', color=gold, z=-0.45, add_to_scene_entities=False)
        parts += strip + [marker, wheel]
        foot.text = '[A] / [D]  turn the cipher wheel'
        foot.y = -0.235
        foot.color = color.rgba(0.4, 0.15, 0.1, 1)
        shift = 0
        right_for = 0.0
        idle = 0.0
        nxt = {}
        key_dirs = (('a', -1), ('left arrow', -1), ('d', 1), ('right arrow', 1))
        was = {k: 0 for k, _ in key_dirs}
        pulse = 0.0
        t_dial = 0.0
        self.scroll_shift = 0
        while right_for < 0.4:
            t_dial += self.dt
            moved = 0
            for k, d in key_dirs:
                h = held_keys[k]
                if h and (not was[k]):
                    moved += d
                    nxt[k] = 0.35
                elif h:
                    nxt[k] -= self.dt
                    if nxt[k] <= 0:
                        moved += d
                        nxt[k] = 0.07
                was[k] = h
            if moved:
                idle = 0.0
            else:
                idle += self.dt
            if idle > 32.0 and shift != 3:
                if int(idle * 4) != int((idle - self.dt) * 4):
                    moved = 1 if (3 - shift) % 26 <= 13 else -1
            if getattr(self, 'scroll_shift_set', None) is not None:
                shift = self.scroll_shift_set
                self.scroll_shift_set = None
                moved = 0
            if moved:
                shift = (shift + (1 if moved > 0 else -1)) % 26
                g.audio.play('decode_tick', 0.3, variation=0.15)
            self.scroll_shift = shift
            body.text = caesar(cipher, -shift)
            for i, tx in enumerate(strip):
                tx.color = gold if i == shift else dim
            marker.x = x0 + shift * step
            wheel.text = f'WHEEL  {shift:02d}'
            if t_dial > 14.0 and shift != 3:
                foot.text = "The crow's seal bears three feathers."
            pulse += self.dt
            glow.color = color.rgba(1, 0.7, 0.3, 0.3 + 0.06 * math.sin(pulse * 5))
            right_for = right_for + self.dt if shift == 3 else 0.0
            yield
        for tx in strip:
            tx.color = dim
        wheel.text = 'WHEEL  03   -   LOCKED'
        foot.y = -0.22
        for _ in range(3):
            self.fx.sparks((self.abdo.x, 1.0, self.abdo.z + 0.3), 10)
        g.audio.play('decode_tick', 0.5)
        yield 0.5
        body.text = plain
        wheel.text = ''
        g.audio.play('stinger_soft', 0.6)
        foot.text = '[E]  burn the message'
        foot.color = color.rgba(0.4, 0.15, 0.1, 1)
        self.scroll_ready = True
        yield (lambda: not self.scroll_ready)
        for e in strip + [marker, wheel]:
            e.enabled = False
        g.audio.play('paper_burn', 0.7)
        self.fx.embers((self.abdo.x, 1.0, self.abdo.z), scale=1.5, rate=0).burst(20)
        self.fx.sparks((self.abdo.x, 1.0, self.abdo.z + 0.3), 18)
        foot.text = ''
        t = 0.0
        while t < 1.3:
            t += self.dt
            k = t / 1.3
            burn = 1.0 - k
            paper.color = color.rgba(0.86 * burn + 0.15, 0.76 * burn * (1 - 0.5 * k) + 0.05, 0.56 * burn, burn)
            edge.color = color.rgba(1.0, 0.45, 0.1, burn * (0.6 + 0.4 * math.sin(Clock.now * 40)))
            glow.color = color.rgba(1.0, 0.5, 0.15, burn * 0.7)
            head.color = color.rgba(0.4, 0.15, 0.1, burn)
            body.color = color.rgba(0.2, 0.1, 0.06, burn)
            paper.scale = (0.9 * (1 - 0.1 * k), 0.61 * (1 - 0.35 * k))
            yield
        for p in parts:
            destroy(p)
        self.scroll_open = False

    def begin_night(self):
        self.tl.to(self, 'tod', 1.0, 55.0, lambda t: t)
        self.sky.fade_to(self, 'sky_night', duration=40.0)
        self.tl.after(18.0, self._stars_on)
        self.game.audio.music('mus_night', 0.5, fade=6.0)

    def _stars_on(self):
        self.sky.stars.enabled = True
        self.fireflies.enabled = True
        self.fireflies.prewarm(5.0)

    def update_time_of_day(self):
        k = self.tod
        if self.in_hall:
            return
        rig = self.rig
        rig.ambient = _mix(DUSK['ambient'], NIGHT['ambient'], k)
        rig.sun_color = _mix(DUSK['sun'], NIGHT['sun'], k)
        rig.sun_dir = _mix(DUSK['sun_dir'], NIGHT['sun_dir'], k)
        rig.fog_color = _mix(DUSK['fog'], NIGHT['fog'], k)
        post = self.game.post
        post.values['tint'] = tuple((_mix(DUSK['tint'][i], NIGHT['tint'][i], k) for i in range(3)))
        self.sun.alpha = max(0.0, 1.0 - k * 1.6)
        self.sun.halo.alpha = max(0.0, 0.55 * (1.0 - k * 1.4))
        self.sun.y = 14 - 40 * k
        self.sun.halo.y = self.sun.y
        self.moon.alpha = min(1.0, max(0.0, (k - 0.25) * 2.0))
        for q, base in self.planet_sprites:
            q.alpha = base * min(1.0, max(0.0, (k - 0.45) * 2.5))

    def on_update(self, dt):
        self.update_time_of_day()
        if not self.in_hall and self.player:
            px = self.player.x
            for t in self.torches:
                if not t['lit'] and abs(px - t['x']) < 8.5 and self.scroll_taken:
                    self._ignite(t)
        for b in self.birds:
            pass

    def on_key(self, key):
        if key == 'e' and self.scroll_open:
            if self.scroll_ready:
                self.scroll_ready = False
            return
        super().on_key(key)

    def enter_hall(self):
        self.tl.run(self.enter_hall_seq())

    def enter_hall_seq(self):
        g = self.game
        self.begin_cutscene()
        yield from self.walk(self.abdo, 54.0, 3.4, speed=2.6)
        lines = [('Sentry', 'Sheikh Harith is waiting. You were not followed?'), ('Abdo', 'A farmer walking home at night. Who would follow?'), ('Sentry', 'Then go in, and keep your voice low.')]
        who = {'Sentry': self.sentry1, 'Abdo': self.abdo}
        self.shot((51, 2.2, -2.4), (54, 1.5, 3.5), speed=1.6)

        def on_line(i, line):
            for n, c in who.items():
                c.talking = n == line[0]
        yield from self.say(lines, on_line=on_line)
        for c in who.values():
            c.talking = False
        g.hud.objective(None)
        self.tent_flap.open(0.9)
        yield 0.9
        yield from self.walk(self.abdo, 54.0, 6.0, speed=2.4)
        g.hud.fade_to(1.0, 1.0)
        g.audio.stop_all(fade=1.5)
        yield 1.2
        self.in_hall = True
        self.hall_setup()
        g.hud.fade_to(0.0, 1.2)
        yield from self.meal()

    def hall_setup(self):
        g = self.game
        H = HX
        rig = self.rig
        rig.ambient = Vec3(0.2, 0.145, 0.15)
        rig.sun_color = Vec3(0, 0, 0)
        rig.fog_color = Vec3(0.035, 0.022, 0.03)
        rig.fog_density = 0.012
        g.post.set(vignette=0.5, bloom=0.95, desat=0.0, grain=0.04, tint=(1.06, 0.96, 0.88))
        self.sky.entity.enabled = False
        self.sky.stars.enabled = False
        self.moon.enabled = False
        self.sun.enabled = False
        for q, _ in self.planet_sprites:
            q.enabled = False
        self.fireflies.enabled = False
        self.fireflies.clear()
        a = self.abdo
        a.root.position = (H, 0, -4.3)
        a.root.rotation_y = 0
        a.angle = 0
        a.amount = 0
        self.cam.pitch, self.cam.distance = (38, 11)
        self.shot((H, 9.5, -12.5), (H, 0.8, 0.8), speed=99)
        self.cam.snap()
        g.audio.music('mus_meal', 0.5, fade=2.0)
        g.audio.loop('amb_hall', 0.35, fade=2.0)

    def gaze(self, speaker):
        for c in self.diners + [self.abdo]:
            if c is speaker:
                c.head_turn = 0
                continue
            dx, dz = (speaker.x - c.x, speaker.z - c.z)
            want = math.degrees(math.atan2(dx, dz))
            c.head_turn = (want - c.angle + 180) % 360 - 180

    def speak_lines(self, lines):
        who = {'Sheikh Harith': self.harith, 'Qais': self.qais, 'Elder Jabir': self.jabir, 'Abdo': self.abdo}

        def on_line(i, line):
            sp = who.get(line[0])
            for n, c in who.items():
                c.talking = c is sp
            if sp:
                self.gaze(sp)
            if self._on_line_extra:
                self._on_line_extra(line)
        yield from self.say(lines, on_line=on_line)
        for c in who.values():
            c.talking = False
    _on_line_extra = None

    def need_e(self, label):
        done = {'v': False}
        self.interact(HX, 0.5, label, lambda: done.update(v=True), radius=99, once=True)
        self.cutscene_active = False
        self.player.locked = True
        self.allow_prompts = True
        yield (lambda: done['v'])
        self.allow_prompts = False
        self.cutscene_active = True

    def serve(self, group_list, name):
        g = self.game
        for i, grp in enumerate(group_list):
            grp.enabled = True
            grp.scale = 0.01
            self.tl.to(grp, 'scale', Vec3(1, 1, 1), 0.5, ease_out, delay=i * 0.18)
        for grp in group_list:
            if getattr(grp, 'steam', None):
                grp.steam.enabled = True
                grp.steam.prewarm(1.2)
        g.audio.play('clink_soft', 0.5)
        self.ring_fx((HX, 0.5), (1.0, 0.8, 0.5), 5.0, 0.9, y=self.table_top + 0.02)

    def eat(self, group_list, bite=0.55):
        g = self.game
        a = self.abdo
        a.arm_r_goal = -118
        g.audio.play('eat', 0.5, variation=0.1)
        for grp in group_list:
            self.tl.to(grp, 'scale', grp.scale * bite, 0.6)
        self.fx.sparks((HX, self.table_top + 0.2, 0.5), 6, color0=(1.0, 0.9, 0.6, 1.0), color1=(1.0, 0.6, 0.2, 0.0))

    def meal(self):
        g = self.game
        H = HX
        a = self.abdo
        a.root.position = (H, 0, -4.3)
        self.begin_cutscene()
        g.hud.title_card('', 'Three courses. One decision.', '', hold=1.4, fade=0.8)
        yield 1.4
        self.shot((H - 4.5, 3.2, -8.0), (H, 1.0, -1.4), speed=0.8)
        yield from self.walk(a, H, -1.45, speed=2.0)
        a.root.rotation_y = 0
        a.face(0, 1)
        a.set_pose('sit')
        yield 0.8
        self.gaze(self.harith)
        self.shot((H - 2.0, 2.3, -4.6), (H, 1.35, 2.2), speed=1.1)
        yield from self.speak_lines([('Sheikh Harith', 'Sit, Abdo bin Suhail. A man who walks in the dark should not meet his fate on an empty stomach.'), ('Abdo', 'Sheikh Harith. Your message said to come alone and tell no one. I obeyed.'), ('Sheikh Harith', 'And that is why you are at this table, and not some other man.')])
        g.hud.caption('FIRST COURSE   •   Bread, dates and olives', hold=2.0, size=1.7, tone=(0.93, 0.76, 0.34))
        self.serve(self.course1, 'course1')
        self.shot((H, 7.5, -7.5), (H, 0.7, 0.4), speed=1.0)
        yield 1.4
        self.shot((H - 0.5, 2.8, -2.8), (H - 0.5, 0.7, 0.5), speed=1.4)
        yield from self.need_e('Take some bread')
        self.eat(self.course1[:1], 0.6)
        yield 1.2
        a.arm_r_goal = None
        self.shot((H + 1.5, 2.6, -3.8), (H - 0.5, 1.3, 2.3), speed=1.0)
        yield from self.speak_lines([('Qais', 'Once, Khaled bin Qusey sat where you sit. We made him king. We fed his armies.'), ('Elder Jabir', "Now a prisoner's daughter is his queen, and her father whispers in his ear."), ('Qais', "Tariq bin Saleh tells him that Thunder is the knife at the Iron Tribe's throat."), ('Sheikh Harith', 'He is not wrong to fear us. He is wrong to hate us.')])
        g.post.tween(1.5, vignette=0.58, bloom=1.0)
        self.tl.to(self.rig, 'ambient', Vec3(0.15, 0.11, 0.13), 2.5)
        g.hud.caption('SECOND COURSE   •   Roast lamb and rice', hold=2.0, size=1.7, tone=(0.93, 0.76, 0.34))
        self.serve(self.course2, 'course2')
        self.shot((H + 1.4, 1.9, -2.2), (H + 1.4, 0.8, 0.6), speed=1.2)
        yield 1.6
        yield from self.need_e('Eat the lamb')
        self.eat(self.course2, 0.6)
        yield 1.2
        a.arm_r_goal = None
        self.shot((H - 2.5, 2.4, -4.0), (H + 0.5, 1.3, 2.0), speed=1.0)
        yield from self.speak_lines([('Abdo', 'You did not bring me here for bread and lamb, Sheikh. Say what you want.'), ('Sheikh Harith', "One night. One blade. Before Khaled's hatred becomes a war. This Friday."), ('Elder Jabir', 'The palace guard changes at midnight. You served in his army, Abdo. You know its corridors.'), ('Sheikh Harith', 'These two go with you. Other hands will deal with Tariq bin Saleh.')])
        self.gaze(self.assassin1)
        self.shot((H + 3.5, 1.7, -3.2), (H - 1.0, 1.2, -1.4), speed=1.2)
        self.assassin1.arm_r_goal = -10
        yield 1.7
        self.assassin1.arm_r_goal = None
        yield from self.speak_lines([('Abdo', 'I bled for Khaled once. I carried his banner into the sand.'), ('Qais', 'And he repaid every one of us with suspicion. Eat, Abdo. Courage needs fuel.')])
        g.hud.caption('THIRD COURSE   •   The cup', hold=2.0, size=1.7, tone=(0.93, 0.76, 0.34))
        self.serve(self.goblets, 'goblets')
        self.shot((H, 1.6, -2.0), (H, 0.85, 0.5), speed=1.4)
        yield 1.5
        yield from self.need_e('Raise your cup')
        a.arm_r_goal = -118
        yield 1.0
        a.arm_r_goal = None
        self.shot((H, 2.0, -3.4), (H, 1.4, 2.4), speed=1.0)
        self._on_line_extra = self._line_hook
        yield from self.speak_lines([('Sheikh Harith', 'Fill the cups. Every man here will drink to what must be done.'), ('Sheikh Harith', 'Khaled bin Qusey dies on Friday night. That is the order of the Thunder Tribe.')])
        self._on_line_extra = None
        yield 0.8
        picked = {'v': None}
        self.shot((H + 3.1, 1.7, -1.6), (H, 1.35, -1.45), speed=1.3)
        g.dialogue.ask('Sheikh Harith', 'Will you carry it out, Abdo?', ['I will do it.', 'He was my commander... is there no other way?'], on_pick=lambda i: picked.update(v=i))
        yield (lambda: picked['v'] is not None)
        if picked['v'] == 0:
            yield from self.speak_lines([('Abdo', 'I will do it.'), ('Sheikh Harith', 'Good. Then drink, and let the wine remember your promise.')])
        else:
            g.state['abdo_doubt'] = True
            yield from self.speak_lines([('Abdo', 'He was my commander... Is there no other way?'), ('Qais', 'There is. We wait, and Tariq has us killed one by one in our beds.'), ('Elder Jabir', 'Think of your wife, Abdo. Your mother. Your father. If Thunder falls, so do they.'), ('Abdo', '...Then I will do it.')])
        g.state['accepted_mission'] = True
        yield from self.toast()
        yield 0.5
        g.hud.fade_to(1.0, 1.4)
        yield 1.6
        g.audio.stop_all(fade=1.5)
        g.hud.caption('Friday night.', hold=2.2, size=2.6)
        yield 3.8
        g.next_scene()

    def _line_hook(self, line):
        if line[1].startswith('Khaled bin Qusey dies'):
            self.kill_order_fx()

    def kill_order_fx(self):
        g = self.game
        g.audio.play('stinger', 0.9)
        g.audio.loop('heartbeat', 0.7, fade=1.5)
        g.post.punch_aberration(0.014)
        g.post.flash((0.9, 0.08, 0.06), 0.35, 1.6)
        self.cam.shake(0.12, 0.7)
        self.shot((HX, 1.5, -1.2), (HX, 0.9, 0.4), speed=1.6)
        for gob in self.goblets:
            self.tl.value(lambda gb=gob: gb.glow, lambda v, gb=gob: gb.set_glow(v), 1.0, 2.2)
        self.tl.to(self.rig, 'ambient', Vec3(0.26, 0.045, 0.055), 2.5)
        self.tl.to(self.rig, 'fog_color', Vec3(0.12, 0.008, 0.015), 2.5)
        g.post.tween(2.5, vignette=0.78, desat=0.38, bloom=1.35, tint=(1.12, 0.7, 0.7))
        for L in self.candle_lights + [self.table_light]:
            self.tl.to(L, 'color', Vec3(1.0, 0.12, 0.08), 2.2)
        for em in self.candle_emitters:
            em.set_color((1.0, 0.25, 0.12, 0.95), (0.55, 0.0, 0.0, 0.0))
        self.goblet_light = self.rig.add((HX, 1.0, 0.5), color=(1.0, 0.1, 0.08), intensity=0.0, radius=5.5, flicker=0.2)
        self.tl.to(self.goblet_light, 'intensity', 1.5, 2.0)

    def toast(self):
        g = self.game
        H = HX
        g.hud.caption('', hold=0.1)
        self.shot((H, 2.6, -4.0), (H, 1.4, 0.5), speed=1.2)
        yield 0.6
        seats = [(self.qais, 0), (self.harith, 1), (self.jabir, 2), (self.assassin1, 3), (self.abdo, 4), (self.assassin2, 5)]
        for ch, i in seats:
            ch.arm_r_goal = -125
        mids = [(H - 0.55, 1.65, 0.5), (H - 0.2, 1.7, 0.6), (H + 0.2, 1.7, 0.6), (H + 0.55, 1.65, 0.5), (H - 0.2, 1.7, 0.4), (H + 0.2, 1.7, 0.4)]
        for gob, p in zip(self.goblets, mids):
            self.tl.to(gob, 'position', Vec3(*p), 1.3)
        yield 1.0
        self.shot((H, 1.8, -1.5), (H, 1.65, 0.5), speed=2.4)
        yield 0.35
        Clock.time_scale = 0.25
        g.audio.play('clink', 1.0)
        g.post.flash((1.0, 0.85, 0.7), 0.7, 2.0)
        g.post.punch_aberration(0.02)
        self.cam.shake(0.1, 0.5)
        self.ring_fx((H, 0.5), (1.0, 0.3, 0.2), 9.0, 1.2, y=1.65)
        self.fx.sparks((H, 1.7, 0.5), 30, color0=(1.0, 0.45, 0.3, 1.0), color1=(0.7, 0.0, 0.0, 0.0))
        self.flash_light((H, 1.9, 0.5), (1.0, 0.2, 0.15), 3.5, 9, 0.9)
        yield 0.5
        Clock.time_scale = 1.0
        yield 1.2
