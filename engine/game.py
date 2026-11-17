import os
import sys
import time
import traceback
from ursina import Entity, Text, Ursina, application, camera, color, window
from engine.assets import FONT, FONT_BOLD, FONT_DIR, ROOT
from engine.audio import Audio
from engine.dialogue import Dialogue
from engine.hud import HUD
from engine.particles import Emitter
from engine.postfx import PostFX
from engine.timing import Clock

class _Driver(Entity):

    def __init__(self, game):
        super().__init__()
        self._game = game

    def update(self):
        self._game.frame()

    def input(self, key):
        self._game.on_input(key)

class Game:

    def __init__(self, start_scene=0, safe=False, fullscreen=False, size=(1280, 720), mute=False, show_fps=False, fixed_dt=None):
        self.safe = safe
        self.app = Ursina(title='The Night Crow  -  CT029-3-2 Imaging and Special Effects', borderless=False, fullscreen=fullscreen, size=size, vsync=True, development_mode=False, editor_ui_enabled=False)
        application.development_mode = False
        application.asset_folder = ROOT
        application.fonts_folder = FONT_DIR
        window.color = color.black
        window.exit_button.visible = False
        window.fps_counter.enabled = False
        for name in ('cog_button', 'collider_counter', 'entity_counter'):
            obj = getattr(window, name, None)
            if obj is not None:
                obj.enabled = False
        from engine.entities import prewarm_models
        prewarm_models()
        camera.clip_plane_near = 0.3
        camera.clip_plane_far = 600
        if fixed_dt:
            Clock.fixed_dt = fixed_dt
        if safe:
            Emitter.quality = 0.55
        self.post = PostFX(enabled=not safe)
        self.hud = HUD()
        self.dialogue = Dialogue()
        self.audio = Audio(enabled=True)
        if mute:
            self.audio.muted = True
        self.dialogue.on_type = lambda: self.audio.play('type_blip', 0.18, variation=0.12)
        self.state = {}
        self.scene = None
        self.scene_index = -1
        self._pending = None
        self.transitioning = False
        self.paused = False
        self.frame_hooks = []
        self.frame_count = 0
        from scenes import LOAD_ERRORS, SCENES
        self.SCENES = SCENES
        self.LOAD_ERRORS = LOAD_ERRORS
        self._build_pause_panel()
        self._fps_text = Text(text='', parent=camera.ui, position=(0.86, 0.47), origin=(0.5, 0.5), scale=0.9, font=FONT, color=color.rgba(0.7, 1, 0.7, 1), z=-0.2, enabled=show_fps, add_to_scene_entities=False)
        self._fps_t, self._fps_n = (0.0, 0)
        self._driver = _Driver(self)
        self._start_scene = start_scene

    def run(self):
        self.hud.black()
        self._load_scene(self._start_scene)
        self.app.run()

    def quit(self):
        application.quit()

    def _optimise(self, sc):
        import os
        if os.environ.get('NC_NOBATCH'):
            return
        try:
            from engine.batch import batch_scene
            t0 = time.time()
            st = batch_scene(sc)
            print(f"[game] batched {st['merged']} objects into {st['groups']} meshes in {time.time() - t0:.2f}s")
        except Exception:
            traceback.print_exc()
            print('[game] batching failed - running this scene unbatched')

    def goto(self, index, fade=0.9):
        if self.transitioning:
            return
        index = max(0, min(index, len(self.SCENES) - 1))
        if self.SCENES[index] is None:
            print(f'[game] scene {index} failed to import: {self.LOAD_ERRORS.get(index)}')
            self.hud.caption(f'Scene {index} has an error - see the console', hold=2.0)
            return
        self.transitioning = True
        self.paused = False
        self._pause_panel_show(False)
        self.audio.stop_all(fade=fade)
        self.hud.fade_to(1.0, fade, on_done=lambda: setattr(self, '_pending', index))

    def next_scene(self):
        self.goto(self.scene_index + 1 if self.scene_index + 1 < len(self.SCENES) else 0)

    def restart_scene(self):
        self.goto(self.scene_index)

    def _load_scene(self, index):
        old = self.scene
        if old is not None:
            try:
                old.destroy()
            except Exception:
                traceback.print_exc()
        self.scene = None
        self.dialogue.close()
        self.hud.prompt(None)
        self.hud.objective(None)
        self.hud.tl.clear()
        self.hud.fade_a = 1.0
        self.hud.letter_amt = 0.0
        self.hud.caption_a = self.hud.title_a = self.hud.sub_a = self.hud.hint_a = 0.0
        self.post.reset()
        Clock.time_scale = 1.0
        cls = self.SCENES[index]
        if cls is None:
            index, cls = (0, self.SCENES[0])
        t0 = time.time()
        try:
            sc = cls(self)
            sc.build()
            self._optimise(sc)
            self.post.bind(sc.tl)
            sc.ready = True
            self.scene, self.scene_index = (sc, index)
            print(f'[game] built scene {index} ({cls.__name__}) in {time.time() - t0:.2f}s')
            sc.start()
        except Exception:
            traceback.print_exc()
            print(f'[game] scene {index} crashed while building - returning to menu')
            if index != 0:
                self._pending = 0
        self.hud.fade_to(0.0, 1.1)
        self.transitioning = False

    def frame(self):
        self.frame_count += 1
        dt = Clock.tick()
        if self._pending is not None:
            idx, self._pending = (self._pending, None)
            self._load_scene(idx)
            dt = 0.0
        if self.scene is not None and self.scene.ready and (not self.paused):
            try:
                self.scene.update(dt)
            except Exception:
                traceback.print_exc()
                self.scene.ready = False
                self.hud.caption('Scene error - see console (F5 = menu)', hold=3.0)
        self.post.update(dt)
        self.hud.update()
        self.dialogue.update()
        self.audio.update(Clock.raw_dt)
        for fn in list(self.frame_hooks):
            fn(self)
        if self._fps_text.enabled:
            self._fps_t += Clock.raw_dt
            self._fps_n += 1
            if self._fps_t >= 0.5:
                self._fps_text.text = f'{self._fps_n / self._fps_t:.0f} FPS'
                self._fps_t, self._fps_n = (0.0, 0)

    def on_input(self, key):
        if key == 'escape':
            self.toggle_pause()
            return
        if self.paused:
            if key == 'r':
                self.restart_scene()
            elif key == 'q':
                self.goto(0)
            elif key == 'x':
                self.quit()
            return
        if key == 'm':
            self.audio.toggle_mute()
            return
        if key == 'f7':
            self._fps_text.enabled = not self._fps_text.enabled
            return
        if key == 'f10':
            self.post.perf = not self.post.perf
            Emitter.quality = 0.55 if self.post.perf else 1.0
            self.hud.caption('Performance mode ' + ('ON  (F10 to switch back)' if self.post.perf else 'OFF'), hold=1.8, size=1.6)
            return
        if key == 'f12':
            self.screenshot()
            return
        if key in ('f1', 'f2', 'f3', 'f4'):
            self.goto(int(key[1]))
            return
        if key == 'f8':
            self.goto(5)
            return
        if key == 'f9':
            self.goto(6)
            return
        if key == 'f5':
            self.goto(0)
            return
        if key == 'f6':
            self.next_scene()
            return
        d = self.dialogue
        if d.active:
            if key in ('space', 'e', 'enter'):
                d.advance()
            elif key in ('1', '2', '3', '4'):
                d.pick(int(key) - 1)
            return
        if self.scene is not None and self.scene.ready:
            self.scene.on_key(key)

    def screenshot(self):
        folder = os.path.join(str(ROOT), 'screenshots')
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"night_crow_{time.strftime('%H%M%S')}.png")
        base.screenshot(path, defaultFilename=False)
        print('[game] screenshot saved:', path)

    def _build_pause_panel(self):
        ui = camera.ui
        self._pause_bg = Entity(parent=ui, model='quad', color=color.rgba(0, 0, 0, 0.72), scale=(3, 2), z=-0.6, enabled=False, add_to_scene_entities=False)
        self._pause_title = Text(text='PAUSED', parent=ui, position=(0, 0.1), origin=(0, 0), scale=3.4, font=FONT_BOLD, color=color.rgba(0.93, 0.76, 0.34, 1), z=-0.7, enabled=False, add_to_scene_entities=False)
        self._pause_help = Text(text='Esc  resume\nR  restart this scene\nQ  main menu\nX  quit game\n\nM  mute      F7  FPS      F10  performance mode\nF12  screenshot', parent=ui, position=(0, -0.02), origin=(0, 0.5), scale=1.25, font=FONT, color=color.rgba(0.9, 0.9, 0.9, 1), z=-0.7, enabled=False, add_to_scene_entities=False)

    def _pause_panel_show(self, on):
        for e in (self._pause_bg, self._pause_title, self._pause_help):
            e.enabled = on

    def toggle_pause(self):
        if self.transitioning:
            return
        self.paused = not self.paused
        self._pause_panel_show(self.paused)
