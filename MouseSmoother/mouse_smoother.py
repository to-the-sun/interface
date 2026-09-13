import math
import os
import sys
import json
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox

# Windows API constants
WH_MOUSE_LL = 14
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_MOUSEWHEEL = 0x020A
LLMHF_INJECTED = 0x00000001
LLMHF_LOWER_IL_INJECTED = 0x00000002

CONFIG_FILENAME = "mouse_smoother_config.json"

DEFAULT_CONFIG = {
    "min_jump": 5.0,
    "max_jump": 100.0,
    "max_smoothing": 0.8,
    "curve_factor": 0.0,
    "enabled": False
}


def get_config_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, CONFIG_FILENAME)


def load_config():
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(data)
                return config
        except Exception as e:
            print(f"Error loading config: {e}")
    return DEFAULT_CONFIG.copy()


def save_config(config):
    path = get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")


def compute_smoothing(jump_pixels, min_jump, max_jump, max_smoothing, curve_factor):
    """
    Computes smoothing amount (0.0 to max_smoothing) given the jump in pixels.
    Small jumps (0 to min_jump pixels) receive maximum smoothing (max_smoothing).
    As the jump size increases towards max_jump, smoothing decreases to 0.0.

    Parameters:
    - jump_pixels: distance in pixels between mouse frames (float)
    - min_jump: adjustable minimum jump threshold in pixels below which maximum smoothing is applied (float)
    - max_jump: jump in pixels at which smoothing reaches 0.0 (float)
    - max_smoothing: maximum smoothing factor [0.0, 1.0) applied to small movements (float)
    - curve_factor: factor varying curve type:
        - curve_factor < 0: Logarithmic behavior
        - curve_factor == 0: Linear behavior
        - curve_factor > 0: Exponential behavior
        Magnitude controls curvature strength (e.g., -5.0 to +5.0).
    """
    if jump_pixels <= min_jump:
        return max(0.0, min(0.999, max_smoothing))

    if max_jump <= min_jump:
        return 0.0

    if jump_pixels >= max_jump:
        return 0.0

    # norm_small_jump goes from 1.0 (at jump_pixels == min_jump) down to 0.0 (at jump_pixels == max_jump)
    norm_small_jump = (max_jump - jump_pixels) / (max_jump - min_jump)
    norm_small_jump = min(1.0, max(0.0, norm_small_jump))

    # Apply curve factor transformation
    if abs(curve_factor) < 1e-6:
        # Linear
        factor = norm_small_jump
    elif curve_factor > 0:
        # Exponential curve
        factor = math.pow(norm_small_jump, 1.0 + curve_factor)
    else:
        # Logarithmic curve
        exponent = 1.0 + abs(curve_factor)
        factor = 1.0 - math.pow(1.0 - norm_small_jump, exponent)

    smoothing = factor * max_smoothing
    return max(0.0, min(0.999, smoothing))


