# Security Policy

## Reporting a Vulnerability

If you discover a security issue in docs-keeper, please **do not open a public issue**. Instead:

- Use GitHub's private vulnerability reporting: https://github.com/kostiantyn-matsebora/docs-keeper/security/advisories/new
- Or email: **kmatsebora@gmail.com** with `[docs-keeper-security]` in the subject line

Please include:

- A clear description of the issue and its impact
- Reproduction steps or a proof-of-concept
- The affected version(s) (`plugin.json` version or git ref)
- Whether you've disclosed the issue elsewhere

You can expect:

- An acknowledgement within **3 business days**
- A first assessment within **7 business days**
- A coordinated disclosure timeline once the impact is clear

## Supported Versions

Only the latest minor version on `master` is actively supported. Older minor versions receive security fixes only when the upgrade path is non-trivial.

| Version | Supported |
|---------|-----------|
| 0.2.x   | ✅ |
| < 0.2   | ❌ |

## Release Integrity

Each tagged release at `https://github.com/kostiantyn-matsebora/docs-keeper/releases` is the authoritative install artifact for `/plugin install docs-keeper@docs-keeper`.

- **Verify a tag** with `git tag -v vX.Y.Z` when signed.
- **CI** (`.github/workflows/ci.yml`) runs the full gate on every push and pull request — `pytest` (mock-free unit + black-box suites), `ruff`, and `build/assemble.py --check` (the core ↔ adapter vendoring guard) — so a released commit always has the engine and the bundled plugin in sync.
- The plugin manifest (`adapters/claude-code/.claude-plugin/plugin.json`) and the marketplace manifest (`.claude-plugin/marketplace.json`) carry the version; they must match the release tag.

## What docs-keeper Executes

docs-keeper ships a platform-neutral Python engine (`core/engine/`, stdlib-only at runtime) and a thin Claude Code adapter (`adapters/claude-code/`). Inside Claude Code it runs as **hooks** declared in `adapters/claude-code/hooks/hooks.json`:

- **SessionStart / Stop / SessionEnd / PostCompact** — session tracking and decision capture.
- **PreToolUse (Bash)** — the commit-time drift gate, which inspects the staged Markdown set when Claude Code runs `git commit`.
- **PostToolUse (Skill)** — marks revise targets revised.

These entrypoints read the host's hook payload, run pure engine logic, and emit a decision/message. **docs-keeper does not bypass or relax the host's permission model** — every file edit or shell command still runs through Claude Code's own tool surface and prompts. The engine reads/writes only under the repo: `.docs-keeper/config.json` (committed settings) and `.docs-keeper/sessions/` (per-machine runtime state).

## Scope

In-scope for security reports:

- Path-traversal or injection in the hook entrypoints (`adapters/claude-code/hooks/cc_*.py`) or the engine (`core/engine/*.py`)
- The commit gate (`cc_maintenance.py`) failing open — letting drift through, or executing unintended commands from a crafted hook payload
- A crafted repo tree, `config.json`, or session/capture file causing the engine to write outside `.docs-keeper/` or the index targets
- Privilege issues in the GitHub Actions workflows (`.github/workflows/*.yml`)

Out of scope:

- Documentation content authored by the docs-keeper agent (producing docs is its purpose)
- Vulnerabilities in third-party agent hosts (Claude Code) — report those upstream

## Public Disclosure

After a fix lands, the vulnerability is recorded in [`CHANGELOG.md`](CHANGELOG.md) under the patching version's `### Security` block, with a CVE if assigned and credit to the reporter (unless they prefer anonymity).
