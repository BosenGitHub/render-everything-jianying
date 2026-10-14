#!/usr/bin/env python3
"""Build draft_content.json from a validated normalized timeline."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import types
from hashlib import sha256
from pathlib import Path
from typing import Any

from validate_timeline import Report, load_json, validate_timeline


def load_library(library_path: Path | None):
    if library_path is not None:
        sys.path.insert(0, str(library_path.resolve()))
    if sys.platform != "win32" and "uiautomation" not in sys.modules:
        stub = types.ModuleType("uiautomation")
        stub.Control = type("Control", (), {})
        stub.WindowControl = type("WindowControl", (), {})
        sys.modules["uiautomation"] = stub
    try:
        import pyJianYingDraft as draft
    except ImportError as error:
        raise SystemExit(
            "未找到 pyJianYingDraft。请传 --library-path 指向已验证仓库根目录，"
            "并安装 requirements.txt。"
        ) from error
    return draft


def staged_path(source: Path, materials_dir: Path) -> Path:
    digest = sha256(str(source).encode("utf-8")).hexdigest()[:10]
    target = materials_dir / f"{digest}-{source.name}"
    if not target.exists():
        shutil.copy2(source, target)
    return target.resolve()


def add_tracks(draft: Any, script: Any, payload: dict[str, Any], materials_dir: Path) -> None:
    for track in payload["tracks"]:
        track_type = getattr(draft.Track_type, track["type"])
        script.add_track(track_type, track["name"], mute=track.get("muted", False))

    for track in payload["tracks"]:
        track_type = track["type"]
        for item in track["items"]:
            target = draft.Timerange(item["target_start_us"], item["duration_us"])
            if track_type == "text":
                style = draft.Text_style(size=float(item.get("font_size", 5.0)), align=1)
                clip = draft.Clip_settings(transform_y=float(item.get("transform_y", -0.8)))
                segment = draft.Text_segment(item["text"], target, style=style, clip_settings=clip)
            else:
                source_file = Path(item["file"]).resolve()
                local_file = staged_path(source_file, materials_dir)
                source_start = item.get("source_start_us", 0)
                source_duration = item.get("source_duration_us", item["duration_us"])
                source = draft.Timerange(source_start, source_duration)
                volume = float(item.get("volume", 1.0))
                if track_type == "video":
                    material = draft.Video_material(str(local_file))
                    if source_file.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                        source = draft.Timerange(0, item["duration_us"])
                    segment = draft.Video_segment(
                        material, target, source_timerange=source, volume=volume
                    )
                else:
                    material = draft.Audio_material(str(local_file))
                    segment = draft.Audio_segment(
                        material, target, source_timerange=source, volume=volume
                    )
                    fade = min(30_000, item["duration_us"] // 2)
                    if fade > 0:
                        segment.add_fade(fade, fade)
            script.add_segment(segment, track_name=track["name"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("timeline", type=Path)
    parser.add_argument("--draft-dir", type=Path, required=True)
    parser.add_argument("--library-path", type=Path)
    args = parser.parse_args(argv)

    timeline = args.timeline.resolve()
    payload = load_json(timeline)
    report = Report()
    _, expected_duration = validate_timeline(payload, report)
    if report.errors:
        for message in report.errors:
            print(f"[错误] {message}")
        print("timeline.json 校验失败，未生成草稿。")
        return 1

    draft_dir = args.draft_dir.resolve()
    draft_dir.mkdir(parents=True, exist_ok=True)
    materials_dir = draft_dir / "materials"
    materials_dir.mkdir(exist_ok=True)
    draft = load_library(args.library_path)
    script = draft.Script_file(payload["width"], payload["height"], payload["fps"])
    add_tracks(draft, script, payload, materials_dir)
    if script.duration != expected_duration:
        raise RuntimeError(
            f"生成时长 {script.duration}us 与期望 {expected_duration}us 不一致"
        )
    draft_content = draft_dir / "draft_content.json"
    script.dump(str(draft_content))
    shutil.copy2(timeline, draft_dir / "timeline.json")
    build_report = {
        "schema_version": 1,
        "title": payload["title"],
        "duration_us": expected_duration,
        "chatcut_project_id": payload["chatcut_project_id"],
        "chatcut_timeline_id": payload["chatcut_timeline_id"],
        "draft_content": str(draft_content),
    }
    (draft_dir / "BUILD_REPORT.json").write_text(
        json.dumps(build_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"草稿目录: {draft_dir}")
    print(f"draft_content.json: {draft_content}")
    print(f"总时长: {expected_duration}us ({expected_duration / 1_000_000:.3f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

