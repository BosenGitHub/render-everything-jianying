# Render Everything → 剪映草稿

把 PDF、论文、URL、文档、聊天、脚本或本地媒体整理为可编辑短视频工程的 Codex Skill。

**固定流程：video-use → ChatCut → 剪映草稿 ZIP。** 最终交付包含原素材映射、源入点、分轨音频和可编辑字幕，不以扁平成片代替工程。

## 安装

将仓库克隆到尚不存在的 Skill 目录：

```bash
git clone https://github.com/BosenGitHub/render-everything-jianying.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/render-everything-jianying"
```

如已有同名 Skill，先备份并选择独立目录，避免覆盖现用版本。重新启动 Codex 或开启新会话加载。

## 依赖

- Python 3.10+；ffmpeg / ffprobe；Git。
- 已安装的 video-use Skill。
- 已连接的 ChatCut 插件及其 asset-import、verification 等技能。
- 本机剪映，用于打开草稿并确认实际可编辑性。
- 构建草稿依赖 pyJianYingDraft，以及 requirements.txt 中的 Python 包；版本和固定提交见 [运行时说明](references/jianying-runtime.md)。这些第三方工具没有打包进本仓库，各自许可独立适用。

## 使用

```text
使用 $render-everything-jianying，读取这份脚本和素材。先确认剪辑策略，
通过 video-use 生成剪辑依据，在 ChatCut 重建并审核可编辑时间线，
最后生成、校验剪映草稿并交付 ZIP、timeline.json 和检查结果。
保留原素材、独立字幕与音频轨道。
```

完整流程见 [SKILL.md](SKILL.md)，数据格式见 [时间线说明](references/timeline-schema.md)。

从仓库根目录执行，所有参数替换为自己的绝对路径：

```bash
python3 scripts/validate_timeline.py "$TIMELINE"
python3 scripts/build_jianying_draft.py "$TIMELINE" --draft-dir "$DRAFT_DIR" --library-path "$JY_LIBRARY"
python3 scripts/validate_timeline.py "$TIMELINE" --draft-content "$DRAFT_DIR/draft_content.json"
python3 scripts/package_draft.py "$DRAFT_DIR" -o "$DELIVERY_ZIP"
```

## 本地验证

```bash
python3 tests/test_skill.py
```

测试覆盖时间线结构、身份/校验字段、同轨重叠、主轨起点、源路径、生成草稿结构、ZIP 确定性及缺失草稿拒绝。测试只证明离线脚本行为，未运行真实 ChatCut 工作流、pyJianYingDraft 构建和剪映打开/保存/重开验收。

## 开源许可

本仓库以 [MIT License](LICENSE) 发布。
