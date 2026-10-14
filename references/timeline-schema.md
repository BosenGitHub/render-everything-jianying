# `timeline.json` 协议

该文件是已验证 ChatCut 时间线与本地剪映草稿之间的确定性桥接层。它只记录可映射到本机文件的可编辑时间线状态。

## 示例

```json
{
  "schema_version": 1,
  "title": "示例短片",
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "verified": true,
  "chatcut_project_id": "project-id",
  "chatcut_timeline_id": "timeline-id",
  "tracks": [
    {
      "name": "V1",
      "type": "video",
      "items": [
        {
          "file": "/absolute/path/clip.mp4",
          "target_start_us": 0,
          "duration_us": 5000000,
          "source_start_us": 1200000,
          "source_duration_us": 5000000,
          "volume": 1.0
        }
      ]
    },
    {
      "name": "字幕",
      "type": "text",
      "items": [
        {
          "text": "这是可编辑字幕",
          "target_start_us": 0,
          "duration_us": 1800000
        }
      ]
    }
  ]
}
```

## 顶层字段

- `schema_version`：固定为 `1`。
- `title`：非空草稿名称。
- `width` / `height`：正整数画布尺寸。
- `fps`：`1..120` 的整数。
- `verified`：必须为 `true`；表示已按 ChatCut verification 检查最新时间线。
- `chatcut_project_id` / `chatcut_timeline_id`：非空字符串。
- `tracks`：至少一条轨道，轨道名不得重复。

## 轨道

- `name`：非空且唯一。
- `type`：`video`、`audio` 或 `text`。
- `muted`：可选布尔值，默认 `false`。
- `items`：按 `target_start_us` 升序排列，同一轨道内不得重叠。
- 第一条 video 轨道是主视频轨；它的第一个 item 必须从 `0` 开始。

## 媒体 item

- `file`：本机绝对路径，必须存在且不是软链接。
- `target_start_us`：非负整数。
- `duration_us`：正整数。
- `source_start_us`：非负整数；图片可省略。
- `source_duration_us`：正整数；图片可省略，默认等于目标时长。
- `volume`：可选，`0..4`，默认 `1.0`。

视频/音频源窗口不得超过 `ffprobe` 读取的真实时长。时间线输出时长是所有 item 的 `target_start_us + duration_us` 最大值。

## 文本 item

- `text`：非空字符串。
- `target_start_us`：非负整数。
- `duration_us`：正整数。
- `font_size`：可选，正数，默认 `5.0`。
- `transform_y`：可选，`-1..1`，默认 `-0.8`。

