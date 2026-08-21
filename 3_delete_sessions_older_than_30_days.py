#!/usr/bin/env python3
"""
Double-click to delete sessions older than 30 days.
"""

import sys
import delete_jules_sessions

if __name__ == "__main__":
    print("=== 3. Delete Sessions Older Than 30 Days ===")
    sys.argv = ["delete_jules_sessions.py", "--days-old", "30"]
    try:
        delete_jules_sessions.main()
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        input("\nPress Enter to exit...")
