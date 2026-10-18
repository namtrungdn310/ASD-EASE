#!/usr/bin/env bash
set -euo pipefail

# git grep returns 0 for matches, 1 for no matches, and >1 for an error.
# Capture that status explicitly so a clean repository passes under set -e.
scan_status=0
git grep --no-ext-grep --line-number --no-color -I --extended-regexp \
  '^(<<<<<<< .+|=======|>>>>>>> .+)[[:space:]]*$' -- . || scan_status=$?

case "$scan_status" in
  0)
    echo "Unresolved merge conflict markers found in tracked files." >&2
    exit 1
    ;;
  1)
    echo "No unresolved merge conflict markers found in tracked files."
    ;;
  *)
    echo "Unable to scan tracked files (git grep exited with $scan_status)." >&2
    exit "$scan_status"
    ;;
esac
