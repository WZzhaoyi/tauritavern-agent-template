#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TauriTavern Agent 生成器
版本: 2.0.0

从 AGENTS.md 配置生成：
  - Agent Profile JSON  → {作品名}.agent-profile.json
  - SKILLS .ttskill     → {作品名}.ttskill
  - 角色卡 JSON         → {作品名}角色卡.json
  - 主题 CSS            → agent-overrides.css
"""

import json
import os
import re
import shutil
import sys
import yaml
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ConfigLoader:
    """从 AGENTS.md 提取 YAML 配置块。"""

    @staticmethod
    def load(project_root: Path) -> dict:
        agents_file = project_root / "AGENTS.md"
        if not agents_file.exists():
            raise FileNotFoundError("AGENTS.md not found")

        text = agents_file.read_text(encoding="utf-8")
        pattern = r"##\s*2\.\s*配置区.*?^```yaml\s*\n(.*?)^```\s*(?:---\s*)?##\s*3\."
        m = re.search(pattern, text, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        if not m:
            raise ValueError("Cannot find YAML config block in AGENTS.md")

        try:
            return yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"YAML parse error: {e}")


class AgentGenerator:
    def __init__(self, project_root: str):
        self.root = Path(project_root)
        self.cfg = ConfigLoader.load(self.root)

        paths = self.cfg.get("paths", {})
        self.characters_dir = self.root / paths.get("characters_dir", "literature/characters")
        self.scenarios_dir = self.root / paths.get("scenarios_dir", "literature/scenarios")
        self.output_dir = self.root / paths.get("output_dir", "output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.pname = self.cfg.get("project", {}).get("name", "作品")

    # ── SKILLS 验证 ──────────────────────────────────────────

    def validate_skills(self) -> List[dict]:
        skills_cfg = self.cfg.get("skills", [])
        results = []
        for s in skills_cfg:
            sid, src = s["id"], s["source_dir"]
            skill_dir = self.root / src
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                raise FileNotFoundError(f"Missing {skill_md}")
            try:
                fm = self._read_frontmatter(skill_md)
            except Exception as e:
                raise ValueError(f"Invalid SKILL.md frontmatter in {src}: {e}")
            if not fm.get("name") or not fm.get("description"):
                raise ValueError(f"SKILL.md in {src} missing 'name' or 'description' in frontmatter")
            results.append({"id": sid, "dir": skill_dir, "frontmatter": fm})
        return results

    @staticmethod
    def _read_frontmatter(path: Path) -> dict:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            raise ValueError("Missing YAML frontmatter")
        end = text.index("---", 3)
        return yaml.safe_load(text[3:end]) or {}

    # ── SKILLS 打包 ──────────────────────────────────────────

    def bundle_ttskill(self, validated: List[dict]) -> str:
        pname_clean = self.pname.replace(" ", "_")
        filename = f"{pname_clean}.ttskill"
        filepath = self.output_dir / filename

        with zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as zf:
            for skill in validated:
                src_dir = skill["dir"]
                arc_root = src_dir.name
                for f in sorted(src_dir.rglob("*")):
                    if f.name.startswith("."):
                        continue
                    arcname = str(Path(arc_root) / f.relative_to(src_dir))
                    zf.write(f, arcname)

        print(f"  [OK] {filename}")
        return str(filepath)

    # ── 角色卡 ────────────────────────────────────────────────

    def generate_character_card(self) -> dict:
        narrator = self.cfg.get("narrator", {})
        style = self.cfg.get("style_sample", {})
        scenarios = self._load_scenarios()

        first_mes = scenarios[0]["body"] if scenarios else ""
        alternate_greetings = [s["body"] for s in scenarios[1:]] if len(scenarios) > 1 else []

        description = self._build_description(style)
        creator = narrator.get("creator", "")
        pversion = self.cfg.get("project", {}).get("version", "1.0.0")
        dim_names = [d["name"] for d in self.cfg.get("dimensions", [])]

        system_prompt = (
            f"你是《{self.pname}》的叙事者。\n"
            f"写作规则详见已关联的 SKILLS 知识包。\n"
            f"状态维度：{', '.join(dim_names)}。"
        )

        data = {
            "name": narrator.get("name", self.pname),
            "description": description,
            "personality": "",
            "scenario": "",
            "first_mes": first_mes,
            "alternate_greetings": alternate_greetings,
            "mes_example": "",
            "creator_notes": "",
            "system_prompt": system_prompt,
            "post_history_instructions": "",
            "tags": [],
            "creator": creator,
            "character_version": pversion,
            "extensions": {},
        }

        return {"spec": "chara_card_v2", "spec_version": "2.0", "data": data}

    def _build_description(self, style: dict) -> str:
        src_file = style.get("source_file")
        max_len = style.get("max_length", 1500)
        if not src_file:
            return ""
        fpath = self.root / src_file
        if not fpath.exists():
            return ""
        text = fpath.read_text(encoding="utf-8")
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        sample = "\n".join(lines)[:max_len]
        return (
            f"以下是本作文风参考段落，续写时应严格模仿其叙事风格、句式与用词：\n\n"
            f"---\n\n{sample}\n\n---"
        )

    def _load_scenarios(self) -> List[dict]:
        if not self.scenarios_dir.exists():
            return []
        results = []
        for fpath in sorted(self.scenarios_dir.glob("*.md")):
            text = fpath.read_text(encoding="utf-8")
            body = text
            parts = re.split(r"^---\s*$", text, maxsplit=2, flags=re.MULTILINE)
            if len(parts) >= 3:
                body = parts[2].strip()
            if body:
                results.append({"body": body, "file": fpath.name})
        return results

    # ── Agent Profile ─────────────────────────────────────────

    def generate_agent_profile(self) -> dict:
        agent_cfg = self.cfg.get("agent", {})
        dims = self.cfg.get("dimensions", [])
        dim_lines = "\n".join(
            f"- {d['name']}：{', '.join(d.get('stages', []))}（ranges: {d.get('ranges', [])})"
            for d in dims
        )

        system_prompt = (
            f"你是《{self.pname}》的 Agent 写作助手。\n\n"
            f"## 职责\n"
            f"1. 读取当前聊天上下文和世界书激活条目。\n"
            f"2. 按需查阅 SKILLS，获取写作风格、状态规则、视角、世界观与角色设定。\n"
            f"3. 在 scratch/ 中拟写草稿，完成后写入 output/main.md。\n"
            f"4. 提交回复到聊天，并在 persist/ 中更新角色状态。\n\n"
            f"## 状态维度\n{dim_lines}\n\n"
            f"## 短对话规则\n"
            f"如果本轮为轻松闲聊，请使用多次 append 提交简短回复，每段保持自然。\n\n"
            f"## 约束\n"
            f"- 中间分析写入 scratch/，不要放进最终回复。\n"
            f"- 每次运行结束时务必调用 workspace.finish。"
        )

        return {
            "schemaVersion": 1,
            "kind": "tauritavern.agentProfile",
            "id": self._safe_id(self.pname),
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
                "agentSystemPrompt": system_prompt,
            },
            "tools": {
                "allow": [
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
                ],
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

    @staticmethod
    def _safe_id(name: str) -> str:
        s = re.sub(r"[^\w\-_]", "-", name.lower().strip())
        return re.sub(r"-+", "-", s).strip("-")

    # ── 主题 CSS ──────────────────────────────────────────────

    def copy_theme(self) -> Optional[str]:
        theme_cfg = self.cfg.get("theme", {})
        src = theme_cfg.get("source_file")
        if not src:
            return None
        src_path = self.root / src
        if not src_path.exists():
            print(f"  [WARN] Theme file not found: {src_path}")
            return None
        dst = self.output_dir / "agent-overrides.css"
        shutil.copy2(src_path, dst)
        print(f"  [OK] agent-overrides.css")
        return str(dst)

    # ── 汇总输出 ──────────────────────────────────────────────

    def run(self):
        print(f"\n{'='*60}")
        print(f"TauriTavern Agent 生成：{self.pname}")
        print(f"{'='*60}\n")

        # 1. 验证 SKILLS
        print("[验证] SKILLS ...")
        validated = self.validate_skills()
        for v in validated:
            print(f"  [OK] {v['id']} ({v['dir']})")

        # 2. 打包 .ttskill
        print("\n[打包] SKILLS → .ttskill ...")
        ttskill_path = self.bundle_ttskill(validated)

        # 3. Agent Profile
        print("\n[生成] Agent Profile ...")
        profile = self.generate_agent_profile()
        pname_clean = self.pname.replace(" ", "_")
        profile_path = self.output_dir / f"{pname_clean}.agent-profile.json"
        profile_path.write_text(
            json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  [OK] {profile_path.name}")

        # 4. 角色卡
        print("\n[生成] 角色卡 ...")
        card = self.generate_character_card()
        card_path = self.output_dir / f"{pname_clean}角色卡.json"
        card_path.write_text(
            json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  [OK] {card_path.name}")

        # 5. 主题 CSS（可选）
        print("\n[生成] 主题 ...")
        self.copy_theme()

        # 6. 导入说明
        self._print_import_guide()

    def _print_import_guide(self):
        pname_clean = self.pname.replace(" ", "_")
        print(f"\n{'='*60}")
        print("导入 TauriTavern")
        print(f"{'='*60}")
        print(f"""
  1. Characters → Import → {pname_clean}角色卡.json
  2. Agent 系统面板 → 配置档案 → 导入 → {pname_clean}.agent-profile.json
  3. Agent 系统面板 → SKILLS → 导入 → {pname_clean}.ttskill
  4. 设为 Active Profile，开启 Agent Mode 即可使用
""")
        print(f"{'='*60}")
        print("生成完成！")
        print(f"{'='*60}\n")


def main():
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent

    try:
        AgentGenerator(str(project_root)).run()
    except Exception as e:
        print(f"\n[Error] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
