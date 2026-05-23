## Git Commit Guidelines

### When to Commit

- Commit after each logically complete change
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

- Each commit must compile and pass tests
- Do not include formatting-only changes unless explicitly requested
- Do not include generated files unless required

### Commit Safety

- Avoid force-push
- Never rewrite published history

### Commit Intent

- Commit message must explain *why* the change exists, not only *what*
- Avoid vague messages like "update code" or "fix issue"

### Multi-step Changes

- If a task requires multiple steps, create commits in this order:
    1. Add or update tests
    2. Implement logic changes
    3. Refactor or cleanup