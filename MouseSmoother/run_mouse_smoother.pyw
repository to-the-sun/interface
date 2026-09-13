import os
import sys

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    target_script = os.path.join(script_dir, "mouse_smoother.py")
    with open(target_script, "r", encoding="utf-8") as f:
        code = f.read()
    exec(compile(code, target_script, "exec"))
