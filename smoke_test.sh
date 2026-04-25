#!/usr/bin/env bash
# Smoke test — verifies kill-switch is ON before any outbound run.
# Exits 0 if safe (kill-switch active), exits 1 if live mode is on.
set -euo pipefail

LIVE="${CONVERSION_ENGINE_LIVE:-false}"

if [[ "${LIVE,,}" == "true" ]]; then
  echo "FAIL: CONVERSION_ENGINE_LIVE=true — live mode is active. All outbound will reach real prospects."
  echo "      Requires Tenacious CEO approval before proceeding."
  exit 1
fi

# Quick Python check matches config.py logic exactly
python3 -c "
import os, sys
kill = os.getenv('CONVERSION_ENGINE_LIVE', 'false').lower() != 'true'
if not kill:
    print('FAIL: Python config sees live mode ON')
    sys.exit(1)
print('OK: Kill-switch is ON — all outbound routes to staff sink')
"
