#!/usr/bin/env python3
"""macOS output-device sample-rate helper (CoreAudio via ctypes).
Usage: audiorate.py [get | <rate>]   (e.g. audiorate.py 96000)"""
import ctypes, ctypes.util, struct, sys, time


def fourcc(s):
    return struct.unpack('>I', s.encode())[0]


class AOPA(ctypes.Structure):
    _fields_ = [('sel', ctypes.c_uint32), ('scope', ctypes.c_uint32), ('elem', ctypes.c_uint32)]


def _load():
    path = ctypes.util.find_library('CoreAudio')
    if not path or sys.platform != 'darwin':
        return None
    return ctypes.cdll.LoadLibrary(path)


CA = _load()


def _dev():
    a = AOPA(fourcc('dOut'), fourcc('glob'), 0)
    dev = ctypes.c_uint32(0); sz = ctypes.c_uint32(4)
    CA.AudioObjectGetPropertyData(ctypes.c_uint32(1), ctypes.byref(a), 0, None,
                                  ctypes.byref(sz), ctypes.byref(dev))
    return dev


def get_rate():
    dev = _dev()
    r = ctypes.c_double(0); s2 = ctypes.c_uint32(8)
    CA.AudioObjectGetPropertyData(dev, ctypes.byref(AOPA(fourcc('nsrt'), fourcc('glob'), 0)),
                                  0, None, ctypes.byref(s2), ctypes.byref(r))
    return r.value


def set_rate(rate):
    dev = _dev()
    for _ in range(6):
        if abs(get_rate() - rate) < 1:
            return True
        r = ctypes.c_double(rate)
        CA.AudioObjectSetPropertyData(dev, ctypes.byref(AOPA(fourcc('nsrt'), fourcc('glob'), 0)),
                                      0, None, 8, ctypes.byref(r))
        time.sleep(0.4)
    return abs(get_rate() - rate) < 1


def main():
    if CA is None:
        print('unsupported platform (macOS only)')
        return 1
    if len(sys.argv) == 1 or sys.argv[1] == 'get':
        print(f'{get_rate():.0f}')
        return 0
    rate = float(sys.argv[1])
    ok = set_rate(rate)
    print(f'{"ok" if ok else "failed"}: {get_rate():.0f} Hz')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
