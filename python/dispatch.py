#!/usr/bin/env python3
import sys, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
USAGE = "usage: wavtool pack <dir> <out.wav> [--ultra] | wavtool rate [96000]"


def run(script, args):
    return subprocess.run([sys.executable, os.path.join(HERE, script)] + args).returncode


def main():
    args = sys.argv[1:]
    if not args:
        print(USAGE)
        return 2
    cmd, rest = args[0], args[1:]
    if cmd == 'pack':
        ultra = ('--ultra' in rest) or ('--repair' in rest)
        rest = [a for a in rest if a != '--ultra']
        return run('tx_pack21.py' if ultra else 'tx_pack.py', rest)
    if cmd == 'rate':
        return run('audiorate.py', rest)
    print(USAGE)
    return 2


if __name__ == '__main__':
    sys.exit(main())
