import importlib
import traceback
LOAD_ERRORS = {}
_REGISTRY = [('menu', 'MenuScene'), ('scene1_meal', 'Scene1Meal'), ('scene2_palace', 'Scene2Palace'), ('scene3_fall', 'Scene3Fall'), ('scene4_crow', 'Scene4Crow'), ('scene4b_city', 'Scene4bCity'), ('scene5_finale', 'Scene5Finale')]

def _load(index, module, cls):
    try:
        return getattr(importlib.import_module(f'scenes.{module}'), cls)
    except ModuleNotFoundError as exc:
        if exc.name == f'scenes.{module}':
            LOAD_ERRORS[index] = 'file not written yet'
            return None
        LOAD_ERRORS[index] = repr(exc)
        traceback.print_exc()
        return None
    except Exception as exc:
        LOAD_ERRORS[index] = repr(exc)
        print(f'[scenes] could not import scenes/{module}.py')
        traceback.print_exc()
        return None
SCENES = [_load(i, m, c) for i, (m, c) in enumerate(_REGISTRY)]
if SCENES[0] is None:
    raise RuntimeError('scenes/menu.py failed to load: ' + LOAD_ERRORS.get(0, '?'))
