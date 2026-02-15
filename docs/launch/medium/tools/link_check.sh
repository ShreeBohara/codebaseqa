#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 <markdown_file> [--extract-only]"
  exit 1
fi

md_file="$1"
extract_only="${2:-}"

if [[ ! -f "$md_file" ]]; then
  echo "File not found: $md_file"
  exit 1
fi

echo "Extracting URLs from $md_file ..."

extract_urls() {
  # Prefer ripgrep when available; fall back to grep for macOS setups without rg.
  if command -v rg >/dev/null 2>&1; then
    rg -o 'https?://[^ )\]"]+' "$md_file" || true
  elif command -v perl >/dev/null 2>&1; then
    perl -nE 'while(/https?:\/\/[^\s)\]"]+/g){say $&}' "$md_file" || true
  else
    grep -Eo 'https?://[^ )]+' "$md_file" || true
  fi
}

urls=()
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  urls+=("$line")
done < <(
  extract_urls | sort -u
)

if [[ ${#urls[@]} -eq 0 ]]; then
  echo "No URLs found."
  exit 0
fi

if [[ "$extract_only" == "--extract-only" ]]; then
  printf "%s\n" "${urls[@]}"
  echo "Extract-only mode: ${#urls[@]} URL(s) found."
  exit 0
fi

failures=0
for url in "${urls[@]}"; do
  code=$(curl -L -sS -o /dev/null -w "%{http_code}" --max-time 20 "$url" || true)
  if [[ "$code" == "000" ]]; then
    echo "FAIL timeout/network: $url"
    failures=$((failures + 1))
  elif [[ "$code" -ge 400 ]]; then
    echo "FAIL HTTP $code: $url"
    failures=$((failures + 1))
  else
    echo "OK   HTTP $code: $url"
  fi
done

if [[ "$failures" -gt 0 ]]; then
  echo "Link check completed with $failures failure(s)."
  exit 2
fi

echo "Link check passed."
