import argparse
import ctypes
import json
import os
import sys
import time
from datetime import datetime

try:
    import tkinter as tk
except Exception:
    tk = None

try:
    from PIL import ImageGrab, ImageTk
except Exception:
    ImageGrab = None
    ImageTk = None

try:
    import pygetwindow as gw
except Exception:
    gw = None


def load_config(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_profiles(path):
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError('profiles file must be a JSON object')
    return data


def save_profiles(path, data):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_window(title):
    if gw is None:
        return None
    wins = gw.getWindowsWithTitle(title)
    if not wins:
        return None
    return wins[0]


def _window_process_name(window):
    hwnd = getattr(window, '_hWnd', None)
    if hwnd is None:
        return None

    pid = ctypes.c_ulong(0)
    ctypes.windll.user32.GetWindowThreadProcessId(int(hwnd), ctypes.byref(pid))
    process_id = int(pid.value)
    if process_id <= 0:
        return None

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, process_id)
    if not handle:
        return None

    try:
        buf_len = ctypes.c_ulong(1024)
        buf = ctypes.create_unicode_buffer(buf_len.value)
        ok = ctypes.windll.kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(buf_len))
        if not ok:
            return None
        full_path = buf.value
        return os.path.basename(full_path)
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def find_window_by_exe(exe_name):
    if gw is None:
        return None
    target = exe_name.strip().lower()
    if not target:
        return None

    for w in gw.getAllWindows():
        if not getattr(w, 'title', '').strip():
            continue
        pname = _window_process_name(w)
        if pname and pname.lower() == target:
            return w
    return None


def focus_window(window):
    if window is None:
        return False

    def _is_foreground(hwnd_value):
        try:
            return int(ctypes.windll.user32.GetForegroundWindow()) == int(hwnd_value)
        except Exception:
            return False

    ok = False
    try:
        # pygetwindow wrappers
        if getattr(window, 'isMinimized', False):
            window.restore()
        window.activate()
        ok = True
    except Exception:
        pass

    hwnd = getattr(window, '_hWnd', None)
    if hwnd is not None:
        try:
            user32 = ctypes.windll.user32
            SW_RESTORE = 9
            HWND_TOPMOST = -1
            HWND_NOTOPMOST = -2
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_SHOWWINDOW = 0x0040
            VK_MENU = 0x12
            KEYEVENTF_KEYUP = 0x0002

            hwnd_int = int(hwnd)

            # Try several techniques because Windows may block foreground switching.
            for _ in range(3):
                fg_hwnd = int(user32.GetForegroundWindow())
                current_tid = int(user32.GetCurrentThreadId())
                target_tid = int(user32.GetWindowThreadProcessId(hwnd_int, None))
                fg_tid = int(user32.GetWindowThreadProcessId(fg_hwnd, None)) if fg_hwnd else 0

                user32.AllowSetForegroundWindow(-1)
                user32.ShowWindow(hwnd_int, SW_RESTORE)

                if fg_tid:
                    user32.AttachThreadInput(current_tid, fg_tid, True)
                if target_tid:
                    user32.AttachThreadInput(current_tid, target_tid, True)

                # ALT key trick often bypasses foreground lock restrictions.
                user32.keybd_event(VK_MENU, 0, 0, 0)
                user32.SetForegroundWindow(hwnd_int)
                user32.BringWindowToTop(hwnd_int)
                user32.SetWindowPos(hwnd_int, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
                user32.SetWindowPos(hwnd_int, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
                user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)

                if target_tid:
                    user32.AttachThreadInput(current_tid, target_tid, False)
                if fg_tid:
                    user32.AttachThreadInput(current_tid, fg_tid, False)

                if _is_foreground(hwnd_int):
                    ok = True
                    break
                time.sleep(0.12)
        except Exception:
            pass

    return ok


def resolve_target_window(cfg):
    window_title = cfg.get('window_title')
    window_exe = cfg.get('window_exe')

    if window_title:
        return find_window(window_title)
    if window_exe:
        return find_window_by_exe(window_exe)
    return None


def grab_region(bbox):
    if ImageGrab is None:
        raise RuntimeError('Pillow ImageGrab not available. Install Pillow.')
    return ImageGrab.grab(bbox=bbox)


def normalize_region(cfg):
    reg = cfg.get('region', {})
    left = int(reg.get('x', 0))
    top = int(reg.get('y', 0))
    right = left + int(reg.get('width', reg.get('w', 0)))
    bottom = top + int(reg.get('height', reg.get('h', 0)))
    return left, top, right, bottom


class PreviewWindow:
    def __init__(self, title='Capture Preview'):
        if tk is None or ImageTk is None:
            raise RuntimeError('Preview requires tkinter and Pillow ImageTk.')

        self.root = tk.Tk()
        self.root.title(title)
        self.root.attributes('-topmost', True)
        self.root.geometry('700x460')
        self.label = tk.Label(self.root)
        self.label.pack(fill=tk.BOTH, expand=True)
        self.info_var = tk.StringVar(value='Region: N/A')
        self.info_label = tk.Label(self.root, textvariable=self.info_var, anchor='w')
        self.info_label.pack(fill=tk.X)
        self.closed = False
        self.reselection_requested = False
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)
        self.root.bind('<KeyPress-r>', self._on_reselect_key)
        self.root.bind('<KeyPress-R>', self._on_reselect_key)
        self.root.focus_force()

    def _on_close(self):
        self.closed = True
        self.root.destroy()

    def _on_reselect_key(self, _event=None):
        self.reselection_requested = True

    def consume_reselection_request(self):
        requested = self.reselection_requested
        self.reselection_requested = False
        return requested

    def hide(self):
        if not self.closed:
            self.root.withdraw()

    def show(self):
        if not self.closed:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()

    def update(self, image, bbox):
        if self.closed:
            return
        max_w, max_h = 640, 360
        img = image.copy()
        w, h = img.size
        scale = min(max_w / max(w, 1), max_h / max(h, 1), 1.0)
        if scale < 1.0:
            img = img.resize((int(w * scale), int(h * scale)))
        photo = ImageTk.PhotoImage(img)
        self.label.configure(image=photo)
        self.label.image = photo
        left, top, right, bottom = bbox
        w = max(0, right - left)
        h = max(0, bottom - top)
        self.info_var.set(f'Region: x={left}, y={top}, w={w}, h={h} | Press R to reselect')
        self.root.update_idletasks()
        self.root.update()


