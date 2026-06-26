"""
Claude Code adapter — config command entrypoint.

Backs `/docs-keeper:config`: view or change settings in
`.docs-keeper/config.json` (the committed, per-repo settings file). Thin glue —
parse argv, wire the repo-rooted file reader, delegate validation + write to
`core.engine.config`.

  --get                       : print the current config as JSON.
  --set <key> <value> [<value> ...] : validate + persist one setting.

Settable keys: `enforcement` (warn|block), `paths` (one or more globs; the
whole array is replaced). Exits 0 on success, 1 on a validation error.
"""

import argparse
import sys

from _engine_import import config, gitio


def invoke_config(action: str, key: str = "", values=None, repo_root: str = "", file_reader=None) -> dict:
    """
    Apply a config action. Returns {exit_code, output, error, path}.

    `output` is the JSON to show the user; `error` is set on validation failure.
    `file_reader` is injectable for tests; defaults to a repo-rooted reader.
    """
    if not repo_root:
        repo_root = gitio.resolve_repo_root_from_git()
    if file_reader is None:
        file_reader = gitio.make_file_reader(repo_root)

    current = config.load_config(file_reader)

    if action == "get":
        return {"exit_code": 0, "output": config.serialize_config(current), "error": "", "path": ""}

    if action == "set":
        new_config, err = config.apply_setting(current, key, values or [])
        if err:
            return {"exit_code": 1, "output": "", "error": err, "path": ""}
        path = config.write_config(repo_root, new_config)
        return {"exit_code": 0, "output": config.serialize_config(new_config), "error": "", "path": path}

    return {"exit_code": 1, "output": "", "error": f"unknown action '{action}'", "path": ""}


def main() -> None:
    parser = argparse.ArgumentParser(description="docs-keeper Claude Code config command.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--get", action="store_true", help="Print the current config as JSON.")
    group.add_argument(
        "--set",
        nargs="+",
        metavar="KEY VALUE",
        help="Set a key: enforcement <warn|block> | paths <glob> [<glob> ...].",
    )
    parser.add_argument("--repo-root", default="", help="Git working tree root")
    args = parser.parse_args()

    if args.get:
        result = invoke_config("get", repo_root=args.repo_root)
    else:
        key = args.set[0]
        values = args.set[1:]
        result = invoke_config("set", key=key, values=values, repo_root=args.repo_root)

    if result["error"]:
        print(result["error"], file=sys.stderr)
    if result["output"]:
        print(result["output"], end="")

    sys.exit(result["exit_code"])


if __name__ == "__main__":
    main()
