import sys
import time
import math
import argparse

# Windows Gaze Input API (winsdk)
try:
    import winsdk.windows.devices.input.preview as win_gaze_preview
    HAS_WINSDK_GAZE = True
except (ImportError, ModuleNotFoundError):
    win_gaze_preview = None
    HAS_WINSDK_GAZE = False

# OSC library
try:
    from pythonosc import udp_client
    HAS_OSC = True
except (ImportError, ModuleNotFoundError):
    udp_client = None
    HAS_OSC = False

# Mouse fallback controller
try:
    from pynput.mouse import Controller as MouseController
    mouse_controller = MouseController()
    HAS_PYNPUT = True
except Exception:
    mouse_controller = None
    HAS_PYNPUT = False

# OSC Configuration
DEFAULT_IP = "127.0.0.1"
DEFAULT_PORT = 6731

# Diagnostics & Statistics
stats = {
    'total_frames': 0,
    'valid_left': 0,
    'valid_right': 0,
    'valid_avg': 0,
    'mouse_moves': 0,
    'mouse_errors': 0,
    'last_error': None,
    'last_gaze_raw': None,
    'last_target_pixel': None,
}

def get_screen_size():
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass
            w, h = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
            if w > 0 and h > 0:
                return w, h
        except Exception:
            pass
    try:
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        root.destroy()
        if w > 0 and h > 0:
            return w, h
    except Exception:
        pass
    return 1920, 1080

def set_cursor_pos(px, py):
    """
    Sets system mouse cursor position using Windows SetCursorPos API (ctypes)
    or pynput fallback.
    """
    if sys.platform == "win32":
        try:
            import ctypes
            if ctypes.windll.user32.SetCursorPos(int(px), int(py)):
                return True
        except Exception:
            pass
    if mouse_controller is not None:
        try:
            mouse_controller.position = (int(px), int(py))
            return True
        except Exception:
            pass
    return False

