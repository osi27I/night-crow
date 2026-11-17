import math
from ursina import Entity, Vec3
from engine.assets import tex
from engine.entities import mk, rgb, shade, glow_quad, torus_model
from engine.timing import ease_in_out

class Character:

    def __init__(self, parent, pos=(0, 0, 0), scale=1.0):
        self.root = Entity(parent=parent, position=pos, add_to_scene_entities=False)
        self.root.scale = scale
        self.base_scale = scale
        self.body = Entity(parent=self.root, add_to_scene_entities=False)
        self.head_pivot = None
        self.arm_l = self.arm_r = None
        self.boot_l = self.boot_r = None
        self.cloak = None
        self.weapon = None
        self.shadow = None
        self.amount = 0.0
        self.phase = 0.0
        self.t = 0.0
        self._attack_t = 0.0
        self.attack_duration = 0.34
        self.pose = 'stand'
        self._pose_blend = 0.0
        self.angle = 0.0
        self.alive = True
        self.talking = False
        self.head_turn = 0.0
        self._head_cur = 0.0
        self.arm_r_goal = None
        self.arm_l_goal = None
        self._arm_r_cur = 0.0
        self._arm_l_cur = 0.0
        self.frozen = False

    @property
    def position(self):
        return self.root.position

    @position.setter
    def position(self, v):
        self.root.position = v

    @property
    def x(self):
        return self.root.x

    @property
    def z(self):
        return self.root.z

    def face(self, dx, dz, dt=None, turn_speed=14.0):
        if abs(dx) < 0.0001 and abs(dz) < 0.0001:
            return
        goal = math.degrees(math.atan2(dx, dz))
        if dt is None:
            self.angle = goal
        else:
            diff = (goal - self.angle + 180.0) % 360.0 - 180.0
            self.angle += diff * min(1.0, turn_speed * dt)
        self.root.rotation_y = self.angle

    def attack(self):
        self._attack_t = self.attack_duration

    @property
    def attacking(self):
        return self._attack_t > 0

    def set_pose(self, pose):
        self.pose = pose
        self._pose_blend = 0.0

    def hide_shadow(self):
        if self.shadow:
            self.shadow.enabled = False

    def freeze(self):
        if self.frozen:
            return
        from engine.batch import bake, strip_default_inputs
        strip_default_inputs(self.root)
        bake(self.root, [self.body], 'frozen')
        self.frozen = True

    def update(self, dt):
        if self.frozen:
            return
        self.t += dt
        walk = self.amount if self.pose == 'stand' else 0.0
        self.phase += dt * (5.5 + 4.5 * walk) * (1.0 if walk > 0.02 else 0.0)
        if self.pose != 'stand':
            self._pose_blend = min(1.0, self._pose_blend + dt * (1.6 if self.pose == 'fall' else 1.2))
        k = ease_in_out(self._pose_blend)
        s = math.sin(self.phase)
        c = math.cos(self.phase)
        bob = abs(s) * 0.06 * walk + math.sin(self.t * 2.0) * 0.012 * (1.0 - walk)
        self.body.y = bob
        self.body.z = 0.0
        if self.boot_l and self.boot_r:
            self.boot_l.z = 0.04 + s * 0.2 * walk
            self.boot_r.z = 0.04 - s * 0.2 * walk
            self.boot_l.y = 0.07 + max(0.0, c) * 0.09 * walk
            self.boot_r.y = 0.07 + max(0.0, -c) * 0.09 * walk
        if self.arm_l and self.arm_r:
            self.arm_l.rotation_x = s * 38.0 * walk
            self.arm_r.rotation_x = -s * 38.0 * walk
            if self._attack_t > 0:
                self._attack_t = max(0.0, self._attack_t - dt)
                a = 1.0 - self._attack_t / self.attack_duration
                swing = math.sin(a * math.pi)
                self.arm_r.rotation_x = -20.0 - 105.0 * swing
                self.body.z = 0.22 * swing
                self.body.rotation_y = 12.0 * (swing - 0.4)
            else:
                self.body.rotation_y = 0.0
        if self.cloak:
            self.cloak.rotation_x = -5.0 - (10.0 + 8.0 * math.sin(self.phase * 2.0)) * walk + math.sin(self.t * 1.6) * 1.5
        if self.pose == 'kneel':
            self.body.y = bob - 0.42 * k
            self.body.rotation_x = 16.0 * k
            if self.head_pivot:
                self.head_pivot.rotation_x = 22.0 * k
            if self.arm_l and self.arm_r:
                self.arm_l.rotation_x = -18.0 * k
                self.arm_r.rotation_x = -18.0 * k
        elif self.pose == 'sit':
            self.body.y = bob - 0.4 * k
            self.body.rotation_x = 0.0
            if self.head_pivot:
                self.head_pivot.rotation_x = 0.0
            if self.arm_l and self.arm_r:
                self.arm_l.rotation_x = -26.0 * k
                self.arm_r.rotation_x = -26.0 * k
        elif self.pose == 'fall':
            self.root.rotation_x = -88.0 * k
            self.root.y = 0.16 * k
            if self.arm_l and self.arm_r:
                self.arm_l.rotation_x = -35.0 * k
                self.arm_r.rotation_x = 28.0 * k
        elif self.pose == 'lie':
            self.root.rotation_x = -90.0 * k
            if self.arm_l and self.arm_r:
                self.arm_l.rotation_x = 0
                self.arm_r.rotation_x = 0
            self.body.y = math.sin(self.t * 1.4) * 0.01
        else:
            self.body.rotation_x = 0.0
            if self.head_pivot:
                self.head_pivot.rotation_x = 0.0
        if self.talking and self.pose in ('stand', 'sit') and self.head_pivot:
            self.head_pivot.rotation_x += math.sin(self.t * 7.0) * 2.5 + 2.0
            if self.arm_l and self.arm_l_goal is None:
                self.arm_l.rotation_x += -16.0 + math.sin(self.t * 3.1) * 14.0
        for arm, goal_name, cur_name in ((self.arm_r, 'arm_r_goal', '_arm_r_cur'), (self.arm_l, 'arm_l_goal', '_arm_l_cur')):
            if arm is None:
                continue
            goal = getattr(self, goal_name)
            if goal is None:
                setattr(self, cur_name, arm.rotation_x)
            else:
                cur = getattr(self, cur_name)
                cur += (goal - cur) * min(1.0, dt * 8.0)
                setattr(self, cur_name, cur)
                if not (arm is self.arm_r and self._attack_t > 0):
                    arm.rotation_x = cur
        if self.head_pivot:
            self._head_cur += (max(-75.0, min(75.0, self.head_turn)) - self._head_cur) * min(1.0, dt * 7.0)
            self.head_pivot.rotation_y = self._head_cur
