# Webhook Delivery & Retry Policy Specification

## Endpoint Requirements
All webhook subscriber endpoints must return an HTTP 2xx status code (e.g., 200 OK, 201 Created) within 5,000 milliseconds (5.0s) of receiving the HTTP POST payload. Responses outside this range or timeouts are flagged as delivery failures.

## Automatic Retry Schedule
When an initial delivery attempt fails, OmniTriage AI engages an automated exponential backoff mechanism with 5 sequential retry attempts:
- Attempt 1: 5 seconds after initial failure
- Attempt 2: 30 seconds after attempt 1
- Attempt 3: 2 minutes (120s) after attempt 2
- Attempt 4: 15 minutes after attempt 3
- Attempt 5: 1 hour (3600s) after attempt 4

## Circuit Breaker & Endpoint Suspension
If all 5 automated retries fail, the webhook subscription endpoint is automatically disabled and placed into an INACTIVE state. An automated incident notification is dispatched to the organization's technical administrator email.

## Replay and Manual Resend
Administrators can inspect failed delivery payloads, verify headers, and trigger manual re-deliveries via Developer Settings > Webhooks > Dead Letter Queue.
