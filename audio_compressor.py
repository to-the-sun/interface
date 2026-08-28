import sys
import os
import json
import time
import math
import numpy as np
import sounddevice as sd
import tkinter as tk
from tkinter import ttk, messagebox

CONFIG_FILE = "audio_compressor_config.json"

DEFAULT_CONFIG = {
    "input_device": None,
    "output_device": None,
    "threshold_db": -20.0,
    "ratio": 4.0,
    "attack_ms": 10.0,
    "release_ms": 100.0,
    "makeup_gain_db": 3.0,
    "upward_boost_db": 6.0,
    "upward_thresh_db": -45.0,
    "enabled": True,
    "sample_rate": 44100
}

class AudioCompressor:
    """
    Real-time dynamic range audio compressor supporting both downward compression
    (reducing loud peaks) and upward compression (boosting quiet speech signals),
    with envelope follower, makeup gain, and peak limiter.
    """
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.enabled = True
        self.threshold_db = -20.0
        self.ratio = 4.0
        self.attack_ms = 10.0
        self.release_ms = 100.0
        self.makeup_gain_db = 3.0
        self.upward_boost_db = 6.0
        self.upward_thresh_db = -45.0

        self._envelope_db = -100.0
        self.current_in_db = -100.0
        self.current_out_db = -100.0
        self.current_gr_db = 0.0

    def set_sample_rate(self, sample_rate):
        if sample_rate and sample_rate > 0:
            self.sample_rate = sample_rate

    def process(self, indata):
        """
        Process audio input numpy array (frames, channels) and return compressed output array.
        """
        if indata is None or indata.size == 0:
            return indata

        outdata = np.copy(indata)
        num_samples, num_channels = indata.shape

        # Measure peak input amplitude
        in_peak = float(np.max(np.abs(indata)))
        self.current_in_db = 20.0 * math.log10(max(in_peak, 1e-5))

        # Time constants for envelope follower
        dt = 1.0 / self.sample_rate
        alpha_att = math.exp(-dt / max(self.attack_ms * 0.001, 1e-4))
        alpha_rel = math.exp(-dt / max(self.release_ms * 0.001, 1e-4))

        # Peak sample magnitude per frame across channels
        mag_per_frame = np.max(np.abs(indata), axis=1)

        max_gr_this_block = 0.0
        env = self._envelope_db

        for i in range(num_samples):
            samp_mag = mag_per_frame[i]
            samp_db = 20.0 * math.log10(max(float(samp_mag), 1e-5))

            if samp_db > env:
                env = alpha_att * env + (1.0 - alpha_att) * samp_db
            else:
                env = alpha_rel * env + (1.0 - alpha_rel) * samp_db

            gr_db = 0.0
            upward_gain_db = 0.0

            if self.enabled:
                # Downward compression for loud signals above threshold_db
                if env > self.threshold_db:
                    over_db = env - self.threshold_db
                    gr_db = over_db * (1.0 - 1.0 / max(self.ratio, 1.0))

                # Upward compression for quiet speech between upward_thresh_db and threshold_db
                if env > self.upward_thresh_db and env < self.threshold_db and self.upward_boost_db > 0:
                    under_db = self.threshold_db - env
                    range_db = max(self.threshold_db - self.upward_thresh_db, 1.0)
                    upward_gain_db = self.upward_boost_db * (under_db / range_db)

            if gr_db > max_gr_this_block:
                max_gr_this_block = gr_db

            total_gain_db = (self.makeup_gain_db + upward_gain_db - gr_db) if self.enabled else 0.0
            gain_lin = 10.0 ** (total_gain_db / 20.0)

            outdata[i] = indata[i] * gain_lin

        self._envelope_db = env
        self.current_gr_db = max_gr_this_block if self.enabled else 0.0

        # Peak limiter to prevent clipping
        np.clip(outdata, -0.99, 0.99, out=outdata)
        outdata = outdata.astype(np.float32)

        # Measure peak output amplitude
        out_peak = float(np.max(np.abs(outdata)))
        self.current_out_db = 20.0 * math.log10(max(out_peak, 1e-5))

        return outdata

class AudioCompressorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Compressor - Input/Output Audio Router")
        self.root.geometry("680x740")
        self.root.minsize(620, 680)

        self.compressor = AudioCompressor()
        self.stream = None

        self.input_devices = []
        self.output_devices = []

        self.config = self.load_config()
        self.apply_config_to_compressor()

        self.build_ui()
        self.refresh_audio_devices()

        # Attempt auto-starting stream if devices were saved
        self.autostart_stream()

        # Meter update timer
        self.update_meters()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_config(self):
        config = DEFAULT_CONFIG.copy()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    config.update(data)
            except Exception as e:
                print(f"Error loading config: {e}")
        return config

    def save_config(self):
        try:
            self.config["threshold_db"] = self.compressor.threshold_db
            self.config["ratio"] = self.compressor.ratio
            self.config["attack_ms"] = self.compressor.attack_ms
            self.config["release_ms"] = self.compressor.release_ms
            self.config["makeup_gain_db"] = self.compressor.makeup_gain_db
            self.config["upward_boost_db"] = self.compressor.upward_boost_db
            self.config["enabled"] = self.compressor.enabled

            in_sel = self.input_combo.get()
            out_sel = self.output_combo.get()
            self.config["input_device"] = in_sel if in_sel else None
            self.config["output_device"] = out_sel if out_sel else None

            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def apply_config_to_compressor(self):
        self.compressor.threshold_db = float(self.config.get("threshold_db", -20.0))
        self.compressor.ratio = float(self.config.get("ratio", 4.0))
        self.compressor.attack_ms = float(self.config.get("attack_ms", 10.0))
        self.compressor.release_ms = float(self.config.get("release_ms", 100.0))
        self.compressor.makeup_gain_db = float(self.config.get("makeup_gain_db", 3.0))
        self.compressor.upward_boost_db = float(self.config.get("upward_boost_db", 6.0))
        self.compressor.enabled = bool(self.config.get("enabled", True))

    def build_ui(self):
        style = ttk.Style()
        style.theme_use('clam')

        # Main Scrollable / Padded container
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title / Banner
        title_lbl = ttk.Label(
            main_frame,
            text="Microphone Audio Compressor Router",
            font=("Segoe UI", 15, "bold")
        )
        title_lbl.pack(anchor=tk.W, pady=(0, 5))

        subtitle_lbl = ttk.Label(
            main_frame,
            text="Process microphone audio with real-time compression and output to Virtual Audio Cable or apps.",
            font=("Segoe UI", 9)
        )
        subtitle_lbl.pack(anchor=tk.W, pady=(0, 15))

        # Device Selection Frame
        dev_frame = ttk.LabelFrame(main_frame, text=" Audio Devices ", padding="10")
        dev_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(dev_frame, text="Input Device (e.g. Mic / NVIDIA Broadcast):", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.input_combo = ttk.Combobox(dev_frame, state="readonly", width=55)
        self.input_combo.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10))

        ttk.Label(dev_frame, text="Output Device (e.g. CABLE Input / Virtual Audio Cable):", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.output_combo = ttk.Combobox(dev_frame, state="readonly", width=55)
        self.output_combo.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10))

        btn_box = ttk.Frame(dev_frame)
        btn_box.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=5)

        self.start_btn = ttk.Button(btn_box, text="Start Processing", command=self.toggle_stream)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.refresh_btn = ttk.Button(btn_box, text="Refresh Devices", command=self.refresh_audio_devices)
        self.refresh_btn.pack(side=tk.LEFT)

        dev_frame.columnconfigure(0, weight=1)

        # Visual Level Meters Frame
        meter_frame = ttk.LabelFrame(main_frame, text=" Real-Time Audio Meters ", padding="10")
        meter_frame.pack(fill=tk.X, pady=(0, 15))

        # Input Meter
        ttk.Label(meter_frame, text="Input Level:").grid(row=0, column=0, sticky=tk.W)
        self.in_meter_canvas = tk.Canvas(meter_frame, height=18, bg="#222222", highlightthickness=0)
        self.in_meter_canvas.grid(row=0, column=1, sticky=tk.EW, padx=10, pady=4)
        self.in_lbl = ttk.Label(meter_frame, text="-60.0 dB", width=9, anchor=tk.E)
        self.in_lbl.grid(row=0, column=2, sticky=tk.E)

        # Output Meter
        ttk.Label(meter_frame, text="Output Level:").grid(row=1, column=0, sticky=tk.W)
        self.out_meter_canvas = tk.Canvas(meter_frame, height=18, bg="#222222", highlightthickness=0)
        self.out_meter_canvas.grid(row=1, column=1, sticky=tk.EW, padx=10, pady=4)
        self.out_lbl = ttk.Label(meter_frame, text="-60.0 dB", width=9, anchor=tk.E)
        self.out_lbl.grid(row=1, column=2, sticky=tk.E)

        # Gain Reduction Meter
        ttk.Label(meter_frame, text="Gain Reduction:").grid(row=2, column=0, sticky=tk.W)
        self.gr_meter_canvas = tk.Canvas(meter_frame, height=18, bg="#222222", highlightthickness=0)
        self.gr_meter_canvas.grid(row=2, column=1, sticky=tk.EW, padx=10, pady=4)
        self.gr_lbl = ttk.Label(meter_frame, text="0.0 dB", width=9, anchor=tk.E)
        self.gr_lbl.grid(row=2, column=2, sticky=tk.E)

        meter_frame.columnconfigure(1, weight=1)

        # Compressor Controls Frame
        comp_frame = ttk.LabelFrame(main_frame, text=" Compressor Settings ", padding="10")
        comp_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Toggle Enable Button
        self.bypass_btn = ttk.Button(comp_frame, text="Compressor: ENABLED", command=self.toggle_compressor_enabled)
        self.bypass_btn.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        # Threshold Slider (-60 to 0 dB)
        ttk.Label(comp_frame, text="Threshold (dB):").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.thresh_scale = ttk.Scale(comp_frame, from_=-60.0, to=0.0, value=self.compressor.threshold_db, command=self.on_thresh_change)
        self.thresh_scale.grid(row=1, column=1, sticky=tk.EW, padx=10)
        self.thresh_lbl = ttk.Label(comp_frame, text=f"{self.compressor.threshold_db:.1f} dB", width=8)
        self.thresh_lbl.grid(row=1, column=2, sticky=tk.E)

        # Ratio Slider (1:1 to 20:1)
        ttk.Label(comp_frame, text="Ratio:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self.ratio_scale = ttk.Scale(comp_frame, from_=1.0, to=20.0, value=self.compressor.ratio, command=self.on_ratio_change)
        self.ratio_scale.grid(row=2, column=1, sticky=tk.EW, padx=10)
        self.ratio_lbl = ttk.Label(comp_frame, text=f"{self.compressor.ratio:.1f}:1", width=8)
        self.ratio_lbl.grid(row=2, column=2, sticky=tk.E)

        # Attack Slider (1 to 200 ms)
        ttk.Label(comp_frame, text="Attack (ms):").grid(row=3, column=0, sticky=tk.W, pady=3)
        self.attack_scale = ttk.Scale(comp_frame, from_=1.0, to=200.0, value=self.compressor.attack_ms, command=self.on_attack_change)
        self.attack_scale.grid(row=3, column=1, sticky=tk.EW, padx=10)
        self.attack_lbl = ttk.Label(comp_frame, text=f"{self.compressor.attack_ms:.0f} ms", width=8)
        self.attack_lbl.grid(row=3, column=2, sticky=tk.E)

        # Release Slider (10 to 1000 ms)
        ttk.Label(comp_frame, text="Release (ms):").grid(row=4, column=0, sticky=tk.W, pady=3)
        self.release_scale = ttk.Scale(comp_frame, from_=10.0, to=1000.0, value=self.compressor.release_ms, command=self.on_release_change)
        self.release_scale.grid(row=4, column=1, sticky=tk.EW, padx=10)
        self.release_lbl = ttk.Label(comp_frame, text=f"{self.compressor.release_ms:.0f} ms", width=8)
        self.release_lbl.grid(row=4, column=2, sticky=tk.E)

        # Makeup Gain Slider (0 to 30 dB)
        ttk.Label(comp_frame, text="Makeup Gain (dB):").grid(row=5, column=0, sticky=tk.W, pady=3)
        self.gain_scale = ttk.Scale(comp_frame, from_=0.0, to=30.0, value=self.compressor.makeup_gain_db, command=self.on_gain_change)
        self.gain_scale.grid(row=5, column=1, sticky=tk.EW, padx=10)
        self.gain_lbl = ttk.Label(comp_frame, text=f"{self.compressor.makeup_gain_db:.1f} dB", width=8)
        self.gain_lbl.grid(row=5, column=2, sticky=tk.E)

        # Quiet Signal Boost / Upward Compression Slider (0 to 20 dB)
        ttk.Label(comp_frame, text="Quiet Signal Boost (dB):").grid(row=6, column=0, sticky=tk.W, pady=3)
        self.upward_scale = ttk.Scale(comp_frame, from_=0.0, to=20.0, value=self.compressor.upward_boost_db, command=self.on_upward_change)
        self.upward_scale.grid(row=6, column=1, sticky=tk.EW, padx=10)
        self.upward_lbl = ttk.Label(comp_frame, text=f"{self.compressor.upward_boost_db:.1f} dB", width=8)
        self.upward_lbl.grid(row=6, column=2, sticky=tk.E)

        comp_frame.columnconfigure(1, weight=1)

        # Virtual Audio Cable Detection & Guidance Box
        guide_frame = ttk.LabelFrame(main_frame, text=" Virtual Audio Input Source Setup ", padding="10")
        guide_frame.pack(fill=tk.X, pady=(0, 5))

        self.vcable_status_lbl = ttk.Label(guide_frame, text="", font=("Segoe UI", 9, "bold"))
        self.vcable_status_lbl.pack(anchor=tk.W, pady=(0, 4))

        guide_text = (
            "Why is a Virtual Audio Cable required to act as an input source for other apps?\n"
            "• Operating systems (Windows Core Audio/WASAPI) strictly separate Hardware Inputs (Microphones) from Outputs (Speakers).\n"
            "• User-level software cannot create system-recognized Input Audio Devices without a registered kernel audio endpoint driver.\n"
            "• A free Virtual Audio Cable (e.g., VB-Audio Cable) provides this driver bridge: select 'CABLE Input' as the Output Device above,\n"
            "  and select 'CABLE Output' as the Microphone/Input Source inside Aqua Voice, Dragon, Discord, or any other program."
        )
        guide_lbl = ttk.Label(guide_frame, text=guide_text, font=("Segoe UI", 8), justify=tk.LEFT)
        guide_lbl.pack(anchor=tk.W)

        # Status Bar
        self.status_lbl = ttk.Label(main_frame, text="Status: Stopped", relief=tk.SUNKEN, anchor=tk.W, padding=3)
        self.status_lbl.pack(fill=tk.X, side=tk.BOTTOM)

    def refresh_audio_devices(self):
        try:
            devices = sd.query_devices()
            self.input_devices = []
            self.output_devices = []

            for idx, dev in enumerate(devices):
                name = dev['name']
                max_in = dev['max_input_channels']
                max_out = dev['max_output_channels']

                label = f"[{idx}] {name}"
                if max_in > 0:
                    self.input_devices.append((idx, label))
                if max_out > 0:
                    self.output_devices.append((idx, label))

            in_values = [d[1] for d in self.input_devices]
            out_values = [d[1] for d in self.output_devices]

            self.input_combo['values'] = in_values
            self.output_combo['values'] = out_values

            # Check for virtual cable presence
            has_vcable = any("cable" in label.lower() or "vb-audio" in label.lower() or "voicemeeter" in label.lower() for label in out_values)
            if has_vcable:
                self.vcable_status_lbl.config(
                    text="✔ Virtual Audio Cable Detected! Ready to route audio to Discord, Aqua Voice, Dragon, etc.",
                    foreground="#2e7d32"
                )
            else:
                self.vcable_status_lbl.config(
                    text="⚠ No Virtual Audio Cable detected. Please install a driver (e.g. VB-Audio Cable) to output to other apps.",
                    foreground="#d32f2f"
                )

            # Preserve previous selections or pick default
            saved_in = self.config.get("input_device")
            saved_out = self.config.get("output_device")

            if saved_in and saved_in in in_values:
                self.input_combo.set(saved_in)
            elif in_values:
                # Default input device if found
                default_in = sd.default.device[0]
                matched = [lbl for idx, lbl in self.input_devices if idx == default_in]
                self.input_combo.set(matched[0] if matched else in_values[0])

            if saved_out and saved_out in out_values:
                self.output_combo.set(saved_out)
            elif out_values:
                # Default output device if found
                default_out = sd.default.device[1]
                matched = [lbl for idx, lbl in self.output_devices if idx == default_out]
                self.output_combo.set(matched[0] if matched else out_values[0])

        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh audio devices:\n{e}")

    def audio_callback(self, indata, outdata, frames, time_info, status):
        if status:
            print(f"Stream status warning: {status}")
        processed = self.compressor.process(indata)
        outdata[:] = processed

    def autostart_stream(self):
        if self.input_combo.get() and self.output_combo.get():
            self.start_stream()

    def toggle_stream(self):
        if self.stream is not None:
            self.stop_stream()
        else:
            self.start_stream()

    def start_stream(self):
        in_sel = self.input_combo.get()
        out_sel = self.output_combo.get()

        if not in_sel or not out_sel:
            messagebox.showwarning("Device Selection Required", "Please select both an Input and an Output audio device.")
            return

        in_idx = int(in_sel.split(']')[0].strip('['))
        out_idx = int(out_sel.split(']')[0].strip('['))

        try:
            in_dev_info = sd.query_devices(in_idx)
            out_dev_info = sd.query_devices(out_idx)

            sr = int(in_dev_info.get('default_samplerate', 44100))
            ch = min(in_dev_info.get('max_input_channels', 1), out_dev_info.get('max_output_channels', 1), 2)

            self.compressor.set_sample_rate(sr)

            self.stream = sd.Stream(
                device=(in_idx, out_idx),
                samplerate=sr,
                channels=ch,
                dtype='float32',
                callback=self.audio_callback,
                blocksize=512
            )
            self.stream.start()
            self.start_btn.config(text="Stop Processing")
            self.status_lbl.config(text=f"Status: Streaming ({in_dev_info['name']} -> {out_dev_info['name']} @ {sr}Hz)")
        except Exception as e:
            self.stream = None
            self.start_btn.config(text="Start Processing")
            self.status_lbl.config(text="Status: Error starting stream")
            messagebox.showerror("Stream Error", f"Could not start audio stream:\n{e}")

    def stop_stream(self):
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                print(f"Error stopping stream: {e}")
            self.stream = None
        self.start_btn.config(text="Start Processing")
        self.status_lbl.config(text="Status: Stopped")

    def toggle_compressor_enabled(self):
        self.compressor.enabled = not self.compressor.enabled
        if self.compressor.enabled:
            self.bypass_btn.config(text="Compressor: ENABLED")
        else:
            self.bypass_btn.config(text="Compressor: BYPASSED (Disabled)")

    def on_thresh_change(self, val):
        val_f = float(val)
        self.compressor.threshold_db = val_f
        self.thresh_lbl.config(text=f"{val_f:.1f} dB")

    def on_ratio_change(self, val):
        val_f = float(val)
        self.compressor.ratio = val_f
        self.ratio_lbl.config(text=f"{val_f:.1f}:1")

    def on_attack_change(self, val):
        val_f = float(val)
        self.compressor.attack_ms = val_f
        self.attack_lbl.config(text=f"{val_f:.0f} ms")

    def on_release_change(self, val):
        val_f = float(val)
        self.compressor.release_ms = val_f
        self.release_lbl.config(text=f"{val_f:.0f} ms")

    def on_gain_change(self, val):
        val_f = float(val)
        self.compressor.makeup_gain_db = val_f
        self.gain_lbl.config(text=f"{val_f:.1f} dB")

    def on_upward_change(self, val):
        val_f = float(val)
        self.compressor.upward_boost_db = val_f
        self.upward_lbl.config(text=f"{val_f:.1f} dB")

    def draw_meter_bar(self, canvas, db_value, min_db=-60.0, max_db=0.0, bar_color="#00e676"):
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1 or h <= 1:
            return

        db_clamped = max(min_db, min(max_db, db_value))
        fraction = (db_clamped - min_db) / (max_db - min_db)
        bar_w = int(w * fraction)

        if bar_w > 0:
            canvas.create_rectangle(0, 0, bar_w, h, fill=bar_color, width=0)

    def draw_gr_bar(self, canvas, gr_db_value, max_gr=24.0, bar_color="#ff5252"):
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1 or h <= 1:
            return

        gr_clamped = max(0.0, min(max_gr, gr_db_value))
        fraction = gr_clamped / max_gr
        bar_w = int(w * fraction)

        if bar_w > 0:
            canvas.create_rectangle(0, 0, bar_w, h, fill=bar_color, width=0)

    def update_meters(self):
        in_db = self.compressor.current_in_db
        out_db = self.compressor.current_out_db
        gr_db = self.compressor.current_gr_db

        self.in_lbl.config(text=f"{in_db:.1f} dB")
        self.out_lbl.config(text=f"{out_db:.1f} dB")
        self.gr_lbl.config(text=f"{gr_db:.1f} dB")

        # Select color based on level
        in_color = "#ff5252" if in_db > -1.0 else ("#ffab40" if in_db > -6.0 else "#00e676")
        out_color = "#ff5252" if out_db > -1.0 else ("#ffab40" if out_db > -6.0 else "#00e676")

        self.draw_meter_bar(self.in_meter_canvas, in_db, bar_color=in_color)
        self.draw_meter_bar(self.out_meter_canvas, out_db, bar_color=out_color)
        self.draw_gr_bar(self.gr_meter_canvas, gr_db)

        self.root.after(30, self.update_meters)

    def on_close(self):
        self.save_config()
        self.stop_stream()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = AudioCompressorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
