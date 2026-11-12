"""Win32 window geometry and input. No game memory or injected game code."""
import ctypes
from ctypes import wintypes

KEY_CODES = {'space': 0x20, 'left': 1, 'right': 2}


class Desktop:
    def __init__(self):
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.user.GetForegroundWindow.restype = wintypes.HWND
        self.user.IsWindow.argtypes = [wintypes.HWND]
        self.user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        self.user.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_size_t]
        self.user.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
        self.user.GetAsyncKeyState.restype = ctypes.c_short
        self.held = set()

    def foreground(self):
        return self.user.GetForegroundWindow()

    def title(self, hwnd):
        text = ctypes.create_unicode_buffer(512)
        self.user.GetWindowTextW(hwnd, text, len(text))
        return text.value

    def region(self, hwnd):
        rect, origin = wintypes.RECT(), wintypes.POINT()
        if not self.user.IsWindow(hwnd) or not self.user.GetClientRect(hwnd, ctypes.byref(rect)):
            raise RuntimeError('Game window no longer exists')
        if not self.user.ClientToScreen(hwnd, ctypes.byref(origin)):
            raise RuntimeError('Cannot locate game window')
        if rect.right < 100 or rect.bottom < 100 or self.user.IsIconic(hwnd):
            raise RuntimeError('Game window minimized or too small')
        return dict(left=origin.x, top=origin.y, width=rect.right, height=rect.bottom)

    def down(self, name):
        code = KEY_CODES.get(name, ord(name.upper()) if len(name) == 1 else 0)
        return bool(self.user.GetAsyncKeyState(code) & 0x8000)

    def cursor(self, region):
        p = wintypes.POINT()
        self.user.GetCursorPos(ctypes.byref(p))
        return ((p.x-region['left'])/region['width'], (p.y-region['top'])/region['height'])

    def set_button(self, name, down):
        if name in ('left', 'right'):
            flag = {'left': (2, 4), 'right': (8, 16)}[name][not down]
            self.user.mouse_event(flag, 0, 0, 0, 0)
        else:
            code = KEY_CODES.get(name, ord(name.upper()) if len(name) == 1 else 0)
            self.user.keybd_event(code, 0, 0 if down else 2, 0)

    def apply(self, action, region, controls):
        # Keep cursor inside client; never click title bar or desktop.
        x, y = [max(.02, min(.98, float(v))) for v in action[:2]]
        self.user.SetCursorPos(region['left'] + int(x*region['width']),
                               region['top'] + int(y*region['height']))
        wanted = {name for name, value in zip(controls, action[2:]) if value >= .65}
        for name in self.held - wanted:
            self.set_button(name, False)
        for name in wanted - self.held:
            self.set_button(name, True)
        self.held = wanted

    def release(self):
        for name in self.held:
            self.set_button(name, False)
        self.held.clear()
