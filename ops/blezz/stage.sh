#!/usr/bin/env bash
set -euo pipefail

bundle=$(cd "$(dirname "$0")" && pwd)
state=/opt/blezz-agentes-staging
url=http://127.0.0.1:3300
export COMPOSE_PROFILES=
unset AGENTES_IMAGE AGENTES_BACKUP_IMAGE HOST_PORT BIND_ADDRESS PUBLIC_URL AGENTES_MEMORY

if (( $# != 0 )); then
  echo 'Usage: stage.sh' >&2
  exit 2
fi
[[ "$(id -u)" == 0 ]]
[[ "$(uname -m)" == x86_64 ]]
(cd "$bundle" && sha256sum --check SHA256SUMS)

app_image=$(sed -n 's/^AGENTES_IMAGE=//p' "$bundle/images.env")
backup_image=$(sed -n 's/^AGENTES_BACKUP_IMAGE=//p' "$bundle/images.env")
version=$(sed -n 's/^UPSTREAM_VERSION=//p' "$bundle/images.env")
[[ "$app_image" =~ ^docker\.io/klausgibin/blezz-workspace@sha256:[0-9a-f]{64}$ ]]
[[ "$backup_image" =~ ^ghcr\.io/agentes-chat/backup@sha256:[0-9a-f]{64}$ ]]
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]

install -d -m 0700 "$state"
exec 9>"$state/deploy.lock"
flock -n 9
docker pull "$app_image"
install -m 0600 "$bundle/docker-compose.yml" "$state/docker-compose.yml"
if [[ ! -f "$state/runtime.env" ]]; then
  umask 077
  {
    printf 'AGENTES_SECRET=%s\n' "$(openssl rand -base64 48)"
    printf 'POSTGRES_PASSWORD=%s\n' "$(openssl rand -hex 24)"
  } > "$state/runtime.env"
fi
temporary=$(mktemp "$state/environment.XXXXXX")
trap 'rm -f "$temporary"' EXIT
cat "$state/runtime.env" > "$temporary"
printf 'PUBLIC_URL=%s\nHOST_PORT=3300\nBIND_ADDRESS=127.0.0.1\nAGENTES_MEMORY=2g\n' "$url" >> "$temporary"
printf 'AGENTES_IMAGE=%s\nAGENTES_BACKUP_IMAGE=%s\n' "$app_image" "$backup_image" >> "$temporary"
mv "$temporary" "$state/.env"
compose=(docker compose --project-name blezz-agentes-staging --project-directory "$state")
"${compose[@]}" pull postgres
"${compose[@]}" up -d --pull never --wait --wait-timeout 240 agentes postgres
health=$(curl --max-time 10 -fsS "$url/api/health")
python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(not (d.get("status") == "ok" and d.get("database") == "ok" and d.get("version") == sys.argv[1]))' "$version" <<< "$health"
printf '%s\n' "$health"
