#!/usr/bin/env bash

set -euo pipefail

environment_name="${1:?environment is required (dev|prod)}"
service_name="${2:?service is required (api)}"
rollout_pull_images="${ROLLOUT_PULL_IMAGES:-true}"
release_file="${RELEASE_FILE:-.deploy.env}"

case "$environment_name" in
  dev|prod) ;;
  *)
    echo "Unsupported environment: $environment_name" >&2
    exit 1
    ;;
esac

case "$service_name" in
  api) ;;
  *)
    echo "Unsupported service: $service_name" >&2
    exit 1
    ;;
esac

compose_file="docker-compose.${environment_name}.yml"
upstreams_template_file="deploy/caddy/upstreams.caddy"
upstreams_file="var/caddy/upstreams.caddy"

read_release_value() {
  local file_path="$1"
  local key="$2"

  if [ ! -f "$file_path" ]; then
    return 0
  fi

  awk -F= -v key="$key" 'index($0, key "=") == 1 { print substr($0, length(key) + 2); exit }' "$file_path"
}

app_image="${APP_IMAGE:-$(read_release_value "$release_file" APP_IMAGE)}"

if [ -z "$app_image" ]; then
  echo "APP_IMAGE is required for rollout." >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  compose_cmd=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  compose_cmd=(docker-compose)
else
  echo "Docker Compose is not available." >&2
  exit 1
fi

compose() {
  APP_IMAGE="$app_image" "${compose_cmd[@]}" -f "$compose_file" "$@"
}

mkdir -p "$(dirname "$upstreams_file")"

if [ ! -f "$upstreams_file" ]; then
  cp "$upstreams_template_file" "$upstreams_file"
fi

current_color="$(
  python3 - "$upstreams_file" <<'PY'
import re
import sys
from pathlib import Path

content = Path(sys.argv[1]).read_text()
match = re.search(r"api_(blue|green):", content)
print(match.group(1) if match else "blue")
PY
)"

if [ "$current_color" = "blue" ]; then
  next_color="green"
else
  next_color="blue"
fi

target_service="api_${next_color}"

if [ "$rollout_pull_images" = "true" ]; then
  docker pull "$app_image"
fi

compose up -d --force-recreate --no-deps "$target_service"

container_id="$(compose ps -q "$target_service")"

for _ in $(seq 1 60); do
  health_status="$(
    docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id"
  )"

  if [ "$health_status" = "healthy" ]; then
    break
  fi

  sleep 2
done

final_status="$(
  docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id"
)"

if [ "$final_status" != "healthy" ]; then
  echo "Service $target_service did not become healthy." >&2
  exit 1
fi

python3 - "$upstreams_file" "$next_color" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
next_color = sys.argv[2]
content = path.read_text()
updated = re.sub(r"api_(blue|green):", f"api_{next_color}:", content, count=1)
path.write_text(updated)
PY

compose up -d --no-deps caddy
compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile
