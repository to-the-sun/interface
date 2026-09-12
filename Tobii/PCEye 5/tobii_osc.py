import sys
import time
import math
import argparse

try:
    import tobii_research as tr
except (ImportError, ModuleNotFoundError):
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print("=" * 72)
    print("ERROR: Failed to import 'tobii_research'.")
    print(f"Current Python version: {py_ver}")
    print("\n'tobii-research' (Tobii Pro SDK) only provides pre-compiled wheels")
    print("on PyPI for Python 3.10 (and 3.8) 64-bit.")
    print("It does NOT support Python 3.11, 3.12, or newer versions.")
    print("\nPlease ensure you are running Python 3.10 (64-bit):")
    print("  1. Download Python 3.10: https://www.python.org/downloads/release/python-31011/")
    print("  2. Install dependencies: py -3.10 -m pip install -r requirements.txt")
    print("  3. Run script: py -3.10 tobii_osc.py")
    print("=" * 72)
    if sys.platform == "win32":
        input("\nPress Enter to exit...")
    sys.exit(1)

try:
    from pythonosc import udp_client
except (ImportError, ModuleNotFoundError):
    print("=" * 72)
    print("ERROR: Failed to import 'pythonosc'.")
    print("Please install required dependencies with:")
    print("  pip install -r requirements.txt")
    print("=" * 72)
    if sys.platform == "win32":
        input("\nPress Enter to exit...")
    sys.exit(1)

try:
    from pynput.mouse import Controller as MouseController
    mouse_controller = MouseController()
except Exception:
    mouse_controller = None

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

def gaze_data_callback(gaze_data, client, move_mouse=True, screen_size=(1920, 1080), debug=False):
    """
    Callback function that is called every time new gaze data is received.
    Streams the data via OSC and optionally moves mouse cursor onscreen.
    """
    global stats
    stats['total_frames'] += 1

    try:
        # Extract left and right gaze points on the display area (normalized 0.0 to 1.0)
        try:
            left_eye = gaze_data.left_gaze_point_on_display_area
            right_eye = gaze_data.right_gaze_point_on_display_area
        except (AttributeError, TypeError):
            left_eye = gaze_data['left_gaze_point_on_display_area']
            right_eye = gaze_data['right_gaze_point_on_display_area']

        lx, ly = left_eye
        rx, ry = right_eye

        # Check for validity (NaN indicates the eye was not tracked)
        valid_l = not (math.isnan(lx) or math.isnan(ly))
        valid_r = not (math.isnan(rx) or math.isnan(ry))

        if valid_l:
            stats['valid_left'] += 1
        if valid_r:
            stats['valid_right'] += 1

        avg_x = None
        avg_y = None

        if valid_l and valid_r:
            stats['valid_avg'] += 1
            # Calculate average gaze point
            avg_x = (lx + rx) / 2.0
            avg_y = (ly + ry) / 2.0

            # Send average gaze (Normalized 0.0 to 1.0)
            client.send_message("/Tobii/gaze_x", float(avg_x))
            client.send_message("/Tobii/gaze_y", float(avg_y))

            # Compatibility with OpenFace 3.0 / OpenFace Lite addresses
            # OpenFace Lite expects approximate degrees.
            # Map 0.5 center to 0, 0.0 to -30, 1.0 to 30.
            # Note: Y is usually inverted in screen space (0 top, 1 bottom)
            client.send_message("/OpenFace/gaze_left_right", float((avg_x - 0.5) * 60.0))
            client.send_message("/OpenFace/gaze_up_down", float((avg_y - 0.5) * -60.0))
        elif valid_l:
            avg_x, avg_y = lx, ly
        elif valid_r:
            avg_x, avg_y = rx, ry

        if valid_l:
            client.send_message("/Tobii/left/gaze_x", float(lx))
            client.send_message("/Tobii/left/gaze_y", float(ly))

        if valid_r:
            client.send_message("/Tobii/right/gaze_x", float(rx))
            client.send_message("/Tobii/right/gaze_y", float(ry))

        # Optional: Pupil Diameter
        try:
            lp = gaze_data.left_pupil_diameter
            rp = gaze_data.right_pupil_diameter
        except (AttributeError, TypeError):
            lp = gaze_data.get('left_pupil_diameter', float('nan'))
            rp = gaze_data.get('right_pupil_diameter', float('nan'))

        if not math.isnan(lp):
            client.send_message("/Tobii/left/pupil_diameter", float(lp))
        if not math.isnan(rp):
            client.send_message("/Tobii/right/pupil_diameter", float(rp))

        stats['last_gaze_raw'] = (lx, ly, rx, ry)

        # Move mouse cursor using gaze data
        if move_mouse and mouse_controller is not None:
            if avg_x is not None and avg_y is not None:
                target_x = max(0.0, min(1.0, avg_x))
                target_y = max(0.0, min(1.0, avg_y))
                sw, sh = screen_size
                px = int(target_x * sw)
                py = int(target_y * sh)
                stats['last_target_pixel'] = (px, py)
                try:
                    mouse_controller.position = (px, py)
                    stats['mouse_moves'] += 1
                except Exception as e:
                    stats['mouse_errors'] += 1
                    stats['last_error'] = f"Failed to set mouse position ({px}, {py}): {e}"
                    if debug:
                        print(f"[DEBUG Error] Mouse position failed: {e}")
            else:
                if debug and (stats['total_frames'] % 30 == 0):
                    print(f"[DEBUG] Gaze callback received but coordinates are NaN/invalid. L: ({lx}, {ly}), R: ({rx}, {ry})")

        if debug and (stats['total_frames'] % 30 == 0):
            print(f"[DEBUG Frame {stats['total_frames']}] Left: ({lx:.3f}, {ly:.3f}), Right: ({rx:.3f}, {ry:.3f}), Avg: ({'N/A' if avg_x is None else f'{avg_x:.3f}'}, {'N/A' if avg_y is None else f'{avg_y:.3f}'}), Mouse Target: {stats.get('last_target_pixel')}")

    except Exception as e:
        stats['last_error'] = f"Callback processing error: {e}"
        if debug:
            print(f"[DEBUG Error] Exception in gaze_data_callback: {e}")

