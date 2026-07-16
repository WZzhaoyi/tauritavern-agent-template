import contextlib
import io
import json
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import yaml

from scripts.generate import AgentGenerator


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_ROOT = REPO_ROOT / "examples" / "hongloumeng"


class HongloumengExampleTest(unittest.TestCase):
    def load_regions(self):
        source = EXAMPLE_ROOT / "interaction" / "regions.yaml"
        return yaml.safe_load(source.read_text(encoding="utf-8"))["regions"]

    def test_map_regions_characters_and_worldbook_match(self):
        regions = self.load_regions()
        region_ids = {region["id"] for region in regions}
        self.assertEqual(4, len(region_ids))

        svg_root = ET.parse(EXAMPLE_ROOT / "interaction" / "map.svg").getroot()
        map_ids = {
            node.attrib["data-region-id"]
            for node in svg_root.iter()
            if "data-region-id" in node.attrib
        }
        self.assertEqual(region_ids, map_ids)

        worldbook = json.loads(
            (EXAMPLE_ROOT / "lorebooks" / "hongloumeng-minimal.worldbook.json")
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
                    EXAMPLE_ROOT
                    / "literature"
                    / "characters"
                    / f"{character['label']}_stages.yaml"
                )
                self.assertTrue(stage_file.exists(), stage_file)

        self.assertEqual({"贾宝玉", "林黛玉", "薛宝钗", "贾探春"}, character_labels)

    def test_example_builds_real_agent_artifacts(self):
        with tempfile.TemporaryDirectory(prefix="hongloumeng-example-") as tmp:
            project = Path(tmp)
            shutil.copy2(EXAMPLE_ROOT / "AGENTS.md", project / "AGENTS.md")
            for directory in ("interaction", "literature"):
                shutil.copytree(EXAMPLE_ROOT / directory, project / directory)
            for directory in ("skills", "extensions", "theme"):
                shutil.copytree(REPO_ROOT / directory, project / directory)
            shutil.copy2(REPO_ROOT / "LICENSE", project / "LICENSE")

            with contextlib.redirect_stdout(io.StringIO()):
                AgentGenerator(str(project)).run()

            output = project / "output" / "agent"
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

            archive = output / "skills" / "interaction-system.ttskill"
            with zipfile.ZipFile(archive) as package:
                self.assertEqual(
                    (EXAMPLE_ROOT / "interaction" / "map.svg").read_bytes(),
                    package.read("assets/map.svg"),
                )
                actions = yaml.safe_load(package.read("assets/actions.yaml"))
                self.assertEqual(
                    {"travel", "visit", "talk", "observe", "continue"},
                    {action["id"] for action in actions["actions"]},
                )
                runtime = yaml.safe_load(package.read("references/runtime.yaml"))
                self.assertEqual(
                    "persist/interaction-state.yaml", runtime["state_file"]
                )


if __name__ == "__main__":
    unittest.main()
