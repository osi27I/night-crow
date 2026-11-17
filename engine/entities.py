from panda3d.core import NodePath
from ursina import Entity, Vec3, color
from engine.shaders import lit_shader
_model_cache = {}

def rgb(r, g, b, a=255):
    return color.rgba32(r, g, b, a)

def shade(c, k):
    return color.rgba(min(1, c.r * k), min(1, c.g * k), min(1, c.b * k), c.a)
_pristine_models = []

def prewarm_models():
    from ursina.mesh_importer import load_model
    for name in ('cube', 'plane', 'quad', 'circle', 'diamond', 'sphere', 'icosphere', 'arrow'):
        try:
            _pristine_models.append(load_model(name))
        except Exception:
            pass

def _fresh_copy(base):
    return base.copy_to(NodePath('model_copy'))

def _build_sphere(lon, lat):
    import math
    from ursina import Mesh
    verts, uvs, norms, tris = ([], [], [], [])
    for j in range(lat + 1):
        v = j / lat
        phi = v * math.pi
        for i in range(lon + 1):
            u = i / lon
            th = u * 2.0 * math.pi
            nx, ny, nz = (math.sin(phi) * math.cos(th), math.cos(phi), math.sin(phi) * math.sin(th))
            verts.append((nx * 0.5, ny * 0.5, nz * 0.5))
            norms.append((nx, ny, nz))
            uvs.append((u, 1.0 - v))
    row = lon + 1
    for j in range(lat):
        for i in range(lon):
            a, b, c, d = (j * row + i, j * row + i + 1, (j + 1) * row + i, (j + 1) * row + i + 1)
            tris.extend([(a, c, b), (b, c, d)])
    return Mesh(vertices=verts, triangles=tris, uvs=uvs, normals=norms, mode='triangle')

def sphere_model(quality=None):
    q = quality or SPHERE_DETAIL
    key = ('sph', q)
    if key not in _model_cache:
        lon, lat = q
        base = _build_sphere(lon, lat)
        _model_cache[key] = base
    return _fresh_copy(_model_cache[key])
SPHERE_DETAIL = (14, 9)

def _build_cylinder(res):
    import math
    from ursina import Mesh
    verts, uvs, norms, tris = ([], [], [], [])
    for i in range(res + 1):
        th = 2.0 * math.pi * i / res
        c, s_ = (math.cos(th), math.sin(th))
        verts.append((c * 0.5, 1.0, s_ * 0.5))
        norms.append((c, 0, s_))
        uvs.append((i / res, 1.0))
        verts.append((c * 0.5, 0.0, s_ * 0.5))
        norms.append((c, 0, s_))
        uvs.append((i / res, 0.0))
    for i in range(res):
        tl, bl, tr, br = (2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 3)
        tris.extend([(tl, bl, tr), (tr, bl, br)])
    for y, ny in ((1.0, 1.0), (0.0, -1.0)):
        centre = len(verts)
        verts.append((0.0, y, 0.0))
        norms.append((0, ny, 0))
        uvs.append((0.5, 0.5))
        ring = len(verts)
        for i in range(res + 1):
            th = 2.0 * math.pi * i / res
            verts.append((math.cos(th) * 0.5, y, math.sin(th) * 0.5))
            norms.append((0, ny, 0))
            uvs.append((0.5 + math.cos(th) * 0.5, 0.5 + math.sin(th) * 0.5))
        for i in range(res):
            if ny > 0:
                tris.append((centre, ring + i, ring + i + 1))
            else:
                tris.append((centre, ring + i + 1, ring + i))
    return Mesh(vertices=verts, triangles=tris, uvs=uvs, normals=norms, mode='triangle')

def _build_cone(res):
    import math
    from ursina import Mesh
    verts, uvs, norms, tris = ([], [], [], [])
    for i in range(res):
        t0, t1 = (2.0 * math.pi * i / res, 2.0 * math.pi * (i + 1) / res)
        tm = (t0 + t1) / 2.0
        a = len(verts)
        nl = math.hypot(1.0, 0.5)
        for th, y, r in ((tm, 0.5, 0.0), (t0, -0.5, 0.5), (t1, -0.5, 0.5)):
            verts.append((math.cos(th) * r, y, math.sin(th) * r))
            norms.append((math.cos(th) / nl * 1.0, 0.5 / nl, math.sin(th) / nl * 1.0))
        uvs.extend([(0.5, 1.0), (i / res, 0.0), ((i + 1) / res, 0.0)])
        tris.append((a, a + 1, a + 2))
    centre = len(verts)
    verts.append((0.0, -0.5, 0.0))
    norms.append((0, -1, 0))
    uvs.append((0.5, 0.5))
    ring = len(verts)
    for i in range(res + 1):
        th = 2.0 * math.pi * i / res
        verts.append((math.cos(th) * 0.5, -0.5, math.sin(th) * 0.5))
        norms.append((0, -1, 0))
        uvs.append((0.5 + math.cos(th) * 0.5, 0.5 + math.sin(th) * 0.5))
    for i in range(res):
        tris.append((centre, ring + i + 1, ring + i))
    return Mesh(vertices=verts, triangles=tris, uvs=uvs, normals=norms, mode='triangle')

