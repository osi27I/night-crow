import math
import os
import random
from PIL import Image, ImageChops, ImageDraw, ImageFilter
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'textures')
os.makedirs(OUT, exist_ok=True)
random.seed(7)

def save(img, name):
    img.save(os.path.join(OUT, name))
    print('  wrote', name, img.size)

def tileable_noise(size, cells, seed, octaves=3):
    total = Image.new('L', (size, size), 0)
    amp, weight_sum = (1.0, 0.0)
    for o in range(octaves):
        n = max(2, cells * 2 ** o)
        rnd = random.Random(seed + o * 101)
        base = Image.new('L', (n, n))
        base.putdata([rnd.randint(0, 255) for _ in range(n * n)])
        tiled = Image.new('L', (n * 3, n * 3))
        for ix in range(3):
            for iy in range(3):
                tiled.paste(base, (ix * n, iy * n))
        big = tiled.resize((size * 3, size * 3), Image.BICUBIC)
        crop = big.crop((size, size, size * 2, size * 2))
        crop = crop.point(lambda p, a=amp: int(p * a))
        total = ImageChops.add(total, crop)
        weight_sum += amp
        amp *= 0.5
    total = total.point(lambda p: min(255, int(p / weight_sum * 1.0)))
    return total

def colorize(gray, dark, light):
    return Image.merge('RGB', [gray.point(lambda p, d=dark[i], l=light[i]: int(d + (l - d) * p / 255.0)) for i in range(3)])

def speckle(img, count, color, size=1, alpha=1.0):
    d = ImageDraw.Draw(img)
    w, h = img.size
    for _ in range(count):
        x, y = (random.randrange(w), random.randrange(h))
        d.rectangle((x, y, x + size, y + size), fill=color)
    return img
import numpy as np
SZ = 512

