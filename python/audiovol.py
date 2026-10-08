#!/usr/bin/env python3
"""macOS system output-volume helper.
Usage: audiovol.py [get | <0-100>]   (e.g. audiovol.py 38)"""
import subprocess, sys


def get_volume():
    r = subprocess.run(['osascript', '-e', 'output volume of (get volume settings)'],
                       capture_output=True, text=True, timeout=5)
    return r.stdout.strip()


def set_volume(v):
    subprocess.run(['osascript', '-e', f'set volume output volume {int(v)}'],
                   capture_output=True, text=True, timeout=5)
    return get_volume()


def main():
    if len(sys.argv) == 1 or sys.argv[1] == 'get':
        print(get_volume())
        return 0
    v = int(sys.argv[1])
    print(f'ok: {set_volume(v)}%')
    return 0


if __name__ == '__main__':
    sys.exit(main())
