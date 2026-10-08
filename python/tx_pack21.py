#!/usr/bin/env python3
import os, sys, argparse, shlex
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pathlib import Path
import wtpack21 as wtpack
import audiorate

ap = argparse.ArgumentParser(description="pack a directory into a 96kHz WAV file (ultra)")
ap.add_argument("src"); ap.add_argument("dst")
ap.add_argument("--no-compress", action="store_true", help="disable in-memory compression")
ap.add_argument("--padding", type=float, default=10.0, help="leading silence seconds")
ap.add_argument("--repair", help="comma-separated data block indices to re-send (repair pack)")
a = ap.parse_args()

files = sorted([f for f in Path(a.src).rglob("*") if f.is_file()])
total = sum(os.path.getsize(f) for f in files)
if a.repair:
    idx = [int(x) for x in a.repair.replace(" ", "").split(",") if x]
    L, R = wtpack.encode_repair_v21(a.src, idx, head_padding_seconds=a.padding,
                                    compress=not a.no_compress)
    wtpack.save_wav_stereo(L, R, a.dst)
    dur = len(L) / wtpack.SAMPLE_RATE
    print(f"repair pack: {len(idx)} blocks, {dur:.1f}s")
    print(f"-> {a.dst}")
    print()
    print("播放命令 (复制即用):")
    print(f"afplay -v 0.5 {shlex.quote(a.dst)}")
    raise SystemExit(0)
L, R = wtpack.encode_directory_v21(a.src, head_padding_seconds=a.padding,
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

rate_ok = False
try:
    rate_ok = audiorate.set_rate(96000)
except Exception:
    pass
print(f"输出设备采样率: {'已设为 96 kHz' if rate_ok else '设置失败 — 播放前请手动确认 96 kHz (wavtool rate 96000)'}")
try:
    import subprocess
    vol = subprocess.run(['osascript', '-e', 'output volume of (get volume settings)'],
                         capture_output=True, text=True, timeout=5).stdout.strip()
    if vol:
        warn = '' if 30 <= int(vol) <= 45 else '  <<< 认证档位约 38%, 音量偏差会吃掉纠错裕度!'
        print(f"系统音量: {vol}%{warn}")
except Exception:
    pass
print("提示: 请先插好音频线再播放; 若播放前插线导致重置, 重跑: wavtool rate 96000")
print(f"-> {a.dst}")
print()
print("播放命令 (复制即用):")
print(f"afplay -v 0.5 {shlex.quote(a.dst)}")
