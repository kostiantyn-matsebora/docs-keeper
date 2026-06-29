# Pull Request

## Summary

Describe what changed and why.

## Changes

- Describe the concrete changes in this PR.

## Checklist

- [ ] Scope is focused and intentionally limited
- [ ] Edited the source (`core/engine/`, `core/spec/`, or `adapters/`) — not the vendored `adapters/claude-code/hooks/_engine/` or `adapters/claude-code/spec/`
- [ ] `python3 build/assemble.py` re-run after any `core/` change
- [ ] `python3 -m pytest`, `python3 -m ruff check .`, and `python3 build/assemble.py --check` all pass
- [ ] Documentation was updated if behavior changed
- [ ] `CHANGELOG.md` was updated for user-visible changes

## Notes

Anything reviewers should pay special attention to.
