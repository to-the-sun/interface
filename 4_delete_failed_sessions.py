#!/usr/bin/env python3
"""
Double-click to delete sessions in FAILED state.
"""

import sys
import delete_jules_sessions

if __name__ == "__main__":
    print("=== 4. Delete Failed Sessions ===")
    sys.argv = ["delete_jules_sessions.py", "--state", "FAILED"]
    try:
        delete_jules_sessions.main()
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        input("\nPress Enter to exit...")
