#!/usr/bin/env python3
"""
Video Downloader
A comprehensive tool to download videos from any web page or direct URL.
Supports both Command-Line Interface (CLI) and a Graphical User Interface (GUI).
Uses yt-dlp with automatic fallback to direct media extraction via urllib.
"""

import argparse
import os
import re
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    import yt_dlp
    HAS_YT_DLP = True
except ImportError:
    HAS_YT_DLP = False

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False


def clean_filename(filename: str) -> str:
    """Sanitize a filename by removing illegal characters."""
    return re.sub(r'[\\/*?:"<>|]', "", filename).strip()


def download_direct_url(url: str, output_dir: str, filename: str = None, progress_hook=None) -> str:
    """
    Fallback downloader for direct video links (mp4, webm, etc.) or simple pages.
    """
    os.makedirs(output_dir, exist_ok=True)
    if not filename:
        parsed_url = urllib.parse.urlparse(url)
        path_name = os.path.basename(parsed_url.path)
        if path_name and "." in path_name:
            filename = clean_filename(path_name) or f"video_{int(time.time())}.mp4"
        else:
            filename = f"video_{int(time.time())}.mp4"

    dest_path = os.path.join(output_dir, filename)

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
    )

    # Attempt with default SSL context, fallback to unverified context if certificate validation fails
    try:
        response = urllib.request.urlopen(req)
    except (urllib.error.URLError, ssl.SSLError) as ssl_err:
        if "CERTIFICATE_VERIFY_FAILED" in str(ssl_err) or isinstance(ssl_err, ssl.SSLError):
            ctx = ssl._create_unverified_context()
            response = urllib.request.urlopen(req, context=ctx)
        else:
            raise

    with response:
        total_size = response.headers.get("Content-Length")
        total_bytes = int(total_size) if total_size and total_size.isdigit() else 0
        downloaded = 0
        chunk_size = 64 * 1024

        with open(dest_path, "wb") as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_hook:
                    percent = (downloaded / total_bytes * 100) if total_bytes > 0 else 0
                    progress_hook(
                        {
                            "status": "downloading",
                            "downloaded_bytes": downloaded,
                            "total_bytes": total_bytes,
                            "filename": dest_path,
                            "_percent_str": f"{percent:.1f}%",
                        }
                    )

    if progress_hook:
        progress_hook({"status": "finished", "filename": dest_path})

    return dest_path


def extract_direct_video_from_html(url: str) -> str:
    """
    Attempts to scrape a direct video source (<video src="..."> or <source src="...">)
    from an HTML page if yt-dlp is unavailable or fails.
    """
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
    )
    try:
        resp = urllib.request.urlopen(req)
    except (urllib.error.URLError, ssl.SSLError) as ssl_err:
        if "CERTIFICATE_VERIFY_FAILED" in str(ssl_err) or isinstance(ssl_err, ssl.SSLError):
            ctx = ssl._create_unverified_context()
            resp = urllib.request.urlopen(req, context=ctx)
        else:
            raise

    with resp:
        content_type = resp.headers.get("Content-Type", "")
        if "video/" in content_type:
            return url
        html = resp.read().decode("utf-8", errors="ignore")

    matches = re.findall(
        r'<video[^>]+src=["\']([^"\']+)["\']|<source[^>]+src=["\']([^"\']+)["\']',
        html,
        re.IGNORECASE,
    )
    for match in matches:
        src = match[0] or match[1]
        if src:
            return urllib.parse.urljoin(url, src)

    # Search for common direct video file extensions in attributes
    ext_match = re.search(r'["\'](https?://[^"\']+\.(?:mp4|webm|mkv|mov)[^"\']*)["\']', html)
    if ext_match:
        return ext_match.group(1)

    return ""


def download_video(
    url: str,
    output_dir: str = "downloads",
    format_opt: str = "best",
    audio_only: bool = False,
    progress_callback=None,
    logger=None,
) -> dict:
    """
    Downloads a video from a given URL.
    Returns a dict with 'success' (bool), 'filepath' (str/None), and 'error' (str/None).
    """
    os.makedirs(output_dir, exist_ok=True)

    if HAS_YT_DLP:
        def yt_hook(d):
            if progress_callback:
                progress_callback(d)

        ydl_opts = {
            "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
            "progress_hooks": [yt_hook],
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
        }

        if audio_only:
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
        elif format_opt == "best":
            ydl_opts["format"] = "bestvideo+bestaudio/best"
        else:
            ydl_opts["format"] = format_opt

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                return {"success": True, "filepath": filename, "error": None}
        except Exception as e:
            yt_err = str(e)
            if logger:
                logger(f"yt-dlp encountered an issue: {yt_err}. Trying direct extraction...")
    else:
        yt_err = "yt-dlp library not installed."

    # Direct extraction / download fallback
    try:
        direct_url = extract_direct_video_from_html(url)
        target_url = direct_url if direct_url else url

        downloaded_file = download_direct_url(
            target_url, output_dir, progress_hook=progress_callback
        )
        return {"success": True, "filepath": downloaded_file, "error": None}
    except Exception as fallback_err:
        return {
            "success": False,
            "filepath": None,
            "error": f"Failed with yt-dlp: {yt_err}; Direct fallback: {fallback_err}",
        }


