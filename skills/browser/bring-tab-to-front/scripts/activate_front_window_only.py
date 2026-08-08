#!/usr/bin/env python3
"""Activate a macOS app bringing only its front window forward.

Uses deprecated SetFrontProcessWithOptions(..., kSetFrontProcessFrontWindowOnly).
Plain `activate` / System Events `set frontmost` can surface every window of the
app above other apps; this keeps sibling windows in their prior z-order relative
to other applications (same approach Keyboard Maestro relies on).

Usage:
  activate_front_window_only.py <pid>
"""

import ctypes
import ctypes.util
import sys


class ProcessSerialNumber(ctypes.Structure):
    _fields_ = [
        ("highLongOfPSN", ctypes.c_uint32),
        ("lowLongOfPSN", ctypes.c_uint32),
    ]


K_SET_FRONT_PROCESS_FRONT_WINDOW_ONLY = 1


def activate_front_window_only(pid):
    lib_path = ctypes.util.find_library("ApplicationServices")
    if not lib_path:
        raise RuntimeError("ApplicationServices framework not found")
    lib = ctypes.cdll.LoadLibrary(lib_path)
    get_psn = lib.GetProcessForPID
    get_psn.argtypes = [ctypes.c_int32, ctypes.POINTER(ProcessSerialNumber)]
    get_psn.restype = ctypes.c_int32
    set_front = lib.SetFrontProcessWithOptions
    set_front.argtypes = [ctypes.POINTER(ProcessSerialNumber), ctypes.c_uint32]
    set_front.restype = ctypes.c_int32
    psn = ProcessSerialNumber(0, 0)
    err = get_psn(int(pid), ctypes.byref(psn))
    if err != 0:
        raise RuntimeError(f"GetProcessForPID failed with {err}")
    err = set_front(ctypes.byref(psn), K_SET_FRONT_PROCESS_FRONT_WINDOW_ONLY)
    if err != 0:
        raise RuntimeError(f"SetFrontProcessWithOptions failed with {err}")


def main(argv):
    if len(argv) != 2 or not str(argv[1]).isdigit():
        print("usage: activate_front_window_only.py <pid>", file=sys.stderr)
        return 2
    activate_front_window_only(int(argv[1]))
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
