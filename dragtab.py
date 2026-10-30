#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Carl Kliefert
"""DragTab: Alt+Tab while dragging out of GTK applications such as Thunderbird.

While a drag is in progress, GTK on X11 grabs the keyboard, so the window
manager never sees Alt+Tab. Raw XInput2 events are still delivered, though.
DragTab watches them, detects Alt+Tab while the left mouse button is held and
raises the next window via xdotool - immediately, not only when Alt is
released. Shift+Alt+Tab goes backwards.

It only acts when the active window belongs to one of the given WM_CLASS
names (default: thunderbird), so it does not switch twice in applications
where the window manager already receives Alt+Tab.

Usage: dragtab.py [-v] [class ...]
"""
import ctypes
import ctypes.util
import re
import signal
import subprocess
import sys

__version__ = "0.1.0"

LEFT_BUTTON = 1

GENERIC_EVENT = 35
XI_ALL_MASTER_DEVICES = 1
RAW_KEY_PRESS, RAW_KEY_RELEASE = 13, 14
RAW_BUTTON_PRESS, RAW_BUTTON_RELEASE = 15, 16

if "--version" in sys.argv[1:]:
    print("dragtab", __version__)
    sys.exit(0)

args = [a for a in sys.argv[1:] if a != "-v"]
VERBOSE = "-v" in sys.argv[1:]
CLASSES = {c.lower() for c in args} or {"thunderbird"}


def log(*parts):
    if VERBOSE:
        print(*parts, file=sys.stderr, flush=True)


# --- Xlib (only what is needed, via ctypes, no extra packages) ---

class XGenericEventCookie(ctypes.Structure):
    _fields_ = [("type", ctypes.c_int), ("serial", ctypes.c_ulong),
                ("send_event", ctypes.c_int), ("display", ctypes.c_void_p),
                ("extension", ctypes.c_int), ("evtype", ctypes.c_int),
                ("cookie", ctypes.c_uint), ("data", ctypes.c_void_p)]


class XEvent(ctypes.Union):
    _fields_ = [("type", ctypes.c_int), ("xcookie", XGenericEventCookie),
                ("pad", ctypes.c_long * 24)]


class XIRawEvent(ctypes.Structure):
    _fields_ = [("type", ctypes.c_int), ("serial", ctypes.c_ulong),
                ("send_event", ctypes.c_int), ("display", ctypes.c_void_p),
                ("extension", ctypes.c_int), ("evtype", ctypes.c_int),
                ("time", ctypes.c_ulong), ("deviceid", ctypes.c_int),
                ("sourceid", ctypes.c_int), ("detail", ctypes.c_int)]


class XIEventMask(ctypes.Structure):
    _fields_ = [("deviceid", ctypes.c_int), ("mask_len", ctypes.c_int),
                ("mask", ctypes.POINTER(ctypes.c_ubyte))]


def x_libraries():
    xlib = ctypes.CDLL(ctypes.util.find_library("X11") or "libX11.so.6")
    xi = ctypes.CDLL(ctypes.util.find_library("Xi") or "libXi.so.6")
    xlib.XOpenDisplay.restype = ctypes.c_void_p
    xlib.XOpenDisplay.argtypes = [ctypes.c_char_p]
    xlib.XDefaultRootWindow.restype = ctypes.c_ulong
    xlib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    xlib.XQueryExtension.argtypes = [ctypes.c_void_p, ctypes.c_char_p] + [ctypes.POINTER(ctypes.c_int)] * 3
    xlib.XStringToKeysym.restype = ctypes.c_ulong
    xlib.XStringToKeysym.argtypes = [ctypes.c_char_p]
    xlib.XKeysymToKeycode.restype = ctypes.c_ubyte
    xlib.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    xlib.XNextEvent.argtypes = [ctypes.c_void_p, ctypes.POINTER(XEvent)]
    xlib.XGetEventData.argtypes = [ctypes.c_void_p, ctypes.POINTER(XGenericEventCookie)]
    xlib.XFreeEventData.argtypes = [ctypes.c_void_p, ctypes.POINTER(XGenericEventCookie)]
    xlib.XFlush.argtypes = [ctypes.c_void_p]
    xi.XIQueryVersion.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
    xi.XISelectEvents.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(XIEventMask), ctypes.c_int]
    return xlib, xi


def keycodes(xlib, dpy, *names):
    codes = {xlib.XKeysymToKeycode(dpy, xlib.XStringToKeysym(n.encode())) for n in names}
    codes.discard(0)
    return codes


