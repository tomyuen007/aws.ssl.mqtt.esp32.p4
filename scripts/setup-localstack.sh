#!/usr/bin/env bash
# Provision AWS IoT Core resources on LocalStack.
# Run once after containers start — idempotent.
# Saves all three credential files to ./certs/:
#   device.pem.crt  device certificate
#   device.key      device private key
#   ca.pem          LocalStack CA cert (for ssl_verify=true, optional for dev)

set -euo pipefail

AWS="aws --endpoint-url=http://localhost:4566 --region us-east-1 \
    --no-verify-ssl \
    --no-cli-pager"
THING_NAME="${THING_NAME:-esp32p4-device-01}"
POLICY_NAME="esp32p4-mqtt-policy"

mkdir -p certs

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

echo "==> Creating certificate + private key..."
CERT_JSON=$($AWS iot create-keys-and-certificate --set-as-active)
CERT_ARN=$(echo "$CERT_JSON" | python3 -c \
    "import sys,json; print(json.load(sys.stdin)['certificateArn'])")

echo "$CERT_JSON" | python3 -c \
    "import sys,json; print(json.load(sys.stdin)['certificatePem'])" \
    > certs/device.pem.crt

echo "$CERT_JSON" | python3 -c \
    "import sys,json; print(json.load(sys.stdin)['keyPair']['PrivateKey'])" \
    > certs/device.key

chmod 600 certs/device.key
echo "    device.pem.crt  saved"
echo "    device.key      saved"
echo "    Certificate ARN: $CERT_ARN"

echo "==> Attaching policy to certificate"
$AWS iot attach-policy \
    --policy-name "$POLICY_NAME" \
    --target "$CERT_ARN"

echo "==> Attaching certificate to thing"
$AWS iot attach-thing-principal \
    --thing-name "$THING_NAME" \
    --principal "$CERT_ARN"

echo "==> Extracting LocalStack CA cert (for ssl_verify=true)..."
if openssl s_client -connect localhost:8883 -showcerts \
        </dev/null 2>/dev/null \
   | openssl x509 -outform pem > certs/ca.pem 2>/dev/null; then
    echo "    ca.pem saved"
else
    echo "    ca.pem not extracted (LocalStack TLS not yet active — set mqtt_ssl_verify=false)"
fi

echo "==> IoT endpoint:"
$AWS iot describe-endpoint --endpoint-type iot:Data-ATS \
    --query 'endpointAddress' --output text

echo ""
echo "Done."
echo "  Emulator  : plain TCP mqtt_port=1883  (no certs needed)"
echo "  LocalStack: SSL  mqtt_ssl_port=8883   mqtt_ssl_verify=false  (self-signed)"
echo "  Real AWS  : SSL  mqtt_ssl_port=8883   mqtt_ssl_verify=true   ca_cert=certs/AmazonRootCA1.pem"
