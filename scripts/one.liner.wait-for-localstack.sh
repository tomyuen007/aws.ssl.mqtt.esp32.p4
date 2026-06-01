#!/usr/bin/env bash
# One-liner form of the LocalStack IoT health-check wait loop.
# Useful for copy-pasting into a terminal without worrying about
# multi-line block formatting.
#
# Usage:
#   bash scripts/one.liner.wait-for-localstack.sh
#
# Or paste the single line directly into any bash terminal:
#   until docker exec localstack curl -sf http://localhost:4566/_localstack/health | grep -q '"iot"'; do sleep 2; done && echo "LocalStack ready."

until docker exec localstack curl -sf http://localhost:4566/_localstack/health | grep -q '"iot"'; do sleep 2; done && echo "LocalStack ready."
