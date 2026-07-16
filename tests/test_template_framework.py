import contextlib
import io
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.generate import AgentGenerator


REPO_ROOT = Path(__file__).resolve().parents[1]


class TemplateFrameworkTest(unittest.TestCase):
    def test_default_template_builds_generic_interaction_display(self):
        with tempfile.TemporaryDirectory(prefix="tauritavern-template-") as tmp:
            project = Path(tmp)
            shutil.copy2(REPO_ROOT / "AGENTS.md", project / "AGENTS.md")
            for directory in ("interaction", "literature"):
                shutil.copytree(REPO_ROOT / directory, project / directory)

            with contextlib.redirect_stdout(io.StringIO()):
                AgentGenerator(str(project), str(REPO_ROOT)).run()

            output = project / "output" / "agent"
            extension = output / "extensions" / "my-card-writer-interaction"
            config = (extension / "package-config.js").read_text(encoding="utf-8")
            runtime = (extension / "index.js").read_text(encoding="utf-8")
            styles = (extension / "style.css").read_text(encoding="utf-8")
            profile = json.loads(
                (output / "my-card-writer.agent-profile.json").read_text(
                    encoding="utf-8"
                )
            )

            self.assertIn('"projectId": "my-card-writer"', config)
            self.assertIn('"narrativeFile": "output/main.md"', config)
            self.assertIn(
                '"characterStateFile": "persist/character_states.json"', config
            )
            self.assertIn("hydrateFromLatestRun", runtime)
            self.assertIn("renderNarrative", runtime)
            self.assertIn("renderBriefing", runtime)
            self.assertIn("waifuMode", runtime)
            self.assertIn("data-vn-mode", styles)
            self.assertIn("tt-interaction-progress", styles)
            self.assertNotIn("hongloumeng", runtime.lower())
            self.assertNotIn("红楼梦", runtime)
            self.assertIsNone(profile["instructions"]["agentSystemPrompt"])
            self.assertEqual(["*"], profile["skills"]["visible"])

            with zipfile.ZipFile(
                output / "skills" / "interaction-system.ttskill"
            ) as package:
                skill = package.read("SKILL.md").decode("utf-8")
                self.assertIn("extensions.briefing", skill)
                self.assertIn("persist/character_states.json", skill)


if __name__ == "__main__":
    unittest.main()
