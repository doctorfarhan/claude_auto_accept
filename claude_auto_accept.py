"""
Claude Code Auto-Accept Plugin for Cmder

"""

import ctypes
import ctypes.wintypes as wt
import time
import sys
import os
import subprocess

# ---------------------------------------------------------------------------
# Win32 Constants
# ---------------------------------------------------------------------------
STD_INPUT_HANDLE = -10
KEY_EVENT = 0x0001
VK_RETURN = 0x0D
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

kernel32 = ctypes.windll.kernel32

# ---------------------------------------------------------------------------
# Console Screen Buffer Info
# ---------------------------------------------------------------------------
class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
    _fields_ = [
        ("dwSize_X", ctypes.c_short),
        ("dwSize_Y", ctypes.c_short),
        ("dwCursorPosition_X", ctypes.c_short),
        ("dwCursorPosition_Y", ctypes.c_short),
        ("wAttributes", wt.WORD),
        ("srWindow_Left", ctypes.c_short),
        ("srWindow_Top", ctypes.c_short),
        ("srWindow_Right", ctypes.c_short),
        ("srWindow_Bottom", ctypes.c_short),
        ("dwMaximumWindowSize_X", ctypes.c_short),
        ("dwMaximumWindowSize_Y", ctypes.c_short),
    ]

# ---------------------------------------------------------------------------
# Input Record structures for WriteConsoleInputW
# ---------------------------------------------------------------------------
class KEY_EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        ("bKeyDown", wt.BOOL),
        ("wRepeatCount", wt.WORD),
        ("wVirtualKeyCode", wt.WORD),
        ("wVirtualScanCode", wt.WORD),
        ("uChar", ctypes.c_wchar),
        ("dwControlKeyState", wt.DWORD),
    ]

class _EventUnion(ctypes.Union):
    _fields_ = [("KeyEvent", KEY_EVENT_RECORD)]

class INPUT_RECORD(ctypes.Structure):
    _fields_ = [
        ("EventType", wt.WORD),
        ("Event", _EventUnion),
    ]

# ---------------------------------------------------------------------------
# Function prototypes
# ---------------------------------------------------------------------------
kernel32.CreateFileW.argtypes = [
    wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p,
    wt.DWORD, wt.DWORD, wt.HANDLE,
]
kernel32.CreateFileW.restype = wt.HANDLE

kernel32.GetConsoleScreenBufferInfo.argtypes = [
    wt.HANDLE, ctypes.POINTER(CONSOLE_SCREEN_BUFFER_INFO),
]
kernel32.GetConsoleScreenBufferInfo.restype = wt.BOOL

kernel32.ReadConsoleOutputCharacterW.argtypes = [
    wt.HANDLE, ctypes.c_wchar_p, wt.DWORD, wt.DWORD,
    ctypes.POINTER(wt.DWORD),
]
kernel32.ReadConsoleOutputCharacterW.restype = wt.BOOL

kernel32.WriteConsoleInputW.argtypes = [
    wt.HANDLE, ctypes.POINTER(INPUT_RECORD), wt.DWORD,
    ctypes.POINTER(wt.DWORD),
]
kernel32.WriteConsoleInputW.restype = wt.BOOL

kernel32.CloseHandle.argtypes = [wt.HANDLE]
kernel32.CloseHandle.restype = wt.BOOL

kernel32.GetConsoleWindow.argtypes = []
kernel32.GetConsoleWindow.restype = wt.HWND

# ---------------------------------------------------------------------------
# Prompt patterns to auto-accept
# ---------------------------------------------------------------------------
PROMPTS = [
    {
        "trigger": "Do you want to proceed?",
        "confirm": ["Yes", "No"],
    },
]

# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------

def open_console_handles():
    """
    Open CONOUT$ and CONIN$ directly.  This works even when
    stdout / stderr have been redirected to NUL.
    """
    h_out = kernel32.CreateFileW(
        "CONOUT$", GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
        None, OPEN_EXISTING, 0, None,
    )
    h_in = kernel32.CreateFileW(
        "CONIN$", GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None, OPEN_EXISTING, 0, None,
    )
    if h_out == INVALID_HANDLE_VALUE or h_in == INVALID_HANDLE_VALUE:
        return None, None
    return h_out, h_in


