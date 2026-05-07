"""Window placement helpers for multi-monitor Windows setups."""

import ctypes
import re


SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
MONITOR_DEFAULTTONEAREST = 2
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
DWMWA_BORDER_COLOR = 34
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36
_HEX_COLOR_PATTERN = re.compile(r"^#([0-9a-fA-F]{6})$")


class WinRect(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class WinMonitorInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", WinRect),
        ("rcWork", WinRect),
        ("dwFlags", ctypes.c_ulong),
    ]


class WinPoint(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
    ]


def _windows_user32():
    try:
        return ctypes.windll.user32
    except AttributeError:
        return None


def _windows_dwmapi():
    try:
        return ctypes.windll.dwmapi
    except AttributeError:
        return None


def _window_handle(window):
    user32 = _windows_user32()
    hwnd = ctypes.c_void_p(int(window.winfo_id()))
    if user32 is None:
        return hwnd
    try:
        user32.GetParent.argtypes = [ctypes.c_void_p]
        user32.GetParent.restype = ctypes.c_void_p
        parent_hwnd = user32.GetParent(hwnd)
        if parent_hwnd:
            return parent_hwnd
    except Exception:
        pass
    return hwnd


def _colorref_from_hex(color):
    match = _HEX_COLOR_PATTERN.match(str(color or "").strip())
    if match is None:
        raise ValueError(f"Unsupported color format: {color!r}")
    red = int(match.group(1)[0:2], 16)
    green = int(match.group(1)[2:4], 16)
    blue = int(match.group(1)[4:6], 16)
    return blue << 16 | green << 8 | red


def _dwm_set_window_attribute(hwnd, attribute, value):
    dwmapi = _windows_dwmapi()
    if dwmapi is None:
        return False
    dwmapi.DwmSetWindowAttribute.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_void_p,
        ctypes.c_uint,
    ]
    dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long
    result = dwmapi.DwmSetWindowAttribute(
        hwnd,
        attribute,
        ctypes.byref(value),
        ctypes.sizeof(value),
    )
    return result == 0


def apply_windows_title_bar_theme(
    window,
    caption_color=None,
    text_color=None,
    border_color=None,
    immersive_dark=True,
):
    if _windows_dwmapi() is None:
        return False
    try:
        window.update_idletasks()
        hwnd = _window_handle(window)
    except Exception:
        return False

    applied = False
    dark_mode = ctypes.c_int(1 if immersive_dark else 0)
    for attribute in (
        DWMWA_USE_IMMERSIVE_DARK_MODE,
        DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1,
    ):
        if _dwm_set_window_attribute(hwnd, attribute, dark_mode):
            applied = True
            break

    for attribute, color in (
        (DWMWA_CAPTION_COLOR, caption_color),
        (DWMWA_TEXT_COLOR, text_color),
        (DWMWA_BORDER_COLOR, border_color),
    ):
        if color is None:
            continue
        try:
            colorref = ctypes.c_uint(_colorref_from_hex(color))
        except ValueError:
            continue
        if _dwm_set_window_attribute(hwnd, attribute, colorref):
            applied = True

    return applied


def fallback_screen_geometry(window):
    return 0, 0, window.winfo_screenwidth(), window.winfo_screenheight()


def monitor_geometry(monitor, use_work_area=False):
    user32 = _windows_user32()
    if user32 is None:
        raise RuntimeError("Windows monitor API is unavailable")

    monitor_info = WinMonitorInfo()
    monitor_info.cbSize = ctypes.sizeof(WinMonitorInfo)
    user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(WinMonitorInfo)]
    user32.GetMonitorInfoW.restype = ctypes.c_bool
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(monitor_info)):
        raise RuntimeError("Unable to read monitor geometry")

    rect = monitor_info.rcWork if use_work_area else monitor_info.rcMonitor
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def monitor_geometry_from_handle(hwnd, use_work_area=False):
    user32 = _windows_user32()
    if user32 is None:
        raise RuntimeError("Windows monitor API is unavailable")

    user32.MonitorFromWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    user32.MonitorFromWindow.restype = ctypes.c_void_p
    monitor = user32.MonitorFromWindow(ctypes.c_void_p(int(hwnd)), MONITOR_DEFAULTTONEAREST)
    return monitor_geometry(monitor, use_work_area=use_work_area)


def monitor_geometry_from_point(x, y, use_work_area=False):
    user32 = _windows_user32()
    if user32 is None:
        raise RuntimeError("Windows monitor API is unavailable")

    user32.MonitorFromPoint.argtypes = [WinPoint, ctypes.c_ulong]
    user32.MonitorFromPoint.restype = ctypes.c_void_p
    monitor = user32.MonitorFromPoint(
        WinPoint(int(x), int(y)),
        MONITOR_DEFAULTTONEAREST,
    )
    return monitor_geometry(monitor, use_work_area=use_work_area)


def pointer_monitor_geometry(window, use_work_area=False):
    try:
        pointer_x, pointer_y = window.winfo_pointerxy()
        return monitor_geometry_from_point(
            pointer_x,
            pointer_y,
            use_work_area=use_work_area,
        )
    except Exception:
        return fallback_screen_geometry(window)


def current_monitor_geometry(window, use_work_area=False):
    try:
        window.update_idletasks()
        return monitor_geometry_from_handle(
            window.winfo_id(),
            use_work_area=use_work_area,
        )
    except Exception:
        return fallback_screen_geometry(window)


def move_window_to(window, x, y):
    user32 = _windows_user32()
    if user32 is not None:
        try:
            hwnd = window.winfo_id()
            user32.GetParent.argtypes = [ctypes.c_void_p]
            user32.GetParent.restype = ctypes.c_void_p
            user32.SetWindowPos.argtypes = [
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_uint,
            ]
            user32.SetWindowPos.restype = ctypes.c_bool
            hwnd = ctypes.c_void_p(int(hwnd))
            parent_hwnd = user32.GetParent(hwnd)
            user32.SetWindowPos(
                parent_hwnd or hwnd,
                None,
                int(x),
                int(y),
                0,
                0,
                SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE,
            )
            return
        except Exception:
            pass

    window.geometry(f"+{max(0, int(x))}+{max(0, int(y))}")


def center_window_on_monitor(window, width, height, geometry):
    monitor_x, monitor_y, monitor_width, monitor_height = geometry
    width = int(min(max(1, width), monitor_width))
    height = int(min(max(1, height), monitor_height))
    x = monitor_x + max(0, (monitor_width - width) // 2)
    y = monitor_y + max(0, (monitor_height - height) // 2)

    window.geometry(f"{width}x{height}")
    window.update_idletasks()
    move_window_to(window, x, y)
    return x, y, width, height


def center_window_on_pointer_monitor(window, width, height, use_work_area=True):
    geometry = pointer_monitor_geometry(window, use_work_area=use_work_area)
    center_window_on_monitor(window, width, height, geometry)
    return geometry
