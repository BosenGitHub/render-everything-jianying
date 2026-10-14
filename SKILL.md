---
name: render-everything-jianying
description: Turn a PDF, paper, URL, document, chat, script, or local media into an editable short-video workflow that must run video-use first, then ChatCut, and finally create and validate a local Jianying draft ZIP. Use when the user wants a short video delivered as a 剪映草稿 rather than a flattened video or a Niwo upload.
---

# Render Everything → 剪映草稿

把用户提供的内容整理为可继续编辑的剪映草稿。固定顺序是：

1. `video-use`
2. ChatCut 可编辑时间线
3. 本地剪映草稿

流程没有 Niwo 阶段，也不向 Niwo 上传任何文件。最终交付是通过校验的剪映草稿 ZIP，不是成片 MP4。

## 开始前

1. 先读取 `${CODEX_HOME:-$HOME/.codex}/skills/video-use/SKILL.md`。
2. 再读取当前 ChatCut 插件的 `chatcut-plugin-basics`、`asset-import`、`verification`；需要导出字幕或 XML 时再读 `export`。
3. 检查 `ffmpeg`、`ffprobe`、Python 3、zip，以及本 skill 的 `scripts/`。
4. 如果工作目录已有 `<videos_dir>/edit/project.md`，先用一句话总结上次会话。

## 输入确认

先读完用户材料，再一次性确认会改变成片的关键变量：画幅、目标时长、受众、语气、必须保留的信息、字幕需求和交付草稿名称。能从用户当前消息确定的内容不重复问。

文案、镜头策略或剪辑方向尚未确认时，不开始剪辑。`video-use` 的“先说明策略、等用户确认、再执行”是硬约束。

## 阶段 A：video-use

1. 将原始媒体保持不变，所有会话产物写入 `<videos_dir>/edit/`。
2. 按 `video-use` 完成素材盘点、逐词转写缓存、`takes_packed.md`、问题预扫和策略确认。
3. 用户确认策略后，生成 `edl.json`、必要的动画、字幕与 `preview.mp4`；遵守其全部生产正确性规则。
4. 对渲染预览做边界、首尾和中点自检；最多三轮修正。
5. `preview.mp4` 只用于审片。下一阶段必须保留原始素材、切点、源入点、轨道和字幕，不得把单个扁平 MP4 当成 ChatCut 的主要交付。

## 阶段 B：ChatCut

1. 创建或定位用户指定的 ChatCut 项目，并尽早展示可见编辑器。
2. 按 ChatCut `asset-import` 规则导入阶段 A 使用的原始/处理后素材。
3. 用 `edl.json` 在 ChatCut 重建可编辑时间线：保留原素材引用、源入点、时长、轨道层级、字幕和音频关系。
4. 结构完成后再做节奏与包装。不要因为阶段 A 已有预览而把预览作为唯一视频片段放进时间线。
5. 用 ChatCut `verification` 同时检查结构与组合画面。刷新受影响范围后再读取，不能依赖旧 item id 或旧时间线状态。
6. 把 ChatCut 时间线作为用户审片界面。用户明确确认最终时间线后，才进入剪映草稿阶段。

## 阶段 C：剪映草稿

1. 从**已验证的最新 ChatCut 时间线**写出 `timeline.json`。格式见 [references/timeline-schema.md](references/timeline-schema.md)。每个媒体 item 必须映射回本机真实文件，不能只留 ChatCut 云端 URL。
2. 运行：

   ```bash
   python3 scripts/validate_timeline.py <timeline.json>
   ```

3. 准备 `pyJianYingDraft`。优先使用已安装版本；需要可复现依赖时，使用 [references/jianying-runtime.md](references/jianying-runtime.md) 中记录的已验证版本和提交。
4. 生成草稿目录：

   ```bash
   python3 scripts/build_jianying_draft.py \
     <timeline.json> \
     --draft-dir <JianyingPro-Drafts>/<draft-name> \
     --library-path <pyJianYingDraft-repo-root>
   ```

5. 再次校验时间线和生成的 `draft_content.json`：

   ```bash
   python3 scripts/validate_timeline.py <timeline.json> \
     --draft-content <draft-dir>/draft_content.json
   ```

6. 退出剪映或回到首页后打开该草稿，人工确认素材可链接、主视频从 0 开始、轨道数量正确、字幕可编辑、总时长一致。发现差异时先修 `timeline.json` 或映射，再重建。
7. 校验通过后打包：

   ```bash
   python3 scripts/package_draft.py <draft-dir> -o <draft-name>.zip
   ```

## `timeline.json` 的来源规则

- 以 ChatCut 最新项目状态为准；`video-use` 的 `edl.json` 是初始剪辑依据，不覆盖用户之后在 ChatCut 的修改。
- `verified` 必须为 `true`，并记录 `chatcut_project_id` 与 `chatcut_timeline_id`。
- 时间统一使用整数微秒；`duration_us` 表示时长，不是结束点。
- 每条轨道内不得重叠；主视频轨必须从 0 开始。
- 视频/音频必须给出 `source_start_us` 与 `source_duration_us`；图片只需给目标时长。
- 文本 item 直接写可编辑字幕文本，不烧录进视频。

## 交付

只交付以下内容：

- 剪映草稿 ZIP
- `timeline.json`
- 校验命令与结果摘要
- ChatCut 项目/时间线标识，方便追溯

不要把 ChatCut 预览或本地预览冒充剪映草稿。不要上传 Niwo。完成本地校验与 ZIP 打包后停止。