def raw_events():
    """Yields (evtype, detail) for raw key and button events, regardless of grabs."""
    xlib, xi = x_libraries()
    dpy = xlib.XOpenDisplay(None)
    if not dpy:
        sys.exit("Cannot connect to the X server (is DISPLAY set?)")
    opcode, event, error = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
    if not xlib.XQueryExtension(dpy, b"XInputExtension", ctypes.byref(opcode),
                                ctypes.byref(event), ctypes.byref(error)):
        sys.exit("X server has no XInput extension")
    # Since XI 2.1, raw events are delivered even during other clients' grabs
    major, minor = ctypes.c_int(2), ctypes.c_int(2)
    if xi.XIQueryVersion(dpy, ctypes.byref(major), ctypes.byref(minor)) != 0:
        sys.exit("XInput 2.2 is required")

    mask = (ctypes.c_ubyte * 4)()
    for evtype in (RAW_KEY_PRESS, RAW_KEY_RELEASE, RAW_BUTTON_PRESS, RAW_BUTTON_RELEASE):
        mask[evtype >> 3] |= 1 << (evtype & 7)
    em = XIEventMask(XI_ALL_MASTER_DEVICES, len(mask), mask)
    xi.XISelectEvents(dpy, xlib.XDefaultRootWindow(dpy), ctypes.byref(em), 1)
    xlib.XFlush(dpy)

    yield {
        "tab": keycodes(xlib, dpy, "Tab"),
        "alt": keycodes(xlib, dpy, "Alt_L", "Alt_R", "Meta_L"),
        "shift": keycodes(xlib, dpy, "Shift_L", "Shift_R"),
    }

    ev = XEvent()
    while True:
        xlib.XNextEvent(dpy, ctypes.byref(ev))  # exits with status 1 if the connection is lost
        c = ev.xcookie
        if c.type != GENERIC_EVENT or c.extension != opcode.value:
            continue
        if not xlib.XGetEventData(dpy, ctypes.byref(ev.xcookie)):
            continue
        try:
            raw = ctypes.cast(ev.xcookie.data, ctypes.POINTER(XIRawEvent)).contents
            evtype, detail = raw.evtype, raw.detail
        finally:
            xlib.XFreeEventData(dpy, ctypes.byref(ev.xcookie))
        yield evtype, detail


# --- Windows via xprop/xdotool ---

def xprop(*args):
    r = subprocess.run(["xprop", *args], capture_output=True, text=True)
    return r.stdout


def window_list(prop, window=None):
    target = ["-id", window] if window else ["-root"]
    return re.findall(r"0x[0-9a-f]+", xprop(*target, prop).split("#", 1)[-1])


def number(prop, window=None):
    target = ["-id", window] if window else ["-root"]
    m = re.search(r"=\s*(\d+)", xprop(*target, prop))
    return int(m.group(1)) if m else None


def active_window():
    windows = window_list("_NET_ACTIVE_WINDOW")
    return windows[0] if windows and int(windows[0], 16) else None


def wm_class(window):
    return re.findall(r'"([^"]*)"', xprop("-id", window, "WM_CLASS"))


def switchable(window, desktop):
    info = xprop("-id", window, "_NET_WM_WINDOW_TYPE", "_NET_WM_STATE", "_NET_WM_DESKTOP")
    wtype = re.search(r"_NET_WM_WINDOW_TYPE\(ATOM\) = (\S+)", info)
    if wtype and wtype.group(1).rstrip(",") not in ("_NET_WM_WINDOW_TYPE_NORMAL",
                                                     "_NET_WM_WINDOW_TYPE_DIALOG"):
        return False
    if "_NET_WM_STATE_SKIP_TASKBAR" in info or "_NET_WM_STATE_HIDDEN" in info:
        return False
    d = re.search(r"_NET_WM_DESKTOP\(CARDINAL\) = (\d+)", info)
    return not d or int(d.group(1)) in (desktop, 0xFFFFFFFF)


def candidates(source):
    """Windows in stacking order from top to bottom, excluding the source window."""
    desktop = number("_NET_CURRENT_DESKTOP") or 0
    stack = reversed(window_list("_NET_CLIENT_LIST_STACKING"))
    return [w for w in stack if int(w, 16) != int(source, 16) and switchable(w, desktop)]


def main():
    events = raw_events()
    keys = next(events)
    alt = shift = left = False
    cycle = None  # [source, candidates, index] while Alt is held
    log("ready, classes:", ", ".join(sorted(CLASSES)), "keys:", keys)

    for evtype, detail in events:
        pressed = evtype in (RAW_KEY_PRESS, RAW_BUTTON_PRESS)

        if evtype in (RAW_BUTTON_PRESS, RAW_BUTTON_RELEASE):
            if detail == LEFT_BUTTON:
                left = pressed
            continue
        if detail in keys["alt"]:
            alt = pressed
            if not alt:
                cycle = None
            continue
        if detail in keys["shift"]:
            shift = pressed
            continue
        if detail not in keys["tab"] or evtype != RAW_KEY_PRESS or not (alt and left):
            continue

        if cycle is None:
            source = active_window()
            if not source:
                continue
            classes = wm_class(source)
            if not CLASSES & {c.lower() for c in classes}:
                log("active window", classes, "not handled")
                continue
            windows = candidates(source)
            if not windows:
                continue
            cycle = [source, windows, -1]
        source, windows, index = cycle
        index = (index - 1 if shift else index + 1) % len(windows)
        cycle[2] = index
        target = windows[index]
        log("switching to", target, wm_class(target))
        subprocess.run(["xdotool", "windowactivate", target], stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()
