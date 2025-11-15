"""Validate censorship config files for schema correctness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List, Set

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.utils.config import load_censorship_config  # noqa: E402


def validate_file(path: Path) -> List[str]:
    errors: List[str] = []
    try:
        config = load_censorship_config(path)
    except Exception as exc:  # pragma: no cover - CLI friendly
        errors.append(f"{path}: failed to load config -> {exc}")
        return errors

    seen_ids: Set[str] = set()
    for source in config.sources:
        if source.id in seen_ids:
            errors.append(f"{path}: duplicate source id '{source.id}'")
        seen_ids.add(source.id)

        if not source.url.startswith("http"):
            errors.append(f"{path}: source '{source.id}' must have an http(s) URL")

        invalid_tags = [tag for tag in source.region_tags if tag not in config.regions]
        if invalid_tags:
            errors.append(
                f"{path}: source '{source.id}' references unknown regions {invalid_tags}"
            )

    if not config.sources:
        errors.append(f"{path}: config contains no sources")

    if not config.valyu.credentials.api_key_env:
        errors.append(f"{path}: Valyu credentials missing api_key_env")

    return errors


def iter_config_files(targets: Iterable[Path]) -> List[Path]:
    files: List[Path] = []
    for target in targets:
        if target.is_file():
            files.append(target)
        elif target.is_dir():
            files.extend(sorted(target.glob("censorship_sources.*")))
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate censorship config files")
    parser.add_argument(
        "paths",
        nargs="*",
        default=["config"],
        help="Files or directories to validate (defaults to config/)",
    )
    args = parser.parse_args()

    root_paths = [Path(p).resolve() for p in args.paths]
    files = iter_config_files(root_paths)

    if not files:
        print("No config files found to validate", file=sys.stderr)
        return 1

    all_errors: List[str] = []
    for file_path in files:
        all_errors.extend(validate_file(file_path))

    if all_errors:
        print("\n".join(all_errors), file=sys.stderr)
        return 1

    print(f"Validated {len(files)} config file(s) successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
