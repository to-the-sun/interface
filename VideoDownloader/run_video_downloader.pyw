#!/usr/bin/env pythonw
"""
Video Downloader Launcher (.pyw for windowless execution on Windows)
"""
import os
import subprocess
import sys

if __name__ == "__main__":
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "video_downloader.py")
    python_exe = sys.executable
    if "python.exe" in python_exe.lower():
        pythonw_exe = python_exe.lower().replace("python.exe", "pythonw.exe")
        if os.path.exists(pythonw_exe):
            python_exe = pythonw_exe

    subprocess.Popen([python_exe, script_path])
