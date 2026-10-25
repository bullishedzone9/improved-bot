# Messaging deployment foundation

## Current implementation
- `messaging/sms.py` provides an opt-in Twilio SMS sender.
- It sends only when explicitly called; it does not run a background loop or send unsolicited alerts.
- It never places broker orders and does not read or transmit broker credentials.
- Missing credentials, invalid E.164 phone numbers, empty/oversized messages, provider errors, and network failures fail closed.
- Provider acceptance is not proof of delivery.

## SMS setup (server-side only)
Configure these environment variables in the hosting provider's secret settings:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER` (E.164 sender number provisioned for the account)

Do not put these values in source code, Streamlit UI fields, GitHub commits, screenshots, or chat. Use a provider account and sender approved for the destination country; confirm current Nigeria route/sender-ID restrictions and pricing directly with the provider before enabling paid sends.

## Safe smoke test
1. Configure secrets only in a private deployment environment.
2. Use a number you own and have consented to receive a test.
3. Call `send_sms("+234…", "SILKOUS SMS setup test. No trade was placed.")` from a controlled test script.
4. Confirm provider status and handset receipt separately.
5. Do not connect market alerts until rate limits, user opt-in/opt-out, delivery logs without message secrets, and alert deduplication are implemented.

## Planned sequence
1. SMS provider foundation (this change).
2. Consent, unsubscribe/STOP handling, rate limits, and tests.
3. WhatsApp Business Cloud API integration.
4. In-app messaging and authenticated preferences.
5. Deploy and verify staging before production.

## Status
Code scaffold only. No credentials configured, SMS sent, provider connected, or deployment verified by this commit. Forex app remains paper-analysis only.
