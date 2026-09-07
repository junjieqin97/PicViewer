## Git Commit Guidelines

Task scope and document precedence are defined in [AGENTS.md](../AGENTS.md).
Read these guidelines before the first repository edit, not only before committing.

### Branch Requirements

- Before editing, inspect the current branch, working-tree status, and any existing diff.
- Use the branch explicitly assigned by the user. Reuse the existing task branch when continuing the same task;
  do not create another branch merely because a new turn starts.
- For a new task that modifies repository files without an assigned branch, create a feature branch from `develop`
  before making changes. New branch names default to `feature-<brief-feature-description>` unless instructed otherwise.
- Preserve pre-existing changes. Do not automatically stash, restore, discard, or commit unrelated user work to prepare
  a branch. If overlapping edits prevent safe isolation, explain the conflict and request the needed decision.
- Commit the task's related changes on its selected branch.

### When to Commit

- For tasks that modify repository files, commit after each logically complete, validated change unless the user
  requests uncommitted work. Reviews and explanations do not require edits or empty commits.
- Do not combine unrelated changes into one commit
- Prefer multiple small commits over one large commit

### Commit Message Format

Use Conventional Commits:

`<type>(<scope>): <summary>`

Allowed types:

- feat
- fix
- refactor
- test
- docs
- chore

Rules:

- Summary must be in imperative mood
- Summary must be concise (≤ 72 characters)
- No trailing period

Examples:

- fix(cache): prevent memory leak on eviction
- refactor(router): extract middleware pipeline
- test(auth): add refresh token edge cases

### Commit Content Rules

- Code commits must remain runnable and pass the applicable checks in [the validation policy](../AGENTS.md#6-validation).
  Documentation-only commits require document checks instead of application tests or startup checks.
- Do not include formatting-only changes unless explicitly requested
- Do not include generated files unless required

### Commit Safety

- Avoid force-push
- Never rewrite published history

### Commit Intent

- Commit message must explain *why* the change exists, not only *what*
- Avoid vague messages like "update code" or "fix issue"
- Record material validation limits and reasons for checks that could not run. If application checks are skipped for
  documentation-only changes, record that runtime behavior is unchanged.

### Multi-step Changes

- When tests are warranted, develop the relevant test, implement the behavior, and then refactor as needed.
  This is a development sequence, not a requirement for separate commits.
- A new regression or feature test may fail during development. Include it with the implementation in one passing,
  logically complete commit rather than committing a known failing test separately.
- Split independent completed changes into separate commits only when each remains runnable and passes its applicable checks.
