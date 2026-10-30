import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from GitHubCopilotAgent.copilot_client import CopilotClient, CopilotAuthError
from GitHubCopilotAgent.agent_engine import JulesAgentEngine
from GitHubCopilotAgent.web_server import JulesWebHandler

class TestGitHubCopilotAgent(unittest.TestCase):

    def setUp(self):
        self.mock_client = MagicMock(spec=CopilotClient)
        self.mock_client.github_token = "dummy_token"
        self.mock_client.ensure_copilot_token.return_value = "copilot_session_token"

    def test_client_token_discovery(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test_env_token"}):
            client = CopilotClient()
            self.assertEqual(client.github_token, "test_env_token")

    def test_agent_engine_list_files(self):
        engine = JulesAgentEngine(client=self.mock_client, repo_dir=".")
        res = engine.execute_tool("list_files", {"path": "."})
        self.assertIn("README.md", res)

    def test_agent_engine_file_ops(self):
        engine = JulesAgentEngine(client=self.mock_client, repo_dir=".")
        test_file = "test_temp_jules.txt"
        try:
            # write
            w_res = engine.execute_tool("write_file", {"filepath": test_file, "content": "Hello World"})
            self.assertIn("Successfully wrote", w_res)

            # read
            r_res = engine.execute_tool("read_file", {"filepath": test_file})
            self.assertEqual(r_res, "Hello World")

            # replace
            rep_res = engine.execute_tool("replace_in_file", {"filepath": test_file, "old_str": "World", "new_str": "Jules"})
            self.assertIn("Successfully replaced", rep_res)

            # verify replace
            r_res2 = engine.execute_tool("read_file", {"filepath": test_file})
            self.assertEqual(r_res2, "Hello Jules")
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_agent_engine_git_branch(self):
        engine = JulesAgentEngine(client=self.mock_client, repo_dir=".")
        res = engine.execute_tool("git_branch", {"branch_name": "test-jules-branch"})
        self.assertIn("Switched to git branch", res)

    def test_agent_engine_process_prompt_streaming(self):
        self.mock_client.chat_completions.return_value = iter([
            {"choices": [{"delta": {"content": "Hello! I am Jules."}}]}
        ])
        engine = JulesAgentEngine(client=self.mock_client, repo_dir=".")
        chunks = list(engine.process_prompt("Hi"))
        self.assertTrue(any(c.get("type") == "content_delta" and "Hello" in c.get("content") for c in chunks))

if __name__ == "__main__":
    unittest.main()