SKIN_TONES = {'tan': rgb(196, 144, 100), 'olive': rgb(170, 124, 84), 'dark': rgb(128, 86, 58), 'light': rgb(214, 170, 130)}

def _headgear(hp, head, hc, skin_c):
    cl = shade(hc, 0.9)
    if head == 'turban':
        for i, (y, sc, tilt, k) in enumerate(((0.185, 0.45, 6, 0.95), (0.235, 0.41, -7, 1.05), (0.285, 0.35, 8, 0.92))):
            mk(hp, torus_model(0.34), (0, y, -0.012), (sc, sc * 0.86, sc * 1.02), shade(cl, k), rot=(tilt, i * 31, 0))
        mk(hp, 'sphere', (0, 0.3, -0.012), (0.27, 0.2, 0.28), shade(cl, 0.96))
        mk(hp, 'sphere', (0.17, 0.0, -0.07), (0.1, 0.3, 0.13), shade(cl, 0.9), rot=(0, 0, -8))
    elif head == 'shemagh':
        mk(hp, 'sphere', (0, 0.19, -0.02), (0.41, 0.34, 0.44), cl)
        mk(hp, 'sphere', (0, 0.205, 0.045), (0.31, 0.19, 0.26), shade(cl, 1.04))
        for sx in (-1, 1):
            mk(hp, 'sphere', (sx * 0.178, -0.06, -0.05), (0.1, 0.36, 0.28), shade(cl, 0.95), rot=(0, 0, sx * -4))
        mk(hp, 'sphere', (0, -0.12, -0.155), (0.36, 0.5, 0.14), shade(cl, 0.93), rot=(-9, 0, 0))
        for y in (0.145, 0.108):
            mk(hp, torus_model(0.1), (0, y, -0.012), (0.43, 0.43, 0.45), rgb(22, 18, 18))
    elif head == 'crown':
        mk(hp, 'sphere', (0, 0.19, -0.02), (0.41, 0.34, 0.44), cl)
        for sx in (-1, 1):
            mk(hp, 'sphere', (sx * 0.178, -0.06, -0.05), (0.1, 0.36, 0.28), shade(cl, 0.95), rot=(0, 0, sx * -4))
        mk(hp, 'sphere', (0, -0.12, -0.155), (0.36, 0.5, 0.14), shade(cl, 0.93), rot=(-9, 0, 0))
        _crown(hp, 0.145)
    elif head == 'helmet':
        steel = hc
        mk(hp, 'sphere', (0, 0.215, -0.01), (0.43, 0.36, 0.46), steel)
        mk(hp, torus_model(0.16), (0, 0.128, -0.006), (0.46, 0.3, 0.48), shade(steel, 0.72))
        for sx in (-1, 1):
            mk(hp, 'sphere', (sx * 0.186, -0.02, 0.01), (0.05, 0.22, 0.22), shade(steel, 0.88))
        mk(hp, 'sphere', (0, 0.03, -0.155), (0.38, 0.2, 0.18), shade(steel, 0.84), rot=(-15, 0, 0))
        for i in range(6):
            mk(hp, 'sphere', (0, 0.405 - 0.012 * abs(i - 2), 0.1 - i * 0.052), (0.05, 0.085, 0.075), rgb(156, 30, 32))
    elif head == 'hood':
        mk(hp, 'sphere', (0, 0.07, -0.115), (0.46, 0.46, 0.5), hc)
        mk(hp, 'sphere', (0, 0.005, -0.2), (0.36, 0.42, 0.3), shade(hc, 1.12))
        mk(hp, torus_model(0.22), (0, 0.02, 0.095), (0.4, 0.4, 0.4), shade(hc, 1.05), rot=(90, 0, 0))
        mk(hp, 'cone', (0, -0.12, -0.34), (0.2, 0.3, 0.2), hc, rot=(-100, 0, 0))
    elif head == 'scarf':
        mk(hp, 'sphere', (0, 0.07, -0.085), (0.43, 0.4, 0.44), hc)
        mk(hp, torus_model(0.2), (0, 0.015, 0.092), (0.41, 0.41, 0.41), shade(hc, 1.06), rot=(90, 0, 0))
        mk(hp, 'sphere', (0, -0.175, -0.04), (0.4, 0.26, 0.34), shade(hc, 0.96))
        mk(hp, 'sphere', (0, -0.3, -0.03), (0.6, 0.24, 0.42), shade(hc, 0.93))
    elif head == 'cap':
        mk(hp, 'sphere', (0, 0.15, -0.02), (0.385, 0.22, 0.4), hc)
        mk(hp, 'cylinder', (0, 0.115, -0.02), (0.382, 0.03, 0.396), shade(hc, 1.5))

