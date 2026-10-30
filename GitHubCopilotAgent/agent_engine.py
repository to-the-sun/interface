#!/usr/bin/env python3
"""
Jules Agent Engine powered by GitHub Copilot.
Handles tool definitions, plan state management, autonomous execution loop,
git branch creation, and GitHub Pull Request submission.
"""

import os
import sys
import json
import subprocess
import glob
from typing import Dict, Any, List, Optional, Callable, Generator

from .copilot_client import CopilotClient

SYSTEM_PROMPT = """You are Jules, an extremely skilled software engineer agent powered by GitHub Copilot.
Your job is to assist users by exploring codebases, making plans, editing code, running commands, and creating pull requests.

You must follow these rules:
1. Always work on a dedicated branch for proposed changes (use git_branch or create_pull_request).
2. Follow planning steps:
   - Formulate a clear plan with numbered steps.
   - Execute tools methodically step by step.
3. Available tools:
   - list_files(path): List files and directories in the given relative directory path.
   - read_file(filepath): Read the contents of a text file.
   - write_file(filepath, content): Write or overwrite a file with given content.
   - replace_in_file(filepath, old_str, new_str): Search and replace exact text in a file.
   - run_bash(command): Execute a shell command in the repository workspace.
   - git_branch(branch_name): Create and switch to a git branch.
   - git_commit(message): Commit all current changes in git.
   - create_pull_request(title, body, branch_name, base_branch): Push branch to origin and create a GitHub Pull Request using `gh pr create`.

Maintain a helpful, concise, and professional tone. Output clear explanations of your actions as you execute tools.
"""

TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Lists files and directories under the given directory relative to repo root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to list (default: .)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads full content of a specified text file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Relative file path to read."}
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Writes or overwrites a file with content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Relative file path to write."},
                    "content": {"type": "string", "description": "Content to write into the file."}
                },
                "required": ["filepath", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "replace_in_file",
            "description": "Replaces old string with new string inside a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Filepath to modify."},
                    "old_str": {"type": "string", "description": "Text string to find and replace."},
                    "new_str": {"type": "string", "description": "Replacement string."}
                },
                "required": ["filepath", "old_str", "new_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "Runs a shell command in the repository workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Bash shell command to run."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_branch",
            "description": "Creates and switches to a git branch for the proposed changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "branch_name": {"type": "string", "description": "Name of the git branch."}
                },
                "required": ["branch_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Commits modified state to current git branch.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Commit message."}
                },
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_pull_request",
            "description": "Pushes the current branch and creates a GitHub Pull Request via gh CLI.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Pull Request title."},
                    "body": {"type": "string", "description": "Pull Request body description."},
                    "branch_name": {"type": "string", "description": "Source branch name."},
                    "base_branch": {"type": "string", "description": "Target base branch (default: main or master)."}
                },
                "required": ["title", "body", "branch_name"]
            }
        }
    }
]

