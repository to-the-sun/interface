#!/usr/bin/env python3
"""
Double-click to delete ALL Jules API sessions.
"""

import sys
import delete_jules_sessions

if __name__ == "__main__":
    print("=== 5. Delete ALL Sessions ===")
    sys.argv = ["delete_jules_sessions.py", "--all"]
    try:
        delete_jules_sessions.main()
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        input("\nPress Enter to exit...")
