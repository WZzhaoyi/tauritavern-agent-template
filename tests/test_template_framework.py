import contextlib
import io
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.check_release import validate_release_tag
from scripts.generate import AgentGenerator, ConfigLoader


REPO_ROOT = Path(__file__).resolve().parents[1]


class TemplateFrameworkTest(unittest.TestCase):
    def test_template_sync_preserves_project_owned_paths(self):
        ignored = {
            line.strip()
            for line in (
                REPO_ROOT / ".github" / ".templatesyncignore"
            ).read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "sync-template.yml"
        ).read_text(encoding="utf-8")

        self.assertEqual(
            {"projects/", "output/", ".github/workflows/"}, ignored
        )
        self.assertIn(
            "source_repo_path: WZzhaoyi/tauritavern-agent-template", workflow
        )
        self.assertIn("is_force_deletion: false", workflow)

    def test_release_workflow_tests_before_publishing(self):
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "release.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("python scripts/check_release.py", workflow)
        self.assertIn("needs: test", workflow)

    def test_project_framework_version_must_match_template(self):
        with tempfile.TemporaryDirectory(prefix="tauritavern-version-") as tmp:
            project = Path(tmp)
            config = (REPO_ROOT / "tauritavern.template.yaml").read_text(
                encoding="utf-8"
            )
            (project / "tauritavern.yaml").write_text(
                config.replace('version: "2.7.0"', 'version: "2.6.0"', 1),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "does not match template version"):
                AgentGenerator(str(project), str(REPO_ROOT))

    def test_release_tag_matches_framework_version(self):
        config_path = REPO_ROOT / "tauritavern.template.yaml"

        self.assertEqual("2.7.0", validate_release_tag("v2.7.0", config_path))
        for invalid_tag in ("2.7.0", "v2.7", "v2.7.1", "v02.7.0"):
            with self.subTest(tag=invalid_tag):
                with self.assertRaises(ValueError):
                    validate_release_tag(invalid_tag, config_path)

    def test_agents_guide_is_not_a_config_source(self):
        with tempfile.TemporaryDirectory(prefix="tauritavern-guide-") as tmp:
            project = Path(tmp)
            shutil.copy2(REPO_ROOT / "AGENTS.md", project / "AGENTS.md")

            with self.assertRaisesRegex(FileNotFoundError, "tauritavern.yaml"):
                ConfigLoader.load(project)

    def test_standalone_yaml_config_does_not_require_agents_guide(self):
        with tempfile.TemporaryDirectory(prefix="tauritavern-config-") as tmp:
            project = Path(tmp)
            shutil.copy2(
                REPO_ROOT / "tauritavern.template.yaml",
                project / "tauritavern.yaml",
            )

            config = ConfigLoader.load(project)

            self.assertEqual(1, config["schema_version"])
            self.assertEqual("my-card-writer", config["project"]["id"])
            self.assertFalse((project / "AGENTS.md").exists())

    def test_default_template_builds_generic_interaction_display(self):
        with tempfile.TemporaryDirectory(prefix="tauritavern-template-") as tmp:
            project = Path(tmp)
            shutil.copy2(REPO_ROOT / "AGENTS.md", project / "AGENTS.md")
            shutil.copy2(
                REPO_ROOT / "tauritavern.template.yaml",
                project / "tauritavern.yaml",
            )
            for directory in ("interaction", "literature"):
                shutil.copytree(REPO_ROOT / directory, project / directory)

            self.assertNotIn(
                "```yaml", (project / "AGENTS.md").read_text(encoding="utf-8")
            )

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
