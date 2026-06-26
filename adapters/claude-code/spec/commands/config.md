# config — procedure

View or change docs-keeper's per-repo settings in `.docs-keeper/config.json` (the committed,
shared settings file — NOT the gitignored runtime state beside it).

> Platform-neutral procedure. The Claude Code adapter exposes it as `/docs-keeper:config` and
> wires reads/writes to the bundled config entrypoint (`hooks/cc_config.py --get` / `--set`).

## Settings

| Key | Type | Values | Default |
|---|---|---|---|
| `enforcement` | string | `warn` (surface drift, never block) · `block` (fail the commit on drift) | `block` |
| `paths` | array of globs | files docs-keeper watches + indexes; `**/` any depth, `*` within a segment, `?` one char | `["**/*.md"]` |

## When to invoke

- The user asks to view, change, tighten, or relax docs-keeper configuration.
- Enforcement should switch between advisory (`warn`) and blocking (`block`).
- The watch/index scope should change (narrow to `docs/`, add another extension, etc.).

## Steps

1. **Show the current config first** via the platform's config entrypoint (`--get`). If the
   file is absent the result is `{}` — engine defaults apply (`enforcement=block`,
   `paths=["**/*.md"]`).
2. **Confirm the requested change** with the user when it materially alters behavior
   (e.g. `warn` → `block`, or narrowing `paths` so existing docs fall out of scope).
3. **Apply each change** through the entrypoint's set action — one key per call:
   - `enforcement <warn|block>`
   - `paths <glob> [<glob> ...]` — pass the FULL desired list; the array is REPLACED, not
     merged. To add or drop a glob, read the current list (`--get`) and pass the new full set.
4. **Never hand-edit `.docs-keeper/config.json`.** Route every write through the entrypoint so
   validation runs and the file stays canonical; invalid values are rejected (non-zero exit).
5. **Report the result.** Show the resulting config and call out scope effects:
   ```
   Updated docs-keeper config:
     enforcement: warn → block
     paths: ["**/*.md"]
   ```
   When narrowing `paths` orphans an existing `index.md` (its children fall out of scope), warn
   that a follow-up `/docs-keeper:index <dir>` may be queued by the drift gate.

## Report format rules (binding)

- Show the effective config as JSON or a one-line-per-key diff. No prose paragraphs.
- State old → new for each changed key.
- On a rejected value, surface the entrypoint's error verbatim and leave the file unchanged.
