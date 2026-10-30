#!/usr/bin/env python3
"""
GitHub Copilot API Client
Handles authentication (gh CLI, GITHUB_TOKEN, credentials.json, Device Flow),
token exchange (api.github.com/copilot_internal/v2/token), and streaming API calls.
"""

import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Any, Generator, Optional, List

# VSCode GitHub Copilot Extension Client ID for OAuth Device Flow
CLIENT_ID = "01ab8ac9400c4e429a23"

class CopilotAuthError(Exception):
    """Raised when authentication with GitHub / Copilot fails."""
    pass

class CopilotClient:
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token or self._find_github_token()
        self.copilot_token: Optional[str] = None
        self.copilot_expires_at: int = 0
        self.copilot_endpoints: Dict[str, str] = {}
        self.pending_device_flow: Optional[Dict[str, Any]] = None

    def _find_github_token(self) -> Optional[str]:
        """Attempt to retrieve GitHub token from env, gh CLI, or credentials file."""
        # 1. Environment variable
        if os.environ.get("GITHUB_TOKEN"):
            return os.environ["GITHUB_TOKEN"]
        if os.environ.get("GH_TOKEN"):
            return os.environ["GH_TOKEN"]

        # 2. gh CLI
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                check=True
            )
            token = result.stdout.strip()
            if token:
                return token
        except Exception:
            pass

        # 3. credentials.json file in current directory or user home
        creds_paths = ["credentials.json", os.path.expanduser("~/.config/github-copilot/credentials.json")]
        for path in creds_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        token = data.get("github_token") or data.get("token") or data.get("access_token")
                        if token:
                            return token
                except Exception:
                    pass

        return None

    def start_device_flow(self) -> Dict[str, Any]:
        """Initiate GitHub OAuth Device Flow and return user_code & verification_uri."""
        req_data = json.dumps({"client_id": CLIENT_ID, "scope": "read:user"}).encode("utf-8")
        req = urllib.request.Request(
            "https://github.com/login/device/code",
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
        try:
            with urllib.request.urlopen(req) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                self.pending_device_flow = res
                return res
        except Exception as e:
            raise CopilotAuthError(f"Failed to initiate device flow: {e}")

    def device_flow_authenticate(self) -> str:
        """Perform GitHub OAuth Device Flow authentication blocking loop."""
        res = self.start_device_flow() if not self.pending_device_flow else self.pending_device_flow

        device_code = res["device_code"]
        user_code = res["user_code"]
        verification_uri = res["verification_uri"]
        interval = res.get("interval", 5)

        print("\n" + "=" * 60)
        print("GitHub Copilot Authentication Required")
        print(f"1. Open URL in browser: {verification_uri}")
        print(f"2. Enter Code: {user_code}")
        print("=" * 60 + "\n")

        poll_data = json.dumps({
            "client_id": CLIENT_ID,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
        }).encode("utf-8")

        while True:
            time.sleep(interval)
            poll_req = urllib.request.Request(
                "https://github.com/login/oauth/access_token",
                data=poll_data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            try:
                with urllib.request.urlopen(poll_req) as resp:
                    poll_res = json.loads(resp.read().decode("utf-8"))
            except Exception:
                continue

            if "access_token" in poll_res:
                token = poll_res["access_token"]
                self.github_token = token
                self.pending_device_flow = None
                # Save to credentials.json
                try:
                    with open("credentials.json", "w", encoding="utf-8") as f:
                        json.dump({"github_token": token}, f, indent=2)
                except Exception:
                    pass
                return token
            elif poll_res.get("error") == "authorization_pending":
                continue
            elif poll_res.get("error") == "slow_down":
                interval += 5
                continue
            else:
                raise CopilotAuthError(f"Device flow authentication failed: {poll_res.get('error_description', poll_res)}")

    def ensure_copilot_token(self) -> str:
        """Obtain or refresh Copilot internal session token."""
        if not self.github_token:
            self.device_flow_authenticate()

        if self.copilot_token and time.time() < (self.copilot_expires_at - 60):
            return self.copilot_token

        req = urllib.request.Request(
            "https://api.github.com/copilot_internal/v2/token",
            headers={
                "Authorization": f"token {self.github_token}",
                "User-Agent": "GithubCopilot/1.155.0",
                "Accept": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self.copilot_token = data["token"]
                self.copilot_expires_at = data.get("expires_at", time.time() + 1800)
                self.copilot_endpoints = data.get("endpoints", {})
                return self.copilot_token
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                req = urllib.request.Request(
                    "https://api.github.com/copilot_internal/v2/token",
                    headers={
                        "Authorization": f"Bearer {self.github_token}",
                        "User-Agent": "GithubCopilot/1.155.0",
                        "Accept": "application/json"
                    }
                )
                try:
                    with urllib.request.urlopen(req) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        self.copilot_token = data["token"]
                        self.copilot_expires_at = data.get("expires_at", time.time() + 1800)
                        self.copilot_endpoints = data.get("endpoints", {})
                        return self.copilot_token
                except Exception as ex:
                    raise CopilotAuthError(f"Copilot Token Request failed (401/403): {ex}. Ensure account has GitHub Copilot (Free/Pro/Biz) active.")
            raise CopilotAuthError(f"Failed to fetch Copilot internal token: {e}")
        except Exception as e:
            raise CopilotAuthError(f"Failed to fetch Copilot internal token: {e}")

    def chat_completions(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: str = "gpt-4o",
        stream: bool = True
    ) -> Generator[Dict[str, Any], None, None]:
        """Send chat completion request to GitHub Copilot API with streaming yield."""
        token = self.ensure_copilot_token()

        base_url = self.copilot_endpoints.get("api", "https://api.individual.githubcopilot.com")
        if not base_url.endswith("/"):
            base_url += "/"
        url = urllib.parse.urljoin(base_url, "chat/completions")

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream
        }
        if tools:
            payload["tools"] = tools

        headers = {
            "Authorization": f"Bearer {token}",
            "Editor-Version": "vscode/1.85.1",
            "User-Agent": "GitHubCopilotChat/0.11.1",
            "Copilot-Integration-Id": "vscode-chat",
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if stream else "application/json"
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req) as resp:
                if stream:
                    for line in resp:
                        line_str = line.decode("utf-8").strip()
                        if not line_str:
                            continue
                        if line_str.startswith("data: "):
                            raw_data = line_str[6:].strip()
                            if raw_data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(raw_data)
                                yield chunk
                            except json.JSONDecodeError:
                                continue
                else:
                    body = resp.read().decode("utf-8")
                    yield json.loads(body)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
            raise RuntimeError(f"Copilot API error ({e.code}): {err_body}")
