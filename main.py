import argparse
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

def parse_size(text):
    try:
        w, h = text.lower().split('x')
        return (int(w), int(h))
    except ValueError:
        raise argparse.ArgumentTypeError('size must look like 1280x720')

def main():
    ap = argparse.ArgumentParser(description='The Night Crow')
    ap.add_argument('--scene', type=int, default=0, help='0 = menu, 1-4 = story scenes')
    ap.add_argument('--safe', action='store_true', help='low-spec mode')
    ap.add_argument('--fullscreen', action='store_true')
    ap.add_argument('--size', type=parse_size, default=(1280, 720))
    ap.add_argument('--mute', action='store_true')
    ap.add_argument('--fps', action='store_true')
    args = ap.parse_args()
    from engine.game import Game
    game = Game(start_scene=args.scene, safe=args.safe, fullscreen=args.fullscreen, size=args.size, mute=args.mute, show_fps=args.fps)
    game.run()
if __name__ == '__main__':
    main()