def _crown(hp, y0, scale=1.0):
    gold = rgb(228, 186, 72)
    deep = rgb(170, 124, 36)
    mk(hp, 'cylinder', (0, y0, -0.012), (0.44 * scale, 0.1 * scale, 0.455 * scale), gold, emissive=0.3)
    for yy in (y0 + 0.005, y0 + 0.095 * scale):
        mk(hp, torus_model(0.07), (0, yy, -0.012), (0.455 * scale, 0.5 * scale, 0.47 * scale), deep, emissive=0.2)
    for i in range(8):
        a = math.radians(i * 45.0)
        sx_, cz_ = (math.sin(a), math.cos(a))
        tall = 1.35 if i == 0 else 1.0
        px, pz = (sx_ * 0.205 * scale, -0.012 + cz_ * 0.215 * scale)
        mk(hp, 'cone', (px, y0 + 0.095 * scale, pz), (0.085 * scale, 0.17 * scale * tall, 0.085 * scale), gold, emissive=0.3)
        mk(hp, 'sphere', (px, y0 + (0.095 + 0.17 * tall) * scale + 0.01, pz), 0.04 * scale, rgb(244, 240, 228), emissive=0.35)
        if i % 2 == 1:
            mk(hp, 'sphere', (sx_ * 0.226 * scale, y0 + 0.05 * scale, -0.012 + cz_ * 0.236 * scale), (0.04 * scale, 0.05 * scale, 0.03 * scale), rgb(40, 190, 110), emissive=0.5)
    mk(hp, 'sphere', (0, y0 + 0.05 * scale, -0.012 + 0.236 * scale), (0.062 * scale, 0.07 * scale, 0.04 * scale), rgb(220, 30, 52), emissive=0.7)
    for sx in (-1, 1):
        mk(hp, 'sphere', (sx * 0.226 * scale, y0 + 0.05 * scale, -0.012), (0.04 * scale, 0.07 * scale, 0.062 * scale), rgb(40, 96, 230), emissive=0.6)

def build_character(parent, pos=(0, 0, 0), robe=rgb(150, 110, 70), trim=rgb(180, 40, 40), skin='tan', head='shemagh', head_color=rgb(236, 230, 214), beard=None, scale=1.0, cloak=None, weapon=None, boots=rgb(46, 32, 24), mask=False, shadow=True, build='normal'):
    ch = Character(parent, pos, scale)
    skin_c = SKIN_TONES.get(skin, SKIN_TONES['tan']) if isinstance(skin, str) else skin
    w = 1.12 if build == 'broad' else 1.0
    B = ch.body
    if shadow:
        sh = glow_quad(ch.root, (0, 0.03, 0), 1.25, rgb(0, 0, 0, 150), tex('shadow'), billboard=False, add=False, bin_sort=5)
        sh.rotation_x = 90
        ch.shadow = sh
    ch.boot_l = mk(B, 'cube', (-0.15 * w, 0.07, 0.04), (0.2, 0.14, 0.34), boots)
    ch.boot_r = mk(B, 'cube', (0.15 * w, 0.07, 0.04), (0.2, 0.14, 0.34), boots)
    for boot in (ch.boot_l, ch.boot_r):
        mk(boot, 'sphere', (0, 0.05, 0.4), (0.92, 0.8, 0.34), shade(boots, 1.18))
        mk(boot, 'cube', (0, 0.62, -0.12), (1.06, 0.55, 0.62), shade(boots, 0.82))
    mk(B, 'cylinder', (0, 0.1, 0), (0.78 * w, 0.4, 0.66 * w), shade(robe, 0.88))
    mk(B, 'cylinder', (0, 0.4, 0), (0.6 * w, 0.78, 0.5 * w), robe)
    mk(B, 'sphere', (0, 1.16, 0), (0.72 * w, 0.44, 0.48), robe)
    mk(B, 'cylinder', (0, 0.7, 0), (0.64 * w, 0.11, 0.54 * w), trim)
    mk(B, 'sphere', (0.17 * w, 0.68, 0.27), (0.13, 0.12, 0.08), shade(trim, 1.15))
    mk(B, 'cube', (0.15 * w, 0.52, 0.28), (0.07, 0.3, 0.03), shade(trim, 0.85), rot=(0, 0, 6))
    mk(B, 'cube', (0.23 * w, 0.54, 0.27), (0.06, 0.26, 0.03), shade(trim, 0.95), rot=(0, 0, -8))
    mk(B, 'sphere', (-0.04, 0.7, 0.275), (0.075, 0.075, 0.03), rgb(212, 170, 66), emissive=0.25)
    mk(B, 'cylinder', (0, 0.2, 0), (0.84 * w, 0.06, 0.72 * w), trim)
    mk(B, 'cylinder', (0, 1.3, 0), (0.4 * w, 0.07, 0.34), trim)
    for side, name in ((-1, 'arm_l'), (1, 'arm_r')):
        pivot = Entity(parent=B, position=(0.4 * w * side, 1.22, 0), add_to_scene_entities=False)
        mk(pivot, 'sphere', (0, -0.02, 0), (0.24, 0.22, 0.24), shade(robe, 1.02))
        mk(pivot, 'cylinder', (0, -0.58, 0), (0.17, 0.58, 0.17), shade(robe, 0.95))
        mk(pivot, 'cylinder', (0, -0.56, 0), (0.205, 0.07, 0.205), trim)
        mk(pivot, 'sphere', (0, -0.64, 0.005), (0.125, 0.14, 0.095), skin_c)
        mk(pivot, 'sphere', (0, -0.71, 0.015), (0.105, 0.085, 0.075), shade(skin_c, 0.96))
        mk(pivot, 'sphere', (0.075 * -side, -0.63, 0.04), (0.05, 0.09, 0.05), shade(skin_c, 1.04))
        setattr(ch, name, pivot)
    hp = Entity(parent=B, position=(0, 1.5, 0), add_to_scene_entities=False)
    ch.head_pivot = hp
    mk(hp, 'cylinder', (0, -0.235, 0), (0.15, 0.12, 0.15), shade(skin_c, 0.88))
    mk(hp, 'sphere', (0, 0, 0), (0.36, 0.38, 0.36), skin_c)
    mk(hp, 'sphere', (0, -0.085, 0.03), (0.3, 0.22, 0.3), shade(skin_c, 0.97))
    for sx in (-1, 1):
        mk(hp, 'sphere', (sx * 0.095, -0.055, 0.115), (0.1, 0.075, 0.07), shade(skin_c, 1.03))
        mk(hp, 'sphere', (sx * 0.078, 0.035, 0.1635), (0.062, 0.04, 0.03), rgb(236, 230, 218))
        mk(hp, 'sphere', (sx * 0.078, 0.034, 0.1745), (0.031, 0.031, 0.016), rgb(40, 26, 18))
        mk(hp, 'cube', (sx * 0.078, 0.06, 0.1715), (0.068, 0.011, 0.012), shade(skin_c, 0.55))
        mk(hp, 'cube', (sx * 0.08, 0.086, 0.162), (0.085, 0.016, 0.02), rgb(36, 26, 20), rot=(0, 0, sx * 3))
        mk(hp, 'sphere', (sx * 0.178, 0.0, -0.01), (0.04, 0.09, 0.07), shade(skin_c, 0.94))
    mk(hp, 'sphere', (0, 0.0, 0.176), (0.035, 0.085, 0.04), shade(skin_c, 0.98))
    mk(hp, 'sphere', (0, -0.04, 0.19), (0.056, 0.05, 0.052), shade(skin_c, 0.93))
    mk(hp, 'cube', (0, -0.094, 0.167), (0.066, 0.011, 0.015), rgb(122, 58, 48))
    if beard is not None:
        mk(hp, 'sphere', (0, -0.15, 0.07), (0.27, 0.22, 0.22), beard)
        mk(hp, 'sphere', (0, -0.06, 0.15), (0.17, 0.05, 0.05), beard)
    _headgear(hp, head, head_color, skin_c)
    if mask:
        mk(hp, 'cone', (0, -0.03, 0.26), (0.13, 0.26, 0.13), rgb(24, 22, 28), rot=(90, 0, 0))
        mk(hp, 'sphere', (0, 0.0, 0.14), (0.3, 0.3, 0.16), rgb(24, 22, 28))
        mk(hp, 'sphere', (-0.075, 0.05, 0.19), 0.04, rgb(255, 210, 90), emissive=1.0)
        mk(hp, 'sphere', (0.075, 0.05, 0.19), 0.04, rgb(255, 210, 90), emissive=1.0)
    if build == 'broad':
        steel_c = rgb(150, 154, 166)
        mk(B, 'sphere', (0, 1.06, 0.06), (0.62, 0.52, 0.42), steel_c, emissive=0.04)
        mk(B, 'cylinder', (0, 0.98, 0.0), (0.66, 0.05, 0.52), shade(steel_c, 0.75))
        for sx in (-1, 1):
            mk(B, 'sphere', (sx * 0.47, 1.26, 0.0), (0.27, 0.17, 0.3), steel_c, emissive=0.04)
        for k in range(7):
            a = k / 7.0 * math.pi * 2.0
            mk(B, 'cube', (math.sin(a) * 0.3 * w, 0.58, math.cos(a) * 0.26 * w), (0.1, 0.2, 0.025), rgb(88, 60, 38), rot=(0, math.degrees(a), 0))
    if cloak is not None:
        ch.cloak = Entity(parent=B, position=(0, 1.32, -0.22), add_to_scene_entities=False)
        mk(ch.cloak, 'cube', (0, -0.62, -0.04), (0.82 * w, 1.3, 0.07), cloak)
        mk(ch.cloak, 'cube', (0, -0.2, 0.0), (0.98 * w, 0.3, 0.2), shade(cloak, 1.1))
        mk(ch.cloak, 'cube', (0, -1.32, -0.05), (0.96 * w, 0.14, 0.06), shade(cloak, 0.8))
    if weapon:
        hand = Entity(parent=ch.arm_r, position=(0, -0.62, 0), add_to_scene_entities=False)
        steel = rgb(206, 210, 222)
        if weapon == 'dagger':
            mk(hand, 'cube', (0, -0.02, 0.22), (0.05, 0.05, 0.38), steel, emissive=0.35)
            mk(hand, 'cube', (0, -0.02, 0.03), (0.16, 0.05, 0.05), rgb(190, 150, 60))
        elif weapon == 'sword':
            mk(hand, 'cube', (0, -0.02, 0.42), (0.06, 0.04, 0.78), steel, emissive=0.3)
            mk(hand, 'cube', (0, -0.02, 0.03), (0.3, 0.05, 0.06), rgb(190, 150, 60))
        elif weapon == 'spear':
            mk(hand, 'cylinder', (0, -0.9, 0), (0.05, 2.5, 0.05), rgb(110, 80, 50))
            mk(hand, 'cone', (0, 1.6, 0), (0.12, 0.34, 0.12), steel, emissive=0.3)
        elif weapon == 'bow':
            wood = rgb(120, 84, 52)
            for k, (z, a) in enumerate(((0.12, 16), (-0.12, -16))):
                mk(hand, 'cube', (0.0, 0.0, z), (0.04, 0.04, 0.5), wood, rot=(a, 0, 0))
            mk(hand, 'cube', (0.0, 0.0, 0.0), (0.05, 0.07, 0.14), rgb(70, 46, 30))
            mk(hand, 'cube', (0.0, 0.0, -0.01), (0.012, 0.012, 0.98), rgb(220, 214, 196))
    return ch