def update_cfg_region(cfg, mode, left, top, width, height, window=None, window_title=None):
    if mode == 'relative':
        if window is None:
            window = resolve_target_window(cfg)
        if window is None:
            raise RuntimeError('Window not found for relative mode.')
        x = left - window.left
        y = top - window.top
        cfg['window_title'] = window.title
    else:
        x = left
        y = top
        cfg['window_title'] = None

    cfg['region'] = {
        'x': int(x),
        'y': int(y),
        'width': int(width),
        'height': int(height),
    }


def run_capture(cfg, interval, output, preview=False):
    os.makedirs(output, exist_ok=True)

    mode = cfg.get('mode', 'absolute')
    window_title = cfg.get('window_title')
    window_exe = cfg.get('window_exe')
    preview_window = None

    if preview:
        preview_window = PreviewWindow(title='Capture Preview (updates every cycle)')

    print(f"Starting capture (mode={mode}) every {interval}s -> {output}")

    while True:
        try:
            if preview_window is not None and preview_window.consume_reselection_request():
                print('Reselect requested. Starting interactive selection...')
                preview_window.hide()
                try:
                    if mode == 'relative' and (window_title or window_exe):
                        selected_window = resolve_target_window(cfg)
                        if selected_window is None:
                            raise RuntimeError('Window not found for current profile.')
                        focus_window(selected_window)
                        time.sleep(0.2)
                    else:
                        selected_window = None

                    left_sel, top_sel, width_sel, height_sel = select_region_with_mouse(selected_window)
                    update_cfg_region(
                        cfg,
                        mode,
                        left_sel,
                        top_sel,
                        width_sel,
                        height_sel,
                        window=selected_window,
                        window_title=window_title,
                    )
                    window_title = cfg.get('window_title')
                    window_exe = cfg.get('window_exe')
                    print('Region updated from preview reselect.')
                except Exception as e:
                    print(f'Reselect cancelled or failed: {e}')
                finally:
                    preview_window.show()

            if mode == 'relative' and (window_title or window_exe):
                w = resolve_target_window(cfg)
                if w is None:
                    key = window_title if window_title else window_exe
                    print(f"Window target '{key}' not found. Retrying...")
                    time.sleep(interval)
                    continue
                rel_left, rel_top, rel_right, rel_bottom = normalize_region(cfg)
                left = w.left + rel_left
                top = w.top + rel_top
                right = w.left + rel_right
                bottom = w.top + rel_bottom
            else:
                left, top, right, bottom = normalize_region(cfg)

            img = grab_region((left, top, right, bottom))
            if preview_window is not None:
                try:
                    preview_window.update(img, (left, top, right, bottom))
                except Exception as e:
                    print(f'Preview update failed: {e}')
                    preview_window = None
            ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            filename = os.path.join(output, f'capture_{ts}.png')
            img.save(filename)
            print(f'Saved {filename}')
        except KeyboardInterrupt:
            print('Stopping capture.')
            break
        except Exception as e:
            print('Capture error:', e)
        time.sleep(interval)


