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

        self.assertEqual({"projects/", ".github/workflows/"}, ignored)
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

    def test_template_uses_conventional_project_layout(self):
        with tempfile.TemporaryDirectory(prefix="tauritavern-template-") as tmp:
            project = Path(tmp)
            shutil.copy2(
                REPO_ROOT / "tauritavern.template.yaml",
                project / "tauritavern.yaml",
            )
            generator = AgentGenerator(str(project), str(REPO_ROOT))
            config = ConfigLoader.load(project)

            self.assertNotIn("paths", config)
            self.assertFalse(config["interaction"]["enabled"])
            self.assertEqual(
                project / "literature/characters", generator.characters_dir
            )
            self.assertEqual(
                project / "literature/scenarios", generator.scenarios_dir
            )
            self.assertEqual(project / "output", generator.output_root)
            self.assertEqual(
                REPO_ROOT / "extensions/interaction-runtime",
                generator._source_path("extensions/interaction-runtime"),
            )

        for directory in ("literature", "interaction", "output"):
            self.assertFalse((REPO_ROOT / directory).exists(), directory)

        runtime = (
            REPO_ROOT / "extensions" / "interaction-runtime" / "index.js"
        ).read_text(encoding="utf-8")
        self.assertNotIn("hongloumeng", runtime.lower())
        self.assertNotIn("红楼梦", runtime)

    def test_neutral_template_does_not_assume_perspective_or_state(self):
        with tempfile.TemporaryDirectory(prefix="tauritavern-neutral-") as tmp:
            project = Path(tmp)
            shutil.copy2(
                REPO_ROOT / "tauritavern.template.yaml",
                project / "tauritavern.yaml",
            )
            generator = AgentGenerator(str(project), str(REPO_ROOT))
            config = ConfigLoader.load(project)

            self.assertEqual([], config["dimensions"])
            self.assertNotIn("第三人称", config["narrator"]["persona"])
            self.assertNotIn("叙事者", config["narrator"]["persona"])

            generator.run()
            output = project / "output" / "agent"
            self.assertEqual([], list((output / "skills").glob("*.ttskill")))
            profile = json.loads(
                (output / "my-card-writer.agent-profile.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(8, profile["tools"]["maxRounds"])
            self.assertEqual(20, profile["tools"]["maxCallsPerRun"])

    def test_interaction_can_run_without_character_dimensions(self):
        with tempfile.TemporaryDirectory(prefix="tauritavern-stateless-ui-") as tmp:
            project = Path(tmp)
            config = (REPO_ROOT / "tauritavern.template.yaml").read_text(
                encoding="utf-8"
            ).replace("enabled: false", "enabled: true", 1)
            (project / "tauritavern.yaml").write_text(config, encoding="utf-8")
            interaction = project / "interaction"
            interaction.mkdir()
            (interaction / "actions.json").write_text(
                '{"actions":[{"id":"continue","label":"继续"}]}',
                encoding="utf-8",
            )
            (interaction / "regions.json").write_text(
                '{"regions":[{"id":"start","label":"起点"}]}',
                encoding="utf-8",
            )

            AgentGenerator(str(project), str(REPO_ROOT)).run()
            output = project / "output" / "agent"
            archives = sorted(path.name for path in (output / "skills").glob("*.ttskill"))
            self.assertEqual(
                ["my-card-writer-interaction-system.ttskill"], archives
            )
            with zipfile.ZipFile(output / "skills" / archives[0]) as package:
                runtime = json.loads(package.read("references/runtime.json"))
                self.assertFalse(runtime["state"]["enabled"])
                self.assertIsNone(runtime["state"]["skill_name"])

            card = json.loads(
                (output / "my-card-writer.character-card.json").read_text(
                    encoding="utf-8"
                )
            )
            marker = card["data"]["extensions"]["tauritavern_interaction"]
            self.assertIsNone(marker["stateSkillName"])
            self.assertIsNone(marker["characterStateFile"])

    def test_stateless_non_agent_build_omits_state_worldbook(self):
        with tempfile.TemporaryDirectory(prefix="tauritavern-stateless-legacy-") as tmp:
            project = Path(tmp)
            config = (REPO_ROOT / "tauritavern.template.yaml").read_text(
                encoding="utf-8"
            ).replace('target: "agent"', 'target: "non_agent"', 1)
            (project / "tauritavern.yaml").write_text(config, encoding="utf-8")

            AgentGenerator(str(project), str(REPO_ROOT)).run()
            output = project / "output" / "non-agent"
            self.assertFalse(
                (output / "my-card-writer.state-worldbook.json").exists()
            )
            card = json.loads(
                (output / "my-card-writer.character-card.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertNotIn(
                "状态更新：非 Agent",
                card["data"]["post_history_instructions"],
            )


if __name__ == "__main__":
    unittest.main()
