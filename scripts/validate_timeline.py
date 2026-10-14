#!/usr/bin/env python3
"""Validate a normalized ChatCut-to-Jianying timeline and optional draft output."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MEDIA_TYPES = {"video", "audio"}
TRACK_TYPES = MEDIA_TYPES | {"text"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} 顶层必须是 JSON 对象")
    return payload


def probe_duration_us(path: Path) -> int | None:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    try:
        return round(float(completed.stdout.strip()) * 1_000_000)
    except ValueError:
        return None


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def validate_timeline(payload: dict[str, Any], report: Report) -> tuple[int, int]:
    allowed = {
        "schema_version", "title", "width", "height", "fps", "verified",
        "chatcut_project_id", "chatcut_timeline_id", "tracks",
    }
    for key in sorted(set(payload) - allowed):
        report.error(f"timeline.json 出现未知字段 {key!r}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        report.error(f"schema_version 必须是 {SCHEMA_VERSION}")
    if not isinstance(payload.get("title"), str) or not payload["title"].strip():
        report.error("title 必须是非空字符串")
    for key in ("width", "height"):
        if not _positive_int(payload.get(key)):
            report.error(f"{key} 必须是正整数")
    fps = payload.get("fps")
    if not _positive_int(fps) or fps > 120:
        report.error("fps 必须是 1..120 的整数")
    if payload.get("verified") is not True:
        report.error("verified 必须为 true，先完成 ChatCut 最新时间线校验")
    for key in ("chatcut_project_id", "chatcut_timeline_id"):
        if not isinstance(payload.get(key), str) or not payload[key].strip():
            report.error(f"{key} 必须是非空字符串")

    tracks = payload.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        report.error("tracks 必须是非空数组")
        return 0, 0

    names: set[str] = set()
    first_video_seen = False
    total_items = 0
    total_duration = 0
    for track_index, track in enumerate(tracks):
        label = f"tracks[{track_index}]"
        if not isinstance(track, dict):
            report.error(f"{label} 必须是对象")
            continue
        for key in sorted(set(track) - {"name", "type", "muted", "items"}):
            report.error(f"{label} 出现未知字段 {key!r}")
        name = track.get("name")
        if not isinstance(name, str) or not name.strip():
            report.error(f"{label}.name 必须是非空字符串")
            name = label
        elif name in names:
            report.error(f"轨道名重复: {name!r}")
        names.add(name)
        track_type = track.get("type")
        if track_type not in TRACK_TYPES:
            report.error(f"{label}.type 必须是 video、audio 或 text")
            continue
        if "muted" in track and not isinstance(track["muted"], bool):
            report.error(f"{label}.muted 必须是布尔值")
        items = track.get("items")
        if not isinstance(items, list):
            report.error(f"{label}.items 必须是数组")
            continue
        previous_end = 0
        for item_index, item in enumerate(items):
            item_label = f"{label}.items[{item_index}]"
            if not isinstance(item, dict):
                report.error(f"{item_label} 必须是对象")
                continue
            allowed_item = {"target_start_us", "duration_us"}
            if track_type in MEDIA_TYPES:
                allowed_item |= {
                    "file", "source_start_us", "source_duration_us", "volume"
                }
            else:
                allowed_item |= {"text", "font_size", "transform_y"}
            for key in sorted(set(item) - allowed_item):
                report.error(f"{item_label} 出现未知字段 {key!r}")

            start = item.get("target_start_us")
            duration = item.get("duration_us")
            if not _nonnegative_int(start):
                report.error(f"{item_label}.target_start_us 必须是非负整数")
                continue
            if not _positive_int(duration):
                report.error(f"{item_label}.duration_us 必须是正整数")
                continue
            end = start + duration
            if start < previous_end:
                report.error(f"{item_label} 与同轨前一项重叠")
            previous_end = max(previous_end, end)
            total_duration = max(total_duration, end)
            total_items += 1

            if track_type == "text":
                if not isinstance(item.get("text"), str) or not item["text"].strip():
                    report.error(f"{item_label}.text 必须是非空字符串")
                if "font_size" in item and not isinstance(item["font_size"], (int, float)):
                    report.error(f"{item_label}.font_size 必须是数字")
                y = item.get("transform_y", -0.8)
                if not isinstance(y, (int, float)) or not -1 <= y <= 1:
                    report.error(f"{item_label}.transform_y 必须在 -1..1")
                continue

            raw_path = item.get("file")
            if not isinstance(raw_path, str) or not raw_path:
                report.error(f"{item_label}.file 必须是本机绝对路径")
                continue
            path = Path(raw_path)
            if not path.is_absolute():
                report.error(f"{item_label}.file 必须是绝对路径: {raw_path}")
                continue
            if not path.is_file():
                report.error(f"{item_label}.file 不存在: {raw_path}")
                continue
            if path.is_symlink():
                report.error(f"{item_label}.file 不能是软链接: {raw_path}")
            is_image = track_type == "video" and path.suffix.lower() in IMAGE_EXTENSIONS
            source_start = item.get("source_start_us", 0)
            source_duration = item.get("source_duration_us", duration)
            if not _nonnegative_int(source_start):
                report.error(f"{item_label}.source_start_us 必须是非负整数")
            if not _positive_int(source_duration):
                report.error(f"{item_label}.source_duration_us 必须是正整数")
            volume = item.get("volume", 1.0)
            if not isinstance(volume, (int, float)) or not 0 <= volume <= 4:
                report.error(f"{item_label}.volume 必须在 0..4")
            if not is_image and _nonnegative_int(source_start) and _positive_int(source_duration):
                media_duration = probe_duration_us(path)
                if media_duration is None:
                    report.error(f"ffprobe 无法读取素材: {raw_path}")
                elif source_start + source_duration > media_duration + 100_000:
                    report.error(
                        f"{item_label} 源窗口 {source_start + source_duration}us "
                        f"超过素材时长 {media_duration}us"
                    )

        if track_type == "video" and not first_video_seen:
            first_video_seen = True
            if not items:
                report.error("主视频轨不能为空")
            elif isinstance(items[0], dict) and items[0].get("target_start_us") != 0:
                report.error("主视频轨第一个 item 必须从 0 开始")

    if not first_video_seen:
        report.error("至少需要一条 video 轨道")
    return total_items, total_duration


def validate_draft(path: Path, expected_duration: int, report: Report) -> None:
    if not path.is_file():
        report.error(f"draft_content.json 不存在: {path}")
        return
    try:
        payload = load_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        report.error(f"draft_content.json 无法解析: {error}")
        return
    canvas = payload.get("canvas_config")
    if not isinstance(canvas, dict) or not _positive_int(canvas.get("width")) or not _positive_int(canvas.get("height")):
        report.error("draft_content.json 缺少合法 canvas_config")
    tracks = payload.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        report.error("draft_content.json 缺少轨道")
    duration = payload.get("duration")
    if not _positive_int(duration):
        report.error("draft_content.json.duration 必须是正整数")
    elif abs(duration - expected_duration) > 100_000:
        report.error(
            f"草稿总时长 {duration}us 与 timeline.json {expected_duration}us 不一致"
        )
    materials = payload.get("materials")
    if not isinstance(materials, dict):
        report.error("draft_content.json 缺少 materials")
        return
    for kind in ("videos", "audios"):
        entries = materials.get(kind, [])
        if not isinstance(entries, list):
            report.error(f"draft_content.json.materials.{kind} 必须是数组")
            continue
        for index, material in enumerate(entries):
            media_path = material.get("path") if isinstance(material, dict) else None
            if not isinstance(media_path, str) or not Path(media_path).is_file():
                report.error(f"草稿素材路径失效: materials.{kind}[{index}]={media_path!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("timeline", type=Path)
    parser.add_argument("--draft-content", type=Path)
    args = parser.parse_args(argv)
    report = Report()
    try:
        payload = load_json(args.timeline.resolve())
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print(f"[错误] timeline.json 无法解析: {error}")
        return 1
    total_items, total_duration = validate_timeline(payload, report)
    if args.draft_content:
        validate_draft(args.draft_content.resolve(), total_duration, report)
    print(f"时间线: {args.timeline.resolve()}")
    print(f"轨道: {len(payload.get('tracks', []))}, 项目: {total_items}")
    print(f"总时长: {total_duration}us ({total_duration / 1_000_000:.3f}s)")
    for message in report.warnings:
        print(f"[告警] {message}")
    for message in report.errors:
        print(f"[错误] {message}")
    if report.errors:
        print(f"校验未通过: {len(report.errors)} 个错误")
        return 1
    print("校验通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

