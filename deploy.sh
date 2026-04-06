#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
RELEASE_FILE="${RELEASE_FILE:-$ROOT_DIR/.deploy.env}"
DEPLOY_ENV="${DEPLOY_ENV:-prod}"
TARGET_IMAGE="${1:-}"

read_release_value() {
  local file_path="$1"
  local key="$2"

  if [ ! -f "$file_path" ]; then
    return 0
  fi

  awk -F= -v key="$key" 'index($0, key "=") == 1 { print substr($0, length(key) + 2); exit }' "$file_path"
}

set_release_value() {
  local file_path="$1"
  local key="$2"
  local value="$3"
  local tmp_file

  tmp_file="$(mktemp)"

  if [ -f "$file_path" ]; then
    awk -v key="$key" -v value="$value" '
      BEGIN { updated = 0 }
      index($0, key "=") == 1 {
        print key "=" value
        updated = 1
        next
      }
      { print }
      END {
        if (!updated) {
          print key "=" value
        }
      }
    ' "$file_path" > "$tmp_file"
  else
    printf '%s=%s\n' "$key" "$value" > "$tmp_file"
  fi

  mv "$tmp_file" "$file_path"
}

TARGET_IMAGE="${TARGET_IMAGE:-${APP_IMAGE:-$(read_release_value "$RELEASE_FILE" APP_IMAGE)}}"

if [ -z "$TARGET_IMAGE" ]; then
  echo "Usage: DEPLOY_ENV=dev|prod ./deploy.sh <image-ref>" >&2
  exit 1
fi

cd "$ROOT_DIR"
set_release_value "$RELEASE_FILE" APP_IMAGE "$TARGET_IMAGE"
APP_IMAGE="$TARGET_IMAGE" RELEASE_FILE="$RELEASE_FILE" bash scripts/zero_downtime_rollout.sh "$DEPLOY_ENV" api
