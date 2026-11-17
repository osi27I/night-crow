import math
import random
from ursina import Text, Vec3, camera, color, destroy
from engine.assets import FONT, FONT_BOLD
from engine.entities import glow_quad, mk, rgb
from engine.props import CrowBird, Sky, ground, moon, planets, rock
from engine.assets import tex
from engine.scene_base import BaseScene
GOLD = (0.93, 0.76, 0.34, 1.0)
DIM = (0.62, 0.62, 0.68, 1.0)
SCENE_TITLES = [('1', 'The Secret Meal', 'Obada Alahmar'), ('2', 'The Fallen King', 'Rami Abdo Hezam'), ('3', 'The Last Survivor', 'Amro'), ('4', 'Night Crow I: The Fort', 'Yusra Abdelaseim Elsayed'), ('4b', 'Night Crow II: Rooftops', 'Group'), ('5', "The Prefect's Villa", 'Group')]

class MenuScene(BaseScene):
    number = 0
    name = 'Title'

    def build(self):
        g = self.game
        rig = self.rig
        rig.ambient = Vec3(0.1, 0.12, 0.21)
        rig.sun_dir = Vec3(0.2, 0.35, 1.0)
        rig.sun_color = Vec3(0.2, 0.26, 0.42)
        rig.fog_color = Vec3(0.04, 0.07, 0.14)
        rig.fog_density = 0.011
        rig.add((-3, 3.5, -2), color=(0.4, 0.52, 1.0), intensity=1.5, radius=15, flicker=0.0)
        rig.add((-3.2, 3.0, 7.5), color=(0.55, 0.65, 1.0), intensity=1.3, radius=11, flicker=0.0)
        self.sky = Sky(self, 'sky_night')
        moon(self, (26, 44, 150), size=44)
        planets(self, ringed=(-120, 50, 150), red=(120, 70, 150))
        mk(self.root, 'plane', (0, 0, 60), (260, 1, 220), rgb(70, 78, 98), tex('sand'), tex_scale=(46, 40))
        for i in range(10):
            rnd = random.Random(i)
            rock(self, rnd.uniform(-18, 18), rnd.uniform(-4, 8), s=rnd.uniform(0.8, 1.8), collide=False)
        mk(self.root, 'cylinder', (-9, 0, 4), (0.5, 5.5, 0.5), rgb(30, 26, 28), rot=(0, 0, -8))
        for ang, h, ln in ((40, 3.4, 2.4), (-30, 4.2, 2.0), (65, 5.0, 1.6)):
            mk(self.root, 'cylinder', (-9.4, h, 4), (0.22, ln, 0.22), rgb(30, 26, 28), rot=(0, 0, ang))
        rnd = random.Random(11)
        for i in range(40):
            x, z = (rnd.uniform(-70, 70), rnd.uniform(34, 100))
            w, h, d = (rnd.uniform(3, 6), rnd.uniform(2.5, 4.5), rnd.uniform(3, 6))
            mk(self.root, 'cube', (x, h / 2, z), (w, h, d), rgb(60, 56, 66), tex('mudbrick'))
            if rnd.random() < 0.5:
                mk(self.root, 'cube', (x, h * 0.55, z - d / 2 - 0.02), (0.7, 0.9, 0.05), rgb(255, 190, 90), emissive=1.0)
        for em in self.fx.fire((30, 0.2, 58), scale=3.0, intensity=1.5):
            em.cull = False
        self.rig.add((30, 4, 58), color=(1.0, 0.5, 0.2), intensity=2.2, radius=45, flicker=0.35)
        self.crow = self.add_char((-3.2, 3.0), robe=rgb(18, 18, 26), trim=rgb(120, 30, 34), head='hood', head_color=rgb(14, 14, 20), cloak=rgb(12, 12, 18), mask=True, weapon='dagger')
        self.crow.arm_r.rotation_x = 0
        self.birds = []
        for i in range(9):
            b = CrowBird(self.root, scale=2.6, col=rgb(6, 8, 14))
            self.birds.append((b, i))
        self.fx.embers((0, 0.4, 2), scale=1.6, rate=9, area=(14, 0, 9)).cull = False
        for x, z in ((-12, -2), (6, -3), (14, 4), (-3, 7), (0, -9)):
            self.fx.smoke((x, 0.2, z), scale=3.0, rate=2, tone=0.38, alpha=0.2, wind=(0.5, 0, 0.1)).cull = False
        self.fx.dust((0, 2, 0), area=(16, 3, 10), count=40, color=(0.6, 0.72, 1.0), alpha=0.35, size=0.1)
        self.mode = 'main'
        self.sel = 0
        self.ui = []
        ui = camera.ui
        from ursina import Entity
        self.title_glow = Entity(parent=ui, model='quad', texture=tex('glow'), position=(0, 0.2), scale=(1.5, 0.34), color=color.rgba(1, 0.7, 0.3, 0), z=-0.2, add_to_scene_entities=False)
        self.title = Text(text='THE NIGHT CROW', parent=ui, position=(0, 0.215), origin=(0, 0), scale=5.0, font=FONT_BOLD, color=color.rgba(0.97, 0.94, 0.88, 0), z=-0.3, add_to_scene_entities=False)
        self.subtitle = Text(text='A  TALE  OF  BETRAYAL,  BLOOD  AND  REVENGE', parent=ui, position=(0, 0.135), origin=(0, 0), scale=1.15, font=FONT, color=color.rgba(0.93, 0.76, 0.34, 0), z=-0.3, add_to_scene_entities=False)
        self.items = []
        for i in range(len(SCENE_TITLES) + 1):
            t = Text(text='', parent=ui, position=(0.42, -0.015 - i * 0.06), origin=(0, 0), scale=1.45, font=FONT_BOLD, color=color.rgba(*DIM[:3], 0), z=-0.3, add_to_scene_entities=False)
            self.items.append(t)
        self.footer = Text(text='W / S  or  ↑ ↓  choose        Enter  confirm        Esc  pause', parent=ui, position=(0, -0.46), origin=(0, 0), scale=0.85, font=FONT, color=color.rgba(0.7, 0.7, 0.75, 0), z=-0.3, add_to_scene_entities=False)
        self.credit = Text(text='CT029-3-2  Imaging and Special Effects', parent=ui, position=(-0.86, -0.46), origin=(-0.5, 0), scale=0.75, font=FONT, color=color.rgba(0.6, 0.6, 0.65, 0), z=-0.3, add_to_scene_entities=False)
        self.ui = [self.title_glow, self.title, self.subtitle, self.footer, self.credit] + self.items
        self.ui_alpha = 0.0
        self.picked = False
        self._refresh_items()
        g.post.set(vignette=0.55, bloom=0.8, grain=0.05, tint=(0.95, 1.0, 1.08))
        g.audio.music('mus_menu', 0.6, fade=2.5)
        g.audio.loop('amb_wind', 0.35, fade=3.0)

    def _options(self):
        if self.mode == 'main':
            return ['Begin the Story', 'Choose a Scene', 'Quit']
        return [f'Scene {n}   {t}' for n, t, _ in SCENE_TITLES]

    def _refresh_items(self):
        opts = self._options()
        if self.mode == 'select':
            opts = opts + ['Back']
        for i, t in enumerate(self.items):
            if i < len(opts):
                on = i == self.sel
                t.text = ('▶  ' if on else '     ') + opts[i]
                t.enabled = True
            else:
                t.text = ''
                t.enabled = False
        self.n_opts = len(opts)

    def start(self):
        self.tl.after(0.8, lambda: self.tl.to(self, 'ui_alpha', 1.0, 2.5))

    def on_key(self, key):
        if self.picked:
            return
        if key in ('w', 'up arrow'):
            self.sel = (self.sel - 1) % self.n_opts
            self.game.audio.play('ui_tick', 0.5)
            self._refresh_items()
        elif key in ('s', 'down arrow'):
            self.sel = (self.sel + 1) % self.n_opts
            self.game.audio.play('ui_tick', 0.5)
            self._refresh_items()
        elif key in ('enter', 'space', 'e'):
            self._choose()
        elif key in ('1', '2', '3', '4', '5', '6') and self.mode == 'select':
            self.sel = int(key) - 1
            self._choose()

    def _choose(self):
        g = self.game
        g.audio.play('ui_select', 0.7)
        if self.mode == 'main':
            if self.sel == 0:
                self._launch(1)
            elif self.sel == 1:
                self.mode, self.sel = ('select', 0)
                self._refresh_items()
            else:
                g.quit()
        elif self.sel >= len(SCENE_TITLES):
            self.mode, self.sel = ('main', 1)
            self._refresh_items()
        else:
            self._launch(self.sel + 1)

    def _launch(self, scene_index):
        self.picked = True
        g = self.game
        g.state.clear()
        g.audio.play('caw', 0.8)
        g.post.flash((0.8, 0.9, 1.0), 0.5, 1.5)
        g.post.punch_aberration(0.01)
        self.tl.to(self, 'ui_alpha', 0.0, 0.8)
        self.cam.shake(0.1, 0.5)
        self.tl.after(0.4, lambda: g.goto(scene_index, fade=1.4))

    def on_update(self, dt):
        t = self.t
        push = 3.0 if self.picked else 0.0
        self._push = getattr(self, '_push', 0.0) + (push - getattr(self, '_push', 0.0)) * min(1.0, dt * 1.5)
        cx = math.sin(t * 0.13) * 1.8
        cy = 1.9 + math.sin(t * 0.21) * 0.25
        self.cam.cine((cx - 1.5, cy - 0.45, -7.0 + self._push), (-1.0, 2.6, 12.0), speed=1.2)
        if self.crow.cloak:
            self.crow.cloak.rotation_x = -8 + math.sin(t * 1.3) * 5 + math.sin(t * 3.1) * 2
        for b, i in self.birds:
            a = t * (0.22 + i * 0.012) + i * 0.7
            r = 18 + i % 3 * 7
            x = 26 + math.cos(a) * r * 1.5
            y = 46 + math.sin(a) * r * 0.55 + i % 4 * 2
            z = 135 + math.sin(a * 0.7) * 6
            dx, dy = (-math.sin(a) * r * 1.5, math.cos(a) * r * 0.55)
            b.root.position = (x, y, z)
            b.root.rotation_y = 90 if dx > 0 else -90
            b.root.rotation_z = -dy * 0.4
            b.update(t)
        k = self.ui_alpha
        pulse = 0.5 + 0.5 * math.sin(t * 1.4)
        self.title.color = color.rgba(0.97, 0.94, 0.88, k)
        self.title_glow.color = color.rgba(1.0, 0.62, 0.25, k * (0.2 + 0.14 * pulse))
        self.subtitle.color = color.rgba(*GOLD[:3], k * 0.95)
        self.footer.color = color.rgba(0.7, 0.7, 0.75, k * 0.8)
        self.credit.color = color.rgba(0.6, 0.6, 0.65, k * 0.8)
        for i, it in enumerate(self.items):
            if it.enabled:
                on = i == self.sel
                c = GOLD if on else DIM
                it.color = color.rgba(c[0], c[1], c[2], k * (1.0 if on else 0.8))

    def destroy(self):
        for t in self.ui:
            destroy(t)
        super().destroy()
