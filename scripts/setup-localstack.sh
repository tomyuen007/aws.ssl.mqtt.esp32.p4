#!/usr/bin/env bash
# Provision AWS IoT Core resources on LocalStack.
# Run once after `docker compose up` — idempotent.

set -euo pipefail

AWS="aws --endpoint-url=http://localhost:4566 --region us-east-1 \
    --no-verify-ssl \
    --no-cli-pager"
THING_NAME="${THING_NAME:-esp32p4-device-01}"
POLICY_NAME="esp32p4-mqtt-policy"

echo "==> Creating IoT thing: $THING_NAME"
$AWS iot create-thing --thing-name "$THING_NAME" 2>/dev/null || \
    echo "    (already exists)"

echo "==> Creating IoT policy: $POLICY_NAME"
$AWS iot create-policy \
    --policy-name "$POLICY_NAME" \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": ["iot:Connect","iot:Publish","iot:Subscribe","iot:Receive"],
            "Resource": "*"
        }]
    }' 2>/dev/null || echo "    (already exists)"

echo "==> Creating certificate (keys saved to ./certs/)"
mkdir -p certs
CERT_ARN=$($AWS iot create-keys-and-certificate \
    --set-as-active \
    --query 'certificateArn' \
    --output text)

$AWS iot describe-certificate --certificate-id "${CERT_ARN##*/}" \
    --query 'certificateDescription.certificatePem' \
    --output text > certs/device.pem.crt

echo "Certificate ARN: $CERT_ARN"

echo "==> Attaching policy to certificate"
$AWS iot attach-policy \
    --policy-name "$POLICY_NAME" \
    --target "$CERT_ARN"

echo "==> Attaching certificate to thing"
$AWS iot attach-thing-principal \
    --thing-name "$THING_NAME" \
    --principal "$CERT_ARN"

echo "==> IoT endpoint:"
$AWS iot describe-endpoint --endpoint-type iot:Data-ATS --query 'endpointAddress' --output text

echo ""
echo "Done. MQTT broker: localhost:1883 (plain, for ESP32 dev)"
echo "Use THING_NAME=$THING_NAME in idf.py menuconfig."
