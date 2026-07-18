#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TauriTavern Agent 生成器
版本: 2.7.0

按 build.target 生成互斥的运行目标产物：
  - agent     → Agent Profile + SKILLS + Agent 角色卡 + 主题
  - non_agent → legacy 角色卡 + 可选状态世界书
"""

import html
import json
import re
import shutil
import sys
import tempfile
import yaml
import zipfile
from pathlib import Path
from typing import List, Optional


class ConfigLoader:
    """读取独立项目配置。"""

    CONFIG_FILENAME = "tauritavern.yaml"
    SUPPORTED_SCHEMA_VERSION = 1

    @classmethod
    def load(cls, project_root: Path) -> dict:
        config_file = project_root / cls.CONFIG_FILENAME
        if not config_file.exists():
            raise FileNotFoundError(f"{cls.CONFIG_FILENAME} not found")

        config = cls._load_yaml_file(config_file)
        schema_version = config.get("schema_version")
        if (
            isinstance(schema_version, bool)
            or schema_version != cls.SUPPORTED_SCHEMA_VERSION
        ):
            raise ValueError(
                f"{cls.CONFIG_FILENAME} schema_version must be "
                f"{cls.SUPPORTED_SCHEMA_VERSION}"
            )
        return config

    @staticmethod
    def _load_yaml_file(path: Path) -> dict:
        try:
            config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"YAML parse error in {path.name}: {e}")
        if not isinstance(config, dict):
            raise ValueError(f"{path.name} must contain a YAML mapping")
        return config


class AgentGenerator:
    STATE_SKILL_ID = "state-system"
    INTERACTION_SKILL_ID = "interaction-system"

    def __init__(self, project_root: str, template_root: Optional[str] = None):
        self.root = Path(project_root)
        self.template_root = Path(template_root) if template_root else self.root
        self.cfg = ConfigLoader.load(self.root)
        self.framework_version = self._validate_framework_version(
            self.cfg.get("framework"), "project"
        )
        self._check_template_framework_version()

        self.characters_dir = self.root / "literature/characters"
        self.scenarios_dir = self.root / "literature/scenarios"
        self.interaction_dir = self.root / "interaction"
        self.lorebooks_dir = self.root / "lorebooks"
        self.output_root = self.root / "output"
        self.build_target = self._validate_build_target(self.cfg.get("build", {}))
        target_dir = "agent" if self.build_target == "agent" else "non-agent"
        self.output_dir = self.output_root / target_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        project = self.cfg.get("project", {})
        self.pname = project.get("name", "作品")
        self.project_id = self._validate_project_id(project.get("id"))
        self.dimensions = self._validate_dimensions(self.cfg.get("dimensions", []))
        self.state_cfg = self._validate_state_config(self.cfg.get("state_system", {}))
        self.interaction_cfg = self._validate_interaction_config(
            self.cfg.get("interaction", {})
        )

    def _source_path(self, relative_path: str) -> Path:
        """项目可覆盖模板资源；具体项目缺省时回退到模板仓库。"""
        project_path = self.root / relative_path
        if project_path.exists() or self.template_root == self.root:
            return project_path
        return self.template_root / relative_path

    @staticmethod
    def _validate_framework_version(value: object, owner: str) -> str:
        if not isinstance(value, dict):
            raise ValueError(f"{owner} framework must be a mapping")
        version = value.get("version")
        if not isinstance(version, str) or not re.fullmatch(
            r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", version
        ):
            raise ValueError(
                f"{owner} framework.version must use MAJOR.MINOR.PATCH"
            )
        return version

    def _check_template_framework_version(self) -> None:
        template_config = self.template_root / "tauritavern.template.yaml"
        if not template_config.exists():
            return
        template_cfg = ConfigLoader._load_yaml_file(template_config)
        template_version = self._validate_framework_version(
            template_cfg.get("framework"), "template"
        )
        if self.framework_version != template_version:
            raise ValueError(
                "project framework.version "
                f"{self.framework_version!r} does not match template version "
                f"{template_version!r}; review migrations before updating the project"
            )

    @staticmethod
    def _validate_build_target(value: object) -> str:
        if not isinstance(value, dict):
            raise ValueError("build must be a mapping")
        target = value.get("target", "agent")
        if target not in {"agent", "non_agent"}:
            raise ValueError("build.target must be 'agent' or 'non_agent'")
        return target

    @staticmethod
    def _validate_project_id(value: object) -> str:
        """Profile ID 与导出文件名使用稳定的 ASCII 标识。"""
        if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9_-]{1,128}", value):
            raise ValueError(
                "project.id must use 1-128 lowercase ASCII letters, digits, '-' or '_'"
            )
        return value

    @staticmethod
    def _validate_dimensions(value: object) -> List[dict]:
        if not isinstance(value, list):
            raise ValueError("dimensions must be a list")

        seen = set()
        dimensions = []
        for raw in value:
            if not isinstance(raw, dict):
                raise ValueError("each dimension must be a mapping")
            dim = dict(raw)
            dim_id = dim.get("id")
            if not isinstance(dim_id, str) or not re.fullmatch(r"[a-z0-9_-]+", dim_id):
                raise ValueError(f"Invalid dimension id: {dim_id!r}")
            if dim_id in seen:
                raise ValueError(f"Duplicate dimension id: {dim_id}")
            seen.add(dim_id)
            if not isinstance(dim.get("name"), str) or not dim["name"].strip():
                raise ValueError(f"dimension {dim_id!r} name must be non-empty text")

            ranges = dim.get("ranges")
            stages = dim.get("stages")
            if not isinstance(ranges, list) or len(ranges) < 2:
                raise ValueError(f"dimension {dim_id!r} ranges must contain at least 2 values")
            if any(isinstance(n, bool) or not isinstance(n, int) for n in ranges):
                raise ValueError(f"dimension {dim_id!r} ranges must be integers")
            if any(left >= right for left, right in zip(ranges, ranges[1:])):
                raise ValueError(f"dimension {dim_id!r} ranges must be strictly increasing")
            if not isinstance(stages, list) or len(stages) != len(ranges) - 1:
                raise ValueError(
                    f"dimension {dim_id!r} stages count must equal ranges count minus one"
                )
            if any(not isinstance(stage, str) or not stage.strip() for stage in stages):
                raise ValueError(f"dimension {dim_id!r} stages must be non-empty text")

            initial = dim.get("initial", ranges[0])
            if isinstance(initial, bool) or not isinstance(initial, int):
                raise ValueError(f"dimension {dim_id!r} initial must be an integer")
            if not ranges[0] <= initial <= ranges[-1]:
                raise ValueError(f"dimension {dim_id!r} initial must be inside its range")
            dim["initial"] = initial

            legacy_key = dim.get("legacy_key", dim.get("name"))
            if (
                not isinstance(legacy_key, str)
                or not legacy_key.strip()
                or "." in legacy_key
            ):
                raise ValueError(
                    f"dimension {dim_id!r} legacy_key must be non-empty text without '.'"
                )
            dim["legacy_key"] = legacy_key.strip()

            update_rules = dim.get("update_rules", "")
            if not isinstance(update_rules, str):
                raise ValueError(f"dimension {dim_id!r} update_rules must be a string")
            dimensions.append(dim)

        return dimensions

    @staticmethod
    def _validate_state_config(value: object) -> dict:
        if not isinstance(value, dict):
            raise ValueError("state_system must be a mapping")

        cfg = {
            "persist_file": value.get("persist_file", "persist/character_states.json"),
            "max_characters_per_turn": value.get("max_characters_per_turn", 2),
            "max_delta_per_dimension": value.get("max_delta_per_dimension", 5),
            "custom_rules": value.get("custom_rules", ""),
            "non_agent": value.get("non_agent", {}),
        }

        persist_file = cfg["persist_file"]
        if (
            not isinstance(persist_file, str)
            or not persist_file.startswith("persist/")
            or ".." in Path(persist_file).parts
            or Path(persist_file).is_absolute()
        ):
            raise ValueError("state_system.persist_file must be a safe path under persist/")
        for key in ("max_characters_per_turn", "max_delta_per_dimension"):
            if isinstance(cfg[key], bool) or not isinstance(cfg[key], int) or cfg[key] < 1:
                raise ValueError(f"state_system.{key} must be a positive integer")
        if not isinstance(cfg["custom_rules"], str):
            raise ValueError("state_system.custom_rules must be a string")

        non_agent = cfg["non_agent"]
        if not isinstance(non_agent, dict):
            raise ValueError("state_system.non_agent must be a mapping")
        emit_legacy = non_agent.get("emit_legacy_updates", True)
        if not isinstance(emit_legacy, bool):
            raise ValueError("state_system.non_agent.emit_legacy_updates must be boolean")
        cfg["non_agent"] = {"emit_legacy_updates": emit_legacy}
        return cfg

    @staticmethod
    def _validate_interaction_config(value: object) -> dict:
        """交互层只保留一个开关，其余使用稳定约定。"""
        if not isinstance(value, dict):
            raise ValueError("interaction must be a mapping")
        enabled = value.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ValueError("interaction.enabled must be boolean")
        return {
            "enabled": enabled,
            "skill_id": AgentGenerator.INTERACTION_SKILL_ID,
            "state_file": "persist/interaction-state.json",
        }

    def _packaged_skill_name(self, skill_id: str) -> str:
        """安装名包含项目 ID，避免多个套件产生同名安装项。"""
        return f"{self.project_id}-{skill_id}"

    # ── SKILLS 验证 ──────────────────────────────────────────

    def validate_skills(self) -> List[dict]:
        skills_cfg = self.cfg.get("skills", [])
        if not isinstance(skills_cfg, list):
            raise ValueError("skills must be a list")
        results = []
        seen_skill_ids = set()
        for s in skills_cfg:
            if not isinstance(s, dict):
                raise ValueError("each skill must be a mapping")
            sid, src = s["id"], s["source_dir"]
            if sid == self.interaction_cfg["skill_id"] and not self.interaction_cfg["enabled"]:
                continue
            if sid == self.STATE_SKILL_ID and not self.dimensions:
                continue
            if not isinstance(sid, str) or not re.fullmatch(r"[a-z0-9_-]+", sid):
                raise ValueError(f"Invalid Skill id: {sid!r}")
            if sid in seen_skill_ids:
                raise ValueError(f"Duplicate Skill id: {sid}")
            seen_skill_ids.add(sid)
            skill_dir = self._source_path(src)
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                raise FileNotFoundError(f"Missing {skill_md}")
            try:
                fm = self._read_frontmatter(skill_md)
            except Exception as e:
                raise ValueError(f"Invalid SKILL.md frontmatter in {src}: {e}")
            if not fm.get("name") or not fm.get("description"):
                raise ValueError(f"SKILL.md in {src} missing 'name' or 'description' in frontmatter")
            if fm["name"] != sid:
                raise ValueError(
                    f"Skill id {sid!r} must match SKILL.md frontmatter name {fm['name']!r}"
                )
            results.append(
                {
                    "id": sid,
                    "name": self._packaged_skill_name(sid),
                    "dir": skill_dir,
                    "frontmatter": fm,
                }
            )

        if self.dimensions and not any(
            skill["id"] == self.STATE_SKILL_ID for skill in results
        ):
            raise ValueError("non-empty dimensions require state-system in the skills list")

        if self.interaction_cfg["enabled"] and not any(
            skill["id"] == self.interaction_cfg["skill_id"] for skill in results
        ):
            raise ValueError(
                "interaction.enabled requires interaction-system in the skills list"
            )
        return results

    @staticmethod
    def _read_frontmatter(path: Path) -> dict:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            raise ValueError("Missing YAML frontmatter")
        end = text.index("---", 3)
        return yaml.safe_load(text[3:end]) or {}

    # ── SKILLS 打包 ──────────────────────────────────────────

    def bundle_ttskills(self, validated: List[dict]) -> List[str]:
        """每个归档只包含一个 Skill，且 SKILL.md 位于归档根目录。"""
        skills_output = self.output_dir / "skills"
        skills_output.mkdir(parents=True, exist_ok=True)
        bundled = []
        skill_name_map = {skill["id"]: skill["name"] for skill in validated}
        expected_filenames = {f"{skill['name']}.ttskill" for skill in validated}
        for existing in skills_output.glob("*.ttskill"):
            if existing.name not in expected_filenames:
                existing.unlink()

        for skill in validated:
            filename = f"{skill['name']}.ttskill"
            filepath = skills_output / filename
            legacy_path = skills_output / f"{skill['id']}.ttskill"
            if legacy_path != filepath and legacy_path.exists():
                legacy_path.unlink()
            with tempfile.TemporaryDirectory(prefix="tauritavern-skill-") as tmp:
                staged_dir = Path(tmp) / skill["name"]
                shutil.copytree(skill["dir"], staged_dir)
                self._scope_staged_skill(
                    staged_dir / "SKILL.md", skill["name"], skill_name_map
                )
                self._inject_generated_references(skill["id"], staged_dir)

                with zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as zf:
                    for fpath in sorted(staged_dir.rglob("*")):
                        if fpath.is_file() and not fpath.name.startswith("."):
                            zf.write(fpath, fpath.relative_to(staged_dir))

            print(f"  [OK] skills/{filename}")
            bundled.append(str(filepath))

        return bundled

    def _scope_staged_skill(
        self, skill_md: Path, packaged_name: str, skill_name_map: dict
    ) -> None:
        """只改打包副本：安装名、触发描述和 Skill 交叉引用均项目化。"""
        text = skill_md.read_text(encoding="utf-8")
        for source_name in sorted(skill_name_map, key=len, reverse=True):
            target_name = skill_name_map[source_name]
            text = re.sub(
                rf"(?<![a-z0-9_-]){re.escape(source_name)}(?![a-z0-9_-])",
                target_name,
                text,
            )

        match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", text, re.DOTALL)
        if not match:
            raise ValueError(f"Missing YAML frontmatter in {skill_md}")
        frontmatter = yaml.safe_load(match.group(1)) or {}
        frontmatter["name"] = packaged_name
        description = str(frontmatter.get("description", "")).rstrip("。 ")
        frontmatter["description"] = (
            f"{description}。仅适用于《{self.pname}》（{self.project_id}）角色卡套件。"
        )
        rendered = yaml.safe_dump(
            frontmatter,
            allow_unicode=True,
            sort_keys=False,
            width=1000,
        ).strip()
        skill_md.write_text(
            f"---\n{rendered}\n---\n\n{text[match.end():].lstrip()}",
            encoding="utf-8",
        )

    def _inject_generated_references(self, skill_id: str, staged_dir: Path) -> None:
        """仅将 Agent 状态工作流所需的资料写入打包副本。"""
        if skill_id == self.interaction_cfg["skill_id"]:
            self._inject_interaction_assets(staged_dir)
            return
        if skill_id != self.STATE_SKILL_ID:
            return

        references_dir = staged_dir / "references"
        references_dir.mkdir(parents=True, exist_ok=True)
        (references_dir / "dimensions.json").write_text(
            json.dumps({"dimensions": self.dimensions}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        update_policy = {
            "version": 1,
            "persist_file": self.state_cfg["persist_file"],
            "constraints": {
                "max_characters_per_turn": self.state_cfg["max_characters_per_turn"],
                "max_delta_per_dimension": self.state_cfg["max_delta_per_dimension"],
                "require_current_turn_evidence": True,
                "clamp_to_ranges": True,
            },
            "custom_rules": self.state_cfg["custom_rules"],
        }
        (references_dir / "update-policy.json").write_text(
            json.dumps(update_policy, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        stages_dir = references_dir / "character-stages"
        stages_dir.mkdir(exist_ok=True)
        if self.characters_dir.exists():
            for source in sorted(self.characters_dir.glob("*_stages.json")):
                self._validate_stage_file(source)
                shutil.copy2(source, stages_dir / source.name)

    def _inject_interaction_assets(self, staged_dir: Path) -> None:
        """把作者维护的声明式交互内容写入 Skill 打包副本。"""
        assets_dir = staged_dir / "assets"
        references_dir = staged_dir / "references"
        assets_dir.mkdir(parents=True, exist_ok=True)
        references_dir.mkdir(parents=True, exist_ok=True)

        self._validate_interaction_sources()
        for filename in ("actions.json", "regions.json", "map.svg"):
            source = self.interaction_dir / filename
            if source.exists():
                shutil.copy2(source, assets_dir / filename)

        runtime = {
            "version": 1,
            "project_id": self.project_id,
            "state_file": self.interaction_cfg["state_file"],
            "state": {
                "enabled": bool(self.dimensions),
                "skill_name": (
                    self._packaged_skill_name(self.STATE_SKILL_ID)
                    if self.dimensions
                    else None
                ),
                "persist_file": self.state_cfg["persist_file"] if self.dimensions else None,
            },
            "extension_fields": "allowed",
        }
        (references_dir / "runtime.json").write_text(
            json.dumps(runtime, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _validate_interaction_sources(self) -> None:
        if not self.interaction_dir.exists():
            raise FileNotFoundError(
                "interaction.enabled requires the interaction/ source directory"
            )

        for filename, root_key in (
            ("actions.json", "actions"),
            ("regions.json", "regions"),
        ):
            source = self.interaction_dir / filename
            if not source.exists():
                raise FileNotFoundError(f"Missing {source}")
            try:
                data = json.loads(source.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid interaction JSON in {source}: {e}")
            items = data.get(root_key) if isinstance(data, dict) else None
            if not isinstance(items, list):
                raise ValueError(f"{source} must contain a {root_key} list")

            seen = set()
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError(f"Each item in {source} must be a mapping")
                item_id = item.get("id")
                label = item.get("label")
                if not isinstance(item_id, str) or not item_id.strip():
                    raise ValueError(f"Each item in {source} must have a non-empty id")
                if item_id in seen:
                    raise ValueError(f"Duplicate id {item_id!r} in {source}")
                seen.add(item_id)
                if not isinstance(label, str) or not label.strip():
                    raise ValueError(
                        f"Interaction item {item_id!r} in {source} needs a label"
                    )

        map_file = self.interaction_dir / "map.svg"
        if map_file.exists() and "<svg" not in map_file.read_text(encoding="utf-8"):
            raise ValueError(f"{map_file} must be an SVG text file")

    def _validate_stage_file(self, source: Path) -> None:
        try:
            text = source.read_text(encoding="utf-8")
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid stage data in {source}: {e}")

        states = data.get("character_states") if isinstance(data, dict) else None
        if not isinstance(states, list) or not states:
            raise ValueError(f"{source} must contain a character_states list")

        dimension_map = {dim["id"]: dim for dim in self.dimensions}
        seen = set()
        for state in states:
            if not isinstance(state, dict) or state.get("id") not in dimension_map:
                raise ValueError(f"{source} contains an unknown or invalid dimension")
            dim_id = state["id"]
            if dim_id in seen:
                raise ValueError(f"{source} contains duplicate dimension {dim_id!r}")
            seen.add(dim_id)

            stage_ranges = state.get("ranges")
            dim_ranges = dimension_map[dim_id]["ranges"]
            if not isinstance(stage_ranges, list) or len(stage_ranges) != len(dim_ranges) - 1:
                raise ValueError(f"{source} has the wrong stage count for {dim_id!r}")
            for index, stage in enumerate(stage_ranges):
                expected_min = dim_ranges[index] if index == 0 else dim_ranges[index] + 1
                expected_max = dim_ranges[index + 1]
                if (
                    not isinstance(stage, dict)
                    or stage.get("min") != expected_min
                    or stage.get("max") != expected_max
                    or not isinstance(stage.get("content"), str)
                    or not stage["content"].strip()
                ):
                    raise ValueError(
                        f"{source} range {index + 1} for {dim_id!r} must be "
                        f"{expected_min}-{expected_max} with non-empty content"
                    )

    # ── 角色卡 ────────────────────────────────────────────────

    def _load_stage_files(self) -> List[tuple]:
        """读取并验证当前格式的全部角色阶段数据。"""
        results = []
        if not self.characters_dir.exists():
            return results
        for source in sorted(self.characters_dir.glob("*_stages.json")):
            self._validate_stage_file(source)
            text = source.read_text(encoding="utf-8")
            data = json.loads(text)
            suffix = "_stages.json"
            character = source.name[: -len(suffix)]
            results.append((character, source, data))
        return results

    def generate_state_worldbook(self) -> dict:
        """将 _stages 编译为供 legacy 状态运行时读取的可导入世界书。"""
        entries = {}
        for uid, (character, _source, data) in enumerate(self._load_stage_files()):
            stages_content = json.dumps(data, ensure_ascii=False, indent=2)
            content = (
                f'<character name="{html.escape(character, quote=True)}">\n'
                "<character_states>\n"
                f"{stages_content}\n"
                "</character_states>\n"
                "</character>"
            )
            entries[str(uid)] = {
                "uid": uid,
                "key": [character],
                "keysecondary": [],
                "comment": f"状态_{character}",
                "content": content,
                "constant": False,
                "selective": True,
                "selectiveLogic": 0,
                "addMemo": True,
                "order": 100 + uid,
                "position": 0,
                "disable": False,
                "probability": 100,
                "useProbability": True,
                "depth": 4,
                "delay": 0,
                "cooldown": 0,
                "sticky": 0,
                "scanDepth": 2,
                "vectorized": False,
                "ignoreBudget": True,
                "excludeRecursion": False,
                "preventRecursion": False,
            }
        return {"entries": entries}

    def generate_character_card(
        self, validated_skills: Optional[List[dict]] = None
    ) -> dict:
        narrator = self.cfg.get("narrator", {})
        style = self.cfg.get("style_sample", {})
        scenarios = self._load_scenarios()

        first_mes = scenarios[0]["body"] if scenarios else ""
        alternate_greetings = [s["body"] for s in scenarios[1:]] if len(scenarios) > 1 else []

        description = self._build_description(style, narrator.get("description", ""))
        creator = narrator.get("creator", "")
        pversion = self.cfg.get("project", {}).get("version", "1.0.0")
        dim_names = [d["name"] for d in self.dimensions]

        default_prompt = (
            f"执行《{self.pname}》角色卡定义的任务。\n"
            "具体身份、输出形式和视角以本角色卡为准；角色和世界事实以已激活世界书为准。"
        )
        if dim_names:
            default_prompt += f"\n状态维度：{', '.join(dim_names)}。"
        system_prompt = narrator.get("persona", "").strip() or default_prompt
        post_history_parts = [narrator.get("style_instructions", "").strip()]
        if self.build_target == "agent":
            post_history_parts.append(self._build_agent_skill_bridge())
        else:
            post_history_parts.append(self._build_non_agent_state_instructions())
        post_history = "\n\n".join(part for part in post_history_parts if part)

        extensions = {}
        packaged_skill_names = []
        if self.build_target == "agent":
            if validated_skills is None:
                validated_skills = self.validate_skills()
            packaged_skill_names = [skill["name"] for skill in validated_skills]
            if packaged_skill_names:
                extensions["tauritavern_agent_template"] = {
                    "version": 1,
                    "projectId": self.project_id,
                    "skillInstallScope": "character",
                    "requiredSkills": packaged_skill_names,
                }
        if self.build_target == "agent" and self.interaction_cfg["enabled"]:
            extensions["tauritavern_interaction"] = {
                "version": 1,
                "projectId": self.project_id,
                "projectName": self.pname,
                "profileId": self.project_id,
                "skillName": self._packaged_skill_name(
                    self.interaction_cfg["skill_id"]
                ),
                "stateSkillName": (
                    self._packaged_skill_name(self.STATE_SKILL_ID)
                    if self.dimensions
                    else None
                ),
                "stateFile": self.interaction_cfg["state_file"],
                "characterStateFile": (
                    self.state_cfg["persist_file"] if self.dimensions else None
                ),
                "narrativeFile": "output/main.md",
                "cacheNamespace": f"{self.project_id}-interaction",
            }

        creator_notes = ""
        if packaged_skill_names:
            creator_notes = (
                "TauriTavern Agent 导入要求：导入或移动以下 Skills 时，将目标作用域设为本角色卡，"
                "不要安装到全局、预设或 Profile 作用域："
                + "、".join(packaged_skill_names)
                + "。"
            )

        data = {
            "name": narrator.get("name", self.pname),
            "description": description,
            "personality": narrator.get("personality", ""),
            "scenario": "",
            "first_mes": first_mes,
            "alternate_greetings": alternate_greetings,
            "mes_example": "",
            "creator_notes": creator_notes,
            "system_prompt": system_prompt,
            "post_history_instructions": post_history,
            "tags": [],
            "creator": creator,
            "character_version": pversion,
            "extensions": extensions,
        }

        return {"spec": "chara_card_v2", "spec_version": "2.0", "data": data}

    def _build_agent_skill_bridge(self) -> str:
        parts = []
        if self.dimensions:
            state_skill = self._packaged_skill_name(self.STATE_SKILL_ID)
            state_file = self.state_cfg["persist_file"]
            parts.append(
                "【Agent 状态扩展】\n"
                f"每次运行使用 skill.read 读取 `{state_skill}` 的 SKILL.md、"
                "references/update-policy.json 与 references/dimensions.json；"
                "若该精确安装名不可见，明确报告缺失，不得猜测或改用其它名称。"
                f"与已激活世界书及 `{state_file}` 在首个工具阶段并行读取，"
                "不先 list/search Skill 或列目录。"
                "首次运行状态文件 Not found 只表示待初始化，不重试。"
                "按该 Skill 的有界事务更新状态；证据不足时保持不变。"
            )
        if self.interaction_cfg["enabled"]:
            interaction_skill = self._packaged_skill_name(
                self.interaction_cfg["skill_id"]
            )
            state_clause = (
                "并完成角色状态事务，" if self.dimensions else ""
            )
            parts.append(
                "【暂停式交互扩展】\n"
                f"每次运行使用 skill.read 读取 `{interaction_skill}` 的 SKILL.md 与 references/runtime.json；"
                "若该精确安装名不可见，明确报告缺失，不得猜测或改用其它名称。"
                f"把它们和 `{self.interaction_cfg['state_file']}` 合并进首个并行工具阶段；"
                "首次 Not found 只表示待初始化。"
                "把普通用户输入或界面在本次隐式 prompt 中传入的最后一个 <tt_interaction_input> 视为玩家本轮选择；"
                "历史中的旧版 [交互行动] 不得重放，也不得在正文中转录任何控制协议。"
                f"完成叙事，{state_clause}更新 persist/interaction-state.json 与 output/main.md，"
                "然后 workspace.commit、workspace.finish；未完成前不输出过程说明。"
            )
        if parts:
            parts.append(
                "【其它 Skills】\n"
                "以上项目 Skill 必读要求不是 Skill 白名单。"
                "其它由当前 run 解析且经 Profile 过滤后可见的 Skills 可按需正常使用。"
            )
        return "\n\n".join(parts)

    def _build_non_agent_state_instructions(self) -> str:
        if (
            not self.dimensions
            or not self.state_cfg["non_agent"]["emit_legacy_updates"]
        ):
            return ""

        dimension_rules = []
        for dim in self.dimensions:
            rule = dim.get("update_rules", "").strip() or "仅在本轮发生明确变化时调整。"
            dimension_rules.append(
                f"- {dim['name']}（legacy key: {dim['legacy_key']}，范围 "
                f"{dim['ranges'][0]}~{dim['ranges'][-1]}）：{rule}"
            )
        custom_rules = self.state_cfg["custom_rules"].strip() or "无额外规则。"

        return (
            "【状态更新：非 Agent 模式兼容】\n"
            "本角色卡由 build.target=non_agent 生成，仅供 Agent Mode 关闭时使用。\n\n"
            "计算原则：\n"
            "- 只计算当前一轮新发生的事件，不重算历史，不因重复描述再次加减。\n"
            f"- 每轮最多更新 {self.state_cfg['max_characters_per_turn']} 个有实际台词、动作或关系进展的角色；"
            "仅被提及或没有新进展的角色不更新。\n"
            f"- 单角色单维度每轮变化绝对值不得超过 {self.state_cfg['max_delta_per_dimension']}；"
            "新值必须等于旧值加增量，并限制在维度范围内。\n"
            "- 旧值必须来自当前已注入状态或最近一次成功更新；无法确认旧值时不猜测、不更新。\n"
            "- 每项变化必须有当前轮可指出的证据；没有变化时不要输出状态更新块。\n\n"
            "维度规则：\n"
            + "\n".join(dimension_rules)
            + "\n\n用户自定义规则：\n"
            + custom_rules
            + "\n\n输出规则：只输出发生变化的变量，并附在正文末尾。路径使用上面列出的 legacy key：\n"
            "<details>\n"
            "<summary>角色状态更新</summary>\n"
            "_.set(\"角色名.legacy_key\", old_value, new_value); // 当前轮证据 [delta]\n"
            "</details>"
        )

    def _build_description(self, style: dict, base_description: str = "") -> str:
        src_file = style.get("source_file")
        max_len = style.get("max_length", 1500)
        if not src_file:
            return base_description
        fpath = self.root / src_file
        if not fpath.exists():
            return base_description
        text = fpath.read_text(encoding="utf-8")
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        sample = "\n".join(lines)[:max_len]
        sample_description = (
            "以下是本项目的输出风格参考；生成内容时按角色卡任务需要参考其叙述节奏、"
            "句式与用词：\n\n"
            f"---\n\n{sample}\n\n---"
        )
        return f"{sample_description}\n\n{base_description}".strip()

    def _load_scenarios(self) -> List[dict]:
        if not self.scenarios_dir.exists():
            return []
        results = []
        for fpath in sorted(self.scenarios_dir.glob("*.md")):
            text = fpath.read_text(encoding="utf-8")
            body = text
            metadata = {}
            parts = re.split(r"^---\s*$", text, maxsplit=2, flags=re.MULTILINE)
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError as e:
                    raise ValueError(f"Invalid scenario frontmatter in {fpath}: {e}")
                if not isinstance(metadata, dict):
                    raise ValueError(f"Scenario frontmatter in {fpath} must be a mapping")
                body = parts[2].strip()
            init_block = self._build_initial_state_block(metadata.get("variables"), fpath)
            if init_block:
                body = f"{body}\n\n{init_block}".strip()
            if body:
                results.append({"body": body, "file": fpath.name, "metadata": metadata})
        return results

    def _build_initial_state_block(self, variables: object, source: Path) -> str:
        if variables is None:
            return ""
        if not isinstance(variables, dict):
            raise ValueError(f"Scenario variables in {source} must be a mapping")

        dimension_map = {dim["id"]: dim for dim in self.dimensions}
        normalized = {}
        for character, values in variables.items():
            if not isinstance(character, str) or not character.strip():
                raise ValueError(f"Scenario character name in {source} must be non-empty text")
            if not isinstance(values, dict):
                raise ValueError(f"Scenario variables for {character!r} in {source} must be a mapping")
            for dim_id, value in values.items():
                if dim_id not in dimension_map:
                    raise ValueError(f"Unknown dimension {dim_id!r} in {source}")
                if isinstance(value, bool) or not isinstance(value, int):
                    raise ValueError(f"Initial value for {character}.{dim_id} must be an integer")
                dim = dimension_map[dim_id]
                if not dim["ranges"][0] <= value <= dim["ranges"][-1]:
                    raise ValueError(f"Initial value for {character}.{dim_id} is outside its range")
                normalized.setdefault(character, {})[dim_id] = value

        if not normalized:
            return ""

        if self.build_target == "agent":
            payload = json.dumps(
                {"version": 1, "characters": normalized},
                ensure_ascii=False,
                indent=2,
            )
            return (
                "<details>\n"
                "<summary>角色状态初始化</summary>\n"
                f"<agent_state_init>\n{payload}\n</agent_state_init>\n"
                "</details>"
            )

        commands = []
        for character, values in normalized.items():
            for dim_id, value in values.items():
                dim = dimension_map[dim_id]
                path = json.dumps(f"{character}.{dim['legacy_key']}", ensure_ascii=False)
                commands.append(f"_.set({path}, {dim['initial']}, {value});")
        return (
            "<details>\n"
            "<summary>角色状态初始化</summary>\n"
            "<character_states_init>\n"
            + "\n".join(commands)
            + "\n</character_states_init>\n"
            "</details>"
        )

    # ── Agent Profile ─────────────────────────────────────────

    def generate_agent_profile(self) -> dict:
        agent_cfg = self.cfg.get("agent", {})

        tool_mode = agent_cfg.get("tool_mode", "full")
        if tool_mode not in {"full", "focused"}:
            raise ValueError("agent.tool_mode must be 'full' or 'focused'")

        tools = [
            "chat.search",
            "chat.read_messages",
            "worldinfo.read_activated",
            "skill.list",
            "skill.search",
            "skill.read",
            "workspace.list_files",
            "workspace.search_files",
            "workspace.read_file",
            "workspace.write_file",
            "workspace.apply_patch",
            "workspace.commit",
            "workspace.finish",
        ]
        if tool_mode == "focused":
            discovery_tools = {
                "skill.list",
                "skill.search",
                "workspace.list_files",
                "workspace.search_files",
            }
            tools = [tool for tool in tools if tool not in discovery_tools]
        if agent_cfg.get("enable_dice", True):
            tools.append("dice.roll")

        return {
            "schemaVersion": 1,
            "kind": "tauritavern.agentProfile",
            "id": self.project_id,
            "displayName": self.pname,
            "description": self.cfg.get("project", {}).get("description", ""),
            "preset": {
                "mode": "currentPromptSnapshot",
            },
            "model": {
                "mode": "currentPromptSnapshot",
            },
            "run": {
                "presentation": "foreground",
                "modelRetry": {
                    "maxRetries": agent_cfg.get("model_retries", 2),
                    "intervalMs": 1000,
                },
            },
            "instructions": {
                "agentSystemPrompt": None,
            },
            "tools": {
                "allow": tools,
                "deny": [],
                "maxRounds": agent_cfg.get("max_rounds", 12),
                "maxCallsPerRun": agent_cfg.get("max_tool_calls", 30),
            },
            "skills": {
                "visible": ["*"],
                "deny": [],
                "maxReadCharsPerCall": 8000,
                "maxReadCharsPerRun": 40000,
            },
            "workspace": {
                "visibleRoots": ["output", "scratch", "persist", "summaries"],
                "writableRoots": ["output", "scratch", "persist", "summaries"],
            },
            "plan": {
                "mode": "none",
            },
            "output": {
                "artifacts": [
                    {
                        "id": "main",
                        "path": "output/main.md",
                        "kind": "markdown",
                        "target": "messageBody",
                        "required": True,
                        "assemblyOrder": 0,
                    }
                ],
            },
        }

    # ── 主题 CSS ──────────────────────────────────────────────

    def copy_theme(self) -> Optional[str]:
        theme_cfg = self.cfg.get("theme", {})
        src = theme_cfg.get("source_file")
        if not src:
            return None
        src_path = self._source_path(src)
        if not src_path.exists():
            print(f"  [WARN] Theme file not found: {src_path}")
            return None
        dst = self.output_dir / "agent-overrides.css"
        shutil.copy2(src_path, dst)
        print(f"  [OK] agent-overrides.css")
        return str(dst)

    # ── 项目世界书与旧产物清理 ──────────────────────────────────

    def copy_project_lorebooks(self) -> List[str]:
        """原样复制作者维护的传统世界书，方便具体项目与套件一起分发。"""
        if not self.lorebooks_dir.exists():
            return []
        sources = sorted(self.lorebooks_dir.glob("*.json"))
        if not sources:
            return []

        destination = self.output_dir / "lorebooks"
        destination.mkdir(parents=True, exist_ok=True)
        copied = []
        for source in sources:
            try:
                json.loads(source.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid lorebook JSON in {source}: {e}")
            target = destination / source.name
            shutil.copy2(source, target)
            print(f"  [OK] lorebooks/{source.name}")
            copied.append(str(target))
        return copied

    def prune_stale_interaction_outputs(self) -> None:
        """移除已停用的交互 Skill 和旧版项目级扩展产物。"""
        if not self.interaction_cfg["enabled"]:
            skill_archives = (
                self.output_dir / "skills" / "interaction-system.ttskill",
                self.output_dir
                / "skills"
                / f"{self._packaged_skill_name(self.INTERACTION_SKILL_ID)}.ttskill",
            )
            for skill_archive in skill_archives:
                if skill_archive.exists():
                    skill_archive.unlink()

        extensions_root = self.output_dir / "extensions"
        extension_dirs = (
            extensions_root / f"{self.project_id}-interaction",
            extensions_root / "tauritavern-interaction",
        )
        for extension_dir in extension_dirs:
            if extension_dir.exists():
                shutil.rmtree(extension_dir)
        if extensions_root.exists() and not any(extensions_root.iterdir()):
            extensions_root.rmdir()

    # ── 汇总输出 ──────────────────────────────────────────────

    def run(self):
        print(f"\n{'='*60}")
        print(f"TauriTavern 目标构建：{self.pname} [{self.build_target}]")
        print(f"{'='*60}\n")

        validated_skills = None
        if self.build_target == "agent":
            self.prune_stale_interaction_outputs()
            print("[验证] SKILLS ...")
            validated_skills = self.validate_skills()
            for v in validated_skills:
                print(f"  [OK] {v['id']} ({v['dir']})")

            print("\n[打包] SKILLS → .ttskill ...")
            self.bundle_ttskills(validated_skills)

            print("\n[生成] Agent Profile ...")
            profile = self.generate_agent_profile()
            profile_path = self.output_dir / f"{self.project_id}.agent-profile.json"
            profile_path.write_text(
                json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"  [OK] {profile_path.name}")
        else:
            if self.dimensions:
                print("[生成] 非 Agent 状态世界书 ...")
                worldbook = self.generate_state_worldbook()
                worldbook_path = self.output_dir / f"{self.project_id}.state-worldbook.json"
                worldbook_path.write_text(
                    json.dumps(worldbook, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(f"  [OK] {worldbook_path.name}")
            else:
                stale_worldbook = (
                    self.output_dir / f"{self.project_id}.state-worldbook.json"
                )
                if stale_worldbook.exists():
                    stale_worldbook.unlink()

        # 4. 角色卡
        print("\n[生成] 角色卡 ...")
        card = self.generate_character_card(validated_skills)
        card_path = self.output_dir / f"{self.project_id}.character-card.json"
        card_path.write_text(
            json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  [OK] {card_path.name}")

        if self.lorebooks_dir.exists() and any(self.lorebooks_dir.glob("*.json")):
            print("\n[复制] 项目世界书 ...")
            self.copy_project_lorebooks()

        if self.build_target == "agent":
            print("\n[生成] 主题 ...")
            self.copy_theme()

        # 6. 导入说明
        self._print_import_guide(validated_skills)

    def _print_import_guide(self, validated_skills: Optional[List[dict]] = None):
        print(f"\n{'='*60}")
        print("导入 TauriTavern")
        print(f"{'='*60}")
        if self.build_target == "agent":
            steps = [
                f"Characters → Import → {self.project_id}.character-card.json"
            ]
            if validated_skills:
                steps.append(
                    "Agent 系统面板 → SKILLS → 逐个导入 skills/*.ttskill，并把导入目标设为"
                    "刚导入的角色卡；不要导入到全局、预设或 Profile 作用域"
                )
            steps.extend(
                [
                    f"Agent 系统面板 → 配置档案 → 导入 → {self.project_id}.agent-profile.json",
                    "设为 Active Profile，开启 Agent Mode",
                ]
            )
            if self.interaction_cfg["enabled"]:
                steps.append(
                    "确保已安装模板根目录 extensions/interaction-runtime/ 通用交互扩展"
                )
            if self.lorebooks_dir.exists() and any(self.lorebooks_dir.glob("*.json")):
                steps.append("导入 lorebooks/ 下的传统世界书并绑定角色卡或聊天")
            step_text = "\n".join(
                f"  {index}. {step}" for index, step in enumerate(steps, start=1)
            )
            print(f"""
  产物目录：{self.output_dir}/
{step_text}
""")
        else:
            if self.dimensions:
                state_steps = f"""
  产物目录：{self.output_dir}/
  1. Characters → Import → {self.project_id}.character-card.json
  2. World Info / Lorebooks → Import → {self.project_id}.state-worldbook.json
  3. 将状态世界书与角色卡/聊天绑定，保持 Agent Mode 关闭
  4. 如需自动保存数值，启用兼容 legacy _.set(...) 的状态运行时
"""
            else:
                state_steps = f"""
  产物目录：{self.output_dir}/
  1. Characters → Import → {self.project_id}.character-card.json
  2. 保持 Agent Mode 关闭；本项目未声明状态维度，无需导入状态世界书
"""
            print(state_steps)
        print(f"{'='*60}")
        print("生成完成！")
        print(f"{'='*60}\n")


def main():
    script_dir = Path(__file__).resolve().parent
    template_root = script_dir.parent
    if len(sys.argv) != 2:
        print("Usage: python scripts/generate.py <project_root>", file=sys.stderr)
        sys.exit(2)
    project_root = Path(sys.argv[1]).resolve()

    try:
        AgentGenerator(str(project_root), str(template_root)).run()
    except Exception as e:
        print(f"\n[Error] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
