import math
import random
from ursina import Vec3, camera
from engine.timing import Clock

def level_look_at(cam, target):
    d = Vec3(*target) - Vec3(*cam.world_position)
    flat = math.hypot(d.x, d.z)
    if flat < 1e-06 and abs(d.y) < 1e-06:
        return
    cam.rotation = Vec3(-math.degrees(math.atan2(d.y, flat)), math.degrees(math.atan2(d.x, d.z)), 0)

class CameraRig:

    def __init__(self, pitch=44.0, distance=12.0, yaw=0.0, fov=68.0):
        self.pitch = pitch
        self.distance = distance
        self.yaw = yaw
        self.height_offset = 1.2
        self.target = Vec3(0, 0, 0)
        self.pos = Vec3(0, 8, -9)
        self.look = Vec3(0, 1, 0)
        self.mode = 'follow'
        self.cine_pos = Vec3(0, 0, 0)
        self.cine_look = Vec3(0, 0, 0)
        self.follow_speed = 5.0
        self.cine_speed = 2.2
        self.bounds = None
        self._shake = 0.0
        self._shake_time = 0.0
        self._shake_total = 0.0
        self._fov_goal = fov
        camera.fov = fov
        self._snap = True

    def follow_offset(self):
        p = math.radians(self.pitch)
        y = math.radians(self.yaw)
        horiz = math.cos(p) * self.distance
        return Vec3(-math.sin(y) * horiz, math.sin(p) * self.distance, -math.cos(y) * horiz)

    def cine(self, position, look_at, speed=None):
        self.mode = 'cine'
        self.cine_pos = Vec3(*position)
        self.cine_look = Vec3(*look_at)
        if speed:
            self.cine_speed = speed

    def release(self):
        self.mode = 'follow'

    def snap(self):
        self._snap = True

    def shake(self, strength=0.3, duration=0.5):
        self._shake = strength
        self._shake_time = duration
        self._shake_total = duration

    def set_fov(self, fov):
        self._fov_goal = fov

    def update(self, dt):
        if self.mode == 'follow':
            goal_pos = self.target + Vec3(0, self.height_offset, 0) + self.follow_offset()
            goal_look = self.target + Vec3(0, self.height_offset, 0)
            speed = self.follow_speed
            if self.bounds:
                goal_pos.x = min(max(goal_pos.x, self.bounds[0]), self.bounds[1])
                goal_pos.z = min(max(goal_pos.z, self.bounds[2]), self.bounds[3])
        else:
            goal_pos, goal_look, speed = (self.cine_pos, self.cine_look, self.cine_speed)
        k = 1.0 if self._snap else 1.0 - math.exp(-speed * dt)
        self._snap = False
        self.pos += (goal_pos - self.pos) * k
        self.look += (goal_look - self.look) * k
        offset = Vec3(0, 0, 0)
        if self._shake_time > 0:
            self._shake_time -= dt
            fade = max(0.0, self._shake_time / max(self._shake_total, 0.0001))
            amp = self._shake * fade
            offset = Vec3(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)) * amp
        camera.position = self.pos + offset
        level_look_at(camera, self.look + offset * 0.5)
        camera.fov += (self._fov_goal - camera.fov) * (1.0 - math.exp(-3.0 * dt))
