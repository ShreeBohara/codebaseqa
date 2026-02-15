#!/usr/bin/env bash
set -euo pipefail

echo "Running secret preflight scan on tracked files ..."

patterns=(
  "sk-[A-Za-z0-9_-]{20,}"
  "ghp_[A-Za-z0-9]{20,}"
  "AKIA[0-9A-Z]{16}"
  "-----BEGIN( RSA)? PRIVATE KEY-----"
)

fail=0
for p in "${patterns[@]}"; do
  if rg -n --hidden -g '!.git' -g '!node_modules' -g '!.next' -g '!data' "$p" . >/tmp/secret_scan_hits.txt 2>/dev/null; then
    echo "Potential secret pattern found ($p):"
    cat /tmp/secret_scan_hits.txt
    fail=1
  fi
done

if [[ "$fail" -eq 1 ]]; then
  echo ""
  echo "Secret preflight FAILED."
  echo "Action: rotate compromised keys and remove secrets before launch."
  exit 2
fi

echo "Secret preflight passed."

