from ursina import Entity, Text, camera, color
from engine.assets import FONT, FONT_BOLD
from engine.timing import Clock, Timeline, ease_out
GOLD = (0.93, 0.76, 0.34)
WHITE = (0.96, 0.94, 0.9)

def _c(rgb, a):
    return color.rgba(rgb[0], rgb[1], rgb[2], max(0.0, min(1.0, a)))

class HUD:
    BAR = 0.115

    def __init__(self):
        ui = camera.ui
        self.tl = Timeline()
        self.fade_a = 1.0
        self.letter_amt = 0.0
        self.obj_a = 0.0
        self.prompt_a = 0.0
        self.caption_a = 0.0
        self.title_a = 0.0
        self.sub_a = 0.0
        self.hint_a = 0.0
        self.detect_a = 0.0
        self.detect_value = 0.0
        self.fade_color = (0.0, 0.0, 0.0)
        self.bar_top = Entity(parent=ui, model='quad', color=color.black, scale=(2.4, self.BAR), z=-0.5, position=(0, 0.5 + self.BAR / 2), add_to_scene_entities=False)
        self.bar_bot = Entity(parent=ui, model='quad', color=color.black, scale=(2.4, self.BAR), z=-0.5, position=(0, -0.5 - self.BAR / 2), add_to_scene_entities=False)
        self.obj_head = Text(text='OBJECTIVE', parent=ui, position=(-0.84, 0.455), origin=(-0.5, 0.5), scale=0.8, font=FONT_BOLD, color=_c(GOLD, 0), z=-0.3, add_to_scene_entities=False)
        self.obj_text = Text(text='', parent=ui, position=(-0.84, 0.425), origin=(-0.5, 0.5), scale=1.15, font=FONT, color=_c(WHITE, 0), z=-0.3, add_to_scene_entities=False)
        self.prompt_bg = Entity(parent=ui, model='quad', color=_c((0, 0, 0), 0), scale=(0.5, 0.062), position=(0, -0.285), z=-0.3, add_to_scene_entities=False)
        self.prompt_text = Text(text='', parent=ui, position=(0, -0.285), origin=(0, 0), scale=1.2, font=FONT_BOLD, color=_c(WHITE, 0), z=-0.35, add_to_scene_entities=False)
        self.caption_text = Text(text='', parent=ui, position=(0, 0.04), origin=(0, 0), scale=2.0, font=FONT, color=_c(WHITE, 0), z=-0.3, add_to_scene_entities=False)
        self.title_small = Text(text='', parent=ui, position=(0, 0.11), origin=(0, 0), scale=1.2, font=FONT_BOLD, color=_c(GOLD, 0), z=-0.3, add_to_scene_entities=False)
        self.title_text = Text(text='', parent=ui, position=(0, 0.035), origin=(0, 0), scale=4.2, font=FONT_BOLD, color=_c(WHITE, 0), z=-0.3, add_to_scene_entities=False)
        self.title_sub = Text(text='', parent=ui, position=(0, -0.06), origin=(0, 0), scale=1.15, font=FONT, color=_c((0.8, 0.78, 0.74), 0), z=-0.3, add_to_scene_entities=False)
        self.hint_text = Text(text='', parent=ui, position=(-0.86, -0.45), origin=(-0.5, -0.5), scale=0.9, font=FONT, color=_c((0.85, 0.85, 0.85), 0), z=-0.3, add_to_scene_entities=False)
        self.detect_bg = Entity(parent=ui, model='quad', color=_c((0, 0, 0), 0), scale=(0.34, 0.022), position=(0, 0.43), z=-0.3, add_to_scene_entities=False)
        self.detect_fill = Entity(parent=ui, model='quad', color=_c((1, 0.8, 0.2), 0), scale=(0.001, 0.014), position=(-0.165, 0.43), origin=(-0.5, 0), z=-0.35, add_to_scene_entities=False)
        self.detect_label = Text(text='', parent=ui, position=(0, 0.46), origin=(0, 0), scale=0.85, font=FONT_BOLD, color=_c((1, 0.8, 0.5), 0), z=-0.3, add_to_scene_entities=False)
        self.fade = Entity(parent=ui, model='quad', color=_c((0, 0, 0), 1), scale=(3, 2), z=-0.9, add_to_scene_entities=False)
        self._objective = ''
        self._last = {}

    def fade_to(self, alpha, duration=0.8, on_done=None, color_rgb=(0, 0, 0)):
        self.fade_color = color_rgb
        self.tl.to(self, 'fade_a', alpha, duration, on_done=on_done)

    def black(self):
        self.fade_a = 1.0
        self.fade_color = (0, 0, 0)

    def letterbox(self, on=True, duration=0.8):
        self.tl.to(self, 'letter_amt', 1.0 if on else 0.0, duration)

    def objective(self, text, announce=True):
        if text is None:
            self.tl.to(self, 'obj_a', 0.0, 0.5)
            return

        def show():
            self._objective = text
            self.obj_text.text = text
            self.tl.to(self, 'obj_a', 1.0, 0.6)
        if self.obj_a > 0.05:
            self.tl.to(self, 'obj_a', 0.0, 0.25, on_done=show)
        else:
            show()

    def prompt(self, text):
        if text:
            if self.prompt_text.text != text:
                self.prompt_text.text = text
                self.prompt_bg.scale_x = 0.08 + 0.0235 * len(text)
            self.prompt_a = min(1.0, self.prompt_a + Clock.raw_dt * 8)
        else:
            self.prompt_a = max(0.0, self.prompt_a - Clock.raw_dt * 8)

    def caption(self, text, hold=2.6, fade=0.9, size=2.0, tone=WHITE):
        self.caption_text.text = text
        self.caption_text.scale = size
        self.caption_tone = tone
        self.caption_a = 0.0
        self.tl.to(self, 'caption_a', 1.0, fade)
        self.tl.after(fade + hold, lambda: self.tl.to(self, 'caption_a', 0.0, fade))
        return fade * 2 + hold
    caption_tone = WHITE

    def title_card(self, small, title, sub='', hold=3.0, fade=1.0):
        self.title_small.text = small
        self.title_text.text = title
        self.title_text.scale = min(4.2, 100.0 / max(1, len(title)))
        self.title_sub.text = sub
        self.title_a = 0.0
        self.sub_a = 0.0
        self.tl.to(self, 'title_a', 1.0, fade)
        self.tl.to(self, 'sub_a', 1.0, fade, delay=0.6)
        self.tl.after(fade + hold, lambda: (self.tl.to(self, 'title_a', 0.0, fade), self.tl.to(self, 'sub_a', 0.0, fade)))
        return fade * 2 + hold

    def hint(self, text, hold=7.0):
        import textwrap
        self.hint_text.text = '\n'.join(textwrap.wrap(text, 112, break_long_words=False)) if text and '\n' not in text else text
        self.tl.to(self, 'hint_a', 1.0, 0.6)
        if hold:
            self.tl.after(hold, lambda: self.tl.to(self, 'hint_a', 0.0, 1.0))

    def detection(self, value, label='NOTICED'):
        if value is None or value <= 0.01:
            self.detect_a = max(0.0, self.detect_a - Clock.raw_dt * 4)
        else:
            self.detect_a = min(1.0, self.detect_a + Clock.raw_dt * 6)
            self.detect_value = value
            self.detect_label.text = label

    def _set(self, ent, key, col):
        if self._last.get(id(ent)) != col:
            ent.color = col
            self._last[id(ent)] = col

    def update(self):
        dt = Clock.raw_dt
        self.tl.update(dt)
        self._set(self.fade, 'fade', _c(self.fade_color, self.fade_a))
        self.fade.enabled = self.fade_a > 0.002
        k = self.letter_amt
        self.bar_top.y = 0.5 + self.BAR / 2 - self.BAR * k
        self.bar_bot.y = -0.5 - self.BAR / 2 + self.BAR * k
        self._set(self.obj_head, 'oh', _c(GOLD, self.obj_a * 0.9))
        self._set(self.obj_text, 'ot', _c(WHITE, self.obj_a))
        self._set(self.prompt_bg, 'pb', _c((0, 0, 0), self.prompt_a * 0.6))
        self._set(self.prompt_text, 'pt', _c(WHITE, self.prompt_a))
        self._set(self.caption_text, 'c', _c(self.caption_tone, self.caption_a))
        self._set(self.title_small, 'ts', _c(GOLD, self.title_a))
        self._set(self.title_text, 'tt', _c(WHITE, self.title_a))
        self._set(self.title_sub, 'tsub', _c((0.8, 0.78, 0.74), self.sub_a))
        self._set(self.hint_text, 'h', _c((0.85, 0.85, 0.85), self.hint_a * 0.85))
        d = self.detect_value
        tint = (1.0, 0.85 - 0.65 * d, 0.25 - 0.1 * d)
        self._set(self.detect_bg, 'db', _c((0, 0, 0), self.detect_a * 0.6))
        self._set(self.detect_fill, 'df', _c(tint, self.detect_a))
        self.detect_fill.scale_x = max(0.001, 0.33 * d)
        self._set(self.detect_label, 'dl', _c(tint, self.detect_a))
