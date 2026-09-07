# PicViewer Architecture

This document describes the existing module layout and the responsibilities used when extending it.
Task scope and document precedence are defined in [AGENTS.md](../AGENTS.md).
Feature requirements and detailed pipeline descriptions are in [the plan](plan.md).

## Directory Map

Paths below are relative to the repository root. This is a map of existing components, not a scaffold to recreate.

```text
src/pic_viewer/
├─ main.py                 # Application assembly and startup
├─ __main__.py             # Python module entry point
├─ controllers/            # Qt interaction and presentation coordination
├─ app/
│  ├─ services/            # Application use cases
│  └─ dto/                 # Structured results and view inputs
├─ domain/
│  ├─ models/              # Business values and settings
│  └─ rules/               # Image analysis and other calculations
├─ infra/
│  ├─ adapters/            # Image decoding, ICC conversion, and metadata libraries
│  └─ system/              # Operating-system integration
├─ ui/
│  ├─ windows/             # Main window, dialogs, and UI assembly
│  ├─ widgets/             # Reusable controls and painting
│  ├─ workers/             # Background service calls and Qt signal delivery
│  ├─ utils/               # Qt presentation helpers
│  ├─ i18n/                # Translation runtime
│  └─ resources/           # Translation sources, icons, and theme styles
├─ config/                 # Settings and logging configuration
├─ common/                 # Shared errors and independent utilities
└─ assets/licenses/        # Bundled third-party license texts
tests/unit/                # Domain, service, adapter, Controller, and widget tests
tests/visual/              # Offscreen rendered checks and their runner
scripts/i18n/              # Translation extraction and compilation
scripts/packaging/         # Build and dependency verification tools
packaging/pyinstaller/     # PyInstaller specification
packaging/icons/           # Native application icons
```

Create additional modules or directories only when needed for the requested change. The architecture does not require
unused repositories, ports, command buses, networking layers, or alternative presentation frameworks.

## Responsibilities and Dependencies

- `main.py` assembles shared services and starts the application. It is the entry point for dependency wiring.
- UI windows and widgets create controls, handle view geometry and painting, and expose presentation state or events.
  Keep image calculations and file I/O outside UI callbacks.
- Controllers bind actions and signals, track active images and presentation state, coordinate workers, map backend
  results and errors to localized text, and update widgets. They call services or domain rules instead of implementing
  image analysis or decoder logic themselves.
- Workers call application services in the background and emit completion or error signals. Controllers handle those
  signals on the UI thread; workers do not mutate widgets or own business rules.
- Application services coordinate use cases, infrastructure adapters, and domain calculations, returning structured DTOs.
  Service and domain modules must not import Qt or UI modules. Infrastructure dependencies must be replaceable in tests;
  the existing services accept concrete adapters through constructor injection, so new abstract ports are not mandatory.
- Domain models and rules contain values, validation, and calculations. They may use NumPy and OpenCV but must not depend
  on Controllers, application services, infrastructure adapters, filesystem access, or a Qt event loop.
- Infrastructure owns image I/O, metadata extraction, color-profile conversion, and operating-system access. Its adapters
  encapsulate third-party dependencies; the existing color-profile adapter uses Qt color-profile primitives without
  owning widgets or requiring the application event loop.
- Configuration and common utilities must not depend back on Controllers or UI. Avoid circular imports across all layers.

## Verification and Maintenance

Use [the validation policy](../AGENTS.md#6-validation) to choose relevant tests and runtime checks.
Update this map when module responsibilities or directory placement change. Update affected pipeline descriptions in
[the plan](plan.md) when data flow changes; do not preserve obsolete internal names solely because they appear there.