def run_cli(args):
    """Command-line interface execution."""
    url = args.url
    if not url:
        print("Video Downloader CLI")
        try:
            url = input("Enter video or web page URL: ").strip()
        except EOFError:
            print("No URL provided. Exiting.")
            return 1

    if not url:
        print("Error: URL cannot be empty.")
        return 1

    print(f"Starting download from: {url}")
    print(f"Output directory: {args.output}")

    last_pct = [-1]

    def cli_progress(d):
        status = d.get("status")
        if status == "downloading":
            pct = d.get("_percent_str", "").strip()
            if pct and pct != last_pct[0]:
                last_pct[0] = pct
                speed = d.get("_speed_str", "").strip()
                eta = d.get("_eta_str", "").strip()
                extra = f" | Speed: {speed}" if speed else ""
                extra += f" | ETA: {eta}" if eta else ""
                print(f"\rDownloading: {pct}{extra}   ", end="", flush=True)
        elif status == "finished":
            print(f"\nDownload completed: {d.get('filename', '')}")

    res = download_video(
        url=url,
        output_dir=args.output,
        format_opt=args.format,
        audio_only=args.audio_only,
        progress_callback=cli_progress,
        logger=print,
    )

    if res["success"]:
        print(f"\nSuccess! Saved to: {res['filepath']}")
        return 0
    else:
        print(f"\nDownload failed: {res['error']}")
        return 1


