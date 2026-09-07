# Rules to Follow

These coding conventions apply to Python changes. Task scope, exceptions, and document precedence are defined in
[AGENTS.md](../AGENTS.md).

## General Goals

- Generate maintainable, testable, and extensible desktop application code, and avoid "one-off script-style" implementations.
- Report the completed work, relevant validation results, and material limitations concisely; follow any explicit
  user request for a different response format.

## Project Structure and Layering

- Follow the existing directory placement and dependency boundaries in [architecture.md](architecture.md).
- Important state must be managed centrally (single source of truth). Do not implicitly share variables across multiple widgets in ways that cause state drift.
- Module responsibilities must be clear, and each file should handle only one category of work.

## Code Standards

- Use syntax compatible with Python 3.10 and type annotations (`typing`). Externally exposed functions/methods must annotate parameter and return types.
- Follow PEP8. Naming: classes use PascalCase, functions/variables use snake_case, and constants use UPPER_SNAKE_CASE.
- Do not use global mutable variables as business state. State must be injected and passed through objects or state managers.
- Functions must have a single responsibility and generally should not exceed 50 lines. Split longer functions into smaller private functions.
- Key functions must include docstrings describing purpose, parameters, return values, exceptions, and boundary conditions.

## Error Handling and Logging

- Any I/O operation (files, network, database) must catch exceptions and provide user-understandable messages, while also recording logs for troubleshooting.
- Do not use bare `except`. Catch specific exceptions, or use `except Exception as e` and record the stack trace with `logging.exception`.
- Use `logging` for unified logging; do not use `print`. Logs must include key context such as feature, parameters, paths, elapsed time, etc. All log output must be in English.

## UI and Interaction Experience

- UI operations must remain responsive. Long-running tasks must not block the main thread; use threads, task queues, or asynchronous mechanisms, and safely return to the UI thread through signals/callbacks to update the interface.
- All UI event handlers should only "collect input + call the business layer + display results"; they must not directly perform complex calculations or I/O.
- User messages should be categorized as information, warning, or error. Text should be concise and clear, avoiding an overload of technical terms.
- Provide recoverable paths for operations that may fail, such as retry, cancel, rollback, or keeping drafts, and avoid causing user data loss.

## Data and Configuration

- Configuration must be managed centrally (through a `config` module or configuration class) and support loading from environment variables/configuration files. Do not scatter configuration throughout the code.
- Data models should use `dataclass` or explicit model classes. Validate inputs for type, range, null values, and format.
- File reads and writes must specify an encoding (default `utf-8`). Use `pathlib` for paths and avoid hardcoding platform path separators.

## Testability

- Business logic must be unit-testable: core logic must not depend on UI widgets; external dependencies should be replaceable through interfaces/dependency injection.
- Provide at least three categories of tests for critical flows: normal path, boundary conditions, and exception path.
- Keep hard-to-test UI code as thin as possible; place use cases in `app/services/` and models or calculations in `domain/`.
  Select verification scope and commands using [the validation policy](../AGENTS.md#6-validation).

## Security and Privacy

- Do not output sensitive information in logs, such as passwords, tokens, or personal privacy data. Such data must be masked or omitted.
- Validate all external input, including file contents, network responses, and user input. Do not trust input.

## Performance and Resources

- Rendering large data volumes should use pagination/virtualization, such as lazy loading lists. Avoid loading everything at once and causing freezes.
- Resources must be released explicitly, including file handles, threads, timers, and network connections. Prefer context managers (`with`).
- Avoid frequently creating/destroying heavyweight objects such as large images or database connections. Use caching or connection pools where applicable.

## Output and Delivery

- By default, do not generate an entire project scaffold unless the user requests it. However, generated code must be directly runnable/integrable, with clear dependencies.
- Keep dependency versions in `pyproject.toml` and installation instructions in the relevant setup or packaging documentation.
- For minor requirement gaps, use the assumption-recording policy in [AGENTS.md](../AGENTS.md#5-implementation-workflow).
- Before delivery, check compliance with applicable conventions. Explain unresolved limitations and alternatives in the
  task response; use code comments only when they help a future maintainer understand lasting behavior.