def build_config_from_args(args):
    return {
        'mode': args.mode,
        'window_title': args.window_title,
        'window_exe': args.window_exe,
        'region': {
            'x': args.x,
            'y': args.y,
            'width': args.width,
            'height': args.height,
        },
    }


def list_window_titles():
    if gw is None:
        return []
    titles = []
    seen = set()
    for title in gw.getAllTitles():
        t = title.strip()
        if not t:
            continue
        if t in seen:
            continue
        seen.add(t)
        titles.append(t)
    return titles


def choose_window_title_interactive():
    titles = list_window_titles()
    if not titles:
        raise RuntimeError('No window titles found. Please open the game window first.')

    print('Select a window:')
    for i, t in enumerate(titles, start=1):
        print(f'[{i}] {t}')

    while True:
        raw = input('Window index (or type a custom title): ').strip()
        if not raw:
            continue
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(titles):
                return titles[idx - 1]
            print('Index out of range, try again.')
            continue
        return raw


def select_region_with_mouse(window=None):
    if ImageGrab is None or ImageTk is None:
        raise RuntimeError('Pillow ImageGrab/ImageTk not available. Install Pillow.')
    if tk is None:
        raise RuntimeError('tkinter is not available in this Python environment.')

    screenshot = ImageGrab.grab()
    width, height = screenshot.size

    state = {
        'start': None,
        'end': None,
        'rect_id': None,
        'done': False,
        'cancelled': False,
    }

    root = tk.Tk()
    root.title('Select Capture Region')
    root.attributes('-topmost', True)
    root.geometry(f'{width}x{height}+0+0')
    root.attributes('-fullscreen', True)

    photo = ImageTk.PhotoImage(screenshot)
    canvas = tk.Canvas(root, width=width, height=height, highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    canvas.create_image(0, 0, anchor=tk.NW, image=photo)

    tips = 'Drag mouse to select region. Enter=confirm, Esc=cancel'
    canvas.create_text(
        12,
        12,
        anchor=tk.NW,
        text=tips,
        fill='yellow',
        font=('Segoe UI', 14, 'bold'),
    )

    if window is not None:
        l, t, r, b = window.left, window.top, window.right, window.bottom
        canvas.create_rectangle(l, t, r, b, outline='cyan', width=2)
        canvas.create_text(
            l + 8,
            t + 8,
            anchor=tk.NW,
            text='Window Bounds',
            fill='cyan',
            font=('Segoe UI', 12, 'bold'),
        )

    def on_down(event):
        state['start'] = (event.x, event.y)
        state['end'] = (event.x, event.y)
        if state['rect_id'] is not None:
            canvas.delete(state['rect_id'])
        state['rect_id'] = canvas.create_rectangle(
            event.x,
            event.y,
            event.x,
            event.y,
            outline='red',
            width=2,
        )

    def on_move(event):
        if state['start'] is None or state['rect_id'] is None:
            return
        state['end'] = (event.x, event.y)
        x1, y1 = state['start']
        x2, y2 = state['end']
        canvas.coords(state['rect_id'], x1, y1, x2, y2)

    def on_up(event):
        if state['start'] is None:
            return
        state['end'] = (event.x, event.y)

    def on_confirm(_event=None):
        if state['start'] is None or state['end'] is None:
            print('No selection made yet.')
            return
        state['done'] = True
        root.destroy()

    def on_cancel(_event=None):
        state['cancelled'] = True
        root.destroy()

    canvas.bind('<ButtonPress-1>', on_down)
    canvas.bind('<B1-Motion>', on_move)
    canvas.bind('<ButtonRelease-1>', on_up)
    root.bind('<Return>', on_confirm)
    root.bind('<Escape>', on_cancel)

    root.mainloop()

    if state['cancelled']:
        raise RuntimeError('Selection cancelled.')
    if not state['done']:
        raise RuntimeError('Selection not confirmed.')

    x1, y1 = state['start']
    x2, y2 = state['end']
    left = min(x1, x2)
    top = min(y1, y2)
    right = max(x1, x2)
    bottom = max(y1, y2)
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        raise RuntimeError('Invalid selection size.')

    return left, top, width, height


def create_profile_interactive(args):
    mode = args.mode
    selected_window_title = None
    selected_window_exe = args.window_exe
    selected_window = None

    if mode == 'relative':
        if selected_window_exe:
            selected_window = find_window_by_exe(selected_window_exe)
            if selected_window is None:
                raise RuntimeError(f"Window for exe '{selected_window_exe}' not found.")
            selected_window_title = selected_window.title
        else:
            selected_window_title = choose_window_title_interactive()
            selected_window = find_window(selected_window_title)
        if selected_window is None:
            raise RuntimeError(f"Window '{selected_window_title}' not found.")

        focused = focus_window(selected_window)
        if not focused:
            print('Warning: failed to force window foreground, please click game window manually.')
        time.sleep(args.focus_delay)

    print('Switch to game window if needed, then drag to select region...')
    left, top, width, height = select_region_with_mouse(selected_window)

    if mode == 'relative':
        x = left - selected_window.left
        y = top - selected_window.top
        window_title = selected_window_title
    else:
        x = left
        y = top
        window_title = None

    return {
        'mode': mode,
        'window_title': window_title,
        'window_exe': selected_window_exe if mode == 'relative' else None,
        'region': {
            'x': int(x),
            'y': int(y),
            'width': int(width),
            'height': int(height),
        },
    }


def handle_config_command(args):
    file_path = args.file
    if args.config_action == 'init':
        if os.path.exists(file_path):
            print(f'Profiles file already exists: {file_path}')
            return
        save_profiles(file_path, {})
        print(f'Created profiles file: {file_path}')
        return

    profiles = load_profiles(file_path)

    if args.config_action == 'list':
        if not profiles:
            print('No profiles found.')
            return
        print('Profiles:')
        for name in sorted(profiles.keys()):
            mode = profiles[name].get('mode', 'absolute')
            print(f'- {name} (mode={mode})')
        return

    if args.config_action == 'show':
        cfg = profiles.get(args.name)
        if cfg is None:
            raise ValueError(f'Profile not found: {args.name}')
        print(json.dumps(cfg, ensure_ascii=False, indent=2))
        return

    if args.config_action == 'add':
        profiles[args.name] = build_config_from_args(args)
        save_profiles(file_path, profiles)
        print(f'Profile saved: {args.name}')
        return

    if args.config_action == 'interactive-add':
        profiles[args.name] = create_profile_interactive(args)
        save_profiles(file_path, profiles)
        print(f'Profile saved (interactive): {args.name}')
        print(json.dumps(profiles[args.name], ensure_ascii=False, indent=2))
        return

    if args.config_action == 'remove':
        if args.name not in profiles:
            raise ValueError(f'Profile not found: {args.name}')
        del profiles[args.name]
        save_profiles(file_path, profiles)
        print(f'Profile removed: {args.name}')
        return

    raise ValueError(f'Unknown config action: {args.config_action}')


def resolve_run_config(args):
    if args.config:
        return load_config(args.config)
    if args.profile:
        profiles = load_profiles(args.profiles_file)
        cfg = profiles.get(args.profile)
        if cfg is None:
            raise ValueError(f'Profile not found: {args.profile}')
        return cfg
    raise ValueError('Please provide --config or --profile')


def build_parser():
    parser = argparse.ArgumentParser(description='Simple capture backend')
    sub = parser.add_subparsers(dest='command')

    run_parser = sub.add_parser('run', help='Run capture loop')
    run_parser.add_argument('--config', '-c', help='Path to single JSON config')
    run_parser.add_argument('--profile', '-p', help='Profile name in profiles file')
    run_parser.add_argument('--profiles-file', default='capture_profiles.json', help='Profiles JSON file')
    run_parser.add_argument('--interval', '-i', type=float, default=1.0, help='Seconds between captures')
    run_parser.add_argument('--output', '-o', default='captures', help='Output directory')
    run_parser.add_argument('--preview', action='store_true', help='Show live preview window of captured region')

    config_parser = sub.add_parser('config', help='Manage capture profiles')
    config_sub = config_parser.add_subparsers(dest='config_action', required=True)

    init_parser = config_sub.add_parser('init', help='Create empty profiles file')
    init_parser.add_argument('--file', default='capture_profiles.json', help='Profiles JSON file')

    list_parser = config_sub.add_parser('list', help='List profiles')
    list_parser.add_argument('--file', default='capture_profiles.json', help='Profiles JSON file')

    show_parser = config_sub.add_parser('show', help='Show a profile')
    show_parser.add_argument('name', help='Profile name')
    show_parser.add_argument('--file', default='capture_profiles.json', help='Profiles JSON file')

    add_parser = config_sub.add_parser('add', help='Add or update a profile')
    add_parser.add_argument('name', help='Profile name')
    add_parser.add_argument('--file', default='capture_profiles.json', help='Profiles JSON file')
    add_parser.add_argument('--mode', choices=['relative', 'absolute'], default='relative')
    add_parser.add_argument('--window-title', default='Roco Kingdom')
    add_parser.add_argument('--window-exe', default=None, help='Target executable name, e.g. NRC-Win64-Shipping.exe')
    add_parser.add_argument('--x', type=int, required=True)
    add_parser.add_argument('--y', type=int, required=True)
    add_parser.add_argument('--width', type=int, required=True)
    add_parser.add_argument('--height', type=int, required=True)

    interactive_add_parser = config_sub.add_parser('interactive-add', help='Interactively select window and region')
    interactive_add_parser.add_argument('name', help='Profile name')
    interactive_add_parser.add_argument('--file', default='capture_profiles.json', help='Profiles JSON file')
    interactive_add_parser.add_argument('--mode', choices=['relative', 'absolute'], default='relative')
    interactive_add_parser.add_argument('--window-exe', default=None, help='Target executable name, e.g. NRC-Win64-Shipping.exe')
    interactive_add_parser.add_argument('--focus-delay', type=float, default=0.35, help='Seconds to wait after focus before selection')

    remove_parser = config_sub.add_parser('remove', help='Remove a profile')
    remove_parser.add_argument('name', help='Profile name')
    remove_parser.add_argument('--file', default='capture_profiles.json', help='Profiles JSON file')

    return parser


def main():
    parser = build_parser()

    # Backward compatibility: if no subcommand is provided, treat as 'run'.
    subcommands = {'run', 'config'}
    argv = sys.argv[1:]
    if argv and argv[0] not in subcommands:
        argv = ['run'] + argv
    elif not argv:
        parser.print_help()
        return

    args = parser.parse_args(argv)

    if args.command == 'config':
        handle_config_command(args)
        return

    cfg = resolve_run_config(args)
    run_capture(cfg, args.interval, args.output, preview=args.preview)


if __name__ == '__main__':
    main()
