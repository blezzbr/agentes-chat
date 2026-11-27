#!/usr/bin/env bash
set -euo pipefail

# Project-level selection covers tests that depend on the changed source.
paths=$(git diff --name-only --no-renames "$1" "$2")
changed() { grep -Eq "$1" <<< "$paths"; }

tests=()
if changed '^(apps/server/|packages/(engine|adapters|db|config|providers|modules)/|patches/|package.json$|bun.lock$|bunfig.toml$)'; then
  if changed '^(apps/server/(src/|test/[^/]+\.test\.)|packages/(engine|adapters|db|config|providers|modules)/|patches/|package.json$|bun.lock$|bunfig.toml$)'; then
    tests+=(packages/engine/test/machine-accounts.test.ts)
  fi
  if changed '^(apps/server/(runner/|test/runner/)|packages/(adapters|config|providers)/|patches/|package.json$|bun.lock$|bunfig.toml$)'; then
    tests+=(apps/server/test/runner)
  fi
fi
if changed '^(packages/(client|live|i18n|tokens)/|patches/|package.json$|bun.lock$|bunfig.toml$)'; then
  for package in client live i18n tokens; do
    if changed "^(packages/$package/|patches/|package.json$|bun.lock$|bunfig.toml$)" &&
      [[ -d "packages/$package/test" ]]; then
      tests+=("packages/$package/test")
    fi
  done
fi
if changed '^(apps/web/|packages/(client|ui|live|i18n|tokens)/|patches/|package.json$|bun.lock$|bunfig.toml$)'; then
  tests+=(apps/web/test/no-ai.test.tsx)
  if changed '^packages/ui/'; then tests+=(packages/ui/test); fi
fi
if changed '^(apps/mobile/|packages/(client|i18n)/|patches/|package.json$|bun.lock$|bunfig.toml$)'; then
  tests+=(apps/mobile/test/features/right-hand-plans.test.ts)
fi
if changed '^deploy/'; then tests+=(deploy/deploy.test.ts); fi

while IFS= read -r path; do
  if [[ "$path" =~ ^(apps|packages|deploy|scripts)/[[:alnum:]_./@+-]+\.test\.(ts|tsx|js|mjs)$ ]] && [[ -f "$path" ]]; then
    covered=false
    for suite in "${tests[@]}"; do
      if [[ "$path" == "$suite" || "$path" == "$suite/"* ]]; then
        covered=true
        break
      fi
    done
    if [[ "$covered" == false ]]; then tests+=("$path"); fi
  fi
done <<< "$paths"

# Multiple changed files may select the same suite. Collapse them before running.
printf 'tests='
if (( ${#tests[@]} )); then
  printf '%s\n' "${tests[@]}" | awk '!seen[$0]++' | paste -sd ' ' -
else
  echo
fi
if changed '^(ops/blezz/|\.github/workflows/blezz-|Dockerfile$|\.dockerignore$|docker-compose.yml$|install.sh$|deploy/|packages/db/migrations/)'; then
  echo "ops=true"
fi