class MouseSmootherEngine:
    def __init__(self, config):
        self.config = config
        self.running = False
        self.lock = threading.Lock()

        # Target and current mouse position (float for smooth interpolation)
        self.target_x = 0.0
        self.target_y = 0.0
        self.curr_x = 0.0
        self.curr_y = 0.0
        self.last_raw_x = 0
        self.last_raw_y = 0

        self.hook_thread = None
        self.smooth_thread = None
        self.hook_id = None
        self.hook_proc_ref = None

    def start(self):
        if self.running:
            return
        self.running = True

        # Initialize current target position from Windows screen API if available
        if sys.platform == 'win32':
            import ctypes
            from ctypes import wintypes
            class POINT(ctypes.Structure):
                _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

            ctypes.windll.user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
            ctypes.windll.user32.GetCursorPos.restype = wintypes.BOOL

            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            self.curr_x, self.curr_y = float(pt.x), float(pt.y)
            self.target_x, self.target_y = float(pt.x), float(pt.y)
            self.last_raw_x, self.last_raw_y = pt.x, pt.y

        self.smooth_thread = threading.Thread(target=self._smooth_loop, daemon=True)
        self.smooth_thread.start()

        if sys.platform == 'win32':
            self.hook_thread = threading.Thread(target=self._hook_loop, daemon=True)
            self.hook_thread.start()

    def stop(self):
        self.running = False
        if sys.platform == 'win32' and self.hook_id:
            import ctypes
            from ctypes import wintypes
            ctypes.windll.user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
            ctypes.windll.user32.UnhookWindowsHookEx.restype = wintypes.BOOL
            ctypes.windll.user32.UnhookWindowsHookEx(self.hook_id)
            self.hook_id = None

    def _smooth_loop(self):
        if sys.platform == 'win32':
            import ctypes
            from ctypes import wintypes
            try:
                ctypes.windll.winmm.timeBeginPeriod.argtypes = [wintypes.UINT]
                ctypes.windll.winmm.timeBeginPeriod.restype = wintypes.UINT
                ctypes.windll.winmm.timeBeginPeriod(1)
            except Exception:
                pass

        while self.running:
            time.sleep(0.002)  # ~500 Hz update loop

            if sys.platform != 'win32':
                continue

            with self.lock:
                min_jump = float(self.config.get('min_jump', 5.0))
                max_jump = float(self.config.get('max_jump', 100.0))
                max_smoothing = float(self.config.get('max_smoothing', 0.8))
                curve_factor = float(self.config.get('curve_factor', 0.0))

                dx = self.target_x - self.curr_x
                dy = self.target_y - self.curr_y
                dist = math.hypot(dx, dy)

                if dist < 0.1:
                    self.curr_x = self.target_x
                    self.curr_y = self.target_y
                    continue

                smoothing = compute_smoothing(dist, min_jump, max_jump, max_smoothing, curve_factor)
                alpha = 1.0 - smoothing

                self.curr_x += dx * alpha
                self.curr_y += dy * alpha

                new_ix = int(round(self.curr_x))
                new_iy = int(round(self.curr_y))

            # Set cursor pos on Windows
            import ctypes
            from ctypes import wintypes
            ctypes.windll.user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
            ctypes.windll.user32.SetCursorPos.restype = wintypes.BOOL
            ctypes.windll.user32.SetCursorPos(new_ix, new_iy)

    def _hook_loop(self):
        import ctypes
        from ctypes import wintypes

        class POINT(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        class MSLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [
                ("pt", POINT),
                ("mouseData", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_size_t)  # ULONG_PTR on Windows 64-bit/32-bit
            ]

        # Declare HOOKPROC signature: LRESULT CALLBACK LowLevelMouseProc(int nCode, WPARAM wParam, LPARAM lParam)
        HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

        # Declare API function signatures
        ctypes.windll.user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD
        ]
        ctypes.windll.user32.SetWindowsHookExW.restype = wintypes.HHOOK

        ctypes.windll.user32.CallNextHookEx.argtypes = [
            wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
        ]
        ctypes.windll.user32.CallNextHookEx.restype = ctypes.c_ssize_t

        ctypes.windll.kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        ctypes.windll.kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE

        ctypes.windll.user32.GetMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT
        ]
        ctypes.windll.user32.GetMessageW.restype = wintypes.BOOL

        ctypes.windll.user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
        ctypes.windll.user32.TranslateMessage.restype = wintypes.BOOL

        ctypes.windll.user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
        ctypes.windll.user32.DispatchMessageW.restype = ctypes.c_ssize_t

        def low_level_mouse_proc(nCode, wParam, lParam):
            try:
                if nCode >= 0 and wParam == WM_MOUSEMOVE:
                    ms = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                    # Ignore injected events if LLMHF_INJECTED is set
                    if not (ms.flags & LLMHF_INJECTED):
                        raw_x = ms.pt.x
                        raw_y = ms.pt.y

                        with self.lock:
                            dx = raw_x - self.last_raw_x
                            dy = raw_y - self.last_raw_y
                            self.last_raw_x = raw_x
                            self.last_raw_y = raw_y

                            # Accumulate delta onto smooth target
                            self.target_x += dx
                            self.target_y += dy
                    else:
                        # Update last_raw_x/y to match current cursor location for injected moves
                        with self.lock:
                            self.last_raw_x = ms.pt.x
                            self.last_raw_y = ms.pt.y
            except Exception as e:
                pass

            return ctypes.windll.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

        self.hook_proc_ref = HOOKPROC(low_level_mouse_proc)
        h_module = ctypes.windll.kernel32.GetModuleHandleW(None)
        self.hook_id = ctypes.windll.user32.SetWindowsHookExW(
            WH_MOUSE_LL, self.hook_proc_ref, h_module, 0
        )

        msg = wintypes.MSG()
        while self.running and ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
            ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))


