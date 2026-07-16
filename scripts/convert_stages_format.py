#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
角色阶段数据格式转换工具。

在 _stages.json 与 _stages.yaml 之间批量转换，并同步更新
AGENTS.md 配置区中的 stages_format。
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml


SUPPORTED_FORMATS = ("json", "yaml")


class ConversionError(Exception):
    """用户可修复的转换错误。"""


class IndentedSafeDumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="批量转换 *_stages 文件格式（JSON ↔ YAML）")
    parser.add_argument("target_format", choices=SUPPORTED_FORMATS, help="目标格式")
    parser.add_argument("--characters-dir", default=None, help="角色目录，默认从 AGENTS.md 读取或使用 literature/characters")
    parser.add_argument("--agents-file", default=None, help="AGENTS.md 路径")
    parser.add_argument("--keep-source", action="store_true", help="保留源格式文件")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已存在的目标文件")
    parser.add_argument("--dry-run", action="store_true", help="只展示将执行的操作")
    parser.add_argument("--no-config-update", action="store_true", help="不更新 AGENTS.md")
    return parser.parse_args()


def load_config_yaml_block(agents_file: Path) -> Tuple[str, int, int]:
    text = agents_file.read_text(encoding="utf-8")
    pattern = r"##\s*2\.\s*配置区.*?^```yaml\s*\n(.*?)^```\s*(?:---\s*)?##\s*3\."
    m = re.search(pattern, text, re.DOTALL | re.IGNORECASE | re.MULTILINE)
    if not m:
        raise ConversionError(f"Cannot extract YAML config from {agents_file}")
    return text, m.start(1), m.end(1)


def get_stages_format_from_config(agents_file: Path) -> str:
    text, start, end = load_config_yaml_block(agents_file)
    cfg = yaml.safe_load(text[start:end]) or {}
    fmt = cfg.get("stages_format", "json")
    if fmt not in SUPPORTED_FORMATS:
        raise ConversionError(f"Invalid stages_format in AGENTS.md: '{fmt}'")
    return fmt


def resolve_characters_dir(project_root: Path, agents_file: Path, cli_value: Optional[str]) -> Path:
    if cli_value:
        p = Path(cli_value)
        return p if p.is_absolute() else project_root / p
    try:
        text, start, end = load_config_yaml_block(agents_file)
        cfg = yaml.safe_load(text[start:end]) or {}
    except Exception:
        return project_root / "literature/characters"
    configured = cfg.get("paths", {}).get("characters_dir", "literature/characters")
    p = Path(configured)
    return p if p.is_absolute() else project_root / p


def source_fmt(path: Path) -> Optional[str]:
    if path.suffix == ".json":
        return "json"
    if path.suffix in (".yaml", ".yml"):
        return "yaml"
    return None


def iter_stage_files(characters_dir: Path) -> Iterable[Tuple[Path, str]]:
    if not characters_dir.exists():
        return
    for path in sorted(characters_dir.glob("*_stages.*")):
        fmt = source_fmt(path)
        if fmt:
            yield path, fmt


def load_data(path: Path, fmt: str) -> Any:
    raw = path.read_text(encoding="utf-8")
    if fmt == "json":
        m = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", raw.strip(), re.DOTALL)
        clean = m.group(1) if m else raw.strip()
        return json.loads(clean) if clean else {}
    return yaml.safe_load(raw) or {}


def dump_data(data: Any, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    return yaml.dump(data, Dumper=IndentedSafeDumper, allow_unicode=True, sort_keys=False)


def target_path_for(src: Path, target_fmt: str) -> Path:
    return src.with_suffix(".json" if target_fmt == "json" else ".yaml")


def convert(src: Path, src_fmt: str, target_fmt: str, keep_source: bool, overwrite: bool, dry_run: bool) -> str:
    dst = target_path_for(src, target_fmt)
    if dst.exists() and dst != src and not overwrite:
        raise ConversionError(f"Target exists: {dst}. Use --overwrite.")
    if dry_run:
        return f"{src} -> {dst}"
    data = load_data(src, src_fmt)
    dst.write_text(dump_data(data, target_fmt), encoding="utf-8")
    if not keep_source and src != dst:
        src.unlink()
    return f"{src} -> {dst}"


def update_config(agents_file: Path, target_fmt: str, dry_run: bool) -> bool:
    text, start, end = load_config_yaml_block(agents_file)
    yaml_text = text[start:end]
    pattern = re.compile(
        r'^(\s*stages_format:\s*)(["\']?)(json|yaml)\2(\s*(?:#.*)?)$',
        re.MULTILINE,
    )
    m = pattern.search(yaml_text)
    if not m:
        raise ConversionError("Cannot find stages_format in AGENTS.md config")
    new_line = f"{m.group(1)}{m.group(2)}{target_fmt}{m.group(2)}{m.group(4)}"
    updated = pattern.sub(new_line, yaml_text, count=1) if m.group(3) != target_fmt else yaml_text
    if updated == yaml_text:
        return False
    if not dry_run:
        agents_file.write_text(text[:start] + updated + text[end:], encoding="utf-8")
    return True


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    agents_file = Path(args.agents_file) if args.agents_file else root / "AGENTS.md"
    if not agents_file.is_absolute():
        agents_file = root / agents_file

    characters_dir = resolve_characters_dir(root, agents_file, args.characters_dir)
    files = list(iter_stage_files(characters_dir))

    try:
        if not files:
            print(f"No *_stages files found in {characters_dir}")
        for src_path, fmt in files:
            print(convert(src_path, fmt, args.target_format, args.keep_source, args.overwrite, args.dry_run))

        if not args.no_config_update:
            changed = update_config(agents_file, args.target_format, args.dry_run)
            tag = " (dry-run)" if args.dry_run else ""
            print(f"{'Updated' if changed else 'Already'}{tag}: stages_format = {args.target_format}")
        return 0
    except ConversionError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
