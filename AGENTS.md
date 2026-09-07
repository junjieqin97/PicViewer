# Agent Instructions

Project: PicViewer, a cross-platform desktop photo viewer.

## 1. Scope and Precedence

You are responsible for implementing, reviewing, and validating the current task within its requested scope.

- These are repository defaults. Explicit user instructions for the current task take precedence over them.
- Repository documents do not override system or developer instructions or platform permissions.
- Within repository documents, resolve conflicts in this order: this AGENTS.md, the feature requirements in
  [docs/plan.md](docs/plan.md), then other referenced documents. Referenced documents use this precedence rule.
- Review-only and explanation-only requests do not authorize file changes or commits. Follow a user request to leave
  changes uncommitted.

## 2. Read Before Acting

Read the documents that apply to the task before the corresponding action. Documents already read in the current
task need not be read again unless they change or the scope expands.

| Task or action | Required reading |
| --- | --- |
| Any repository modification | [Git guidelines](docs/git.md), before the first edit, including branch and working-tree checks |
| Feature or behavior change | Relevant requirements and pipeline sections in [the plan](docs/plan.md) |
| Python code change | [Coding rules](docs/rules.md) and [architecture](docs/architecture.md) |
| UI behavior or appearance change | Relevant sections of [the UI specification](docs/ui.md) |
| Layout, style, text fit, or accessibility change | [Visual checks](docs/visual-testing.md) |
| Add, change, or remove user-visible text in any layer, including Controllers | [Internationalization rules](docs/i18n.md) |
| Architecture or module placement change | [Architecture](docs/architecture.md) and affected pipeline descriptions in [the plan](docs/plan.md) |
| Packaging or release change | Relevant sections of [packaging](docs/packaging.md) and [CI](docs/ci.md) documentation |
| Documentation-only change or review | The documents being changed or reviewed and references needed to check their accuracy |

The current user task defines the work to perform. The plan describes feature requirements and current implementation;
its section order is not a development queue. Only advance a roadmap when the user requests it and explicit ordered,
unfinished items exist. Do not infer new work from existing feature descriptions.

## 3. Fixed Technical Choices

Do not change these choices unless explicitly instructed:

- Python 3.10
- Anaconda / Conda environment: `PicViewer`
- PySide6 for the GUI, OpenCV for image processing, and pyexiv2 for image metadata
- Cross-platform support for Windows, macOS, and Linux

The complete Python dependency list and version constraints are maintained in [pyproject.toml](pyproject.toml).
Environment provisioning and native dependency sources are documented in [docs/packaging.md](docs/packaging.md).
Run `conda activate PicViewer` in the same shell before running project Python, test, installation, or packaging
commands. If that shell already has `PicViewer` activated, activation need not be repeated. Do not assume activation
persists into a new shell.

## 4. Architecture Boundaries

- Keep UI presentation separate from business logic; core logic must be testable without a Qt event loop.
- Use `controllers/` for Qt interaction coordination, `app/` for use cases and DTOs, `domain/` for models and calculations,
  and `infra/` for image I/O, library adapters, and operating-system access.
- `ui/workers/` bridges background service calls to Qt signals; it must not implement business rules or update widgets.
- Follow the existing directory map and dependency rules in [docs/architecture.md](docs/architecture.md).
  Create directories only when needed for the current task; do not scaffold unused layers or relocate unrelated code.

## 5. Implementation Workflow

1. Establish the requested behavior, relevant existing behavior, and verification scope.
2. Complete the pre-edit checks in the Git guidelines and design data flow for affected components.
3. Implement core logic and relevant tests, then integrate affected Controllers, workers, and UI.
4. Check documentation and translation impact, and run the applicable validation below.
5. Follow the Git guidelines for committing the completed change and report the result.

Use the smallest reasonable interpretation of minor gaps. Record assumptions affecting lasting behavior in relevant
documentation or explanatory code comments; record temporary execution assumptions in the task response or commit message.
Avoid premature optimization and unrelated refactoring.

## 6. Validation

- For changed non-UI behavior, prefer focused unit tests using generated arrays or temporary fixtures. Use real image
  files only when necessary to exercise formats, metadata, or decoder behavior.
- Run the affected existing tests. Add tests when they verify meaningful new behavior or a regression; new UI tests
  are optional. Broaden to the full unit suite when shared code or cross-layer behavior is affected.
- For layout, style, text fit, or accessibility changes, run the applicable visual cases and inspect affected UI behavior
  using [docs/visual-testing.md](docs/visual-testing.md). Use the full matrix for shared layout or theme changes.
- For changes that may affect application startup or runtime behavior, launch the app and verify the affected basic flow.
  Offscreen checks alone do not verify native window behavior.
- For documentation-only changes, check accuracy, relative links, paths, and consistency across affected documents;
  application startup and application tests are not required.
- Report checks performed, results, and any checks that could not run with their reasons. Include material validation
  limits in the commit message when a commit is made; do not report unverified behavior as verified.

Run these existing entry points from the repository root after activating the project environment:

| Purpose | Command |
| --- | --- |
| Focused unit test example | `python -m unittest tests.unit.test_focus_peaking -v` (choose modules relevant to the change) |
| Full unit suite | `python -m unittest discover -s tests/unit` |
| Visual regression matrix | `python -m tests.visual.run` (see the visual guide for individual cases) |
| Application startup | `python -m pic_viewer.main` |

## 7. Change Boundaries and Documentation

- Unless explicitly requested, do not add frameworks, network features, auto-update, telemetry, or UI redesign beyond
  the required functionality.
- Prefer small, incremental changes. Preserve pre-existing user work and keep unrelated changes out of the task.
  Delete code only when the current fix or refactor removes or replaces it.
- Repository documentation must be in English. Conversation replies follow the user's language; translation resources
  follow their target language.
- Update affected documentation when architecture or documented behavior changes, keeping related documentation and code
  in the same commit.
- Whenever user-visible text changes, check both English and Chinese translation sources according to
  [docs/i18n.md](docs/i18n.md), regardless of the source file's layer. Layout-only changes with unchanged copy do not
  require translation updates. Translation paths and generated-file rules are maintained in that document.

## 8. Completion by Task Type

| Task type | Completion criteria |
| --- | --- |
| Review-only or explanation-only | Deliver the requested findings or explanation with references and relevant limitations; no edits or commits |
| Documentation-only change | Requested content is updated and document checks pass; follow the Git guidelines for delivery |
| Code or behavior change | Requested behavior is implemented, applicable rules and checks are satisfied, affected documentation and translations are updated, and delivery follows the Git guidelines |

If a required check cannot run, distinguish implemented work from unverified behavior and report the limitation.
