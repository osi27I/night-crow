from ursina import camera
from engine.shaders import post_shader
from engine.timing import Clock
DEFAULTS = {'vignette': 0.35, 'desat': 0.0, 'bloom': 0.55, 'grain': 0.035, 'aberration': 0.0006, 'tint': (1.0, 1.0, 1.0), 'sight': 0.0}

class PostFX:

    def __init__(self, enabled=True):
        self.enabled = enabled
        self.values = dict(DEFAULTS)
        self.flash_color = (1.0, 1.0, 1.0)
        self.flash_amount = 0.0
        self.flash_decay = 2.5
        self._aberr_kick = 0.0
        self._tl = None
        self.perf = False
        if enabled:
            camera.shader = post_shader

    def bind(self, timeline):
        self._tl = timeline

    def reset(self):
        self.values = dict(DEFAULTS)
        self.flash_amount = 0.0
        self._aberr_kick = 0.0

    def set(self, **kw):
        self.values.update(kw)

    def tween(self, duration=1.0, **targets):
        for key, target in targets.items():
            self._tl.to_item(self.values, key, target, duration)

    def flash(self, color=(1.0, 1.0, 1.0), amount=0.8, decay=2.5):
        self.flash_color, self.flash_amount, self.flash_decay = (color, amount, decay)

    def punch_aberration(self, strength=0.012):
        self._aberr_kick = strength

    def update(self, dt):
        if not self.enabled:
            return
        self.flash_amount = max(0.0, self.flash_amount - self.flash_decay * dt)
        self._aberr_kick = max(0.0, self._aberr_kick - 0.03 * dt * 10)
        v = self.values
        camera.set_shader_input('time', Clock.now % 100.0)
        camera.set_shader_input('vignette', float(v['vignette']))
        camera.set_shader_input('desat', float(v['desat']))
        camera.set_shader_input('bloom', 0.0 if self.perf else float(v['bloom']))
        camera.set_shader_input('grain', float(v['grain']))
        camera.set_shader_input('aberration', float(v['aberration']) + self._aberr_kick)
        camera.set_shader_input('tint', tuple(v['tint']))
        camera.set_shader_input('flash', float(self.flash_amount))
        camera.set_shader_input('flash_color', tuple(self.flash_color))
        camera.set_shader_input('sight', float(v.get('sight', 0.0)))
