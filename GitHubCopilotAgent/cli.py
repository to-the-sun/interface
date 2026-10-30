#!/usr/bin/env python3
"""
CLI entry point for Jules GitHub Copilot Agent.
Supports interactive terminal mode and web UI launcher mode.
"""

import os
import sys
import argparse
import webbrowser
import threading

from .copilot_client import CopilotClient, CopilotAuthError
from .agent_engine import JulesAgentEngine
from .web_server import start_server

def main():
    parser = argparse.ArgumentParser(description="Jules — GitHub Copilot Agent CLI & UI")
    parser.add_argument("prompt", nargs="*", help="Initial prompt or instruction for Jules")
    parser.add_argument("--web", action="store_true", help="Launch HTML Web Interface in browser")
    parser.add_argument("--port", type=int, default=8080, help="Port for Web Interface (default: 8080)")
    parser.add_argument("--model", type=str, default="gpt-4o", help="Copilot model to use (default: gpt-4o)")
    parser.add_argument("--repo", type=str, default=".", help="Target repository directory (default: current dir)")

    args = parser.parse_args()

    if args.web:
        print(f"Starting Jules Web UI on http://localhost:{args.port} ...")
        threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{args.port}")).start()
        start_server(port=args.port, repo_dir=args.repo)
        return

    print("=" * 60)
    print("🤖 Jules — GitHub Copilot Autonomous Agent")
    print("=" * 60)

    try:
        client = CopilotClient()
        engine = JulesAgentEngine(client=client, repo_dir=args.repo)
    except CopilotAuthError as e:
        print(f"❌ Authentication Error: {e}")
        sys.exit(1)

    initial_prompt = " ".join(args.prompt) if args.prompt else None

    if not initial_prompt:
        try:
            initial_prompt = input("\nWhat task would you like Jules to work on?\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

    if not initial_prompt:
        print("No task provided. Exiting.")
        sys.exit(0)

    print(f"\n🚀 Jules is processing task using model '{args.model}'...\n")

    def run_prompt_loop(prompt_text):
        for event in engine.process_prompt(prompt_text, model=args.model):
            evt_type = event.get("type")
            if evt_type == "content_delta":
                sys.stdout.write(event.get("content", ""))
                sys.stdout.flush()
            elif evt_type == "tool_call":
                print(f"\n\n🔧 [Tool Call] {event.get('name')}({event.get('args')})")
            elif evt_type == "tool_result":
                res = event.get("result", "")
                preview = res[:200] + "..." if len(res) > 200 else res
                print(f"📋 [Tool Result]: {preview}\n")

    run_prompt_loop(initial_prompt)

    while True:
        try:
            user_followup = input("\n> Follow-up / Instruction (or 'exit' to quit): ").strip()
            if not user_followup or user_followup.lower() in ("exit", "quit"):
                break
            run_prompt_loop(user_followup)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

if __name__ == "__main__":
    main()
