#!/bin/sh
# Portable Python-3 launcher for docs-keeper hooks.
#
# Claude Code runs hook command strings through a POSIX shell (sh on Linux/macOS,
# Git Bash on Windows), but the interpreter name differs by platform: `python3` is
# the norm on Linux/macOS and is often absent on Windows, while `python` is the norm
# on Windows and is often absent on Linux. Prefer python3, fall back to python.
#
# Usage: python_runner.sh <script.py> [args...]
if command -v python3 >/dev/null 2>&1; then
  exec python3 "$@"
elif command -v python >/dev/null 2>&1; then
  exec python "$@"
else
  echo "docs-keeper: no 'python3' or 'python' interpreter found on PATH" >&2
  exit 1
fi
