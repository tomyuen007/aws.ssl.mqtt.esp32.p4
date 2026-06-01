#!/usr/bin/env bash
# Wait for LocalStack IoT service to be healthy.
# Blocks until the health endpoint reports "iot" as active.
# Safe to run multiple times — exits immediately if already healthy.
#
# Usage:
#   bash scripts/wait.for.localstack.sh
#   bash scripts/wait.for.localstack.sh 60   # custom timeout in seconds (default 120)

set -euo pipefail

TIMEOUT="${1:-120}"
DEADLINE=$(( $(date +%s) + TIMEOUT ))

echo "Waiting for LocalStack IoT to be ready (timeout ${TIMEOUT}s)..."

until docker exec localstack \
    curl -sf http://localhost:4566/_localstack/health | grep -q '"iot"'; do

  if [[ $(date +%s) -ge $DEADLINE ]]; then
    echo "ERROR: LocalStack IoT not ready after ${TIMEOUT}s."
    echo "  Check container logs:  docker logs localstack"
    exit 1
  fi

  sleep 2
done

echo "LocalStack ready."
