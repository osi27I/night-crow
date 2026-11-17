import math
import random
from panda3d.core import PTA_LVecBase3f, PTA_float, LVecBase3f
from ursina import Vec3, scene, camera
from engine.timing import Clock
MAX_LIGHTS = 8

class FlickerLight:

    def __init__(self, pos, color=(1.0, 0.62, 0.28), intensity=1.5, radius=9.0, flicker=0.25, speed=9.0):
        self.pos = Vec3(*pos)
        self.color = Vec3(*color)
        self.intensity = intensity
        self.radius = radius
        self.flicker = flicker
        self.speed = speed
        self.scale = 1.0
        self.enabled = True
        self._phase = random.random() * 100.0

    def strength(self, t):
        if not self.enabled:
            return 0.0
        s = self.speed
        n = math.sin(t * s + self._phase) * 0.5 + math.sin(t * s * 2.31 + self._phase * 1.7) * 0.3 + math.sin(t * s * 5.7 + self._phase * 0.3) * 0.2
        return max(0.0, self.intensity * self.scale * (1.0 + self.flicker * n))

class LightRig:

    def __init__(self):
        self.lights = []
        self.ambient = Vec3(0.18, 0.18, 0.26)
        self.sun_dir = Vec3(0.3, 0.8, -0.4)
        self.sun_color = Vec3(0.0, 0.0, 0.0)
        self.fog_color = Vec3(0.05, 0.06, 0.1)
        self.fog_density = 0.018
        self.focus = Vec3(0, 0, 0)
        self._pos = PTA_LVecBase3f.empty_array(MAX_LIGHTS)
        self._col = PTA_LVecBase3f.empty_array(MAX_LIGHTS)
        self._rad = PTA_float.empty_array(MAX_LIGHTS)
        for i in range(MAX_LIGHTS):
            self._pos.setElement(i, LVecBase3f(0, 0, 0))
            self._col.setElement(i, LVecBase3f(0, 0, 0))
            self._rad.setElement(i, 0.0)

    def add(self, pos, **kwargs):
        light = FlickerLight(pos, **kwargs)
        self.lights.append(light)
        return light

    def remove(self, light):
        if light in self.lights:
            self.lights.remove(light)

    def clear(self):
        self.lights.clear()

    def level_at(self, pos):
        t = Clock.now
        level = (self.ambient.x + self.ambient.y + self.ambient.z) / 3.0
        for L in self.lights:
            d = math.hypot(L.pos.x - pos.x, L.pos.z - pos.z)
            if d < L.radius:
                fall = (1.0 - d / L.radius) ** 2
                lc = (L.color.x + L.color.y + L.color.z) / 3.0
                level += L.strength(t) * fall * lc * 1.2
        return level

    def update(self):
        t = Clock.now
        fx, fz = (self.focus.x, self.focus.z)
        ranked = sorted((L for L in self.lights if L.enabled and L.strength(t) > 0.01), key=lambda L: math.hypot(L.pos.x - fx, L.pos.z - fz) - L.radius * 0.6)[:MAX_LIGHTS]
        for i in range(MAX_LIGHTS):
            if i < len(ranked):
                L = ranked[i]
                s = L.strength(t)
                self._pos.setElement(i, LVecBase3f(L.pos.x, L.pos.y, L.pos.z))
                self._col.setElement(i, LVecBase3f(L.color.x * s, L.color.y * s, L.color.z * s))
                self._rad.setElement(i, L.radius)
            else:
                self._rad.setElement(i, 0.0)
        scene.set_shader_input('light_pos', self._pos)
        scene.set_shader_input('light_col', self._col)
        scene.set_shader_input('light_rad', self._rad)
        scene.set_shader_input('ambient_color', LVecBase3f(*self.ambient))
        scene.set_shader_input('sun_dir', LVecBase3f(*self.sun_dir))
        scene.set_shader_input('sun_color', LVecBase3f(*self.sun_color))
        scene.set_shader_input('fog_color', LVecBase3f(*self.fog_color))
        scene.set_shader_input('fog_density', float(self.fog_density))
        cp = camera.world_position
        scene.set_shader_input('cam_pos', LVecBase3f(cp.x, cp.y, cp.z))
