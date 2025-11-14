#!/bin/bash
# Subscribe bot to WebHook on Max API (bash/curl version)
# Usage: bash subscribe.sh
# Replace YOUR_WEBHOOK_URL and YOUR_TOKEN before running

WEBHOOK_URL="https://your.domain/updates"  # Your public HTTPS URL
TOKEN="${MAX_ACCESS_TOKEN}"  # Or export MAX_ACCESS_TOKEN="token" first
SECRET="my-webhook-secret-12345"  # Any secret string

if [ -z "$TOKEN" ]; then
    echo "Error: MAX_ACCESS_TOKEN not set"
    exit 1
fi

echo "Subscribing to WebHook: $WEBHOOK_URL"

curl -X POST "https://platform-api.max.ru/subscriptions?access_token=$TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"$WEBHOOK_URL\",
    \"update_types\": [\"message_created\"],
    \"secret\": \"$SECRET\"
  }"

echo ""
echo "Done"
