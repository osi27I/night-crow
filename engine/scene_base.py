import math
from ursina import Entity, Vec3, destroy, camera
from ursina import scene as ursina_scene
from engine.assets import tex
from engine.camera_rig import CameraRig
from engine.characters import build_character
from engine.collision import World
from engine.entities import glow_quad
from engine.lighting import LightRig
from engine.particles import ParticleSystem
from engine.player import Player
from engine.timing import Clock, Timeline, ease_out

class Interactable:

    def __init__(self, x, z, radius, label, callback, once, key='E'):
        self.x, self.z, self.radius = (x, z, radius)
        self.label, self.callback, self.once, self.key = (label, callback, once, key)
        self.enabled = True

class Trigger:

    def __init__(self, x, z, w, d, callback, once):
        self.x, self.z, self.w, self.d = (x, z, w, d)
        self.callback, self.once = (callback, once)
        self.enabled = True
        self.inside = False

    def contains(self, px, pz):
        return abs(px - self.x) <= self.w / 2.0 and abs(pz - self.z) <= self.d / 2.0

class BaseScene:
    number = 0
    name = 'Scene'
    author = ''

    def __init__(self, game):
        self.game = game
        self.root = Entity(parent=ursina_scene, add_to_scene_entities=False)
        self.tl = Timeline()
        self.rig = LightRig()
        self.fx = ParticleSystem(self.root)
        self.world = World()
        self.cam = CameraRig()
        self.sky = None
        self.player = None
        self.actors = []
        self.updaters = []
        self.interactables = []
        self.triggers = []
        self.guards = []
        self.abil = None
        self.nav = None
        self.bounds = None
        self.stealth_light = False
        self.stealth_active = False
        self.failing = False
        self.allow_prompts = False
        self.dt = 0.016
        self.t = 0.0
        self.cutscene_active = False
        self._camera_target_override = None
        self.ready = False

    def build(self):
        raise NotImplementedError

    def start(self):
        pass

    def on_update(self, dt):
        pass

    def on_action(self):
        pass

    def on_spotted(self, guard):
        self.caught('You were spotted')

    def reset_section(self):
        pass

    def make_pivot(self, pos=(0, 0, 0)):
        return Entity(parent=self.root, position=pos, add_to_scene_entities=False)

    def add_char(self, pos, **look):
        ch = build_character(self.root, (pos[0], 0, pos[1]) if len(pos) == 2 else pos, **look)
        self.actors.append(ch)
        return ch

    def add_guard(self, guard):
        self.guards.append(guard)
        self.actors.append(guard)
        return guard

    def set_player(self, ch, speed=3.6, run_speed=6.2):
        self.player = Player(self, ch, speed=speed, run_speed=run_speed)
        return self.player

    def interact(self, x, z, label, callback, radius=1.9, once=True):
        it = Interactable(x, z, radius, label, callback, once)
        self.interactables.append(it)
        return it

    def trigger(self, x, z, w, d, callback, once=True):
        tr = Trigger(x, z, w, d, callback, once)
        self.triggers.append(tr)
        return tr

    def begin_cutscene(self, letterbox=True):
        self.cutscene_active = True
        if self.player:
            self.player.locked = True
        if letterbox:
            self.game.hud.letterbox(True)
        self.game.hud.prompt(None)

    def end_cutscene(self):
        self.cutscene_active = False
        if self.player:
            self.player.locked = False
        self.game.hud.letterbox(False)
        self.cam.release()

    def say(self, lines, on_line=None):
        done = {'v': False}
        self.game.dialogue.start(lines, on_done=lambda: done.update(v=True), on_line=on_line)
        while not done['v']:
            yield

    def walk(self, ch, x, z, speed=2.3, stop_dist=0.12, run=False):
        sp = speed * (1.7 if run else 1.0)
        while True:
            dx, dz = (x - ch.root.x, z - ch.root.z)
            d = math.hypot(dx, dz)
            if d <= stop_dist:
                break
            step = min(d, sp * max(self.dt, 0.001))
            ch.root.x += dx / d * step
            ch.root.z += dz / d * step
            ch.face(dx, dz, self.dt)
            ch.amount = 1.0 if run else 0.72
            yield
        ch.amount = 0.0

    def go(self, ch, x, z, **kw):
        return self.tl.run(self.walk(ch, x, z, **kw))

    def turn_to(self, ch, x, z):
        ch.face(x - ch.root.x, z - ch.root.z)

    def shot(self, position, look_at, speed=2.2):
        self.cam.cine(position, look_at, speed)

    def ring_fx(self, pos, color=(1.0, 0.7, 0.3), size=6.0, duration=0.9, y=0.08):
        e = glow_quad(self.root, (pos[0], y, pos[2] if len(pos) > 2 else pos[1]), 0.3, (*color, 0.9), tex('ring'), billboard=False, add=True, bin_sort=37)
        e.rotation_x = 90
        self.tl.to(e, 'scale', Vec3(size, size, 1), duration, ease_out)
        self.tl.to(e, 'alpha', 0.0, duration)
        self.tl.after(duration + 0.05, lambda: destroy(e))

    def flash_light(self, pos, color=(1.0, 0.85, 0.6), intensity=3.0, radius=14.0, duration=0.4):
        L = self.rig.add(pos, color=color, intensity=intensity, radius=radius, flicker=0.0)
        self.tl.to(L, 'scale', 0.0, duration)
        self.tl.after(duration + 0.05, lambda: self.rig.remove(L))
        return L

    def caught(self, reason='You were spotted'):
        if self.failing:
            return
        self.failing = True
        g = self.game
        g.audio.play('alert', 0.8)
        g.post.flash((1.0, 0.12, 0.06), 0.55)
        g.post.punch_aberration(0.02)
        self.cam.shake(0.25, 0.4)
        if self.player:
            self.player.locked = True
        Clock.time_scale = 0.3
        self.tl.run(self._fail_script(reason))

    def _fail_script(self, reason):
        g = self.game
        yield 0.35
        g.hud.fade_to(1.0, 0.5)
        yield 0.55
        Clock.time_scale = 1.0
        g.hud.caption(reason + '...', hold=0.9, fade=0.4)
        yield 0.2
        self.reset_section()
        self.failing = False
        for gd in self.guards:
            gd.awareness = 0.0
            gd.spotted_called = False
        yield 1.0
        g.hud.fade_to(0.0, 0.7)
        if self.player:
            self.player.locked = False

    def update(self, dt):
        self.dt = dt
        self.t += dt
        self.tl.update(dt)
        if self.player:
            self.player.update(dt)
        for a in self.actors:
            a.update(dt)
        for u in self.updaters:
            u(dt)
        self.on_update(dt)
        if self.abil is not None:
            self.abil.update(dt)
        self._interactions()
        focus = self.player.pos if self.player else Vec3(0, 0, 0)
        self.fx.update(dt, focus)
        if self._camera_target_override is not None:
            self.cam.target = self._camera_target_override
        elif self.player:
            self.cam.target = focus
        self.cam.update(dt)
        self.rig.focus = focus
        self.rig.update()
        if self.sky:
            self.sky.update(dt)
        if self.stealth_active and self.guards:
            peak = max((g.awareness for g in self.guards if g.alive), default=0.0)
            self.game.hud.detection(peak if peak > 0.02 else None)
        else:
            self.game.hud.detection(None)

    def _interactions(self):
        hud = self.game.hud
        blocked = self.player.locked and (not self.allow_prompts) if self.player else True
        if not self.player or blocked or self.cutscene_active or self.game.dialogue.active:
            hud.prompt(None)
            self._near = None
            return
        px, pz = (self.player.x, self.player.z)
        best, best_d = (None, 1000000000.0)
        for it in self.interactables:
            if not it.enabled:
                continue
            d = math.hypot(px - it.x, pz - it.z)
            if d <= it.radius and d < best_d:
                best, best_d = (it, d)
        self._near = best
        hud.prompt(f'[{best.key}]  {best.label}' if best else None)
        for tr in self.triggers:
            if not tr.enabled:
                continue
            inside = tr.contains(px, pz)
            if inside and (not tr.inside):
                tr.callback()
                if tr.once:
                    tr.enabled = False
            tr.inside = inside
    _near = None

    def on_key(self, key):
        if self.abil is not None and key in ('c', 'g', 'r'):
            self.abil.on_key(key)
            return
        if key == 'e' and self._near is not None and (not self.cutscene_active):
            it = self._near
            if it.once:
                it.enabled = False
            self.game.hud.prompt(None)
            it.callback()
        elif key == 'space' and (not self.cutscene_active) and self.player and (not self.player.locked) and (not self.failing):
            self.on_action()

    def destroy(self):
        self.tl.clear()
        self.rig.clear()
        self.game.audio.stop_all(fade=1.0)
        self.game.dialogue.close()
        Clock.time_scale = 1.0
        self.game.hud.prompt(None)
        if self.abil is not None:
            self.abil.destroy()
        destroy(self.root)
