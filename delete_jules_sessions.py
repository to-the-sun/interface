#!/usr/bin/env python3
"""
delete_jules_sessions.py - Delete old or specified Jules API sessions.

Usage:
  python3 delete_jules_sessions.py [options]

Examples:
  # Dry run: view sessions that would be deleted (older than 7 days)
  python3 delete_jules_sessions.py --dry-run --days-old 7

  # Delete sessions older than 30 days
  python3 delete_jules_sessions.py --days-old 30 --force

  # Delete ALL sessions
  python3 delete_jules_sessions.py --all --force

  # List all sessions without deleting
  python3 delete_jules_sessions.py --list-only
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

DEFAULT_BASE_URL = "https://jules.googleapis.com/v1alpha"


def fetch_all_sessions(api_key, base_url=DEFAULT_BASE_URL):
    """Fetch all sessions from the Jules API handling pagination."""
    sessions = []
    page_token = None

    while True:
        url = f"{base_url.rstrip('/')}/sessions?pageSize=100"
        if page_token:
            url += f"&pageToken={urllib.parse.quote(page_token)}"

        req = urllib.request.Request(
            url,
            headers={
                "X-Goog-Api-Key": api_key,
                "Content-Type": "application/json",
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(req) as response:
                status = getattr(response, "status", 200)
                if status != 200:
                    raise RuntimeError(f"API request failed with status code {status}")
                data = json.loads(response.read().decode("utf-8"))
                current_sessions = data.get("sessions", [])
                sessions.extend(current_sessions)
                page_token = data.get("nextPageToken")
                if not page_token:
                    break
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else str(e)
            raise RuntimeError(f"HTTP Error {e.code}: {e.reason}\n{error_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"URL Error: {e.reason}")

    return sessions


def parse_timestamp(ts_str):
    """Parse ISO 8601 timestamp string into a timezone-aware datetime object."""
    if not ts_str:
        return None
    # Handle 'Z' suffix for Python fromisoformat compatibility
    formatted_ts = ts_str.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(formatted_ts)
    except ValueError:
        # Fallback manual parse if isoformat fails
        return None


def filter_sessions(sessions, days_old=None, state=None, delete_all=False):
    """Filter sessions based on age, state, or all flag."""
    if delete_all:
        target_sessions = sessions
    else:
        target_sessions = list(sessions)

    filtered = []
    now = datetime.now(timezone.utc)

    for session in target_sessions:
        # State filter
        if state and session.get("state", "").upper() != state.upper():
            continue

        # Days old filter
        if days_old is not None:
            create_time_str = session.get("createTime") or session.get("updateTime")
            if create_time_str:
                created_dt = parse_timestamp(create_time_str)
                if created_dt:
                    age = now - created_dt
                    if age < timedelta(days=days_old):
                        continue

        filtered.append(session)

    return filtered


def delete_session(session_name_or_id, api_key, base_url=DEFAULT_BASE_URL):
    """Delete a single session via the Jules API."""
    if "/" in str(session_name_or_id):
        endpoint = str(session_name_or_id)
    else:
        endpoint = f"sessions/{session_name_or_id}"

    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    req = urllib.request.Request(
        url,
        headers={
            "X-Goog-Api-Key": api_key,
        },
        method="DELETE",
    )

    try:
        with urllib.request.urlopen(req) as response:
            status = getattr(response, "status", 200)
            return status in (200, 204)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        raise RuntimeError(f"HTTP Error {e.code} when deleting {session_name_or_id}: {e.reason}\n{error_body}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL Error when deleting {session_name_or_id}: {e.reason}")


def main():
    parser = argparse.ArgumentParser(description="Delete old or specified Jules API sessions.")
    parser.add_argument("--api-key", default=os.getenv("JULES_API_KEY"), help="Jules API key (or set JULES_API_KEY env var)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL for Jules API")
    parser.add_argument("--days-old", type=float, help="Delete sessions created/updated more than N days ago")
    parser.add_argument("--state", help="Filter by session state (e.g. COMPLETED, FAILED, QUEUED)")
    parser.add_argument("--all", action="store_true", help="Target all sessions (ignores age restriction)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate deletion without deleting anything")
    parser.add_argument("--list-only", action="store_true", help="Only list sessions and exit")
    parser.add_argument("--force", "-f", action="store_true", help="Do not ask for confirmation before deleting")

    args = parser.parse_args()

    if not args.api_key:
        print("Error: API key is required. Set JULES_API_KEY environment variable or pass --api-key.", file=sys.stderr)
        sys.exit(1)

    print("Fetching sessions from Jules API...")
    try:
        all_sessions = fetch_all_sessions(args.api_key, args.base_url)
    except Exception as e:
        print(f"Error fetching sessions: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Total sessions found: {len(all_sessions)}")

    if args.list_only:
        for idx, s in enumerate(all_sessions, start=1):
            s_id = s.get("name") or s.get("id", "unknown")
            title = s.get("title") or s.get("prompt", "No prompt")
            state = s.get("state", "UNKNOWN")
            created = s.get("createTime", "Unknown date")
            print(f"[{idx}] {s_id} | State: {state} | Created: {created} | Title/Prompt: {title[:60]}")
        return

    if not args.all and args.days_old is None and not args.state:
        print("Warning: Neither --days-old, --state, nor --all specified.", file=sys.stderr)
        print("To protect against accidental deletion, please specify --days-old N, --state STATE, or --all.", file=sys.stderr)
        sys.exit(1)

    target_sessions = filter_sessions(all_sessions, days_old=args.days_old, state=args.state, delete_all=args.all)

    print(f"Sessions matching criteria for deletion: {len(target_sessions)}")

    if not target_sessions:
        print("No matching sessions found to delete.")
        return

    for idx, s in enumerate(target_sessions, start=1):
        s_id = s.get("name") or s.get("id", "unknown")
        title = s.get("title") or s.get("prompt", "No prompt")
        state = s.get("state", "UNKNOWN")
        created = s.get("createTime", "Unknown date")
        print(f"  [{idx}] {s_id} | State: {state} | Created: {created} | Title: {title[:60]}")

    if args.dry_run:
        print("\n[DRY RUN] No sessions were deleted.")
        return

    if not args.force:
        confirm = input(f"\nAre you sure you want to delete these {len(target_sessions)} sessions? (y/N): ")
        if confirm.strip().lower() not in ("y", "yes"):
            print("Operation cancelled.")
            return

    print("\nDeleting sessions...")
    success_count = 0
    fail_count = 0

    for s in target_sessions:
        s_name = s.get("name") or s.get("id")
        try:
            delete_session(s_name, args.api_key, args.base_url)
            print(f"Deleted: {s_name}")
            success_count += 1
        except Exception as e:
            print(f"Failed to delete {s_name}: {e}", file=sys.stderr)
            fail_count += 1

    print(f"\nFinished! Successfully deleted: {success_count}, Failed: {fail_count}.")


if __name__ == "__main__":
    main()