class JulesAgentEngine:
    def __init__(self, client: CopilotClient, repo_dir: str = "."):
        self.client = client
        self.repo_dir = os.path.abspath(repo_dir)
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self.plan: List[Dict[str, Any]] = []
        self.event_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.current_branch: Optional[str] = self._get_current_git_branch()

    def add_event_listener(self, callback: Callable[[Dict[str, Any]], None]):
        self.event_callbacks.append(callback)

    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        payload = {"type": event_type, "data": data}
        for cb in self.event_callbacks:
            try:
                cb(payload)
            except Exception:
                pass

    def _get_current_git_branch(self) -> Optional[str]:
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_dir, capture_output=True, text=True, check=True
            )
            return res.stdout.strip()
        except Exception:
            return None

    def execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Executes a tool locally in the workspace."""
        self._emit_event("tool_start", {"tool": name, "args": args})

        try:
            if name == "list_files":
                target_path = os.path.join(self.repo_dir, args.get("path", "."))
                if not os.path.exists(target_path):
                    res = f"Directory not found: {args.get('path', '.')}"
                else:
                    items = os.listdir(target_path)
                    res_items = []
                    for item in sorted(items):
                        full = os.path.join(target_path, item)
                        if os.path.isdir(full):
                            res_items.append(f"{item}/")
                        else:
                            res_items.append(item)
                    res = "\n".join(res_items) if res_items else "(empty directory)"

            elif name == "read_file":
                target_path = os.path.join(self.repo_dir, args["filepath"])
                if not os.path.exists(target_path):
                    res = f"File not found: {args['filepath']}"
                else:
                    with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                        res = f.read()

            elif name == "write_file":
                target_path = os.path.join(self.repo_dir, args["filepath"])
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(args["content"])
                res = f"Successfully wrote {len(args['content'])} characters to {args['filepath']}"

            elif name == "replace_in_file":
                target_path = os.path.join(self.repo_dir, args["filepath"])
                if not os.path.exists(target_path):
                    res = f"File not found: {args['filepath']}"
                else:
                    with open(target_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    if args["old_str"] not in content:
                        res = f"Target text not found in {args['filepath']}"
                    else:
                        new_content = content.replace(args["old_str"], args["new_str"], 1)
                        with open(target_path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        res = f"Successfully replaced target text in {args['filepath']}"

            elif name == "run_bash":
                proc = subprocess.run(
                    args["command"],
                    shell=True,
                    cwd=self.repo_dir,
                    capture_output=True,
                    text=True
                )
                output = proc.stdout
                if proc.stderr:
                    output += "\n" + proc.stderr
                res = output.strip() or f"(exit code {proc.returncode})"

            elif name == "git_branch":
                branch = args["branch_name"]
                proc = subprocess.run(
                    ["git", "checkout", "-b", branch],
                    cwd=self.repo_dir, capture_output=True, text=True
                )
                if proc.returncode != 0:
                    subprocess.run(["git", "checkout", branch], cwd=self.repo_dir, capture_output=True, text=True)
                self.current_branch = branch
                res = f"Switched to git branch '{branch}'"

            elif name == "git_commit":
                subprocess.run(["git", "add", "-A"], cwd=self.repo_dir, check=True)
                proc = subprocess.run(
                    ["git", "commit", "-m", args["message"]],
                    cwd=self.repo_dir, capture_output=True, text=True
                )
                res = proc.stdout.strip() or proc.stderr.strip() or "Committed changes."

            elif name == "create_pull_request":
                branch = args.get("branch_name") or self.current_branch or "jules-patch"
                base = args.get("base_branch", "main")
                title = args["title"]
                body = args["body"]

                # Push branch
                push_proc = subprocess.run(
                    ["git", "push", "-u", "origin", branch],
                    cwd=self.repo_dir, capture_output=True, text=True
                )

                # Attempt gh pr create
                pr_cmd = ["gh", "pr", "create", "--title", title, "--body", body, "--head", branch, "--base", base]
                pr_proc = subprocess.run(pr_cmd, cwd=self.repo_dir, capture_output=True, text=True)

                if pr_proc.returncode == 0:
                    res = f"Pull Request successfully created!\n{pr_proc.stdout.strip()}"
                else:
                    res = f"Git pushed branch '{branch}'. PR creation output: {pr_proc.stderr.strip() or pr_proc.stdout.strip()}"

            else:
                res = f"Unknown tool: {name}"

        except Exception as e:
            res = f"Error executing tool {name}: {str(e)}"

        self._emit_event("tool_end", {"tool": name, "result": res})
        return res

    def process_prompt(self, user_prompt: str, model: str = "gpt-4o") -> Generator[Dict[str, Any], None, None]:
        """Main agent message loop. Streams reasoning, invokes tools, yields responses."""
        self.messages.append({"role": "user", "content": user_prompt})
        self._emit_event("user_message", {"content": user_prompt})

        max_turns = 15
        for _ in range(max_turns):
            response_chunks = []
            tool_calls_map: Dict[int, Dict[str, Any]] = {}

            stream = self.client.chat_completions(
                messages=self.messages,
                tools=TOOLS_SPEC,
                model=model,
                stream=True
            )

            for chunk in stream:
                choices = chunk.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})

                # Process text chunk
                content_chunk = delta.get("content")
                if content_chunk:
                    response_chunks.append(content_chunk)
                    yield {"type": "content_delta", "content": content_chunk}

                # Process tool call chunks
                tool_calls_delta = delta.get("tool_calls")
                if tool_calls_delta:
                    for tc in tool_calls_delta:
                        idx = tc.get("index", 0)
                        if idx not in tool_calls_map:
                            tool_calls_map[idx] = {
                                "id": tc.get("id", f"call_{idx}"),
                                "type": "function",
                                "function": {"name": "", "arguments": ""}
                            }
                        if tc.get("id"):
                            tool_calls_map[idx]["id"] = tc["id"]
                        fn = tc.get("function", {})
                        if fn.get("name"):
                            tool_calls_map[idx]["function"]["name"] += fn["name"]
                        if fn.get("arguments"):
                            tool_calls_map[idx]["function"]["arguments"] += fn["arguments"]

            full_text = "".join(response_chunks)

            # Form assistant message entry
            assistant_msg: Dict[str, Any] = {"role": "assistant"}
            if full_text:
                assistant_msg["content"] = full_text

            if tool_calls_map:
                formatted_calls = list(tool_calls_map.values())
                assistant_msg["tool_calls"] = formatted_calls
                self.messages.append(assistant_msg)

                # Execute all requested tools
                for tc in formatted_calls:
                    tool_id = tc["id"]
                    func_name = tc["function"]["name"]
                    raw_args = tc["function"]["arguments"]
                    try:
                        args_dict = json.loads(raw_args) if raw_args else {}
                    except Exception:
                        args_dict = {}

                    yield {"type": "tool_call", "name": func_name, "args": args_dict}
                    tool_result = self.execute_tool(func_name, args_dict)
                    yield {"type": "tool_result", "name": func_name, "result": tool_result}

                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "name": func_name,
                        "content": tool_result
                    })
            else:
                if full_text:
                    self.messages.append(assistant_msg)
                break
