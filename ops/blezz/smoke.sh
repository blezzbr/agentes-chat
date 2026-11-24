#!/usr/bin/env bash
set -euo pipefail

root=$(git rev-parse --show-toplevel)
work=$(mktemp -d)
compose=(docker compose --project-name blezz-ci --project-directory "$work" -f "$root/docker-compose.yml")
trap '"${compose[@]}" down --volumes --remove-orphans >/dev/null 2>&1 || true; rm -rf "$work"' EXIT

url=http://127.0.0.1:3300
{
  printf 'AGENTES_SECRET=%s\n' "$(openssl rand -base64 48)"
  printf 'POSTGRES_PASSWORD=%s\n' "$(openssl rand -hex 24)"
  printf 'PUBLIC_URL=%s\nHOST_PORT=3300\nBIND_ADDRESS=127.0.0.1\n' "$url"
  printf 'AGENTES_IMAGE=agentes-blezz:test\nAGENTES_BACKUP_IMAGE=ghcr.io/agentes-chat/backup:%s\n' "$UPSTREAM_VERSION"
} > "$work/.env"

healthy() {
  for _ in $(seq 90); do
    if curl -fsS "$url/api/health" 2>/dev/null | jq -e --arg version "$UPSTREAM_VERSION" \
      '.status == "ok" and .database == "ok" and .version == $version'; then
      return 0
    fi
    sleep 2
  done
  "${compose[@]}" ps
  return 1
}

"${compose[@]}" up -d
healthy
curl -fsS "$url/" -o "$work/index.html"
grep -q 'id="root"' "$work/index.html"
curl -fsS "$url/runner/agentes-runner.mjs" -o "$work/runner.mjs"
test "$(head -n 1 "$work/runner.mjs")" = '#!/usr/bin/env node'
node "$work/runner.mjs" --version

"${compose[@]}" exec -T postgres psql -U agentes -d agentes -v ON_ERROR_STOP=1 \
  -c 'CREATE TABLE blezz_smoke_marker (id integer PRIMARY KEY); INSERT INTO blezz_smoke_marker VALUES (1);'
"${compose[@]}" stop agentes
"${compose[@]}" run --rm -T agentes migrate
"${compose[@]}" up -d
healthy

"${compose[@]}" exec -T postgres pg_dump -U agentes -d agentes --format=custom > "$work/database.dump"
"${compose[@]}" exec -T postgres createdb -U agentes restored
"${compose[@]}" exec -T postgres pg_restore -U agentes -d restored --exit-on-error < "$work/database.dump"
"${compose[@]}" exec -T postgres psql -U agentes -d restored -tAc 'SELECT id FROM blezz_smoke_marker' | grep -x 1
