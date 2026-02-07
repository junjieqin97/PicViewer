# Agent Instructions

Project: PicViewer (Python 3 + PyQt5 + OpenCV)

## 1. Agent Role & Responsibility

You are the sole maintainer of this repository.

Your responsibilities include:

- Implementing features according to the development plan
- Maintaining code quality and project structure
- Writing tests where applicable
- Managing Git commits and history
- Ensuring the application remains runnable at all times

All changes must follow the rules defined in this document.

## 2. Development Plan

The high-level development plan is defined in: [docs/plan.md](docs/plan.md)

You MUST:

- Read the entire plan before making changes
- Follow the plan sequentially unless explicitly instructed otherwise
- Keep implementation aligned with stated goals and non-goals

If a plan item is unclear or underspecified, make the smallest reasonable interpretation and document the assumption in
code comments or commit messages.

## 3. Technical Stack (Fixed)

Do NOT change these unless explicitly instructed.

- Language: Python 3
- Package Manager: Anaconda
  - Conda Env Name: PicViewer
  - You MUST activate the conda environment by running `conda activate PicViewer` before executing the python command.
- GUI Framework: PyQt5
- Image Processing: OpenCV
- Target OS: cross-platform (Windows / macOS / Linux)

## 4. Project Architecture Guidelines

### 4.1 Structure

Use a clean, modular layout:

```text
PicViewer/
├─ pyproject.toml
├─ README.md
├─ src/
│  └─ pic_viewer/
│     ├─ __init__.py
│     ├─ main.py                 # 程序入口（创建App、装配依赖、启动主窗口）
│     │
│     ├─ ui/                     # 视图层：窗口、控件、资源、UI状态
│     │  ├─ __init__.py
│     │  ├─ windows/             # 主窗口/对话框/页面
│     │  ├─ widgets/             # 可复用组件
│     │  ├─ i18n/                # 国际化辅助
│     │  ├─ presenters/          # (可选) MVP/MVVM 的展示逻辑 / view-model
│     │  └─ resources/           # 图标、qss/css、图片、字体、翻译文件等
│     │
│     ├─ app/                    # 应用层：用例编排（“点击按钮后要做什么”）
│     │  ├─ __init__.py
│     │  ├─ services/            # 应用服务/用例（例如：导入文件、生成报告）
│     │  ├─ commands/            # (可选) 命令对象、撤销/重做
│     │  └─ dto/                 # (可选) 跨层数据结构（避免domain对象直出到UI）
│     │
│     ├─ domain/                 # 领域层：核心业务模型与规则（尽量不依赖GUI/IO）
│     │  ├─ __init__.py
│     │  ├─ models/              # 实体、值对象
│     │  ├─ rules/               # 校验规则、计算逻辑
│     │  └─ ports/               # 抽象接口（Repository、Gateway、Clock等）
│     │
│     ├─ infra/                  # 基础设施层：domain ports 的具体实现
│     │  ├─ __init__.py
│     │  ├─ persistence/         # sqlite/sqlalchemy/文件存储等
│     │  ├─ network/             # http/grpc/websocket等
│     │  ├─ system/              # OS相关：剪贴板、通知、开机自启
│     │  └─ adapters/            # 第三方SDK封装
│     │
│     ├─ config/                 # 配置与环境
│     │  ├─ __init__.py
│     │  ├─ settings.py          # 统一读取配置（env/ini/yaml）
│     │  └─ logging.yaml
│     │
│     ├─ common/                 # 通用工具：不会反向依赖业务
│     │  ├─ __init__.py
│     │  ├─ errors.py            # 自定义异常
│     │  ├─ event_bus.py         # (可选) 事件总线
│     │  └─ utils.py
│     │
│     └─ assets/                 # (可选) 静态资源集中管理（也可放ui/resources）
│
├─ tests/
│  ├─ unit/                      # domain/app 层单元测试
│  ├─ integration/               # infra 集成测试
│  └─ e2e/                       # (可选) UI自动化
│
├─ scripts/                      # 开发脚本（格式化、打包、生成版本号等）
└─ packaging/                    # PyInstaller/Briefcase/cx_Freeze 打包相关
   ├─ pyinstaller.spec
   └─ icons/
```

### 4.2 Rules:

- UI code MUST NOT contain business logic
- Core logic MUST be testable without Qt event loop
- Avoid circular dependencies

## 5. Coding Rules

The python coding rules are defined in: [docs/rules.md](docs/rules.md)

The UI design guidelines are defined in: [docs/ui.md](docs/ui.md)

The i18n rules are defined in: [docs/i18n.md](docs/i18n.md)

The translation files(*.ts files) are stored in: `src/pic_viewer/ui/resources/i18n`

You MUST:

- Read the coding rules and the UI design guidelines before making changes
- Follow these rules and guidelines unless explicitly instructed otherwise
- Check if the translation files also need to be updated while modifying the UI layer code

## 6. Feature Implementation Rules

For each feature:

1. Understand user-visible behavior first
2. Design data flow before writing UI
3. Implement core logic
4. Integrate UI
5. Verify basic manual behavior
6. Commit

Avoid premature optimization.

## 7. Git Commit Guidelines (Mandatory)

The git commit guidelines are defined in: [docs/git.md](docs/git.md)

You MUST:

- Read the git commit guidelines before committing code
- Follow these guidelines unless explicitly instructed otherwise

## 8. Testing Policy

- Prefer unit tests for non-UI logic
- UI tests are optional; focus on stability
- Tests must not depend on real image files unless necessary

If testing is not feasible, explain why in the commit message.

## 9. Out of Scope (Do NOT do these)

Unless explicitly instructed:

- Do NOT add new frameworks
- Do NOT introduce network features
- Do NOT add auto-update or telemetry
- Do NOT redesign UI beyond required functionality

## 10. Documentation Rules

- Update docs/ when architecture or behavior changes
- Keep doc changes in the same commit as code changes

## 11. Safety & Stability Rules

- Prefer small, incremental changes
- If unsure, choose the safest approach
- Do not delete code unless necessary

## 12. Authority & Precedence

Rule precedence:

1. This AGENTS.md
2. docs/plan.md
3. Other referenced documents

If conflicts exist, follow the highest-precedence rule.

## 13. Completion Definition

A task is complete when:

- Feature matches the plan
- Code follows this document
- App starts without errors
- Changes are committed

## Final Instruction

Treat this document as binding instructions.
If any action would violate these rules, do NOT proceed.