def _build_torus(ratio, seg_u=18, seg_v=8):
    import math
    from ursina import Mesh
    rt = 0.5 * ratio
    R = 0.5 - rt
    verts, uvs, norms, tris = ([], [], [], [])
    for iu in range(seg_u + 1):
        th = 2.0 * math.pi * iu / seg_u
        for iv in range(seg_v + 1):
            ph = 2.0 * math.pi * iv / seg_v
            cx, sx = (math.cos(th), math.sin(th))
            cp, sp = (math.cos(ph), math.sin(ph))
            verts.append(((R + rt * cp) * cx, rt * sp, (R + rt * cp) * sx))
            norms.append((cp * cx, sp, cp * sx))
            uvs.append((iu / seg_u, iv / seg_v))
    row = seg_v + 1
    for iu in range(seg_u):
        for iv in range(seg_v):
            a, b = (iu * row + iv, iu * row + iv + 1)
            c, d = ((iu + 1) * row + iv, (iu + 1) * row + iv + 1)
            tris.extend([(a, c, b), (b, c, d)])
    return Mesh(vertices=verts, triangles=tris, uvs=uvs, normals=norms, mode='triangle')

def _build_blade():
    from ursina import Mesh
    outline = [(-0.3, 0.0), (0.3, 0.0), (0.5, 0.45), (0.0, 1.0), (-0.5, 0.45)]
    verts, norms, uvs, tris = ([], [], [], [])
    for ny in (1.0, -1.0):
        base = len(verts)
        for x, z in outline:
            verts.append((x, 0.0, z))
            norms.append((0, ny, 0))
            uvs.append((x + 0.5, z))
        for a, b, c in ((0, 2, 1), (0, 4, 2), (4, 3, 2)):
            tris.append((base + a, base + c, base + b) if ny > 0 else (base + a, base + b, base + c))
    return Mesh(vertices=verts, triangles=tris, uvs=uvs, normals=norms, mode='triangle')

def blade_model():
    key = ('blade',)
    if key not in _model_cache:
        _model_cache[key] = _build_blade()
    return _fresh_copy(_model_cache[key])

def torus_model(ratio=0.22):
    key = ('torus', ratio)
    if key not in _model_cache:
        _model_cache[key] = _build_torus(ratio)
    return _fresh_copy(_model_cache[key])

def cylinder_model(res=12):
    key = ('cyl', res)
    if key not in _model_cache:
        _model_cache[key] = _build_cylinder(res)
    return _fresh_copy(_model_cache[key])

def cone_model(res=12):
    key = ('cone', res)
    if key not in _model_cache:
        _model_cache[key] = _build_cone(res)
    return _fresh_copy(_model_cache[key])

def mk(parent=None, model='cube', pos=(0, 0, 0), scale=1, col=None, texture=None, tex_scale=None, emissive=0.0, rot=(0, 0, 0), origin=None, double_sided=False, **kw):
    if model == 'sphere':
        try:
            big = max(scale) if isinstance(scale, (tuple, list)) else float(scale)
        except Exception:
            big = 1.0
        model = sphere_model((8, 5) if big < 0.2 else (11, 7) if big < 0.5 else None)
    elif model == 'cylinder':
        model = cylinder_model()
    elif model == 'torus':
        model = torus_model()
    elif model == 'cone':
        model = cone_model()
        if origin is None:
            origin = (0, -0.5, 0)
    e = Entity(parent=parent, model=model, position=pos, scale=scale, color=col if col is not None else color.white, texture=texture, rotation=rot, shader=lit_shader, double_sided=double_sided, add_to_scene_entities=False, **kw)
    if tex_scale is not None:
        e.texture_scale = tex_scale
    if emissive:
        e.set_shader_input('emissive', float(emissive))
    if origin is not None:
        e.origin = origin
    return e

def glow_quad(parent, pos, size, col, texture, billboard=True, add=True, bin_sort=45):
    from panda3d.core import ColorBlendAttrib, TransparencyAttrib
    if isinstance(col, (tuple, list)):
        col = color.rgba(*col)
    e = Entity(parent=parent, model='quad', position=pos, scale=size, color=col, texture=texture, billboard=billboard, add_to_scene_entities=False)
    e.setLightOff()
    e.setDepthWrite(False)
    e.setBin('fixed', bin_sort)
    if add:
        e.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha, ColorBlendAttrib.OOne))
    else:
        e.setTransparency(TransparencyAttrib.MAlpha)
    return e
