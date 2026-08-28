#!/usr/bin/env pythonw
import sys
import os
import subprocess

# Ensure working directory is set to script root
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Import and execute main GUI application
from audio_compressor import main

if __name__ == "__main__":
    main()
