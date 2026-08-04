#!/usr/bin/env python3
"""
MIDI to Input Control Script
----------------------------
This script listens to a MIDI input (virtual port or LoopMIDI port) and translates
specific MIDI notes to mouse clicks, mouse dragging, and keyboard events.

Requirements:
- When a MIDI NOTE ON is received for pitch 127, generate a left click
- When a MIDI NOTE ON is received for pitch 126, generate a right click
- When a MIDI NOTE ON is received for pitch 125, generate a double click
- When a MIDI NOTE ON is received for pitch 124, initiate a drag, and when a MIDI note off is received for pitch 124, conclude the drag
- When a MIDI NOTE ON is received for pitch 123, simulate a key press of the F4 hotkey and change the `mode` to `paused`
- When a MIDI NOTE ON is received for pitch 122, simulate a key press of the F4 hotkey and change the `mode` to `frozen`
- If the mouse is frozen in place and has no movement at all, all of these functions should be disabled except for receiving a NOTE ON for pitch 123 if in `paused` mode, or receiving a NOTE ON for pitch 122 if in `paused` or `frozen` mode.

The script posts descriptive messages to the console when any functions are triggered or ignored.
"""

import os
import sys
import time
import argparse
import threading
import traceback

def is_admin():
    """Checks if the script is running with administrator privileges."""
    if sys.platform != 'win32':
        return True
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def elevate_privileges():
    """Restarts the script with administrator privileges if on Windows and not already admin."""
    if sys.platform == 'win32' and not is_admin():
        import ctypes
        print("[*] Detected non-administrator execution.")
        print("[*] Administrative privileges are required to click/keypress inside restricted windows like Task Manager, PowerShell, or On-Screen Keyboards.")
        print("[*] Elevating privileges via Windows UAC Prompt...")
        time.sleep(1.5)
        
        # Prepare arguments
        script = os.path.abspath(sys.argv[0])
        params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        
        try:
            # Re-run with admin privileges
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
            if int(ret) > 32:
                # Successfully launched elevated instance, exit this one
                sys.exit(0)
            else:
                print(f"[!] UAC Elevation failed with return code {ret}.")
        except Exception as e:
            print(f"[!] UAC Elevation failed: {e}")
            print("[*] Continuing without administrator privileges...")

