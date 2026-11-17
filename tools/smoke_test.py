import os
import sys
import time
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from tools.playtest import PlayTest

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    hop = '--no-hop' not in sys.argv

    def script(t):
        g = t.game
        sc = g.scene
        yield from t.seconds(3.0)
        t0 = time.time()
        frames = 90
        yield from t.wait(frames)
        per = (time.time() - t0) / frames * 1000.0
        print(f'RESULT scene={n} name={type(sc).__name__} frame_ms={per:.1f} errors={t.errors}')
        t.shot(f'smoke_{n}')
        if hop:
            sc.tl.clear()
            g.dialogue.close()
            g.next_scene()
            yield from t.seconds(3.0)
            nxt = g.scene
            yield from t.wait(60)
            print(f"RESULT next={type(nxt).__name__} number={getattr(nxt, 'number', '?')} errors={t.errors}")
            t.shot(f'smoke_{n}_next')
        print('DONE')
    PlayTest(scene=n, fixed_dt=1 / 30).run(script)
if __name__ == '__main__':
    main()
