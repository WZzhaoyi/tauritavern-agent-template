import contextlib
import io
import json
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from scripts.generate import AgentGenerator


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = REPO_ROOT / "projects" / "hongloumeng"


class HongloumengProjectTest(unittest.TestCase):
    def load_regions(self):
        source = PROJECT_ROOT / "interaction" / "regions.json"
        return json.loads(source.read_text(encoding="utf-8"))["regions"]

    def test_map_regions_characters_and_worldbook_match(self):
        regions = self.load_regions()
        region_ids = {region["id"] for region in regions}
        self.assertEqual(4, len(region_ids))

        svg_root = ET.parse(PROJECT_ROOT / "interaction" / "map.svg").getroot()
        map_ids = {
            node.attrib["data-region-id"]
            for node in svg_root.iter()
            if "data-region-id" in node.attrib
        }
        self.assertEqual(region_ids, map_ids)

        worldbook = json.loads(
            (PROJECT_ROOT / "lorebooks" / "hongloumeng-minimal.worldbook.json")
            .read_text(encoding="utf-8")
        )
        entries = list(worldbook["entries"].values())
        keys = {key for entry in entries for key in entry["key"]}

        character_labels = set()
        for region in regions:
            self.assertIn(region["label"], keys)
            for character in region.get("characters", []):
                character_labels.add(character["label"])
                self.assertIn(character["label"], keys)
                stage_file = (
                    PROJECT_ROOT
                    / "literature"
                    / "characters"
                    / f"{character['label']}_stages.json"
                )
                self.assertTrue(stage_file.exists(), stage_file)

        self.assertEqual({"贾宝玉", "林黛玉", "薛宝钗", "贾探春"}, character_labels)

    def test_project_builds_real_agent_artifacts(self):
        with tempfile.TemporaryDirectory(prefix="hongloumeng-project-") as tmp:
            project = Path(tmp)
            shutil.copy2(PROJECT_ROOT / "AGENTS.md", project / "AGENTS.md")
            shutil.copy2(
                PROJECT_ROOT / "tauritavern.yaml", project / "tauritavern.yaml"
            )
            for directory in ("interaction", "literature", "lorebooks"):
                shutil.copytree(PROJECT_ROOT / directory, project / directory)

            self.assertNotIn(
                "```yaml", (project / "AGENTS.md").read_text(encoding="utf-8")
            )

            build_log = io.StringIO()
            with contextlib.redirect_stdout(build_log):
                AgentGenerator(str(project), str(REPO_ROOT)).run()

            output = project / "output" / "agent"
            self.assertIn(f"产物目录：{output}/", build_log.getvalue())
            card = json.loads(
                (output / "hongloumeng-garden.character-card.json")
                .read_text(encoding="utf-8")
            )
            profile = json.loads(
                (output / "hongloumeng-garden.agent-profile.json")
                .read_text(encoding="utf-8")
            )

            self.assertEqual(
                "hongloumeng-garden",
                card["data"]["extensions"]["tauritavern_interaction"]["projectId"],
            )
            self.assertIn("诗社", card["data"]["first_mes"])
            self.assertIn("<agent_state_init>", card["data"]["first_mes"])
            self.assertIn("interaction-system", card["data"]["post_history_instructions"])
            self.assertIsNone(profile["instructions"]["agentSystemPrompt"])
            self.assertEqual(["*"], profile["skills"]["visible"])

            extension = output / "extensions" / "hongloumeng-garden-interaction"
            self.assertTrue((extension / "manifest.json").exists())
            self.assertTrue((extension / "LICENSE").exists())
            self.assertIn(
                '"projectId": "hongloumeng-garden"',
                (extension / "package-config.js").read_text(encoding="utf-8"),
            )
            self.assertIn(
                '"projectName": "红楼梦·大观园"',
                (extension / "package-config.js").read_text(encoding="utf-8"),
            )
            extension_config = (extension / "package-config.js").read_text(
                encoding="utf-8"
            )
            self.assertIn('"stateSkillName": "state-system"', extension_config)
            self.assertIn(
                '"characterStateFile": "persist/character_states.json"',
                extension_config,
            )
            self.assertIn('"narrativeFile": "output/main.md"', extension_config)
            extension_code = (extension / "index.js").read_text(encoding="utf-8")
            self.assertIn("JSON.parse", extension_code)
            self.assertNotIn("libs?.yaml", extension_code)
            self.assertNotIn("/send", extension_code)
            self.assertIn("quiet_prompt: runtime.lastActionRecord", extension_code)
            self.assertIn("quietToLoud: true", extension_code)
            self.assertIn("presentation: 'background'", extension_code)
            self.assertIn("<tt_interaction_input", extension_code)
            self.assertIn("runtime.runCommitted", extension_code)
            self.assertIn("请更换 API", extension_code)
            self.assertIn("model\\.tool_call_required", extension_code)
            self.assertIn("readWorkspaceFile", extension_code)
            self.assertIn("agent.listRuns", extension_code)
            self.assertIn("renderNarrative", extension_code)
            self.assertIn("renderBriefing", extension_code)
            self.assertIn("waifuMode", extension_code)
            extension_css = (extension / "style.css").read_text(encoding="utf-8")
            self.assertIn("grid-template-columns: minmax(0, 1fr)", extension_css)
            self.assertIn("data-open", extension_css)
            self.assertIn("data-vn-mode", extension_css)
            self.assertIn("tt-interaction-progress", extension_css)
            self.assertLess(
                extension_code.index("store.listKeys"),
                extension_code.index("store.getJson"),
            )

            archive = output / "skills" / "interaction-system.ttskill"
            with zipfile.ZipFile(archive) as package:
                interaction_skill = package.read("SKILL.md").decode("utf-8")
                self.assertIn("workspace.list_files", interaction_skill)
                self.assertIn("正常首轮", interaction_skill)
                self.assertIn("<tt_interaction_input", interaction_skill)
                self.assertIn("有界快速路径", interaction_skill)
                self.assertIn("不得重复列目录", interaction_skill)
                self.assertIn("extensions.briefing", interaction_skill)
                self.assertIn("workspace.commit", interaction_skill)
                self.assertEqual(
                    (PROJECT_ROOT / "interaction" / "map.svg").read_bytes(),
                    package.read("assets/map.svg"),
                )
                actions = json.loads(package.read("assets/actions.json"))
                self.assertEqual(
                    {"travel", "visit", "talk", "observe", "continue"},
                    {action["id"] for action in actions["actions"]},
                )
                runtime = json.loads(package.read("references/runtime.json"))
                self.assertEqual(
                    "persist/interaction-state.json", runtime["state_file"]
                )

            state_archive = output / "skills" / "state-system.ttskill"
            with zipfile.ZipFile(state_archive) as package:
                state_skill = package.read("SKILL.md").decode("utf-8")
                self.assertIn("workspace.list_files", state_skill)
                self.assertIn("workspace.write_file", state_skill)
                self.assertIn("Agent 回合预算", state_skill)
                self.assertIn("不读取任何角色阶段文件", state_skill)
                self.assertIn("不重复读取", state_skill)
                dimensions = json.loads(package.read("references/dimensions.json"))
                policy = json.loads(package.read("references/update-policy.json"))
                self.assertEqual("closeness", dimensions["dimensions"][0]["id"])
                self.assertEqual(
                    "persist/character_states.json", policy["persist_file"]
                )

            generated_lorebook = (
                output / "lorebooks" / "hongloumeng-minimal.worldbook.json"
            )
            self.assertEqual(
                (PROJECT_ROOT / "lorebooks" / "hongloumeng-minimal.worldbook.json")
                .read_bytes(),
                generated_lorebook.read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
