#!/usr/bin/env python3
"""Create a deterministic ZIP from a validated Jianying draft directory."""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("draft_dir", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.draft_dir.resolve()
    if not (root / "draft_content.json").is_file():
        print(f"缺少 draft_content.json: {root}")
        return 1
    files = [p for p in sorted(root.rglob("*")) if p.is_file()]
    for path in files:
        if path.is_symlink():
            print(f"草稿包不能包含软链接: {path}")
            return 1
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo.from_file(path, path.relative_to(root).as_posix())
            info.date_time = (1980, 1, 1, 0, 0, 0)
            with path.open("rb") as handle:
                archive.writestr(info, handle.read(), compress_type=zipfile.ZIP_DEFLATED)
    print(f"草稿 ZIP: {output}")
    print(f"文件数: {len(files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