def run_script():
    # Detect the python-rtmidi vs rtmidi package conflict before importing mido
    try:
        import rtmidi
        if not hasattr(rtmidi, 'API_UNSPECIFIED'):
            raise ImportError(
                "The incorrect 'rtmidi' package is installed instead of the correct 'python-rtmidi' package.\n"
                "This namespace conflict causes 'mido' to fail with an AttributeError.\n\n"
                "To resolve this issue, please close this window and run the following commands in your command prompt/terminal:\n"
                "  pip uninstall rtmidi\n"
                "  pip install python-rtmidi"
            )
    except ImportError as e:
        # If rtmidi isn't installed at all, mido will fail below anyway, which is caught correctly
        pass

    try:
        import mido
    except ImportError as e:
        raise ImportError(
            f"The 'mido' library is not installed.\n"
            f"Please run 'pip install mido python-rtmidi' to install the required MIDI dependencies."
        ) from e

    # Attempt to import pynput, fall back to mocks if X11 is not available (headless/testing env)
    try:
        from pynput.mouse import Button, Controller as MouseController
        from pynput.keyboard import Key, Controller as KeyboardController
        PYNPUT_AVAILABLE = True
    except Exception as e:
        PYNPUT_AVAILABLE = False
        print(f"[*] Warning: pynput could not be initialized ({e}). "
              f"Mouse and keyboard inputs will be mocked for testing/headless execution.")
        
        # Mock classes to allow headless test runs
        class Button:
            left = "left"
            right = "right"
        class Key:
            f4 = "f4"
        class MouseController:
            def __init__(self):
                self._position = (0, 0)
            @property
            def position(self):
                return self._position
            @position.setter
            def position(self, pos):
                self._position = pos
            def click(self, button, count=1):
                print(f"[Mock Mouse] Click {button} x{count}")
            def press(self, button):
                print(f"[Mock Mouse] Press {button}")
            def release(self, button):
                print(f"[Mock Mouse] Release {button}")
        class KeyboardController:
            def press(self, key):
                print(f"[Mock Keyboard] Press {key}")
            def release(self, key):
                print(f"[Mock Keyboard] Release {key}")

    class MouseMonitor(threading.Thread):
        """
        Monitors mouse movement.
        Tracks whether the mouse is stationary (frozen) based on a threshold duration.
        """
        def __init__(self, mouse_controller, interval=0.05, frozen_threshold=1.0):
            super().__init__(daemon=True)
            self.mouse = mouse_controller
            self.interval = interval
            self.frozen_threshold = frozen_threshold
            
            # Initialize position
            try:
                self.last_pos = self.mouse.position
            except Exception:
                self.last_pos = (0, 0)
                
            self.last_move_time = time.time()
            self.lock = threading.Lock()
            self.running = True

        def run(self):
            while self.running:
                try:
                    curr_pos = self.mouse.position
                    if curr_pos != self.last_pos:
                        with self.lock:
                            self.last_pos = curr_pos
                            self.last_move_time = time.time()
                except Exception:
                    pass
                time.sleep(self.interval)

        def is_frozen(self):
            with self.lock:
                elapsed = time.time() - self.last_move_time
                return elapsed > self.frozen_threshold

    class MidiInputController:
        """
        Processes incoming MIDI messages and triggers actions according to defined rules.
        """
        def __init__(self, mouse_controller, keyboard_controller, is_frozen_func):
            self.mouse = mouse_controller
            self.keyboard = keyboard_controller
            self.is_frozen_func = is_frozen_func
            
            self.mode = "active"  # Initial mode: "active" (can be "paused" or "frozen")
            self.is_dragging = False

        def handle_midi_message(self, msg):
            # We only care about note_on and note_off
            if msg.type not in ('note_on', 'note_off'):
                return

            pitch = msg.note
            velocity = getattr(msg, 'velocity', 0)
            
            is_note_on = (msg.type == 'note_on' and velocity > 0)
            is_note_off = (msg.type == 'note_off' or (msg.type == 'note_on' and velocity == 0))

            if not (is_note_on or is_note_off):
                return

            # Determine if mouse is frozen (no movement at all)
            frozen = self.is_frozen_func()

            if frozen:
                # Check for the allowed exceptions:
                # - Pitch 123 NOTE ON if in 'paused' mode
                # - Pitch 122 NOTE ON if in 'paused' or 'frozen' mode
                allowed = False
                if is_note_on:
                    if pitch == 123 and self.mode == "paused":
                        allowed = True
                    elif pitch == 122 and self.mode in ("paused", "frozen"):
                        allowed = True

                if not allowed:
                    # If it's one of our mapped pitches, log that it was ignored
                    if pitch in (122, 123, 124, 125, 126, 127):
                        print(f"[Ignored] MIDI {msg.type.upper()} for pitch {pitch} IGNORED. Mouse is frozen (Mode: '{self.mode}').")
                    return

            # Execute actions if allowed (either mouse is not frozen, or it's an exception case)
            if is_note_on:
                if pitch == 127:
                    print(f"[Triggered] Left Click (Pitch {pitch})")
                    self.mouse.click(Button.left, 1)
                elif pitch == 126:
                    print(f"[Triggered] Right Click (Pitch {pitch})")
                    self.mouse.click(Button.right, 1)
                elif pitch == 125:
                    print(f"[Triggered] Double Click (Pitch {pitch})")
                    self.mouse.click(Button.left, 2)
                elif pitch == 124:
                    if not self.is_dragging:
                        print(f"[Triggered] Drag Initiate (Pitch {pitch})")
                        self.is_dragging = True
                        self.mouse.press(Button.left)
                    else:
                        print(f"[Info] Drag already initiated (Pitch {pitch})")
                elif pitch == 123:
                    print(f"[Triggered] F4 Keypress & change Mode to 'paused' (Pitch {pitch})")
                    self.keyboard.press(Key.f4)
                    self.keyboard.release(Key.f4)
                    self.mode = "paused"
                elif pitch == 122:
                    print(f"[Triggered] F4 Keypress & change Mode to 'frozen' (Pitch {pitch})")
                    self.keyboard.press(Key.f4)
                    self.keyboard.release(Key.f4)
                    self.mode = "frozen"

            elif is_note_off:
                if pitch == 124:
                    if self.is_dragging:
                        print(f"[Triggered] Drag Conclude (Pitch {pitch})")
                        self.is_dragging = False
                        self.mouse.release(Button.left)
                    else:
                        print(f"[Info] Drag conclude received but drag was not active (Pitch {pitch})")

    def auto_connect_midi(preferred_port_name=None):
        """
        Attempts to create a virtual MIDI port. If that's not supported (e.g., Windows),
        polls available MIDI input ports and connects to LoopMIDI or any available port.
        """
        if preferred_port_name:
            # If user explicitly provided a port name, try to open it directly
            try:
                return mido.open_input(preferred_port_name)
            except Exception as e:
                print(f"[*] Could not open user-specified port '{preferred_port_name}': {e}")
                print("[*] Falling back to automatic port scanning...")

        # First, try to open a virtual port (works on macOS and Linux with CoreMIDI/ALSA sequencer)
        virtual_port_name = "Python Virtual MIDI"
        try:
            inport = mido.open_input(virtual_port_name, virtual=True)
            print(f"[*] Successfully created virtual MIDI input port: '{virtual_port_name}'")
            print("[*] Other applications can now select and send MIDI notes to this port.")
            return inport
        except NotImplementedError:
            print("[*] Virtual MIDI port creation is not supported on this platform (e.g., Windows).")
            print("[*] Scanning for available MIDI input ports (e.g., LoopMIDI)...")

        # Polling loop for Windows / systems without virtual MIDI support
        while True:
            try:
                ports = mido.get_input_names()
            except Exception as e:
                print(f"[*] Error getting MIDI input names: {e}")
                ports = []

            if not ports:
                print("[*] No MIDI inputs found. Please connect a MIDI device or start LoopMIDI.")
                print("[*] Retrying in 3 seconds...", flush=True)
                time.sleep(3)
                continue

            # Look for loop/LoopMIDI in the names
            target_port = None
            for p in ports:
                if "loop" in p.lower():
                    target_port = p
                    break

            # Fallback to the first available port if no LoopMIDI is found
            if not target_port and ports:
                target_port = ports[0]
                print(f"[*] LoopMIDI not explicitly found. Defaulting to first available port: '{target_port}'")

            if target_port:
                try:
                    inport = mido.open_input(target_port)
                    print(f"[*] Successfully connected to MIDI input port: '{target_port}'")
                    return inport
                except Exception as e:
                    print(f"[*] Failed to open MIDI port '{target_port}': {e}")
                    print("[*] Retrying in 3 seconds...", flush=True)
                    time.sleep(3)

    parser = argparse.ArgumentParser(description="MIDI to Mouse Clicks & Key Presses.")
    parser.add_argument("--port", type=str, default=None, help="Name of the MIDI port to connect to directly.")
    parser.add_argument("--threshold", type=float, default=1.0, help="Time in seconds of no movement to consider mouse frozen (default: 1.0s).")
    parser.add_argument("--no-elevate", action="store_true", help="Do not attempt to automatically elevate privileges to Administrator on Windows.")
    args = parser.parse_args()

    # Automatically elevate to Admin if on Windows to allow clicks/keypresses inside restricted processes
    if not args.no_elevate:
        elevate_privileges()

    # Start minimized on Windows
    if sys.platform == "win32":
        try:
            import ctypes
            console_hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if console_hwnd:
                ctypes.windll.user32.ShowWindow(console_hwnd, 6)  # 6 = SW_MINIMIZE
        except Exception as e:
            print(f"[*] Failed to minimize console window: {e}")

    # Initialize Controller Instances
    mouse = MouseController()
    keyboard = KeyboardController()

    # Start Mouse Monitoring
    monitor = MouseMonitor(mouse, frozen_threshold=args.threshold)
    monitor.start()

    # Initialize the input processor
    controller = MidiInputController(mouse, keyboard, monitor.is_frozen)

    # Connect to MIDI
    inport = auto_connect_midi(args.port)

    print("\n" + "="*50)
    print(" MIDI To Input translation active!")
    print(f" - Mouse frozen threshold set to: {args.threshold} seconds")
    print(f" - Administrator Privileges: {'Active (Required for task manager, powershell, etc.)' if is_admin() else 'Inactive (Some windows may ignore clicks)'}")
    print(" - Press Ctrl+C in this console to exit.")
    print("="*50 + "\n")

    try:
        for msg in inport:
            controller.handle_midi_message(msg)
    except KeyboardInterrupt:
        print("\n[*] Exiting MIDI to Input Control Script. Goodbye!")
    finally:
        monitor.running = False


if __name__ == "__main__":
    try:
        run_script()
    except Exception as err:
        print("\n" + "!"*50)
        print(" AN ERROR OCCURRED DURING RUNTIME:")
        print("!"*50)
        traceback.print_exc()
        print("!"*50)
        input("\nPress Enter to exit...")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[*] Exited by user.")
