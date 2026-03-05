#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_SCRIPT="${SCRIPT_DIR}/fetch_figma_raw.py"

if [[ ! -f "${TARGET_SCRIPT}" ]]; then
  echo "Missing script: ${TARGET_SCRIPT}" >&2
  exit 1
fi

for exe in python3 python; do
  if command -v "${exe}" >/dev/null 2>&1; then
    exec "${exe}" "${TARGET_SCRIPT}" "$@"
  fi
done

echo "No Python launcher found. Install Python or ensure one of these is available: python3, python." >&2
exit 1
