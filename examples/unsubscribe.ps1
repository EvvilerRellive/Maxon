# Unsubscribe bot from WebHook on Max API
# Usage: PowerShell unsubscribe.ps1
# Replace YOUR_WEBHOOK_URL and YOUR_TOKEN

$webhookUrl = "https://your.domain/updates"  # Same URL as subscribed
$token = $env:MAX_ACCESS_TOKEN  # Or pass token directly

if (-not $token) {
    Write-Host "Error: MAX_ACCESS_TOKEN not set."
    exit 1
}

# URL encode the webhook URL for query parameter
$encodedUrl = [System.Uri]::EscapeDataString($webhookUrl)

Write-Host "Unsubscribing from WebHook: $webhookUrl"

$response = Invoke-RestMethod `
    -Uri "https://platform-api.max.ru/subscriptions?access_token=$token&url=$encodedUrl" `
    -Method Delete

Write-Host "Response:"
$response | ConvertTo-Json
