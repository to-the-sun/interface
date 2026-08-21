#!/usr/bin/env python3
"""
Double-click to preview (dry-run) deleting sessions older than 7 days.
"""

import sys
import delete_jules_sessions

if __name__ == "__main__":
    print("=== 2. Dry Run: Preview Sessions Older Than 7 Days ===")
    sys.argv = ["delete_jules_sessions.py", "--days-old", "7", "--dry-run"]
    try:
        delete_jules_sessions.main()
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        input("\nPress Enter to exit...")
