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
            build_output = build_log.getvalue()
            self.assertIn(f"产物目录：{output}/", build_output)
            self.assertIn("把导入目标设为刚导入的角色卡", build_output)
            self.assertIn("不要导入到全局、预设或 Profile 作用域", build_output)
            self.assertIn("extensions/interaction-runtime/", build_output)
            self.assertNotIn("[生成] 暂停式交互扩展", build_output)
            self.assertFalse((output / "extensions").exists())
            card = json.loads(
                (output / "hongloumeng-garden.character-card.json")
                .read_text(encoding="utf-8")
            )
            profile = json.loads(
                (output / "hongloumeng-garden.agent-profile.json")
                .read_text(encoding="utf-8")
            )

            interaction_marker = card["data"]["extensions"]["tauritavern_interaction"]
            skill_binding = card["data"]["extensions"][
                "tauritavern_agent_template"
            ]
            self.assertEqual("character", skill_binding["skillInstallScope"])
            self.assertEqual(
                {
                    "hongloumeng-garden-interaction-system",
                    "hongloumeng-garden-state-system",
                },
                set(skill_binding["requiredSkills"]),
            )
            self.assertIn("目标作用域设为本角色卡", card["data"]["creator_notes"])
            self.assertIn("不要安装到全局", card["data"]["creator_notes"])
            self.assertEqual("hongloumeng-garden", interaction_marker["projectId"])
            self.assertEqual(
                "hongloumeng-garden-interaction-system",
                interaction_marker["skillName"],
            )
            self.assertEqual(
                "hongloumeng-garden-state-system",
                interaction_marker["stateSkillName"],
            )
            self.assertIn("诗社", card["data"]["first_mes"])
            self.assertIn("<details>", card["data"]["first_mes"])
            self.assertIn("<agent_state_init>", card["data"]["first_mes"])
            self.assertIn(
                "hongloumeng-garden-interaction-system",
                card["data"]["post_history_instructions"],
            )
            self.assertIn(
                "不先 list/search Skill",
                card["data"]["post_history_instructions"],
            )
            self.assertIn(
                "使用 skill.read 读取",
                card["data"]["post_history_instructions"],
            )
            self.assertIn(
                "若该精确安装名不可见",
                card["data"]["post_history_instructions"],
            )
            self.assertNotIn("角色作用域", card["data"]["post_history_instructions"])
            self.assertNotIn(
                "全局、预设或 Profile 作用域",
                card["data"]["post_history_instructions"],
            )
            self.assertIn(
                "不是 Skill 白名单",
                card["data"]["post_history_instructions"],
            )
            self.assertIn(
                "其它由当前 run 解析且经 Profile 过滤后可见的 Skills 可按需正常使用",
                card["data"]["post_history_instructions"],
            )
            self.assertIsNone(profile["instructions"]["agentSystemPrompt"])
            self.assertEqual(["*"], profile["skills"]["visible"])
            self.assertEqual([], profile["skills"]["deny"])

            archive = (
                output
                / "skills"
                / "hongloumeng-garden-interaction-system.ttskill"
            )
            with zipfile.ZipFile(archive) as package:
                interaction_skill = package.read("SKILL.md").decode("utf-8")
                self.assertIn(
                    "name: hongloumeng-garden-interaction-system", interaction_skill
                )
                self.assertIn("仅适用于《红楼梦·大观园》", interaction_skill)
                self.assertNotIn("角色作用域", interaction_skill)
                self.assertIn("不要先列 workspace 目录", interaction_skill)
                self.assertIn("正常首轮", interaction_skill)
                self.assertIn("<tt_interaction_input", interaction_skill)
                self.assertIn("有界快速路径", interaction_skill)
                self.assertIn("不重试读取", interaction_skill)
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
                self.assertEqual(
                    "hongloumeng-garden-state-system",
                    runtime["state"]["skill_name"],
                )

            state_archive = output / "skills" / "hongloumeng-garden-state-system.ttskill"
            with zipfile.ZipFile(state_archive) as package:
                state_skill = package.read("SKILL.md").decode("utf-8")
                self.assertIn("name: hongloumeng-garden-state-system", state_skill)
                self.assertNotIn("角色作用域", state_skill)
                self.assertIn("不要先列目录", state_skill)
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