def nz(cells, seed, octaves=5, size=SZ, persistence=0.55, aniso=(1, 1)):
    rnd = np.random.RandomState(seed)
    total = np.zeros((size, size), np.float32)
    amp, norm = (1.0, 0.0)
    for o in range(octaves):
        cx = max(2, int(cells * aniso[0] * 2 ** o))
        cy = max(2, int(cells * aniso[1] * 2 ** o))
        base = rnd.rand(cy, cx).astype(np.float32)
        tiled = np.tile(base, (3, 3))
        im = Image.fromarray((tiled * 255).astype(np.uint8), 'L').resize((cx * 3 * (size // cx + 1), cy * 3 * (size // cy + 1)), Image.BICUBIC)
        w, h = im.size
        crop = im.crop((w // 3, h // 3, 2 * w // 3, 2 * h // 3)).resize((size, size), Image.BICUBIC)
        total += np.asarray(crop, np.float32) / 255.0 * amp
        norm += amp
        amp *= persistence
    total /= norm
    lo, hi = (np.percentile(total, 1), np.percentile(total, 99))
    return np.clip((total - lo) / max(1e-06, hi - lo), 0, 1)

def ramp(t, stops):
    pos = [p for p, _ in stops]
    out = np.zeros(t.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(t, pos, [col[c] for _, col in stops])
    return out

def to_img(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB')

def blur(arr, r):
    pad = int(r * 4) + 2
    p = np.pad(arr, pad, mode='wrap')
    im = Image.fromarray((np.clip(p, 0, 1) * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im, np.float32)[pad:-pad, pad:-pad] / 255.0

def wrap_line(draw_fn, pts, width=1):
    for ox in (-SZ, 0, SZ):
        for oy in (-SZ, 0, SZ):
            draw_fn([(x + ox, y + oy) for x, y in pts], width)

def cracks(img, count, seed, col=(70, 52, 38), length=(40, 120), width=1, branch=0.35):
    rnd = random.Random(seed)
    d = ImageDraw.Draw(img)

    def seg(pts, w):
        d.line(pts, fill=col, width=w)
    for _ in range(count):
        x, y = (rnd.uniform(0, SZ), rnd.uniform(0, SZ))
        a = rnd.uniform(0, 6.28)
        pts = [(x, y)]
        for _ in range(rnd.randint(5, 11)):
            a += rnd.uniform(-0.55, 0.55)
            ln = rnd.uniform(length[0], length[1]) / 7.0
            x, y = (x + math.cos(a) * ln, y + math.sin(a) * ln)
            pts.append((x, y))
            if rnd.random() < branch * 0.3:
                bx, by, ba = (x, y, a + rnd.choice((-1, 1)) * rnd.uniform(0.6, 1.2))
                bp = [(bx, by)]
                for _ in range(rnd.randint(2, 4)):
                    bx, by = (bx + math.cos(ba) * ln * 0.7, by + math.sin(ba) * ln * 0.7)
                    bp.append((bx, by))
                wrap_line(seg, bp, 1)
        wrap_line(seg, pts, width)
    return img

def grain_overlay(arr, seed, strength=0.12):
    g = nz(96, seed, 2)
    return arr * (1.0 - strength + strength * 2 * g[..., None])

def specks(arr, count, col, seed, size=(1, 2), alpha=0.8):
    img = to_img(arr)
    d = ImageDraw.Draw(img)
    rnd = random.Random(seed)
    for _ in range(count):
        x, y = (rnd.randrange(SZ), rnd.randrange(SZ))
        s = rnd.randint(*size)
        d.ellipse((x, y, x + s, y + s), fill=col)
    return np.asarray(img, np.float32)

def make_sand():
    t = nz(5, 11, 6)
    base = ramp(t, [(0.0, (150, 112, 70)), (0.35, (186, 146, 96)), (0.7, (214, 178, 124)), (1.0, (232, 202, 150))])
    yy, xx = np.mgrid[0:SZ, 0:SZ].astype(np.float32)
    warp = nz(3, 17, 3) * 40.0
    rip = np.sin((yy + warp) / SZ * 2 * math.pi * 14.0 + nz(4, 19, 2) * 3.0) * 0.5 + 0.5
    base *= 0.9 + 0.14 * rip[..., None]
    blotch = nz(2, 23, 3)
    base *= 0.88 + 0.22 * blotch[..., None]
    base = grain_overlay(base, 29, 0.18)
    base = specks(base, 900, (118, 88, 54), 31, (1, 2))
    base = specks(base, 500, (238, 214, 168), 32, (1, 2))
    img = to_img(base)
    d = ImageDraw.Draw(img)
    rnd = random.Random(35)
    for _ in range(46):
        x, y, r = (rnd.randrange(SZ), rnd.randrange(SZ), rnd.randint(2, 5))
        shade_ = rnd.randint(110, 170)
        d.ellipse((x + 1, y + 1, x + r + 2, y + r + 2), fill=(96, 74, 52))
        d.ellipse((x, y, x + r, y + r), fill=(shade_, shade_ - 14, shade_ - 34))
    save(img, 'sand.png')

def make_dirt():
    t = nz(6, 23, 6)
    base = ramp(t, [(0.0, (46, 32, 22)), (0.5, (86, 62, 42)), (1.0, (132, 98, 66))])
    base = grain_overlay(base, 24, 0.22)
    yy = np.mgrid[0:SZ, 0:SZ][0].astype(np.float32)
    rut = np.exp(-np.sin(yy / SZ * 2 * math.pi * 2.0 + nz(3, 25, 2) * 2.0) ** 2 * 6.0)
    base *= 1.0 - 0.18 * rut[..., None]
    base = specks(base, 1400, (30, 22, 16), 26, (1, 2))
    base = specks(base, 500, (150, 118, 86), 27, (1, 2))
    img = to_img(base)
    d = ImageDraw.Draw(img)
    rnd = random.Random(28)
    for _ in range(60):
        x, y, r = (rnd.randrange(SZ), rnd.randrange(SZ), rnd.randint(3, 8))
        v = rnd.randint(90, 150)
        d.ellipse((x + 1, y + 2, x + r + 1, y + r + 2), fill=(30, 22, 18))
        d.ellipse((x, y, x + r, y + r - 1), fill=(v, v - 10, v - 24))
    img = cracks(img, 10, 29, col=(28, 20, 14), length=(60, 160))
    save(img, 'dirt.png')

def make_ash():
    t = nz(5, 31, 6)
    base = ramp(t, [(0.0, (14, 12, 14)), (0.5, (38, 34, 34)), (1.0, (92, 86, 82))])
    base = grain_overlay(base, 32, 0.25)
    img = to_img(base)
    glow = Image.new('RGB', (SZ, SZ), (0, 0, 0))
    glow = cracks(glow, 16, 33, col=(255, 110, 30), length=(50, 140), width=2)
    g = np.asarray(glow.filter(ImageFilter.GaussianBlur(1.2)), np.float32) * 0.55
    arr = np.asarray(img, np.float32) + g
    arr = specks(arr, 700, (190, 186, 178), 34, (1, 2))
    arr = specks(arr, 260, (255, 120, 40), 35, (1, 1))
    save(to_img(arr), 'ash.png')

def make_rock():
    t = nz(4, 41, 6, persistence=0.6)
    base = ramp(t, [(0.0, (74, 68, 66)), (0.45, (128, 118, 110)), (0.8, (164, 152, 140)), (1.0, (190, 178, 164))])
    base = grain_overlay(base, 42, 0.3)
    layers = np.sin(np.mgrid[0:SZ, 0:SZ][0] / SZ * 2 * math.pi * 3.0 + nz(3, 43, 3) * 4.0) * 0.5 + 0.5
    base *= 0.9 + 0.16 * layers[..., None]
    lichen = (nz(8, 44, 3) > 0.74).astype(np.float32)
    lichen = blur(lichen, 1.6)
    base = base * (1 - 0.35 * lichen[..., None]) + np.array([150, 150, 96], np.float32) * 0.35 * lichen[..., None]
    img = to_img(base)
    img = cracks(img, 14, 45, col=(40, 36, 36), length=(60, 180), width=1, branch=1.0)
    arr = specks(np.asarray(img, np.float32), 800, (46, 42, 42), 46, (1, 2))
    save(to_img(arr), 'rock.png')

def ashlar(name, hues, mortar, seed):
    rnd = random.Random(seed)
    heights = [80, 64, 96, 64, 80, 64, 64]
    arr = np.zeros((SZ, SZ, 3), np.float32)
    arr[:] = mortar
    mortar_noise = nz(64, seed + 3, 2)
    arr *= 0.8 + 0.4 * mortar_noise[..., None]
    grain = nz(48, seed + 5, 3)
    y0 = 0
    for ri, hgt in enumerate(heights):
        widths = []
        total = 0
        while total < SZ - 90:
            w = rnd.randint(110, 230)
            widths.append(w)
            total += w
        widths.append(SZ - total)
        k = SZ / float(sum(widths))
        widths = [max(60, int(round(w * k))) for w in widths]
        widths[-1] = SZ - sum(widths[:-1])
        x0 = rnd.randint(0, 60) if ri else 0
        xs = 0
        for w in widths:
            bx0, bx1 = ((xs + x0) % SZ, (xs + x0) % SZ + w)
            t = rnd.random()
            col = np.array([hues[0][i] + (hues[1][i] - hues[0][i]) * t for i in range(3)], np.float32)
            ys = slice(y0 + 3, y0 + hgt - 2)
            for xo in (0, -SZ):
                xa, xb = (max(0, bx0 + 3 + xo), min(SZ, bx1 - 2 + xo))
                if xb <= xa:
                    continue
                blk = arr[ys, xa:xb]
                shade_y = np.linspace(1.1, 0.86, blk.shape[0])[:, None, None]
                g = grain[ys, xa:xb][..., None]
                blk[:] = col * shade_y * (0.82 + 0.36 * g)
                blk[:2] *= 1.28
                blk[-2:] *= 0.62
                blk[:, :2] *= 1.12
                blk[:, -2:] *= 0.74
            xs += w
        y0 += hgt
    img = to_img(arr)
    d = ImageDraw.Draw(img)
    for _ in range(420):
        x, y = (rnd.randrange(SZ), rnd.randrange(SZ))
        r = rnd.randint(1, 2)
        d.ellipse((x, y, x + r, y + r), fill=tuple((int(c * 0.55) for c in hues[0])))
    img = cracks(img, 6, seed + 9, col=tuple((int(c * 0.5) for c in mortar)), length=(30, 90))
    save(img, name)

def make_stone():
    ashlar('stone.png', ((128, 112, 88), (192, 172, 138)), (66, 58, 48), 41)

def make_stone_dark():
    ashlar('stone_dark.png', ((50, 56, 70), (104, 112, 130)), (22, 24, 32), 43)

def make_mudbrick():
    t = nz(4, 47, 6)
    wash = ramp(t, [(0.0, (160, 120, 82)), (0.5, (198, 158, 112)), (1.0, (222, 188, 142))])
    streak = nz(40, 49, 3, aniso=(1.0, 0.07))
    wash *= 0.86 + 0.28 * streak[..., None]
    trowel = nz(10, 51, 3, aniso=(0.3, 1.0))
    wash *= 0.94 + 0.12 * trowel[..., None]
    wash = grain_overlay(wash, 53, 0.2)
    rnd = random.Random(55)
    br = np.zeros((SZ, SZ, 3), np.float32)
    br[:] = (96, 70, 48)
    bimg = to_img(br)
    bd = ImageDraw.Draw(bimg)
    rows, bh = (16, SZ // 16)
    for r in range(rows):
        off = 0 if r % 2 == 0 else 32
        for c in range(-1, 9):
            x = c * 64 + off
            v = rnd.randint(-18, 18)
            bd.rectangle((x + 2, r * bh + 2, x + 60, r * bh + bh - 3), fill=(146 + v, 100 + v, 66 + v))
    brick = np.asarray(bimg, np.float32)
    chip = nz(8, 57, 4)
    mask = np.clip((chip - 0.74) * 10.0, 0, 1)
    mask = blur(mask, 1.2)
    rim = np.clip(blur(mask, 3.0) - mask, 0, 1) * 1.6
    out = wash * (1 - mask[..., None]) + brick * mask[..., None]
    out *= 1.0 - 0.45 * rim[..., None]
    img = to_img(out)
    img = cracks(img, 18, 59, col=(104, 74, 50), length=(40, 130))
    arr = specks(np.asarray(img, np.float32), 800, (120, 88, 60), 60, (1, 2))
    save(to_img(arr), 'mudbrick.png')

def make_plaster():
    t = nz(3, 53, 5)
    base = ramp(t, [(0.0, (196, 178, 148)), (0.55, (222, 206, 176)), (1.0, (238, 224, 196))])
    base *= 0.94 + 0.12 * nz(30, 63, 3, aniso=(1.0, 0.1))[..., None]
    base = grain_overlay(base, 64, 0.14)
    img = to_img(base)
    save(cracks(img.copy(), 8, 65, col=(150, 132, 108), length=(30, 90)), 'plaster_plain.png')
    d = ImageDraw.Draw(img)
    d.rectangle((0, 420, SZ, 470), fill=(124, 70, 52))
    d.rectangle((0, 410, SZ, 418), fill=(200, 164, 92))
    d.rectangle((0, 472, SZ, 478), fill=(200, 164, 92))
    for k in range(0, SZ, 32):
        d.polygon([(k + 16, 428), (k + 28, 445), (k + 16, 462), (k + 4, 445)], fill=(222, 196, 128))
        d.polygon([(k + 16, 436), (k + 22, 445), (k + 16, 454), (k + 10, 445)], fill=(124, 70, 52))
    img = cracks(img, 8, 65, col=(150, 132, 108), length=(30, 90))
    save(img, 'plaster.png')

def make_wood():
    arr = np.zeros((SZ, SZ, 3), np.float32)
    rnd = random.Random(71)
    planks = 6
    pw = SZ // planks
    grain_long = nz(10, 73, 4, aniso=(0.25, 1.0))
    ring = nz(6, 74, 3, aniso=(0.5, 1.0))
    for i in range(planks):
        tone = rnd.uniform(0.82, 1.12)
        sl = slice(i * pw, (i + 1) * pw)
        g = grain_long[:, sl]
        wave = np.sin(np.mgrid[0:SZ, 0:pw][1] * 0.35 + ring[:, sl] * 14.0) * 0.5 + 0.5
        t = np.clip(g * 0.55 + wave * 0.45, 0, 1)
        arr[:, sl] = ramp(t, [(0.0, (64, 40, 24)), (0.5, (104, 70, 42)), (1.0, (140, 98, 62))]) * tone
        arr[:, i * pw:i * pw + 3] *= 0.35
        arr[:, (i + 1) * pw - 3:(i + 1) * pw] *= 0.7
    img = to_img(arr)
    d = ImageDraw.Draw(img)
    for _ in range(5):
        x, y = (rnd.randint(20, SZ - 20), rnd.randint(20, SZ - 20))
        for r, c in ((14, (58, 36, 22)), (9, (84, 54, 32)), (4, (50, 30, 18))):
            d.ellipse((x - r, y - int(r * 1.6), x + r, y + int(r * 1.6)), outline=c, width=2)
    for i in range(planks):
        for y in (22, SZ - 22):
            d.ellipse((i * pw + 10, y, i * pw + 15, y + 5), fill=(30, 28, 30))
            d.ellipse((i * pw + pw - 17, y, i * pw + pw - 12, y + 5), fill=(30, 28, 30))
    for _ in range(40):
        x = rnd.randrange(SZ)
        y = rnd.randrange(SZ)
        d.line([(x, y), (x + rnd.randint(-2, 2), y + rnd.randint(20, 70))], fill=(40, 26, 16), width=1)
    arr = grain_overlay(np.asarray(img, np.float32), 75, 0.14)
    save(to_img(arr), 'wood.png')

def make_rug():
    s = SZ
    img = Image.new('RGB', (s, s), (122, 28, 30))
    d = ImageDraw.Draw(img)
    cream, navy, gold, rust = ((226, 206, 160), (24, 36, 70), (206, 160, 60), (160, 60, 40))
    d.rectangle((14, 14, s - 15, s - 15), outline=gold, width=8)
    d.rectangle((38, 38, s - 39, s - 39), outline=cream, width=4)
    d.rectangle((52, 52, s - 53, s - 53), fill=navy)
    c = s // 2
    for r, col in ((184, (122, 28, 30)), (150, cream), (118, (122, 28, 30)), (84, gold), (50, navy), (26, rust)):
        d.polygon([(c, c - r), (c + r, c), (c, c + r), (c - r, c)], fill=col)
    for k in range(10):
        x = 66 + k * 38
        d.polygon([(x, 62), (x + 22, 62), (x + 11, 86)], fill=cream)
        d.polygon([(x, s - 63), (x + 22, s - 63), (x + 11, s - 87)], fill=cream)
        d.polygon([(62, x), (62, x + 22), (86, x + 11)], fill=cream)
        d.polygon([(s - 63, x), (s - 63, x + 22), (s - 87, x + 11)], fill=cream)
        d.polygon([(x + 11, 98), (x + 17, 104), (x + 11, 110), (x + 5, 104)], fill=gold)
    for k in range(4):
        cx_, cy_ = (96 if k % 2 == 0 else s - 96, 96 if k < 2 else s - 96)
        d.ellipse((cx_ - 26, cy_ - 26, cx_ + 26, cy_ + 26), fill=gold)
        d.ellipse((cx_ - 16, cy_ - 16, cx_ + 16, cy_ + 16), fill=(122, 28, 30))
        d.ellipse((cx_ - 6, cy_ - 6, cx_ + 6, cy_ + 6), fill=cream)
    arr = np.asarray(img, np.float32)
    yy, xx = np.mgrid[0:s, 0:s]
    weave = ((xx // 2 + yy // 2) % 2 * 0.1 + 0.95)[..., None]
    arr *= weave
    arr = grain_overlay(arr, 77, 0.22)
    wear = nz(4, 78, 4)[..., None]
    arr *= 0.86 + 0.24 * wear
    save(to_img(arr), 'rug.png')

def make_tile():
    s = SZ
    img = Image.new('RGB', (s, s), (210, 200, 178))
    d = ImageDraw.Draw(img)
    cell = s // 4
    blue, teal, cream, grout = ((38, 78, 128), (46, 126, 134), (232, 222, 198), (150, 140, 120))
    for ix in range(4):
        for iy in range(4):
            x0, y0 = (ix * cell, iy * cell)
            d.rectangle((x0, y0, x0 + cell - 1, y0 + cell - 1), fill=cream, outline=grout, width=3)
            m = cell // 2
            cx, cy = (x0 + m, y0 + m)
            col = blue if (ix + iy) % 2 == 0 else teal
            d.polygon([(cx, cy - m + 12), (cx + m - 12, cy), (cx, cy + m - 12), (cx - m + 12, cy)], fill=col)
            d.polygon([(cx, cy - m + 34), (cx + m - 34, cy), (cx, cy + m - 34), (cx - m + 34, cy)], fill=cream)
            d.polygon([(cx, cy - 12), (cx + 12, cy), (cx, cy + 12), (cx - 12, cy)], fill=col)
            for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                px, py = (cx + dx * (m - 22), cy + dy * (m - 22))
                d.ellipse((px - 7, py - 7, px + 7, py + 7), fill=col)
                d.ellipse((px - 3, py - 3, px + 3, py + 3), fill=cream)
    arr = np.asarray(img, np.float32)
    glaze = nz(5, 79, 4)[..., None]
    arr *= 0.88 + 0.22 * glaze
    arr = grain_overlay(arr, 80, 0.12)
    out = to_img(arr)
    out = cracks(out, 5, 81, col=(110, 100, 84), length=(30, 80))
    save(out, 'tile.png')

def make_banner(name, field, trim, emblem):
    img = Image.new('RGB', (128, 256), field)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 127, 255), outline=trim, width=6)
    cx, cy = (64, 110)
    if emblem == 'anvil':
        d.ellipse((cx - 34, cy - 34, cx + 34, cy + 34), outline=trim, width=5)
        d.rectangle((cx - 24, cy - 10, cx + 24, cy + 2), fill=trim)
        d.polygon([(cx - 24, cy - 10), (cx - 40, cy - 6), (cx - 24, cy - 2)], fill=trim)
        d.rectangle((cx - 8, cy + 2, cx + 8, cy + 20), fill=trim)
        d.rectangle((cx - 20, cy + 20, cx + 20, cy + 28), fill=trim)
    elif emblem == 'bolt':
        d.polygon([(cx + 6, cy - 44), (cx - 22, cy + 4), (cx - 2, cy + 4), (cx - 10, cy + 46), (cx + 24, cy - 8), (cx + 4, cy - 8)], fill=trim)
    elif emblem == 'flame':
        d.polygon([(cx, cy - 46), (cx + 26, cy + 10), (cx + 10, cy + 38), (cx - 10, cy + 38), (cx - 26, cy + 10)], fill=trim)
        d.polygon([(cx, cy - 10), (cx + 12, cy + 18), (cx, cy + 32), (cx - 12, cy + 18)], fill=field)
    elif emblem == 'eagle':
        d.polygon([(cx, cy - 40), (cx + 40, cy - 10), (cx + 16, cy - 12), (cx + 10, cy + 40), (cx - 10, cy + 40), (cx - 16, cy - 12), (cx - 40, cy - 10)], fill=trim)
    for k in range(5):
        d.line((20 + k * 22, 250, 20 + k * 22, 256), fill=trim, width=3)
    grain = tileable_noise(128, 12, 71, 2).resize((128, 256))
    img = ImageChops.blend(img, ImageChops.multiply(img, Image.merge('RGB', [grain] * 3)), 0.28)
    save(img, name)

def radial(size, power):
    img = Image.new('L', (size, size))
    px = img.load()
    c = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            r = math.hypot(x - c, y - c) / c
            px[x, y] = int(255 * max(0.0, 1.0 - r) ** power)
    return img

def make_glow():
    a = radial(128, 2.2)
    img = Image.merge('RGBA', [Image.new('L', (128, 128), 255)] * 3 + [a])
    save(img, 'glow.png')

def make_smoke():
    a = radial(128, 1.1)
    n = tileable_noise(128, 4, 83, 3)
    a = ImageChops.multiply(a, n.point(lambda p: 140 + p // 2))
    a = a.point(lambda p: int(p * 0.9))
    img = Image.merge('RGBA', [Image.new('L', (128, 128), 255)] * 3 + [a])
    save(img, 'smoke.png')

def make_flame():
    size = 128
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    px = img.load()
    for y in range(size):
        t = y / (size - 1)
        half = math.sin(min(1.0, t * 1.15) * math.pi * 0.62) * 0.46 * size
        for x in range(size):
            dx = abs(x - size / 2)
            if dx < half:
                edge = 1.0 - dx / max(half, 1)
                heat = edge ** 0.7 * (0.35 + 0.65 * t)
                r = 255
                g = int(110 + 145 * heat)
                b = int(30 + 190 * heat ** 2.2)
                a = int(255 * min(1.0, edge * 1.6) * (0.25 + 0.75 * t ** 0.6))
                px[x, y] = (r, g, b, a)
    img = img.filter(ImageFilter.GaussianBlur(1.6))
    save(img, 'flame.png')

def make_moon():
    s = 256
    img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    glow = radial(s, 1.6)
    img.paste(Image.new('RGBA', (s, s), (200, 215, 255, 255)), (0, 0), glow.point(lambda p: int(p * 0.5)))
    d.ellipse((s // 2 - 56, s // 2 - 56, s // 2 + 56, s // 2 + 56), fill=(238, 240, 226, 255))
    for _ in range(12):
        x, y, r = (random.randint(88, 168), random.randint(88, 168), random.randint(4, 12))
        if math.hypot(x - 128, y - 128) < 46:
            d.ellipse((x - r, y - r, x + r, y + r), fill=(212, 214, 200, 255))
    save(img, 'moon.png')

def make_sky(name, stops):
    img = Image.new('RGB', (4, 256))
    px = img.load()
    for y in range(256):
        t = 1.0 - y / 255.0
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t0 <= t <= t1:
                k = (t - t0) / max(1e-06, t1 - t0)
                col = tuple((int(c0[j] + (c1[j] - c0[j]) * k) for j in range(3)))
                break
        else:
            col = stops[-1][1]
        for x in range(4):
            px[x, y] = col
    save(img, name)

def make_soft_circle():
    a = radial(64, 0.5).point(lambda p: min(255, int(p * 1.6)))
    img = Image.merge('RGBA', [Image.new('L', (64, 64), 0)] * 3 + [a])
    save(img, 'shadow.png')

def make_cone():
    S = 256
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    px = img.load()
    for y in range(S):
        t = 1.0 - y / (S - 1.0)
        half = 0.02 + 0.48 * t
        for x in range(S):
            u = abs((x + 0.5) / S - 0.5)
            if u < half:
                edge = 1.0 - (u / half) ** 3
                a = (1.0 - t) ** 0.8 * edge * 0.95
                px[x, y] = (255, 255, 255, int(255 * max(0.0, min(1.0, a))))
    save(img, 'cone.png')

def make_shaft():
    W, H = (64, 256)
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    px = img.load()
    for y in range(H):
        t = y / (H - 1.0)
        v = math.sin(math.pi * t) ** 0.7
        for x in range(W):
            u = abs((x + 0.5) / W - 0.5) * 2.0
            a = max(0.0, 1.0 - u ** 1.6) * v
            px[x, y] = (255, 255, 255, int(255 * a))
    save(img, 'shaft.png')

def make_ring():
    S = 256
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    px = img.load()
    c = (S - 1) / 2.0
    for y in range(S):
        for x in range(S):
            d = math.hypot(x - c, y - c) / c
            a = max(0.0, 1.0 - abs(d - 0.86) / 0.1)
            a2 = max(0.0, 1.0 - abs(d - 0.74) / 0.04) * 0.5
            px[x, y] = (255, 255, 255, int(255 * min(1.0, a + a2)))
    save(img, 'ring.png')

def make_star():
    S = 128
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    px = img.load()
    c = (S - 1) / 2.0
    for y in range(S):
        for x in range(S):
            dx, dy = (abs(x - c) / c, abs(y - c) / c)
            a = max(0.0, 1.0 - (dx * 6.0 + dy * 0.9)) if dx < dy else max(0.0, 1.0 - (dy * 6.0 + dx * 0.9))
            a = max(a, max(0.0, 1.0 - math.hypot(dx, dy) * 3.0) * 0.8)
            px[x, y] = (255, 255, 255, int(255 * min(1.0, a)))
    save(img, 'star.png')

def make_leaves():
    S = 256
    rnd = random.Random(21)
    img = Image.new('RGB', (S, S), (22, 40, 24))
    d = ImageDraw.Draw(img)
    greens = [(34, 66, 36), (44, 82, 42), (56, 98, 46), (70, 112, 52), (84, 124, 58), (96, 132, 60)]
    for layer in range(3):
        for _ in range(430):
            cx, cy = (rnd.uniform(0, S), rnd.uniform(0, S))
            ln, wd = (rnd.uniform(9, 17), rnd.uniform(3.2, 5.6))
            ang = rnd.uniform(0, math.pi)
            base = greens[min(len(greens) - 1, max(0, int(rnd.gauss(1.5 + layer * 1.4, 1.1))))]
            col = tuple((int(c * rnd.uniform(0.88, 1.1)) for c in base))
            ca, sa = (math.cos(ang), math.sin(ang))
            pts = []
            for t in range(9):
                u = t / 8.0
                x = (u - 0.5) * ln
                y = math.sin(math.pi * u) * wd * 0.5
                pts.append((x, y))
            pts += [(x, -y) for x, y in reversed(pts[1:-1])]
            for ox in (-S, 0, S):
                for oy in (-S, 0, S):
                    poly = [(cx + ox + x * ca - y * sa, cy + oy + x * sa + y * ca) for x, y in pts]
                    d.polygon(poly, fill=col)
                    d.line([poly[0], poly[8]], fill=tuple((int(c * 0.7) for c in col)), width=1)
    img = img.filter(ImageFilter.SMOOTH)
    save(img, 'leaves.png')

def make_planet(name, c1, c2, bands=7, ring=None, seed=1, radius=None, light=(-0.55, 0.5, 0.67), spots=False):
    import numpy as np
    N = 256
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    cx = cy = (N - 1) / 2.0
    R = radius or (62 if ring else 100)
    dx, dy = ((xx - cx) / R, (yy - cy) / R)
    r2 = dx * dx + dy * dy
    inside = r2 <= 1.0
    nz = np.sqrt(np.clip(1.0 - r2, 0.0, 1.0))
    L = np.array(light, np.float32)
    L = L / np.linalg.norm(L)
    lam = np.clip(dx * L[0] + -dy * L[1] + nz * L[2], 0.0, 1.0)
    rnd = np.random.RandomState(seed)
    small = rnd.rand(16, 16).astype(np.float32)
    big = np.array(Image.fromarray((small * 255).astype(np.uint8)).resize((N, N), Image.BICUBIC), np.float32) / 255.0
    if spots:
        pat = big
    else:
        pat = 0.5 + 0.5 * np.sin(dy * bands * math.pi + big * 3.2)
    col = np.zeros((N, N, 3), np.float32)
    for k in range(3):
        col[..., k] = c1[k] * (1.0 - pat) + c2[k] * pat
    shade_ = (0.1 + 0.9 * lam ** 0.85) * (0.55 + 0.45 * nz ** 0.5)
    col *= shade_[..., None]
    rim = (1.0 - nz) ** 3 * lam
    col += rim[..., None] * np.array([70, 90, 150], np.float32) * 0.5
    edge = np.clip((1.0 - np.sqrt(r2)) * R / 1.6, 0.0, 1.0)
    a_planet = np.where(inside, edge, 0.0)
    out = np.zeros((N, N, 4), np.float32)
    out[..., :3] = col
    out[..., 3] = a_planet * 255.0
    if ring:
        tilt = math.radians(-20)
        ct, st = (math.cos(tilt), math.sin(tilt))
        px, py = (xx - cx, yy - cy)
        u = px * ct + py * st
        v = -px * st + py * ct
        A, Bm = (R * 1.95, R * 0.5)
        e = np.sqrt((u / A) ** 2 + (v / Bm) ** 2)
        inner = 0.62
        ring_a = np.where((e > inner) & (e < 1.0), 1.0, 0.0)
        ring_a *= np.clip((e - inner) * 40, 0, 1) * np.clip((1.0 - e) * 40, 0, 1)
        gap = 0.5 + 0.5 * np.sin(e * 62.0 + big * 2.0)
        ring_a *= (0.35 + 0.55 * gap) * (e < 0.86) + (0.2 + 0.25 * gap) * (e >= 0.86) * 0.9
        ring_col = np.array([226, 206, 166], np.float32) * (0.45 + 0.55 * (0.5 + 0.5 * np.clip(-px / R * L[0] * 0.3 + 0.7, 0, 1)))[..., None]
        front = v > 0
        behind_ok = ~inside | front
        ra = ring_a * behind_ok * 235.0
        base_a = out[..., 3]
        new_a = ra + base_a * (1.0 - ra / 255.0)
        wr = np.where(new_a > 0, ra / np.maximum(new_a, 0.001), 0.0)
        out[..., :3] = out[..., :3] * (1.0 - wr[..., None]) + ring_col * wr[..., None]
        out[..., 3] = new_a
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA')
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    save(img, name)
if __name__ == '__main__':
    print('Generating textures into', OUT)
    make_sand()
    make_dirt()
    make_ash()
    make_rock()
    make_stone()
    make_stone_dark()
    make_mudbrick()
    make_plaster()
    make_wood()
    make_rug()
    make_tile()
    make_leaves()
    make_banner('banner_iron.png', (44, 58, 84), (190, 196, 210), 'anvil')
    make_banner('banner_thunder.png', (62, 34, 92), (232, 200, 80), 'bolt')
    make_banner('banner_fire.png', (110, 30, 20), (240, 150, 40), 'flame')
    make_banner('banner_roman.png', (128, 24, 28), (230, 190, 70), 'eagle')
    make_cone()
    make_shaft()
    make_ring()
    make_star()
    make_glow()
    make_smoke()
    make_flame()
    make_moon()
    make_soft_circle()
    make_sky('sky_dusk.png', [(0.0, (255, 150, 70)), (0.18, (232, 110, 90)), (0.45, (120, 70, 130)), (1.0, (28, 34, 82))])
    make_sky('sky_night.png', [(0.0, (46, 70, 104)), (0.25, (22, 34, 68)), (0.6, (8, 12, 30)), (1.0, (3, 5, 14))])
    make_sky('sky_dawn.png', [(0.0, (255, 196, 128)), (0.2, (240, 150, 120)), (0.5, (150, 120, 150)), (1.0, (50, 66, 112))])
    make_sky('sky_smoke.png', [(0.0, (112, 52, 28)), (0.07, (66, 38, 36)), (0.2, (34, 30, 44)), (0.5, (16, 18, 32)), (1.0, (6, 8, 18))])
    make_planet('planet_ringed.png', (196, 150, 92), (240, 214, 160), bands=7, ring=True, seed=3)
    make_planet('planet_red.png', (118, 40, 28), (214, 98, 58), seed=11, spots=True, radius=96)
    make_planet('planet_blue.png', (40, 70, 130), (140, 190, 235), bands=3, seed=5, radius=96)
    print('done.')
