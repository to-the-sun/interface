#!/usr/bin/env python3
"""
Web Server for Jules GitHub Copilot Agent.
Provides REST and SSE endpoints for real-time Web UI streaming.
"""

import os
import sys
import json
import http.server
import socketserver
import urllib.parse
from typing import Dict, Any

from .copilot_client import CopilotClient
from .agent_engine import JulesAgentEngine

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

class JulesWebHandler(http.server.BaseHTTPRequestHandler):
    agent_engine: JulesAgentEngine = None

    def log_message(self, format, *args):
        pass  # Quiet HTTP logging

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            index_path = os.path.join(STATIC_DIR, "index.html")
            if os.path.exists(index_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(index_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Index file not found")
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/prompt":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                body = json.loads(post_data.decode('utf-8'))
                user_prompt = body.get("prompt", "")
                model = body.get("model", "gpt-4o")
            except Exception:
                self.send_error(400, "Invalid JSON payload")
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            try:
                for event in JulesWebHandler.agent_engine.process_prompt(user_prompt, model=model):
                    event_str = f"data: {json.dumps(event)}\n\n"
                    self.wfile.write(event_str.encode('utf-8'))
                    self.wfile.flush()
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            except Exception as e:
                err_event = json.dumps({"type": "error", "message": str(e)})
                self.wfile.write(f"data: {err_event}\n\n".encode('utf-8'))
                self.wfile.flush()
        else:
            self.send_error(404, "Endpoint not found")

def start_server(port: int = 8080, repo_dir: str = "."):
    client = CopilotClient()
    engine = JulesAgentEngine(client=client, repo_dir=repo_dir)
    JulesWebHandler.agent_engine = engine

    server_address = ('', port)
    httpd = socketserver.TCPServer(server_address, JulesWebHandler)
    print(f"🚀 Jules Copilot Web Interface available at http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down web server...")
        httpd.server_close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    start_server(port=port)