def run_windows_gaze(client, move_mouse=True, screen_size=(1920, 1080), debug=False):
    """
    Starts streaming gaze data using Microsoft's Windows.Devices.Input.Preview Gaze API.
    Returns (gaze_source, token) or None on failure.
    """
    global stats
    if sys.platform != "win32":
        print("ERROR: Windows Gaze Input API (Windows.Devices.Input.Preview) is only supported on Windows platform.")
        return None

    if not HAS_WINSDK_GAZE:
        print("=" * 72)
        print("ERROR: Failed to import 'winsdk'.")
        print("Windows Gaze Input API requires the 'winsdk' package.")
        print("Please install required dependencies with:")
        print("  pip install winsdk python-osc pynput")
        print("=" * 72)
        return None

    print("Initializing Microsoft Windows Gaze Input API (Windows.Devices.Input.Preview)...")
    try:
        import asyncio
        async def check_access():
            return await win_gaze_preview.GazeInputSourcePreview.request_access_async()

        try:
            access_status = asyncio.run(check_access())
        except Exception:
            access_status = win_gaze_preview.GazeInputSourcePreview.request_access_async().get_results()

        print(f"Windows Gaze Access Status: {access_status}")
        if access_status != win_gaze_preview.GazeInputAccessStatus.ALLOWED:
            print(f"WARNING: Windows Gaze Input access status is '{access_status}'.")
            print("Ensure Eye Tracking capability is permitted under Windows Privacy Settings (Settings -> Privacy & Security -> Eye tracker).")

        gaze_source = win_gaze_preview.GazeInputSourcePreview.get_for_current_view()
        if gaze_source is None:
            print("ERROR: GazeInputSourcePreview.get_for_current_view() returned None.")
            print("Ensure PCEye 5 / Gaze device is recognized by Windows as an input device.")
            return None

    except Exception as e:
        print(f"Failed to initialize Windows Gaze Input API: {e}")
        return None

    def on_gaze_moved(sender, args):
        global stats
        stats['total_frames'] += 1
        try:
            cp = getattr(args, 'current_point', None)
            if cp is None:
                return

            eye_pos = getattr(cp, 'eye_gaze_position_in_pixels', None)
            if eye_pos is None:
                if debug and (stats['total_frames'] % 30 == 0):
                    print(f"[DEBUG Frame {stats['total_frames']}] Gaze moved but eye position is None.")
                return

            px = float(eye_pos.x)
            py = float(eye_pos.y)

            sw, sh = screen_size
            avg_x = max(0.0, min(1.0, px / sw)) if sw > 0 else 0.5
            avg_y = max(0.0, min(1.0, py / sh)) if sh > 0 else 0.5

            stats['valid_avg'] += 1
            stats['valid_left'] += 1
            stats['valid_right'] += 1
            stats['last_gaze_raw'] = (avg_x, avg_y, avg_x, avg_y)

            if client:
                client.send_message("/Tobii/gaze_x", float(avg_x))
                client.send_message("/Tobii/gaze_y", float(avg_y))
                client.send_message("/OpenFace/gaze_left_right", float((avg_x - 0.5) * 60.0))
                client.send_message("/OpenFace/gaze_up_down", float((avg_y - 0.5) * -60.0))

            target_pixel = (int(px), int(py))
            stats['last_target_pixel'] = target_pixel

            if move_mouse:
                if set_cursor_pos(px, py):
                    stats['mouse_moves'] += 1
                else:
                    stats['mouse_errors'] += 1
                    stats['last_error'] = f"Failed to set mouse position ({px}, {py})"

            if debug and (stats['total_frames'] % 30 == 0):
                print(f"[DEBUG Frame {stats['total_frames']}] WinGaze Pixel: ({px:.1f}, {py:.1f}), Avg: ({avg_x:.3f}, {avg_y:.3f}), Mouse Target: {target_pixel}")

        except Exception as e:
            stats['last_error'] = f"WinGaze Callback error: {e}"
            if debug:
                print(f"[DEBUG Error] Exception in WinGaze callback: {e}")

    try:
        token = gaze_source.add_gaze_moved(on_gaze_moved)
        print("Subscribed to Windows Gaze Input API gaze_moved events.")
        return (gaze_source, token)
    except Exception as e:
        print(f"Error subscribing to gaze_moved events: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Stream Windows Gaze Input API (PCEye 5) gaze data to OSC and control mouse cursor')
    parser.add_argument('--ip', type=str, default=DEFAULT_IP, help='OSC Destination IP (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='OSC Destination Port (default: 6731)')
    parser.add_argument('--no-mouse', action='store_true', help='Disable moving mouse cursor onscreen using gaze data')
    parser.add_argument('--debug', action='store_true', help='Enable verbose per-frame debug logging')
    args = parser.parse_args()

    if not HAS_OSC:
        print("=" * 72)
        print("ERROR: Failed to import 'pythonosc'.")
        print("Please install required dependencies with:")
        print("  pip install -r requirements.txt")
        print("=" * 72)
        if sys.platform == "win32":
            input("\nPress Enter to exit...")
        sys.exit(1)

    client = udp_client.SimpleUDPClient(args.ip, args.port)
    move_mouse = not args.no_mouse
    screen_size = get_screen_size()

    print("=== Microsoft Windows Gaze Input API (Windows.Devices.Input.Preview) Mode ===")
    if move_mouse:
        print(f"[Mouse Control] Mouse control enabled (SetCursorPos). Target resolution: {screen_size[0]}x{screen_size[1]}")
    else:
        print("[Mouse Control] Mouse control disabled.")

    win_gaze_handle = run_windows_gaze(client, move_mouse=move_mouse, screen_size=screen_size, debug=args.debug)
    if win_gaze_handle is None:
        print("\nFailed to initialize Windows Gaze Input API.")
        print("Troubleshooting:")
        print("1. Ensure Windows 10/11 is running with an eye tracker registered as a gaze device.")
        print("2. Verify Eye Tracking permission under Windows Settings -> Privacy & Security -> Eye tracker.")
        if sys.platform == "win32":
            input("\nPress Enter to exit...")
        sys.exit(1)

    print(f"Streaming gaze data to {args.ip}:{args.port}...")
    print("Press Ctrl+C to stop.")

    print("\n--- Diagnostic & Heartbeat Monitor Active ---")
    if args.debug:
        print("Verbose debug mode enabled (--debug). Printouts occur periodically per-frame.")
    print("Monitoring incoming gaze frames and mouse cursor updates...\n")

    last_stat_time = time.time()
    last_frame_count = 0

    try:
        while True:
            time.sleep(2)
            now = time.time()
            dt = now - last_stat_time
            frames_delta = stats['total_frames'] - last_frame_count
            fps = frames_delta / dt if dt > 0 else 0
            last_stat_time = now
            last_frame_count = stats['total_frames']

            print(f"[STATUS] Windows Gaze API | Frames: {stats['total_frames']} ({fps:.1f} fps) | Valid Avg: {stats['valid_avg']} | Mouse Moves: {stats['mouse_moves']}")
            if stats['total_frames'] == 0:
                print("  -> WARNING: No gaze data callbacks received yet from Windows Gaze Input API.")
                print("     Ensure PCEye 5 is registered and permitted under Windows Eye Tracker settings.")
            elif move_mouse and stats['mouse_moves'] == 0:
                print("  -> WARNING: Valid gaze data received, but mouse moved 0 times.")
                if stats['last_error']:
                    print(f"     Reason: {stats['last_error']}")
            if stats['last_error']:
                print(f"  -> Last Error: {stats['last_error']}")

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        if win_gaze_handle is not None:
            try:
                gaze_src, token = win_gaze_handle
                gaze_src.remove_gaze_moved(token)
                print("Successfully unsubscribed from Windows Gaze Input API.")
            except Exception:
                pass

if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
