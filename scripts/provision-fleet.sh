#!/usr/bin/env bash
# provision-fleet.sh — create AWS IoT Things + certs for a fleet of ESP32 devices
#
# Usage:
#   bash scripts/provision-fleet.sh [--count N] [--prefix NAME] [--jobs N]
#
# Output:
#   certs/<prefix>-<NNNN>/device.pem.crt
#   certs/<prefix>-<NNNN>/device.key
#   certs/<prefix>-<NNNN>/device.pub.key
#
# Idempotent: skips devices whose cert files already exist.

set -euo pipefail

POLICY_NAME="esp32p4-policy"
PREFIX="esp32p4-device"
COUNT=10
JOBS=10

while [[ $# -gt 0 ]]; do
  case $1 in
    --count)  COUNT=$2;  shift 2 ;;
    --prefix) PREFIX=$2; shift 2 ;;
    --jobs)   JOBS=$2;   shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

provision_one() {
  local i=$1
  local THING_NAME
  THING_NAME=$(printf "%s-%04d" "$PREFIX" "$i")
  local CERT_DIR="certs/$THING_NAME"

  if [[ -f "$CERT_DIR/device.pem.crt" && -f "$CERT_DIR/device.key" ]]; then
    echo "SKIP  $THING_NAME"
    return
  fi

  mkdir -p "$CERT_DIR"

  # create-thing is idempotent — ignore AlreadyExistsException
  aws iot create-thing --thing-name "$THING_NAME" > /dev/null 2>&1 || true

  local CERT_ARN
  CERT_ARN=$(aws iot create-keys-and-certificate \
    --set-as-active \
    --certificate-pem-outfile "$CERT_DIR/device.pem.crt" \
    --public-key-outfile      "$CERT_DIR/device.pub.key" \
    --private-key-outfile     "$CERT_DIR/device.key" \
    --query certificateArn --output text)

  aws iot attach-policy \
    --policy-name "$POLICY_NAME" \
    --target "$CERT_ARN"

  aws iot attach-thing-principal \
    --thing-name "$THING_NAME" \
    --principal "$CERT_ARN"

  echo "OK    $THING_NAME  ($CERT_ARN)"
}

export -f provision_one
export POLICY_NAME PREFIX

echo "Provisioning $COUNT devices  prefix=$PREFIX  parallel=$JOBS"
seq 1 "$COUNT" | xargs -P "$JOBS" -I{} bash -c 'provision_one "$@"' _ {}
echo "Done. Certs saved to certs/<thing-name>/"
