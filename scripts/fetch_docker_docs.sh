#!/usr/bin/env bash
set -euo pipefail

TEMP_DIR=$(mktemp -d)
DEST_DIR="/root/ReClaw-2.0/data/manuals/docker"
mkdir -p "$DEST_DIR"

echo "==> 1. Cloning official Docker docs repository (shallow, ~10s)..."
git clone --depth 1 https://github.com/docker/docs.git "$TEMP_DIR/docker-docs"

echo "==> 2. Bundling Docker Compose v2 Manual..."
COMPOSE_OUT="$DEST_DIR/01_Docker_Compose_v2_Official_Manual.md"
echo "# Docker Compose v2 Official Manual" > "$COMPOSE_OUT"
echo "Generated: $(date -u)" >> "$COMPOSE_OUT"
find "$TEMP_DIR/docker-docs/content/manuals/compose" -type f -name "*.md" | sort | while read -r f; do
    echo -e "\n\n---\n## File: $(basename "$f")\n" >> "$COMPOSE_OUT"
    cat "$f" >> "$COMPOSE_OUT"
done

echo "==> 3. Bundling Docker Engine & Networking Manual..."
ENGINE_OUT="$DEST_DIR/02_Docker_Engine_and_Networking_Manual.md"
echo "# Docker Engine & Networking Official Manual" > "$ENGINE_OUT"
echo "Generated: $(date -u)" >> "$ENGINE_OUT"
find "$TEMP_DIR/docker-docs/content/manuals/engine" -type f -name "*.md" | sort | while read -r f; do
    echo -e "\n\n---\n## File: $(basename "$f")\n" >> "$ENGINE_OUT"
    cat "$f" >> "$ENGINE_OUT"
done

rm -rf "$TEMP_DIR"

echo "==> SUCCESS. Pristine Markdown manuals generated:"
ls -lh "$DEST_DIR"
