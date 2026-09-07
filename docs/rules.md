# Python Coding Conventions

These conventions apply to Python changes. Task scope, precedence, assumptions, dependency management, and delivery
follow [AGENTS.md](../AGENTS.md). Module placement, layer responsibilities, and dependency boundaries are defined in
[architecture.md](architecture.md).

## Code Clarity and Compatibility

- Use Python 3.10-compatible syntax. Public functions and methods must annotate parameter and return types.
- Follow PEP 8 for new Python identifiers: PascalCase classes, snake_case functions and variables, and UPPER_SNAKE_CASE
  constants. Preserve framework-required method names, existing public interfaces, and names specified in [ui.md](ui.md),
  including Qt overrides such as `paintEvent` and UI attributes such as `actOpenFile`.
- Give modules and functions clear responsibilities. Treat 50 lines as a review prompt; split functions when doing so
  improves cohesion, branching complexity, or readability. Do not fragment coherent UI assembly solely to meet a line limit.
- Document public APIs and non-obvious contracts, side effects, or failure conditions. Simple functions may use a brief
  docstring; do not repeat type annotations or fill in sections that add no useful information. For image operations,
  document relevant array shape, RGB/BGR order, dtype, bit depth, value range, and whether inputs are modified in place.
- Keep application logic modular and maintainable. Development and maintenance scripts may remain simple and task-specific
  without reproducing application layers.

## State, Configuration, and Input Contracts

- Give each shared state value one authoritative owner and pass it explicitly to consumers. Keep component-local state
  with that component; do not introduce a global state manager for all state or use global mutable variables as business state.
- Use the existing configuration module for externally configurable settings. Add environment variables, configuration
  files, or persistence only when the requested behavior requires them; transient view and session state can remain local
  to its owner.
- Use dataclasses or explicit model classes for structured business data. Validate external inputs at entry points and
  enforce important business invariants where values are created or changed. Check applicable types, ranges, missing values,
  and formats; reuse established contracts instead of repeating the same checks in every internal call.
- For text file I/O, specify the encoding explicitly, defaulting to UTF-8 unless the format requires another encoding.
  Use binary mode for bytes and let the format or serialization library handle encoding when appropriate. Use `pathlib`
  for filesystem paths and avoid hardcoded platform path separators.

## Exceptions, Logging, and Privacy

- Catch exceptions where a layer can recover, translate an error into its own contract, or terminate a task cleanly.
  Otherwise, let them propagate to that boundary. Preserve the original cause when translating exceptions, for example
  with `raise ImageLoadError(...) from exc`; do not require a try/except around every I/O call.
- Do not use bare `except`. Prefer specific exceptions; reserve `except Exception` for deliberate safety boundaries such
  as worker entry points or third-party adapters. Distinguish expected failures from unexpected defects and do not silently
  discard unexpected errors.
- Use `logging` for runtime diagnostics, with English messages and context relevant to the event. Record unexpected
  exception tracebacks at the responsible boundary, avoiding duplicate stack traces at every layer. Choose log severity
  according to the failure and recovery outcome.
- Intentional command-line results or summaries may use standard output, including `print`; diagnostic logging must not
  be mixed into machine-readable command output.
- Omit or mask sensitive information in logs, including credentials and private metadata. Include paths and parameters
  only when useful for diagnosis and appropriate for disclosure.

## UI Responsiveness and Failure Recovery

- Keep expensive I/O and computation off the UI thread using the existing worker and signal flow in the architecture.
  Apply widget updates on the UI thread; a callback alone does not establish thread safety.
- Map backend errors to concise, appropriately classified user messages in the presentation layer, following
  [i18n.md](i18n.md). Avoid exposing raw tracebacks or unnecessary implementation details in dialogs and status text.
- Preserve user data and provide recovery appropriate to the operation, using existing error states and actions where
  possible. A failed image load may offer retry or allow selecting another image; rollback, drafts, or other new recovery
  features are needed only when the requested workflow calls for them.

## Performance and Resource Ownership

- Choose optimizations from an observed bottleneck or a clear workload requirement. Keep large-image processing and
  rendering responsive with appropriate memory use; choose lazy loading, virtualization, or reuse when they address the
  actual problem. Do not add pagination, caches, or connection pools solely to satisfy a generic performance rule.
- When adding or changing a cache, define its key, capacity or memory bound, lifetime, and invalidation conditions.
  Avoid repeated expensive image allocation where reuse is safe and useful.
- Give resources explicit owners and lifetimes. Prefer context managers for owned resources that support them, such as
  files. Respect Qt parent-child ownership and thread-pool auto-deletion instead of requiring manual deletion of every
  object; use appropriate Qt lifetime APIs when objects need earlier cleanup.
- Treat stopping active work separately from object destruction. The owner must coordinate task completion or shutdown
  and prevent callbacks from updating disposed views; object ownership alone does not define a task's cancellation policy.

## Test Design

Verification scope and commands follow [the validation policy](../AGENTS.md#6-validation).
For critical behavior, consider normal operation, boundaries, and failure paths and cover the applicable cases.
These are review dimensions, not a fixed number of tests per function. Assert observable behavior and regression outcomes
rather than duplicating implementation details in tests.
