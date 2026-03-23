# Purpose
- Keep changes correct, small, and cheap to review.
- Prefer existing patterns and read only the files needed for the task.

# How To Work
- Start by checking the nearest `AGENTS.md`, the user request, and the smallest relevant code/config files.
- Restate the goal, identify the affected area, and make a short plan for non-trivial work.
- Search before adding code; extend existing modules, helpers, and tests first.

# Source Of Truth
- Authoritative order: user request, nearest `AGENTS.md`, referenced code/tests, explicit configs/docs.
- If sources conflict, stop and report the conflict instead of guessing.

# Local Overrides
- The nearest `AGENTS.md` to the working directory takes precedence.
- Root `AGENTS.md` sets default repo behavior; subdirectory `AGENTS.md` files may narrow it.

# Planning Rules
- A plan is required for multi-file work, risky changes, infra/config changes, schema/API contract changes, or unclear scope.
- Keep plans short, actionable, and stored in `plans/*.md` when they should persist.
- Skip persistent plans for trivial single-file edits.

# Token Efficiency Rules
- Read the smallest useful set of files first.
- Prefer targeted search and file reads over loading entire directories.
- Use local context instead of global context whenever possible.
- Reference docs instead of embedding large explanations.
- Keep progress updates brief and include only decisions, validation, and risks.

# Editing Rules
- Make minimal diffs and avoid unrelated formatting.
- Reuse existing patterns, names, and utilities.
- Remove or avoid duplication.
- Replace behavior-shaping literals with named constants.
- Do not add dependencies unless clearly necessary.
- Update nearby docs only when behavior, workflow, or contracts change.

# Testing & Validation
- Run the narrowest relevant checks first, then broader checks if warranted.
- Validate touched areas with available tests, lint, typecheck, or build commands.
- If validation cannot run, state exactly why and note the risk.
- Report assumptions, edge cases checked, and any unverified paths.

# Safety & Scope
- Stay within the requested scope.
- Do not rewrite architecture without a stated reason.
- Never overwrite user changes unless explicitly asked.
- Ask before destructive, irreversible, or secret-handling operations.

# Output Style
- Keep responses short, concrete, and implementation-focused.
- For non-trivial tasks, report the plan, validation, and residual risks.
- Prefer file references over long code excerpts.

# Escalation Rules
- Escalate on conflicting requirements, missing credentials/assets, unsafe operations, or uncertainty that could cause incorrect behavior.
- Make explicit assumptions only when the risk is low and the change is easy to revise.

# Configuration Awareness (`.codex/config.toml`)
- Repo behavioral defaults live in `.codex/config.toml`, not here.
- Check that file before assuming model, reasoning, approval, or workspace defaults.
- Keep `AGENTS.md` focused on workflow guardrails.

# Definition Of Done
- Requested change implemented with a minimal diff.
- Relevant patterns reused and no avoidable duplication introduced.
- Needed docs or plans updated.
- Relevant validation run, or gaps and risks reported explicitly.
