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


def load_api_key(cli_key=None, config_path="credentials.json"):
    """Load API key from CLI argument, environment variable, or credentials.json."""
    if cli_key:
        return cli_key

    env_key = os.getenv("JULES_API_KEY")
    if env_key:
        return env_key

    # Try credentials.json in current directory or script directory
    search_paths = [config_path]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_config = os.path.join(script_dir, config_path)
    if script_config not in search_paths:
        search_paths.append(script_config)

    for p in search_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    key = data.get("JULES_API_KEY") or data.get("api_key")
                    if key and key != "YOUR_API_KEY_HERE":
                        return key
            except Exception as e:
                print(f"Warning: Failed to read credentials from {p}: {e}", file=sys.stderr)

    return None


def fetch_sessions_with_query(api_key, query_params="", base_url=DEFAULT_BASE_URL):
    """Fetch sessions from the Jules API with given query parameters handling pagination."""
    sessions = []
    page_token = None

    while True:
        url = f"{base_url.rstrip('/')}/sessions?pageSize=100"
        if query_params:
            url += f"&{query_params.lstrip('&')}"
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
                    break
                data = json.loads(response.read().decode("utf-8"))
                current_sessions = data.get("sessions", [])
                sessions.extend(current_sessions)
                page_token = data.get("nextPageToken")
                if not page_token:
                    break
        except Exception:
            # Query parameter variant may not be supported by endpoint
            break

    return sessions


def fetch_all_sessions(api_key, base_url=DEFAULT_BASE_URL):
    """Fetch all sessions from the Jules API, attempting multiple query parameters to include archived items."""
    query_variants = [
        "",
        "includeArchived=true",
        "showArchived=true",
        "filter=state%3DARCHIVED",
        "filter=archived%3Dtrue",
        "filter=is_archived%3Dtrue",
    ]

    all_sessions_by_key = {}

    for query in query_variants:
        fetched = fetch_sessions_with_query(api_key, query_params=query, base_url=base_url)
        for s in fetched:
            s_key = s.get("name") or s.get("id")
            if s_key and s_key not in all_sessions_by_key:
                all_sessions_by_key[s_key] = s

    return list(all_sessions_by_key.values())


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
        if state:
            req_state = state.upper()
            sess_state = str(session.get("state", "")).upper()

            is_archived_flag = (
                session.get("isArchived") is True
                or session.get("archived") is True
                or str(session.get("isArchived")).lower() == "true"
                or str(session.get("archived")).lower() == "true"
                or bool(session.get("archivedTime"))
                or bool(session.get("archiveTime"))
                or bool(session.get("archived_at"))
            )

            if req_state == "ARCHIVED":
                if sess_state not in ("ARCHIVED", "STATE_ARCHIVED", "SESSION_STATE_ARCHIVED") and "ARCHIV" not in sess_state and not is_archived_flag:
                    continue
            else:
                if sess_state != req_state:
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
    parser.add_argument("--api-key", help="Jules API key (or set JULES_API_KEY env var / credentials.json)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL for Jules API")
    parser.add_argument("--days-old", type=float, help="Delete sessions created/updated more than N days ago")
    parser.add_argument("--state", help="Filter by session state (e.g. COMPLETED, FAILED, QUEUED, ARCHIVED)")
    parser.add_argument("--all", action="store_true", help="Target all sessions (ignores age restriction)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate deletion without deleting anything")
    parser.add_argument("--list-only", action="store_true", help="Only list sessions and exit")
    parser.add_argument("--force", "-f", action="store_true", help="Do not ask for confirmation before deleting")

    args = parser.parse_args()

    api_key = load_api_key(args.api_key)

    if not api_key:
        print("Error: API key is required. Please paste your API key into credentials.json,", file=sys.stderr)
        print("set the JULES_API_KEY environment variable, or pass --api-key.", file=sys.stderr)
        sys.exit(1)

    print("Fetching sessions from Jules API...")
    try:
        all_sessions = fetch_all_sessions(api_key, args.base_url)
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
            delete_session(s_name, api_key, args.base_url)
            print(f"Deleted: {s_name}")
            success_count += 1
        except Exception as e:
            print(f"Failed to delete {s_name}: {e}", file=sys.stderr)
            fail_count += 1

    print(f"\nFinished! Successfully deleted: {success_count}, Failed: {fail_count}.")


if __name__ == "__main__":
    main()
