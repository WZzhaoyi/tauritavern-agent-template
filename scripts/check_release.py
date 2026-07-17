#!/usr/bin/env python3
"""Validate a release tag against the framework version."""

import re
import sys
from pathlib import Path

import yaml


TAG_PATTERN = re.compile(r"v(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)")


def validate_release_tag(tag: str, config_path: Path) -> str:
    if not TAG_PATTERN.fullmatch(tag):
        raise ValueError("release tag must use vMAJOR.MINOR.PATCH")

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    framework = config.get("framework")
    if not isinstance(framework, dict):
        raise ValueError("framework configuration is missing")

    version = framework.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError("framework.version must be non-empty text")
    if tag != f"v{version}":
        raise ValueError(
            f"release tag {tag!r} does not match framework.version {version!r}"
        )
    return version


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/check_release.py vMAJOR.MINOR.PATCH", file=sys.stderr)
        return 2

    config_path = Path(__file__).resolve().parents[1] / "tauritavern.template.yaml"
    try:
        version = validate_release_tag(sys.argv[1], config_path)
    except (OSError, ValueError, yaml.YAMLError) as error:
        print(f"[Error] {error}", file=sys.stderr)
        return 1

    print(f"Release tag matches framework version {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
