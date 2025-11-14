# Subscribe bot to WebHook on Max API
# Usage: PowerShell subscribe.ps1
# Replace YOUR_WEBHOOK_URL and YOUR_TOKEN

$webhookUrl = "https://your.domain/updates"  # Your public HTTPS URL
$token = $env:MAX_ACCESS_TOKEN  # Or pass token directly: "your_token_here"
$secret = "my-webhook-secret-12345"  # Any secret string (optional but recommended)

if (-not $token) {
    Write-Host "Error: MAX_ACCESS_TOKEN not set. Set it or pass token directly."
    exit 1
}

$body = @{
    url = $webhookUrl
    update_types = @("message_created")
    secret = $secret
} | ConvertTo-Json

Write-Host "Subscribing to WebHook: $webhookUrl"
Write-Host "Body: $body"

$response = Invoke-RestMethod `
    -Uri "https://platform-api.max.ru/subscriptions?access_token=$token" `
    -Method Post `
    -Body $body `
    -ContentType 'application/json'

Write-Host "Response:"
$response | ConvertTo-Json -Depth 5
