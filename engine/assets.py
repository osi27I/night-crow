from pathlib import Path
from ursina import Texture
ROOT = Path(__file__).resolve().parent.parent
TEXTURE_DIR = ROOT / 'assets' / 'textures'
SOUND_DIR = ROOT / 'assets' / 'sounds'
MUSIC_DIR = ROOT / 'assets' / 'music'
FONT_DIR = ROOT / 'assets' / 'fonts'
FONT = 'DejaVuSerif.ttf'
FONT_BOLD = 'DejaVuSerif-Bold.ttf'
_cache = {}

def tex(name, filtering='mipmap'):
    key = (name, filtering)
    if key in _cache:
        return _cache[key]
    path = TEXTURE_DIR / f'{name}.png'
    texture = Texture(path, filtering=filtering) if path.is_file() else None
    if texture is None:
        print(f'[assets] missing texture: {path}')
    _cache[key] = texture
    return texture

def sound_path(name):
    for folder in (SOUND_DIR, MUSIC_DIR):
        for ext in ('.wav', '.ogg', '.mp3'):
            p = folder / f'{name}{ext}'
            if p.is_file():
                return p
    return None
