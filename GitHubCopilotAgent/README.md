# Jules — GitHub Copilot Autonomous Coding Agent

An autonomous AI software engineering agent that emulates **Jules** using **GitHub Copilot (Free, Pro, or Business)** plan subscriptions.

It connects directly to GitHub Copilot's chat completions API, plans complex coding tasks, executes local file operations and terminal commands, creates git branches for proposed changes, and submits Pull Requests via GitHub CLI.

---

## Features

- 🤖 **Emulates Jules**: Formulates step-by-step execution plans, explores codebases, edits files, runs tests, and submits PRs.
- 💳 **Supports GitHub Copilot Free Plan**: Works with any active GitHub Copilot subscription using `gh auth token`, `GITHUB_TOKEN`, or OAuth Device Flow authentication.
- 🌐 **Web Interface**: Dark-themed HTML/CSS/JS frontend matching the Jules interface with live chat streaming, plan checklists, and tool output streams.
- 💻 **Interactive CLI**: Terminal interface for quick command-line agent runs.
- 🚀 **One-Click Launchers**: Double-clickable `run_copilot_agent.bat` and `run_copilot_agent.pyw` launchers on Windows.

---

## Quick Start

### Option 1: Web Interface (GUI)
Double-click `run_copilot_agent.bat` or run:
```bash
python -m GitHubCopilotAgent.cli --web
```
This automatically opens your browser at `http://localhost:8080`.

### Option 2: CLI Mode
Run in terminal:
```bash
python -m GitHubCopilotAgent.cli "Fix bug in audio compressor sample rate conversion"
```

---

## Authentication

Jules auto-detects authentication in the following order:
1. `GITHUB_TOKEN` or `GH_TOKEN` environment variable.
2. Active GitHub CLI session (`gh auth token`).
3. Local `credentials.json` file.
4. **OAuth Device Flow**: If no token is detected, Jules provides a URL and user code to authenticate via GitHub in your browser.

---

## Running Unit Tests

Run the unit test suite with Python's built-in `unittest`:
```bash
python3 -m unittest GitHubCopilotAgent/test_copilot_agent.py
```
