#!/usr/bin/env python3
import os, sys, argparse, shlex
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pathlib import Path
import wtpack

ap = argparse.ArgumentParser(description="pack a directory into a WAV file")
ap.add_argument("src"); ap.add_argument("dst")
ap.add_argument("--no-compress", action="store_true", help="disable in-memory compression")
ap.add_argument("--padding", type=float, default=10.0, help="leading silence seconds")
ap.add_argument("--keep-volume", action="store_true", help="do not auto-set the system volume to 38%%")
ap.add_argument("--fast", action="store_true", help=argparse.SUPPRESS)
a = ap.parse_args()

files = sorted([f for f in Path(a.src).rglob("*") if f.is_file()])
total = sum(os.path.getsize(f) for f in files)
L, R = wtpack.encode_directory_v20(a.src, head_padding_seconds=a.padding,
                                   compress=not a.no_compress)
wtpack.save_wav_stereo(L, R, a.dst)

blob = b"".join(f.read_bytes() for f in files)
if not a.no_compress and blob:
    stored = sum(len(wtpack._compress_chunk(blob[i:i + wtpack.SEG_RAW]))
                 for i in range(0, len(blob), wtpack.SEG_RAW))
else:
    stored = len(blob)
ratio = (stored / total) if total else 1.0
dur = len(L) / wtpack.SAMPLE_RATE
print(f"files={len(files)} payload={total}B stored={stored}B ({ratio:.1%})")
print(f"duration={dur:.1f}s ({dur/60:.1f} min)")
try:
    import audiovol
    before = audiovol.get_volume()
    if a.keep_volume:
        warn = '' if before == '38' else '  <<< 认证档位约 38%, 音量偏差会吃掉纠错裕度!'
        print(f"系统音量: {before}%{warn} (--keep-volume 未改动)")
    else:
        after = audiovol.set_volume(38)
        if before != after:
            print(f"系统音量: {before}% → 已自动设为 38% (认证档; 想保留原值用 --keep-volume)")
        else:
            print("系统音量: 38% (认证档 ✓)")
except Exception:
    pass
print(f"-> {a.dst}")
print()
print("播放命令 (复制即用):")
print(f"afplay -v 0.5 {shlex.quote(a.dst)}")