class VideoDownloaderGUI:
    """Tkinter-based Graphical User Interface for the Video Downloader."""

    def __init__(self, root):
        self.root = root
        self.root.title("Video Downloader")
        self.root.geometry("620x380")
        self.root.minsize(550, 320)

        # Apply dark theme styling
        self.bg_color = "#1e1e24"
        self.fg_color = "#f0f0f5"
        self.accent_color = "#3b82f6"
        self.entry_bg = "#2b2b36"
        self.root.configure(bg=self.bg_color)

        self._is_downloading = False
        self._build_ui()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TProgressbar", thickness=16, troughcolor=self.entry_bg, background=self.accent_color)

        main_frame = tk.Frame(self.root, bg=self.bg_color, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_lbl = tk.Label(
            main_frame,
            text="Universal Video Downloader",
            font=("Segoe UI", 16, "bold"),
            bg=self.bg_color,
            fg=self.fg_color,
        )
        title_lbl.pack(anchor="w", pady=(0, 15))

        # URL Frame
        url_frame = tk.Frame(main_frame, bg=self.bg_color)
        url_frame.pack(fill=tk.X, pady=(0, 10))

        url_label = tk.Label(url_frame, text="Video / Page URL:", bg=self.bg_color, fg=self.fg_color, font=("Segoe UI", 10))
        url_label.pack(anchor="w", pady=(0, 5))

        self.url_entry = tk.Entry(
            url_frame,
            bg=self.entry_bg,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            relief=tk.FLAT,
            font=("Segoe UI", 10),
            highlightthickness=1,
            highlightbackground="#444",
            highlightcolor=self.accent_color,
        )
        self.url_entry.pack(fill=tk.X, ipady=4)

        # Output Folder Frame
        folder_frame = tk.Frame(main_frame, bg=self.bg_color)
        folder_frame.pack(fill=tk.X, pady=(0, 10))

        folder_label = tk.Label(folder_frame, text="Download Folder:", bg=self.bg_color, fg=self.fg_color, font=("Segoe UI", 10))
        folder_label.pack(anchor="w", pady=(0, 5))

        folder_input_row = tk.Frame(folder_frame, bg=self.bg_color)
        folder_input_row.pack(fill=tk.X)

        self.folder_var = tk.StringVar(value=os.path.abspath("downloads"))
        self.folder_entry = tk.Entry(
            folder_input_row,
            textvariable=self.folder_var,
            bg=self.entry_bg,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            relief=tk.FLAT,
            font=("Segoe UI", 10),
            highlightthickness=1,
            highlightbackground="#444",
            highlightcolor=self.accent_color,
        )
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

        browse_btn = tk.Button(
            folder_input_row,
            text="Browse...",
            command=self._browse_folder,
            bg="#374151",
            fg=self.fg_color,
            activebackground="#4b5563",
            activeforeground=self.fg_color,
            relief=tk.FLAT,
            padx=10,
            cursor="hand2",
        )
        browse_btn.pack(side=tk.RIGHT, padx=(8, 0))

        # Options Row
        opts_frame = tk.Frame(main_frame, bg=self.bg_color)
        opts_frame.pack(fill=tk.X, pady=(0, 10))

        self.audio_only_var = tk.BooleanVar(value=False)
        audio_chk = tk.Checkbutton(
            opts_frame,
            text="Audio Only (Extract MP3)",
            variable=self.audio_only_var,
            bg=self.bg_color,
            fg=self.fg_color,
            selectcolor=self.entry_bg,
            activebackground=self.bg_color,
            activeforeground=self.fg_color,
            cursor="hand2",
        )
        audio_chk.pack(side=tk.LEFT)

        # Progress bar & status label
        self.progress_bar = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, mode="determinate", style="TProgressbar")
        self.progress_bar.pack(fill=tk.X, pady=(10, 5))

        self.status_var = tk.StringVar(value="Ready to download.")
        self.status_lbl = tk.Label(
            main_frame,
            textvariable=self.status_var,
            bg=self.bg_color,
            fg="#9ca3af",
            font=("Segoe UI", 9),
            anchor="w",
        )
        self.status_lbl.pack(fill=tk.X, pady=(0, 15))

        # Download Button
        self.download_btn = tk.Button(
            main_frame,
            text="Download Video",
            command=self._start_download_thread,
            bg=self.accent_color,
            fg="#ffffff",
            activebackground="#2563eb",
            activeforeground="#ffffff",
            font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT,
            pady=8,
            cursor="hand2",
        )
        self.download_btn.pack(fill=tk.X)

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder:
            self.folder_var.set(folder)

    def _start_download_thread(self):
        if self._is_downloading:
            return

        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter a valid video or webpage URL.")
            return

        out_dir = self.folder_var.get().strip()
        if not out_dir:
            out_dir = "downloads"

        self._is_downloading = True
        self.download_btn.config(state=tk.DISABLED, text="Downloading...")
        self.progress_bar["value"] = 0
        self.status_var.set("Connecting and fetching stream...")

        t = threading.Thread(
            target=self._download_worker,
            args=(url, out_dir, self.audio_only_var.get()),
            daemon=True,
        )
        t.start()

    def _download_worker(self, url: str, out_dir: str, audio_only: bool):
        def gui_progress(d):
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                pct_str = d.get("_percent_str", "").strip()

                val = 0
                if total and total > 0:
                    val = (downloaded / total) * 100
                elif pct_str:
                    try:
                        val = float(pct_str.replace("%", ""))
                    except ValueError:
                        pass

                speed = d.get("_speed_str", "").strip()
                eta = d.get("_eta_str", "").strip()
                msg = f"Downloading: {pct_str}"
                if speed:
                    msg += f" | {speed}"
                if eta:
                    msg += f" | ETA {eta}"

                self.root.after(0, self._update_progress, val, msg)
            elif status == "finished":
                self.root.after(0, self._update_progress, 100, "Processing downloaded media...")

        res = download_video(
            url=url,
            output_dir=out_dir,
            audio_only=audio_only,
            progress_callback=gui_progress,
        )

        self.root.after(0, self._on_download_complete, res)

    def _update_progress(self, percent: float, msg: str):
        self.progress_bar["value"] = percent
        self.status_var.set(msg)

    def _on_download_complete(self, res: dict):
        self._is_downloading = False
        self.download_btn.config(state=tk.NORMAL, text="Download Video")

        if res["success"]:
            self.progress_bar["value"] = 100
            self.status_var.set(f"Completed: {os.path.basename(res['filepath'])}")
            messagebox.showinfo(
                "Download Succeeded",
                f"Video successfully downloaded to:\n{res['filepath']}",
            )
        else:
            self.status_var.set("Download failed.")
            messagebox.showerror("Download Error", f"Error downloading video:\n{res['error']}")


def main():
    parser = argparse.ArgumentParser(
        description="Download video from any web page or direct URL.",
        epilog="If no URL is provided and Tkinter is available, the graphical interface will launch.",
    )
    parser.add_argument("url", nargs="?", help="URL of the video or webpage")
    parser.add_argument(
        "-o", "--output", default="downloads", help="Directory where video should be saved (default: downloads)"
    )
    parser.add_argument(
        "-f", "--format", default="best", help="Video format code or option for yt-dlp (default: best)"
    )
    parser.add_argument(
        "-a", "--audio-only", action="store_true", help="Extract audio only (MP3)"
    )
    parser.add_argument(
        "--cli", action="store_true", help="Force command-line interface even when no URL is provided"
    )

    args = parser.parse_args()

    # Determine whether to launch GUI or CLI
    # If URL is supplied or CLI flag is set or Tkinter is not available, run CLI
    if args.url or args.cli or not HAS_TKINTER:
        sys.exit(run_cli(args))
    else:
        root = tk.Tk()
        app = VideoDownloaderGUI(root)
        root.mainloop()


if __name__ == "__main__":
    main()
