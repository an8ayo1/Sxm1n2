"""Run with Python 3.10+ after installing requirements.txt."""
import argparse


def main():
    parser=argparse.ArgumentParser(description='Sketch Racer / Neon Circuit')
    parser.add_argument('--smoke-test',action='store_true',help='Render 360 deterministic frames, then exit')
    parser.add_argument('--screenshot',help='Save the final smoke-test frame to this PNG path')
    parser.add_argument('--offscreen',action='store_true',help='Render without an interactive window (requires a graphics context)')
    args=parser.parse_args()
    try:
        from racer.app import Game
    except ImportError as error:
        raise SystemExit('Install dependencies first: python -m pip install -r requirements.txt\n'+str(error))
    Game(args.smoke_test,args.screenshot,args.offscreen).run()


if __name__=='__main__':
    main()