class MouseSmootherGUI:
    def __init__(self):
        self.config = load_config()
        self.engine = MouseSmootherEngine(self.config)

        self.root = tk.Tk()
        self.root.title("Mouse Movement Smoother")
        self.root.geometry("640x680")
        self.root.minsize(580, 600)

        self._init_variables()
        self._build_ui()
        self._draw_curve()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        if self.config.get("enabled", False):
            self.toggle_smoothing()

    def _init_variables(self):
        self.var_min_jump = tk.DoubleVar(value=float(self.config.get("min_jump", 5.0)))
        self.var_max_jump = tk.DoubleVar(value=float(self.config.get("max_jump", 100.0)))
        self.var_max_smoothing = tk.DoubleVar(value=float(self.config.get("max_smoothing", 0.8)))
        self.var_curve_factor = tk.DoubleVar(value=float(self.config.get("curve_factor", 0.0)))
        self.var_enabled = tk.BooleanVar(value=False)

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title / Header
        title_label = ttk.Label(main_frame, text="Mouse Movement Smoother", font=("Segoe UI", 14, "bold"))
        title_label.pack(anchor=tk.W, pady=(0, 10))

        # Canvas Frame for Curve Visualization
        canvas_frame = ttk.LabelFrame(main_frame, text="Smoothing Curve Response Graph", padding=8)
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.canvas = tk.Canvas(canvas_frame, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda e: self._draw_curve())

        # Controls Frame
        controls_frame = ttk.LabelFrame(main_frame, text="Curve & Threshold Parameters", padding=10)
        controls_frame.pack(fill=tk.X, pady=(0, 10))

        # Grid configuration
        controls_frame.columnconfigure(1, weight=1)

        row = 0

        # Min Jump Slider (X-axis minimum jump in pixels)
        ttk.Label(controls_frame, text="Minimum Jump (Min Threshold px):").grid(row=row, column=0, sticky=tk.W, pady=4)
        self.lbl_min_jump = ttk.Label(controls_frame, text=f"{self.var_min_jump.get():.1f} px", width=10, anchor=tk.E)
        self.lbl_min_jump.grid(row=row, column=2, sticky=tk.E, pady=4, padx=(5, 0))
        scale_min_jump = ttk.Scale(
            controls_frame, from_=0.0, to=50.0, variable=self.var_min_jump,
            command=lambda v: self._on_param_change()
        )
        scale_min_jump.grid(row=row, column=1, sticky=tk.EW, padx=8, pady=4)

        row += 1

        # Max Jump Scale Slider (X-axis max scale in pixels)
        ttk.Label(controls_frame, text="Maximum Jump Scale (Max px):").grid(row=row, column=0, sticky=tk.W, pady=4)
        self.lbl_max_jump = ttk.Label(controls_frame, text=f"{self.var_max_jump.get():.1f} px", width=10, anchor=tk.E)
        self.lbl_max_jump.grid(row=row, column=2, sticky=tk.E, pady=4, padx=(5, 0))
        scale_max_jump = ttk.Scale(
            controls_frame, from_=10.0, to=300.0, variable=self.var_max_jump,
            command=lambda v: self._on_param_change()
        )
        scale_max_jump.grid(row=row, column=1, sticky=tk.EW, padx=8, pady=4)

        row += 1

        # Max Smoothing Slider (Y-axis max factor)
        ttk.Label(controls_frame, text="Maximum Smoothing (Max Y):").grid(row=row, column=0, sticky=tk.W, pady=4)
        self.lbl_max_smoothing = ttk.Label(controls_frame, text=f"{self.var_max_smoothing.get():.2f}", width=10, anchor=tk.E)
        self.lbl_max_smoothing.grid(row=row, column=2, sticky=tk.E, pady=4, padx=(5, 0))
        scale_max_smoothing = ttk.Scale(
            controls_frame, from_=0.0, to=0.98, variable=self.var_max_smoothing,
            command=lambda v: self._on_param_change()
        )
        scale_max_smoothing.grid(row=row, column=1, sticky=tk.EW, padx=8, pady=4)

        row += 1

        # Curve Factor Slider (Logarithmic <-> Linear <-> Exponential)
        ttk.Label(controls_frame, text="Curve Factor (Log <-> Exp):").grid(row=row, column=0, sticky=tk.W, pady=4)
        self.lbl_curve_factor = ttk.Label(controls_frame, text=self._format_curve_label(), width=14, anchor=tk.E)
        self.lbl_curve_factor.grid(row=row, column=2, sticky=tk.E, pady=4, padx=(5, 0))
        scale_curve_factor = ttk.Scale(
            controls_frame, from_=-5.0, to=5.0, variable=self.var_curve_factor,
            command=lambda v: self._on_param_change()
        )
        scale_curve_factor.grid(row=row, column=1, sticky=tk.EW, padx=8, pady=4)

        # Status & Toggle Frame
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X)

        self.btn_toggle = ttk.Button(
            bottom_frame, text="Enable Mouse Smoothing", command=self.toggle_smoothing, width=25
        )
        self.btn_toggle.pack(side=tk.LEFT, pady=5)

        self.lbl_status = ttk.Label(bottom_frame, text="Status: Disabled", font=("Segoe UI", 10, "bold"), foreground="#cc3333")
        self.lbl_status.pack(side=tk.RIGHT, pady=5)

    def _format_curve_label(self):
        val = self.var_curve_factor.get()
        if abs(val) < 0.1:
            return f"{val:+.1f} (Linear)"
        elif val < 0:
            return f"{val:+.1f} (Logarithmic)"
        else:
            return f"{val:+.1f} (Exponential)"

    def _on_param_change(self):
        min_j = self.var_min_jump.get()
        max_j = max(min_j + 1.0, self.var_max_jump.get())
        max_s = self.var_max_smoothing.get()
        c_fac = self.var_curve_factor.get()

        self.lbl_min_jump.config(text=f"{min_j:.1f} px")
        self.lbl_max_jump.config(text=f"{max_j:.1f} px")
        self.lbl_max_smoothing.config(text=f"{max_s:.2f}")
        self.lbl_curve_factor.config(text=self._format_curve_label())

        # Update engine config dictionary
        self.config["min_jump"] = min_j
        self.config["max_jump"] = max_j
        self.config["max_smoothing"] = max_s
        self.config["curve_factor"] = c_fac

        self._draw_curve()

    def _draw_curve(self):
        self.canvas.delete("all")

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        if w < 50 or h < 50:
            return

        pad_left = 50
        pad_right = 20
        pad_top = 30
        pad_bottom = 40

        graph_w = w - pad_left - pad_right
        graph_h = h - pad_top - pad_bottom

        min_j = self.var_min_jump.get()
        max_j = max(min_j + 1.0, self.var_max_jump.get())
        max_s = self.var_max_smoothing.get()
        c_fac = self.var_curve_factor.get()

        # Draw Gridlines & Axes
        self.canvas.create_line(pad_left, pad_top, pad_left, pad_top + graph_h, fill="#555555", width=2)
        self.canvas.create_line(pad_left, pad_top + graph_h, pad_left + graph_w, pad_top + graph_h, fill="#555555", width=2)

        # X-Axis Ticks & Labels (Pixels Jump reversed: max_j on left, 0px on right)
        steps = 5
        for i in range(steps + 1):
            x_val = max_j - (max_j / steps) * i
            x_pos = pad_left + (i / steps) * graph_w
            self.canvas.create_line(x_pos, pad_top + graph_h, x_pos, pad_top + graph_h + 5, fill="#888888")
            self.canvas.create_text(x_pos, pad_top + graph_h + 18, text=f"{int(round(x_val))}px", fill="#aaaaaa", font=("Segoe UI", 8))

        # Y-Axis Ticks & Labels (Smoothing Amount)
        for i in range(steps + 1):
            y_val = (1.0 / steps) * i
            y_pos = pad_top + graph_h - (i / steps) * graph_h
            self.canvas.create_line(pad_left - 5, y_pos, pad_left, y_pos, fill="#888888")
            self.canvas.create_text(pad_left - 25, y_pos, text=f"{y_val:.1f}", fill="#aaaaaa", font=("Segoe UI", 8))

        # Axis Title Labels
        self.canvas.create_text(
            pad_left + graph_w / 2, pad_top + graph_h + 32,
            text="Frame Jump (Pixels)", fill="#ffffff", font=("Segoe UI", 9, "bold")
        )
        self.canvas.create_text(
            15, pad_top + graph_h / 2,
            text="Smoothing", fill="#ffffff", font=("Segoe UI", 9, "bold"), angle=90
        )

        # Draw Min Jump Threshold Marker Line (Reversed axis: position is at (max_j - min_j))
        if min_j > 0:
            min_x_pos = pad_left + ((max_j - min_j) / max_j) * graph_w
            if pad_left <= min_x_pos <= pad_left + graph_w:
                self.canvas.create_line(min_x_pos, pad_top, min_x_pos, pad_top + graph_h, fill="#ffaa00", dash=(3, 3))
                self.canvas.create_text(min_x_pos, pad_top - 10, text=f"Min Threshold ({min_j:.1f}px)", fill="#ffaa00", font=("Segoe UI", 8))

        # Draw Maximum Smoothing Reference Line
        max_s_y_pos = pad_top + graph_h - max_s * graph_h
        self.canvas.create_line(pad_left, max_s_y_pos, pad_left + graph_w, max_s_y_pos, fill="#00aaff", dash=(2, 4))
        self.canvas.create_text(pad_left + graph_w - 40, max_s_y_pos - 8, text=f"Max Y ({max_s:.2f})", fill="#00aaff", font=("Segoe UI", 8))

        # Plot Curve (Reversed X axis: left is max_j, right is 0px)
        points = []
        num_samples = 150
        for step in range(num_samples + 1):
            # jp decreases from max_j down to 0.0 as step goes from 0 to num_samples
            jp = max_j - (max_j / num_samples) * step
            sm = compute_smoothing(jp, min_j, max_j, max_s, c_fac)

            px = pad_left + (step / num_samples) * graph_w
            py = pad_top + graph_h - sm * graph_h
            points.append((px, py))

        # Draw smooth line connecting samples
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            self.canvas.create_line(x1, y1, x2, y2, fill="#00ffcc", width=2)

        # Plot Type Header inside Graph
        if abs(c_fac) < 0.1:
            curve_type_str = "Linear Response Curve"
        elif c_fac < 0:
            curve_type_str = f"Logarithmic Response Curve (Factor: {c_fac:.1f})"
        else:
            curve_type_str = f"Exponential Response Curve (Factor: {c_fac:.1f})"

        self.canvas.create_text(
            pad_left + 10, pad_top + 15,
            text=curve_type_str, fill="#00ffcc", font=("Segoe UI", 10, "bold"), anchor=tk.W
        )

    def toggle_smoothing(self):
        if not self.var_enabled.get():
            self.var_enabled.set(True)
            self.engine.start()
            self.btn_toggle.config(text="Disable Mouse Smoothing")
            self.lbl_status.config(text="Status: Active", foreground="#33cc33")
            self.config["enabled"] = True
        else:
            self.var_enabled.set(False)
            self.engine.stop()
            self.btn_toggle.config(text="Enable Mouse Smoothing")
            self.lbl_status.config(text="Status: Disabled", foreground="#cc3333")
            self.config["enabled"] = False

    def _on_close(self):
        self.engine.stop()
        save_config(self.config)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = MouseSmootherGUI()
    app.run()
