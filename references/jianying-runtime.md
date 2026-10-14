# 剪映草稿运行时

本 skill 使用 `pyJianYingDraft` 生成 `draft_content.json`，只使用视频、图片、音频、文本、剪切、音量和 30ms 音频淡入淡出这些基础能力。

## 已验证版本

- 仓库：`https://github.com/border1px/JianYingDraft.git`
- 验证提交：`73f7a88222b81e9641ebd8bf3f8b103b0a1f0416`
- Python 包版本：`0.1.3`
- Python 依赖：`pymediainfo==7.0.1`、`imageio==2.37.2`

可复现安装方式：

```bash
git clone https://github.com/border1px/JianYingDraft.git <edit-dir>/deps/JianYingDraft
git -C <edit-dir>/deps/JianYingDraft checkout 73f7a88222b81e9641ebd8bf3f8b103b0a1f0416
python3 -m pip install pymediainfo==7.0.1 imageio==2.37.2
```

macOS/Linux 只生成草稿，不调用该库的 Windows UI 自动导出能力。`build_jianying_draft.py` 会为这个未使用的模块安装最小导入桩，避免强制安装 `uiautomation`。

剪映 6+ 草稿存在加密与兼容变化。最终验证必须在用户本机当前剪映版本里打开生成草稿；脚本校验只证明结构、媒体路径和时间线映射一致。

