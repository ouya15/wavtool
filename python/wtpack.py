import numpy as np
import struct, zlib, wave
from pathlib import Path
from reedsolo import RSCodec, ReedSolomonError

SAMPLE_RATE = 44100
PREAMBLE_LEN = 1024
GUARD_LEN = 32
MAGIC_LEN = 256
HEADER_FORMAT = "<4sHHHHI"

def make_preamble_segment():
    t = np.arange(PREAMBLE_LEN) / SAMPLE_RATE
    return (np.sin(2 * np.pi * 800 * t) * 30000).astype(np.int16)

def _chirp(f0, f1):
    t = np.arange(MAGIC_LEN) / SAMPLE_RATE
    k = (f1 - f0) / (MAGIC_LEN / SAMPLE_RATE)
    ph = 2 * np.pi * (f0 * t + k / 2 * t ** 2)
    return (np.sin(ph) * 30000).astype(np.int16)

MAGIC_A = _chirp(1300.0, 1400.0)

SYM_K = 8
SYM_TRIM = 2
PILOT_PERIOD = 8
N_BITS = 4
SPACING = 4096.0
LEVELS = (np.arange(16) - 7.5) * SPACING
PILOT_Q = 7
CW_N = 255
CW_DATA = 223
CW_COUNT = 19
STREAM_BYTES = CW_COUNT * CW_N
PAYLOAD_CAP = CW_COUNT * CW_DATA
_rs = RSCodec(CW_N - CW_DATA)
N_DATA_SYMS = (STREAM_BYTES * 8 + N_BITS - 1) // N_BITS
N_GROUPS = (N_DATA_SYMS + (PILOT_PERIOD - 2)) // (PILOT_PERIOD - 1)
N_SYMBOLS = N_GROUPS * PILOT_PERIOD
DATA_MASK = (np.arange(N_SYMBOLS) % PILOT_PERIOD) != (PILOT_PERIOD - 1)
assert DATA_MASK.sum() >= N_DATA_SYMS
PILOT_IDX = np.where(~DATA_MASK)[0]
BLOCK_SAMPLES = PREAMBLE_LEN + GUARD_LEN + MAGIC_LEN + N_SYMBOLS * SYM_K
CHUNK = 4096
SEG_RAW = 262144
try:
    import zstandard as _zstd
    _HAS_ZSTD = True
except Exception:
    _HAS_ZSTD = False
EQ_FC_DEFAULT = 39.0
EQ_ALPHA = 1e-2
EQ_PAD = 8192
MANI_VERSION = 20

def _compress_chunk(b: bytes) -> bytes:
    if _HAS_ZSTD:
        return _zstd.ZstdCompressor(level=19).compress(b)
    return zlib.compress(b, 6)

def rs_encode_payload(payload: bytes) -> bytes:
    assert len(payload) <= PAYLOAD_CAP
    payload = payload + b"\x00" * (PAYLOAD_CAP - len(payload))
    out = bytearray()
    for i in range(CW_COUNT):
        out += bytes(_rs.encode(payload[i * CW_DATA:(i + 1) * CW_DATA]))
    return bytes(out)

def bytes_to_syms(data: bytes) -> np.ndarray:
    b = np.frombuffer(data, dtype=np.uint8).astype(np.int32)
    q = np.empty(len(b) * 2, dtype=np.int32)
    q[0::2] = (b >> 4) & 15
    q[1::2] = b & 15
    return q

def build_block(block_type: bytes, block_index: int, total_blocks: int, data: bytes) -> np.ndarray:
    header = struct.pack(HEADER_FORMAT, block_type, 0, block_index, total_blocks, 0, len(data))
    crc = (zlib.crc32(header + data) & 0xFFFFFFFF).to_bytes(4, "little")
    stream = rs_encode_payload(header + data + crc)
    q_data = bytes_to_syms(stream)
    q_pad = np.concatenate([q_data, np.zeros(DATA_MASK.sum() - len(q_data), dtype=np.int32)])
    syms = np.empty(N_SYMBOLS, dtype=np.float64)
    syms[DATA_MASK] = LEVELS[q_pad]
    syms[~DATA_MASK] = LEVELS[PILOT_Q]
    wav = np.repeat(syms, SYM_K).astype(np.int16)
    return np.concatenate([make_preamble_segment(),
                           np.zeros(GUARD_LEN, dtype=np.int16),
                           MAGIC_A, wav])

def encode_directory_v20(root_dir: str, head_padding_seconds: float = 10.0,
                         compress: bool = True) -> Tuple[np.ndarray, np.ndarray]:
    root = Path(root_dir).resolve()
    files = sorted([f for f in root.rglob("*") if f.is_file()])
    paths, sizes, crcs, blobs = [], [], [], []
    for f in files:
        rel = str(f.relative_to(root))
        content = f.read_bytes()
        paths.append(rel.encode("utf-8"))
        sizes.append(len(content))
        crcs.append(zlib.crc32(content) & 0xFFFFFFFF)
        blobs.append(content)
    raw_stream = b"".join(blobs)

    if compress and raw_stream:
        segs = [raw_stream[i:i + SEG_RAW] for i in range(0, len(raw_stream), SEG_RAW)]
        stored_segs = [_compress_chunk(s) for s in segs]
        stored = b"".join(stored_segs)
        stored_sizes = [len(s) for s in stored_segs]
    else:
        stored = raw_stream
        stored_sizes = []

    entries = b"".join(struct.pack("<H", len(pb)) + pb + struct.pack("<II", sz, cr)
                       for pb, sz, cr in zip(paths, sizes, crcs))
    flags = 2 | (1 if stored_sizes else 0) | (4 if stored_sizes and _HAS_ZSTD else 0)
    mani = struct.pack("<BBIIIH", MANI_VERSION, flags, SEG_RAW, len(files), len(raw_stream),
                       len(stored_sizes))
    mani += b"".join(struct.pack("<I", sz) for sz in stored_sizes)
    mani += zlib.compress(entries, 9)

    n_data_blocks = max(1, (len(stored) + CHUNK - 1) // CHUNK)
    mani_chunks = [mani[i:i + CHUNK] for i in range(0, len(mani), CHUNK)] or [b""]
    mani_blocks = [build_block(b"MANI", bi, len(mani_chunks), mc)
                   for bi, mc in enumerate(mani_chunks)]
    data_blocks = []
    for bi in range(n_data_blocks):
        data_blocks.append(build_block(b"DATA", bi, n_data_blocks, stored[bi * CHUNK:(bi + 1) * CHUNK]))
    done = build_block(b"DONE", 0, 0, struct.pack("<I", len(files)))

    left = np.concatenate(mani_blocks + data_blocks[0::2] + [done])
    right = np.concatenate(mani_blocks + data_blocks[1::2])
    n = max(len(left), len(right))
    L = np.zeros(n, dtype=np.int16); L[:len(left)] = left
    R = np.zeros(n, dtype=np.int16); R[:len(right)] = right
    pad = int(head_padding_seconds * SAMPLE_RATE)
    zp = np.zeros(pad, dtype=np.int16)
    return np.concatenate([zp, L]), np.concatenate([zp, R])

def save_wav_stereo(L: np.ndarray, R: np.ndarray, filename: str) -> None:
    with wave.open(filename, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SAMPLE_RATE)
        inter = np.empty(len(L) * 2, dtype=np.int16)
        inter[0::2] = L; inter[1::2] = R
        w.writeframes(inter.tobytes())
