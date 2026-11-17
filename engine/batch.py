import gc
from collections import defaultdict
from panda3d.core import NodePath, ShaderAttrib
from ursina import Entity
from engine.shaders import lit_shader

class Baked(Entity):

    def __init__(self, parent, name='baked', **kw):
        super().__init__(parent=parent, add_to_scene_entities=False, **kw)
        self.name = name

    @property
    def color(self):
        return getattr(self, '_color', (1, 1, 1, 1))

    @color.setter
    def color(self, value):
        self._color = value
        self.setColorScale(value[0], value[1], value[2], value[3])

def _walk(root):
    out, stack = ([], [root])
    while stack:
        p = stack.pop()
        for k in list(p._children):
            if k:
                out.append(k)
                stack.append(k)
    return out

def _held_ids(root, ents):
    if not ents:
        return set()
    ids = {id(e) for e in ents}
    child_lists = {id(e._children) for e in ents}
    child_lists.add(id(root._children))
    held = set()
    for o in gc.get_referrers(*ents):
        if o is ents or o is ids or o is child_lists or (o is held):
            continue
        if type(o) is tuple and len(o) == len(ents):
            continue
        if id(o) in child_lists:
            continue
        if type(o) is dict:
            is_entity_dict = '_children' in o
            for key, v in o.items():
                if id(v) not in ids:
                    continue
                if key == 'Entity':
                    continue
                if key == '_parent' and is_entity_dict:
                    continue
                held.add(id(v))
            continue
        for r in gc.get_referents(o):
            if id(r) in ids:
                held.add(id(r))
    return held

def _has_effects(e):
    try:
        return e.getEffects().getNumEffects() > 0
    except Exception:
        return True

def _node_ok(e):
    if type(e) is not Entity:
        return False
    if not e.enabled or e.isHidden():
        return False
    if getattr(e, 'collider', None) is not None:
        return False
    if _has_effects(e):
        return False
    if e.model is not None and e.shader is not lit_shader:
        return False
    return True

def _subtree_free(e, held):
    if id(e) in held or not _node_ok(e):
        return False
    for k in e._children:
        if k and (not _subtree_free(k, held)):
            return False
    return True

def _detach(items):
    for e in items:
        p = getattr(e, '_parent', None)
        if p is not None and hasattr(p, '_children') and (e in p._children):
            p._children.remove(e)

def _lift_geoms(grp):
    found = grp.findAllMatches('**/+GeomNode')
    for i in range(found.getNumPaths()):
        gn = found.getPath(i)
        p = gn.getParent()
        clean = True
        while p != grp and (not p.isEmpty()):
            n = p.node()
            if not n.getState().isEmpty() or not n.getEffects().isEmpty():
                clean = False
                break
            p = p.getParent()
        if clean and gn.getParent() != grp:
            gn.wrtReparentTo(grp)
    for i in range(grp.getNumChildren() - 1, -1, -1):
        c = grp.getChild(i)
        if not c.node().isGeomNode() and c.getNumChildren() == 0:
            c.removeNode()

def merge_into(parent, items, name='welded'):
    grp = NodePath(name)
    grp.reparentTo(parent)
    for e in items:
        e.wrtReparentTo(grp)
    _detach(items)
    grp.flattenStrong()
    _lift_geoms(grp)
    grp.flattenStrong()
    return grp

def bake(parent, entities, name='baked'):
    entities = [e for e in entities if e]
    node = Baked(parent, name)
    for e in entities:
        e.wrtReparentTo(node)
    _detach(entities)
    node.flattenStrong()
    _lift_geoms(node)
    node.flattenStrong()
    return node
_JUNK_INPUTS = ('texture_scale', 'texture_offset', 'fog_color', 'fog_density', 'tileset_size', 'texture_rotation')

def strip_default_inputs(root):
    n = 0
    for e in _walk(root):
        if type(e) is not Entity:
            continue
        if e.model is None:
            if e.getAttrib(ShaderAttrib) is not None:
                e.clearAttrib(ShaderAttrib.getClassType())
                n += 1
            continue
        if e.shader is not lit_shader:
            continue
        sa = e.getAttrib(ShaderAttrib)
        if sa is None:
            continue
        for name in _JUNK_INPUTS:
            if sa.hasShaderInput(name):
                e.clearShaderInput(name)
                n += 1
    return n

def batch_scene(scene, cell=14.0, min_items=3):
    root = scene.root
    strip_default_inputs(root)
    held = _held_ids(root, _walk(root))
    stats = {'merged': 0, 'groups': 0}

    def visit(parent, is_root):
        free = [k for k in list(parent._children) if k and _subtree_free(k, held)]
        free_ids = {id(k) for k in free}
        for k in list(parent._children):
            if k and id(k) not in free_ids:
                visit(k, False)
        if is_root:
            chunks = defaultdict(list)
            for k in free:
                p = k.getPos(root)
                chunks[int(p.x // cell), int(p.z // cell)].append(k)
            for (cx, cz), items in chunks.items():
                if len(items) >= min_items:
                    merge_into(parent, items, f'chunk_{cx}_{cz}')
                    stats['merged'] += len(items)
                    stats['groups'] += 1
        elif len(free) >= min_items:
            merge_into(parent, free, 'welded')
            stats['merged'] += len(free)
            stats['groups'] += 1
    visit(root, True)
    return stats
