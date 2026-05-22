# Agent Instructions

Project: PicViewer (Python 3 + PySide2 + OpenCV)

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

- Language: Python 3.10
- Package Manager: Anaconda
  - Conda Env Name: PicViewer
  - You MUST activate the conda environment by running `conda activate PicViewer` before executing the python command.
- GUI Framework: PySide2
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
│     ├─ main.py                 # Program entry point: create the app, assemble dependencies, and launch the main window
│     │
│     ├─ ui/                     # View layer: windows, widgets, resources, and UI state
│     │  ├─ __init__.py
│     │  ├─ windows/             # Main windows, dialogs, and pages
│     │  ├─ widgets/             # Reusable components
│     │  ├─ i18n/                # Internationalization helpers
│     │  ├─ presenters/          # Optional: MVP/MVVM presentation logic or view models
│     │  └─ resources/           # Icons, QSS/CSS, images, fonts, translation files, etc.
│     │
│     ├─ app/                    # Application layer: use-case orchestration, such as what to do after a button is clicked
│     │  ├─ __init__.py
│     │  ├─ services/            # Application services / use cases, such as importing files or generating reports
│     │  ├─ commands/            # Optional: command objects, undo/redo
│     │  └─ dto/                 # Optional: cross-layer data structures to avoid exposing domain objects directly to the UI
│     │
│     ├─ domain/                 # Domain layer: core business models and rules, preferably independent of GUI/IO
│     │  ├─ __init__.py
│     │  ├─ models/              # Entities and value objects
│     │  ├─ rules/               # Validation rules and calculation logic
│     │  └─ ports/               # Abstract interfaces, such as Repository, Gateway, Clock, etc.
│     │
│     ├─ infra/                  # Infrastructure layer: concrete implementations of domain ports
│     │  ├─ __init__.py
│     │  ├─ persistence/         # SQLite, SQLAlchemy, file storage, etc.
│     │  ├─ network/             # HTTP, gRPC, WebSocket, etc.
│     │  ├─ system/              # OS-related features: clipboard, notifications, auto-start on boot
│     │  └─ adapters/            # Wrappers around third-party SDKs
│     │
│     ├─ config/                 # Configuration and environment
│     │  ├─ __init__.py
│     │  ├─ settings.py          # Unified configuration loading, such as env/ini/yaml
│     │  └─ logging.yaml
│     │
│     ├─ common/                 # Common utilities that do not depend back on business logic
│     │  ├─ __init__.py
│     │  ├─ errors.py            # Custom exceptions
│     │  ├─ event_bus.py         # Optional: event bus
│     │  └─ utils.py
│     │
│     └─ assets/                 # Optional: centralized static resources, alternatively placed under ui/resources
│
├─ tests/
│  ├─ unit/                      # Unit tests for the domain/app layers
│  ├─ integration/               # Integration tests for the infra layer
│  └─ e2e/                       # Optional: UI automation
│
├─ scripts/                      # Development scripts, such as formatting, packaging, version generation, etc.
└─ packaging/                    # Packaging-related files for PyInstaller, Briefcase, cx_Freeze, etc.
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
