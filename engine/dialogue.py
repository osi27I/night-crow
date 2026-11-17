import textwrap
from ursina import Entity, Text, camera, color
from engine.assets import FONT, FONT_BOLD
from engine.timing import Clock
SPEAKER_COLORS = {'': (0.78, 0.76, 0.72), 'Abdo': (0.98, 0.72, 0.36), 'Khaled': (0.52, 0.72, 1.0), 'Sheikh Harith': (0.78, 0.55, 0.98), 'Qais': (0.95, 0.5, 0.5), 'Zainab': (0.95, 0.6, 0.78), 'Guard': (0.8, 0.8, 0.85), 'Servant': (0.8, 0.8, 0.85), 'Assassin': (0.7, 0.75, 0.8), 'Night Crow': (0.75, 0.8, 0.95), 'Centurion': (0.95, 0.45, 0.4), 'Soldier': (0.8, 0.8, 0.85), 'Varro': (0.95, 0.45, 0.4), 'Legionary': (0.8, 0.8, 0.85), 'Sentry A': (0.8, 0.8, 0.85), 'Sentry B': (0.8, 0.8, 0.85), 'Messenger': (0.7, 0.85, 0.7), 'Elder Jabir': (0.82, 0.82, 0.62), 'Wife': (0.95, 0.6, 0.78), 'Sentry': (0.8, 0.7, 0.95), 'Mother': (0.9, 0.78, 0.6), 'Father': (0.9, 0.78, 0.6), 'Idris': (0.86, 0.8, 0.62), 'Nadia': (0.92, 0.66, 0.74), 'Harun': (0.86, 0.8, 0.62), 'Salim': (0.78, 0.82, 0.66), 'Samir': (0.7, 0.86, 0.74), 'Hajar': (0.8, 0.76, 0.9)}
WRAP = 88

class Dialogue:

    def __init__(self):
        ui = camera.ui
        self.bg = Entity(parent=ui, model='quad', color=color.rgba(0.03, 0.025, 0.05, 0.84), scale=(1.52, 0.205), position=(0, -0.335), z=-0.4, enabled=False, add_to_scene_entities=False)
        self.edge = Entity(parent=ui, model='quad', color=color.rgba(0.88, 0.7, 0.3, 0.9), scale=(1.52, 0.004), position=(0, -0.2325), z=-0.45, enabled=False, add_to_scene_entities=False)
        self.name = Text(text='', parent=ui, position=(-0.725, -0.255), origin=(-0.5, 0.5), scale=1.2, font=FONT_BOLD, z=-0.5, enabled=False, add_to_scene_entities=False)
        self.body = Text(text='', parent=ui, position=(-0.725, -0.292), origin=(-0.5, 0.5), scale=1.12, font=FONT, color=color.rgba(0.96, 0.94, 0.9, 1), z=-0.5, enabled=False, add_to_scene_entities=False)
        self.hint = Text(text='SPACE  ▼', parent=ui, position=(0.725, -0.428), origin=(0.5, -0.5), scale=0.8, font=FONT, color=color.rgba(0.88, 0.7, 0.3, 0.9), z=-0.5, enabled=False, add_to_scene_entities=False)
        self.active = False
        self.lines = []
        self.index = -1
        self.full = ''
        self.shown = 0.0
        self.typing = False
        self.auto = None
        self.auto_timer = 0.0
        self.on_done = None
        self.on_line = None
        self.on_type = None
        self.mode = 'talk'
        self.options = []
        self.on_pick = None
        self._last_n = -1
        self._blink = 0.0

    def start(self, lines, on_done=None, on_line=None):
        self.lines = list(lines)
        self.on_done = on_done
        self.on_line = on_line
        self.index = -1
        self.mode = 'talk'
        self._layout(False)
        self._show(True)
        self._next()

    def _layout(self, tall):
        dy = 0.075 if tall else 0.0
        self.bg.scale_y = 0.205 + dy
        self.bg.y = -0.335 + dy / 2.0
        self.edge.y = -0.2325 + dy
        self.name.y = -0.255 + dy
        self.body.y = -0.292 + dy

    def say(self, speaker, text, auto=None, on_done=None):
        self.start([(speaker, text, auto) if auto else (speaker, text)], on_done)

    def ask(self, speaker, question, options, on_pick):
        self.mode = 'choice'
        self.options = list(options)
        self.on_pick = on_pick
        self.lines = []
        self._layout(True)
        self._show(True)
        self._set_speaker(speaker)
        rows = [textwrap.fill(question, WRAP)] + [''] + [f'[{i + 1}]  {o}' for i, o in enumerate(options)]
        self.full = '\n'.join(rows)
        self.body.text = self.full
        self.typing = False
        self.hint.enabled = False

    def advance(self):
        if not self.active or self.mode == 'choice':
            return
        if self.typing:
            self.shown = len(self.full)
            self._refresh_text(force=True)
            self.typing = False
            return
        self._next()

    def pick(self, i):
        if self.active and self.mode == 'choice' and (0 <= i < len(self.options)):
            cb = self.on_pick
            self._show(False)
            self.mode = 'talk'
            if cb:
                cb(i)

    def close(self):
        self._show(False)

    def _show(self, on):
        self.active = on
        for e in (self.bg, self.edge, self.name, self.body, self.hint):
            e.enabled = on

    def _set_speaker(self, speaker):
        self.name.text = speaker.upper() if speaker else ''
        c = SPEAKER_COLORS.get(speaker, (0.85, 0.85, 0.9))
        self.name.color = color.rgba(c[0], c[1], c[2], 1)
        body_c = (0.8, 0.78, 0.74) if not speaker else (0.96, 0.94, 0.9)
        self.body.color = color.rgba(body_c[0], body_c[1], body_c[2], 1)

    def _next(self):
        self.index += 1
        if self.index >= len(self.lines):
            self._show(False)
            cb = self.on_done
            self.on_done = None
            if cb:
                cb()
            return
        line = self.lines[self.index]
        speaker, text = (line[0], line[1])
        self.auto = line[2] if len(line) > 2 else None
        self.auto_timer = 0.0
        self._set_speaker(speaker)
        self.full = textwrap.fill(text, WRAP)
        if not speaker:
            self.full = self.full
        self.shown = 0.0
        self.typing = True
        self._last_n = -1
        self.body.text = ''
        self.hint.enabled = self.auto is None
        if self.on_line:
            self.on_line(self.index, line)

    def _refresh_text(self, force=False):
        n = int(self.shown)
        if n != self._last_n or force:
            self._last_n = n
            self.body.text = self.full[:n]
            if self.on_type and n % 3 == 0 and (n > 0):
                self.on_type()

    def update(self):
        if not self.active:
            return
        dt = Clock.raw_dt
        if self.mode == 'talk':
            if self.typing:
                self.shown += dt * 52.0
                if self.shown >= len(self.full):
                    self.shown = len(self.full)
                    self.typing = False
                self._refresh_text()
            elif self.auto is not None:
                self.auto_timer += dt
                if self.auto_timer >= self.auto:
                    self._next()
            self._blink += dt
            if self.hint.enabled:
                self.hint.alpha = 0.45 + 0.55 * (0.5 + 0.5 * __import__('math').sin(self._blink * 5))
