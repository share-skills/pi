#!/usr/bin/env python3
"""Validate PI platform descriptions stay trigger-optimized."""

import sys

from distribute import (
    ROOT,
    VARIANTS,
    canonical_description,
    parse_frontmatter_simple,
    validate_trigger_description,
)


def main() -> int:
    failures = []
    checked = 0

    for variant, config in VARIANTS.items():
        lang = config["lang"]
        expected = canonical_description(lang)
        validate_trigger_description(expected, lang)

        for _frontmatter_dir, output_path, _needs_purge in config["targets"]:
            path = ROOT / output_path
            if not path.exists():
                failures.append(f"{variant}: missing {output_path}")
                continue

            data = parse_frontmatter_simple(path.read_text(encoding="utf-8"))
            actual = data.get("description", "")

            try:
                validate_trigger_description(actual, lang)
            except ValueError as exc:
                failures.append(f"{output_path}: {exc}")
                continue

            if actual != expected:
                failures.append(
                    f"{output_path}: description mismatch\n"
                    f"  expected: {expected}\n"
                    f"  actual:   {actual}"
                )
                continue

            checked += 1

    if failures:
        print("❌ Description validation failed:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print(f"✅ Description validation passed: {checked} platform files match trigger terms.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