def main():
    parser = argparse.ArgumentParser(description='Stream Tobii PCEye 5 gaze data to OSC and control mouse cursor')
    parser.add_argument('--ip', type=str, default=DEFAULT_IP, help='OSC Destination IP (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='OSC Destination Port (default: 6731)')
    parser.add_argument('--no-mouse', action='store_true', help='Disable moving mouse cursor onscreen using gaze data')
    parser.add_argument('--debug', action='store_true', help='Enable verbose per-frame debug logging')
    args = parser.parse_args()

    client = udp_client.SimpleUDPClient(args.ip, args.port)

    move_mouse = not args.no_mouse
    if move_mouse:
        if mouse_controller is None:
            print("[Warning] pynput mouse controller could not be initialized; mouse control disabled.")
            move_mouse = False
        else:
            try:
                curr_pos = mouse_controller.position
                print(f"[Mouse Debug] pynput Mouse Controller active. Current cursor position: {curr_pos}")
            except Exception as e:
                print(f"[Mouse Debug] pynput initialized but getting position returned error: {e}")

    screen_size = get_screen_size()

    print("Searching for Tobii eye trackers...")
    try:
        found_eyetrackers = tr.find_all_eyetrackers()
    except Exception as e:
        print(f"Error searching for eye trackers: {e}")
        sys.exit(1)

    if len(found_eyetrackers) == 0:
        print("No Tobii eye trackers found!")
        print("\nTroubleshooting:")
        print("1. Ensure the Tobii Runtime (or TD Control for PCEye 5) is running.")
        print("2. Check if the device is plugged in and calibrated.")
        print("3. Note: The consumer 'Eye Tracker 5' is NOT supported by this SDK unless it has a Pro Upgrade.")
        sys.exit(1)

    eyetracker = found_eyetrackers[0]
    print(f"--- Connected Device ---")
    print(f"Model: {eyetracker.model}")
    print(f"Serial: {eyetracker.serial_number}")
    print(f"Address: {eyetracker.address}")
    print(f"------------------------")
    print(f"Streaming gaze data to {args.ip}:{args.port}...")
    if move_mouse:
        print(f"Mouse cursor movement: ENABLED (Screen resolution: {screen_size[0]}x{screen_size[1]})")
    else:
        print("Mouse cursor movement: DISABLED")
    print("Press Ctrl+C to stop.")

    # Subscribe to gaze data
    eyetracker.subscribe_to(tr.EYETRACKER_GAZE_DATA,
                            lambda x: gaze_data_callback(x, client, move_mouse=move_mouse, screen_size=screen_size, debug=args.debug))

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

            print(f"[STATUS] Frames: {stats['total_frames']} ({fps:.1f} fps) | Valid L: {stats['valid_left']} | Valid R: {stats['valid_right']} | Valid Avg: {stats['valid_avg']} | Mouse Moves: {stats['mouse_moves']}")
            if stats['total_frames'] == 0:
                print("  -> WARNING: No gaze data callbacks received yet from Tobii eye tracker.")
                print("     Ensure TD Control / Tobii Service is running and the PCEye 5 is connected.")
            elif stats['valid_avg'] == 0:
                print("  -> WARNING: Gaze callbacks ARE running, but gaze coordinates are NaN.")
                print("     Ensure you are sitting within range (18-30 inches) and calibrated in TD Control.")
            elif move_mouse and stats['mouse_moves'] == 0:
                print("  -> WARNING: Valid gaze data received, but mouse moved 0 times.")
                if mouse_controller is None:
                    print("     Reason: pynput mouse controller is None.")
                if stats['last_error']:
                    print(f"     Reason: {stats['last_error']}")
            if stats['last_error']:
                print(f"  -> Last Error: {stats['last_error']}")

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        eyetracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA)
        print("Successfully unsubscribed from eye tracker.")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