def read_visible_screen(h_out):
    """Return the visible portion of the console buffer as a string."""
    csbi = CONSOLE_SCREEN_BUFFER_INFO()
    if not kernel32.GetConsoleScreenBufferInfo(h_out, ctypes.byref(csbi)):
        return ""

    width = csbi.dwSize_X
    top = csbi.srWindow_Top
    bottom = csbi.srWindow_Bottom

    lines = []
    for row in range(top, bottom + 1):
        buf = ctypes.create_unicode_buffer(width + 1)
        chars_read = wt.DWORD(0)
        # COORD passed by value as DWORD: low-word = X, high-word = Y
        coord = (row << 16) | 0
        kernel32.ReadConsoleOutputCharacterW(
            h_out, buf, width, coord, ctypes.byref(chars_read)
        )
        lines.append(buf.value.rstrip())
    return "\n".join(lines)


def send_enter(h_in):
    """Write an Enter key-press into the console input buffer."""
    records = (INPUT_RECORD * 2)()
    for idx, down in enumerate([True, False]):
        records[idx].EventType = KEY_EVENT
        records[idx].Event.KeyEvent.bKeyDown = down
        records[idx].Event.KeyEvent.wRepeatCount = 1
        records[idx].Event.KeyEvent.wVirtualKeyCode = VK_RETURN
        records[idx].Event.KeyEvent.wVirtualScanCode = 0x1C
        records[idx].Event.KeyEvent.uChar = '\r'
        records[idx].Event.KeyEvent.dwControlKeyState = 0
    written = wt.DWORD(0)
    kernel32.WriteConsoleInputW(h_in, records, 2, ctypes.byref(written))


def send_enter_via_conemu():
    """Fallback: send Enter through ConEmuC GuiMacro."""
    base = os.environ.get("ConEmuBaseDir", "")
    if not base:
        return False
    for name in ("ConEmuC64.exe", "ConEmuC.exe"):
        exe = os.path.join(base, name)
        if os.path.isfile(exe):
            try:
                subprocess.run(
                    [exe, "-GuiMacro", 'Keys("Enter")'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=3,
                    creationflags=0x08000000,   # CREATE_NO_WINDOW
                )
                return True
            except Exception:
                pass
    return False

# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def prompt_detected(screen_text):
    """
    Return True if the visible screen contains a Claude Code
    confirmation prompt that should be auto-accepted.
    """
    for prompt in PROMPTS:
        if prompt["trigger"] not in screen_text:
            continue
        lines = screen_text.split("\n")
        for i, line in enumerate(lines):
            if prompt["trigger"] in line:
                # check the next few lines for the confirmation options
                context = "\n".join(lines[i : i + 8])
                if all(opt in context for opt in prompt["confirm"]):
                    return True
    return False

# ---------------------------------------------------------------------------
# Lock file helpers (one instance per console)
# ---------------------------------------------------------------------------

def _lock_path():
    hwnd = kernel32.GetConsoleWindow()
    tmp = os.environ.get("TEMP", os.environ.get("TMP", "."))
    return os.path.join(tmp, f"cmder_claude_aa_{hwnd}.pid")


def acquire_lock():
    path = _lock_path()
    if os.path.exists(path):
        try:
            with open(path) as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)          # still alive
            return False                 # another instance running
        except (OSError, ValueError):
            pass                         # stale lock
    try:
        with open(path, "w") as f:
            f.write(str(os.getpid()))
    except OSError:
        pass
    return True


def release_lock():
    try:
        os.remove(_lock_path())
    except OSError:
        pass

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    if not acquire_lock():
        sys.exit(0)

    h_out, h_in = open_console_handles()
    if h_out is None or h_in is None:
        release_lock()
        sys.exit(1)

    COOLDOWN = 3        # seconds after an accept before looking again
    POLL     = 0.5      # seconds between screen reads
    SETTLE   = 0.3      # seconds to wait after detection before sending key

    last_accept = 0.0

    try:
        while True:
            try:
                now = time.time()
                if now - last_accept < COOLDOWN:
                    time.sleep(POLL)
                    continue

                screen = read_visible_screen(h_out)
                if prompt_detected(screen):
                    time.sleep(SETTLE)
                    # Primary: write directly to THIS console's input buffer
                    send_enter(h_in)
                    last_accept = time.time()

                time.sleep(POLL)
            except KeyboardInterrupt:
                break
            except Exception:
                time.sleep(2)
    finally:
        kernel32.CloseHandle(h_out)
        kernel32.CloseHandle(h_in)
        release_lock()


if __name__ == "__main__":
    main()
