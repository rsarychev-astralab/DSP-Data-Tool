#!/usr/bin/env bash
# Запуск контейнера с сохранением «Исходные данные» на диск хоста
# (иначе загрузки через «Сохранить маппинг полей» живут только внутри контейнера).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE_DIR="$ROOT/Исходные данные"
IMAGE="${DSP_IMAGE:-dsp-transform}"
NAME="${DSP_CONTAINER:-dsp-transform}"
PORT="${DSP_PORT:-5555}"

mkdir -p "$SOURCE_DIR"

ENV_FILE="$ROOT/.env"

docker build -t "$IMAGE" "$ROOT"

docker stop "$NAME" 2>/dev/null || true
docker rm "$NAME" 2>/dev/null || true

RUN_ARGS=(
  run -d
  --name "$NAME"
  --restart unless-stopped
  -p "${PORT}:8000"
  -v "$SOURCE_DIR:/app/Исходные данные"
)
if [[ -f "$ENV_FILE" ]]; then
  RUN_ARGS+=(--env-file "$ENV_FILE")
fi
RUN_ARGS+=("$IMAGE")

docker "${RUN_ARGS[@]}"

echo "OK: http://127.0.0.1:${PORT}"
echo "Исходные данные на хосте: $SOURCE_DIR"
