import math

class World:

    def __init__(self):
        self.boxes = []
        self.circles = []

    def add_box(self, cx, cz, w, d, blocks_sight=True):
        self.boxes.append((cx, cz, w / 2.0, d / 2.0, blocks_sight))

    def add_circle(self, cx, cz, r, blocks_sight=False):
        self.circles.append((cx, cz, r, blocks_sight))

    def clear(self):
        self.boxes.clear()
        self.circles.clear()

    def resolve(self, x, z, radius):
        for _ in range(3):
            for cx, cz, hw, hd, _s in self.boxes:
                nx = min(max(x, cx - hw), cx + hw)
                nz = min(max(z, cz - hd), cz + hd)
                dx, dz = (x - nx, z - nz)
                dist = math.hypot(dx, dz)
                if dist < radius:
                    if dist > 1e-06:
                        push = (radius - dist) / dist
                        x += dx * push
                        z += dz * push
                    else:
                        left, right = (x - (cx - hw), cx + hw - x)
                        near, far = (z - (cz - hd), cz + hd - z)
                        m = min(left, right, near, far)
                        if m == left:
                            x = cx - hw - radius
                        elif m == right:
                            x = cx + hw + radius
                        elif m == near:
                            z = cz - hd - radius
                        else:
                            z = cz + hd + radius
            for cx, cz, r, _s in self.circles:
                dx, dz = (x - cx, z - cz)
                dist = math.hypot(dx, dz)
                if dist < radius + r:
                    if dist > 1e-06:
                        push = (radius + r - dist) / dist
                        x += dx * push
                        z += dz * push
                    else:
                        x += radius + r
        return (x, z)

    def line_of_sight(self, ax, az, bx, bz):
        dx, dz = (bx - ax, bz - az)
        for cx, cz, hw, hd, blocks in self.boxes:
            if not blocks:
                continue
            tmin, tmax = (0.0, 1.0)
            hit = True
            for a0, d, lo, hi in ((ax, dx, cx - hw, cx + hw), (az, dz, cz - hd, cz + hd)):
                if abs(d) < 1e-09:
                    if a0 < lo or a0 > hi:
                        hit = False
                        break
                else:
                    t1, t2 = ((lo - a0) / d, (hi - a0) / d)
                    if t1 > t2:
                        t1, t2 = (t2, t1)
                    tmin, tmax = (max(tmin, t1), min(tmax, t2))
                    if tmin > tmax:
                        hit = False
                        break
            if hit:
                return False
        return True
