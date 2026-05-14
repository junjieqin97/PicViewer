# PicViewer

This project is developed by AI.

Please see the [AGENTS.md](AGENTS.md).

## Notes

- High-DPI 支持已启用：图片显示区与信息区分析图会按 DPR 渲染。

## 国际化（简体中文/英文）

- 语言优先级：`PICVIEWER_LANG` > 系统语言 > `zh_CN`。
- 支持值：
  - 中文：`zh` / `zh_CN` / `zh-CN`
  - 英文：`en` / `en_US` / `en-GB`
- 不支持运行时切换，语言在应用启动时确定。

### 环境变量示例

```bash
PICVIEWER_LANG=en python -m pic_viewer.main
```

## 日志

- 默认模式：日志输出到控制台。
- 开发者模式：日志输出到 `~/.PicViewer/logs/picviewer.log`，单文件最大 5MB，保留 5 个滚动备份。
- 日志级别仍由 `PICVIEWER_LOG_LEVEL` 控制，默认值为 `INFO`。

### 开发者模式示例

```bash
python -m pic_viewer.main --developer-mode
PICVIEWER_LOG_LEVEL=DEBUG python -m pic_viewer.main --developer-mode
```

### 回退规则

- 若选择英文但运行时找不到 `picviewer_en.qm`，应用会自动回退到中文并继续启动。
- 源码仓库默认只提交 `.ts`，`.qm` 由 CI/打包阶段生成。

### 翻译文件维护

```bash
# 从 Python 源码更新 ts
scripts/i18n/update_ts.sh

# 从 ts 生成 qm（默认输出到 src/pic_viewer/ui/resources/i18n）
scripts/i18n/build_qm.sh
```

更多约定见 [docs/i18n.md](docs/i18n.md)。
