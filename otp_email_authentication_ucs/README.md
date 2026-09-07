# OTP & Email Authentication (`otp_email_authentication_ucs`)

Developed by **Uncanny Consulting Services LLP (UCS)** for **Odoo 17.0**.

---

## Overview

**OTP & Email Authentication** introduces secure, multi-factor Email OTP verification to the Odoo 17 login workflow. It ensures that after entering correct primary credentials (login & password), users with OTP enabled must enter a cryptographically generated 4, 6, or 8 digit One-Time Password sent to their registered email before gaining access to the Odoo backend or portal.

---

## Key Features

- **Multi-Factor Authentication (2FA)**: Adds an Email OTP challenge step after primary password validation.
- **Global & User-Level Controls**:
  - Global activation setting (`Settings -> General Settings -> OTP & Email Authentication`).
  - Per-user toggle (`Settings -> Users & Companies -> Users -> Require OTP & Email Authentication`).
  - Flexible activation rules: OTP is only required when both global OTP and user OTP are enabled.
- **Cryptographic Security**:
  - Generated using Python's `secrets` library (`secrets.choice('0123456789')`).
  - Stored securely in database using SHA-256 with per-challenge random salts. Plaintext OTPs are **never** stored or logged.
  - Constant-time string comparison (`secrets.compare_digest`) prevents timing attacks.
- **Rate Limiting & Brute-Force Protection**:
  - Expiration window (default: 1 minute).
  - Maximum verification attempts (default: 5 attempts).
  - Resend cooldown timer (default: 60 seconds).
  - Maximum resend attempts per session (default: 3 resends).
- **Responsive & Modern Verification Screen**:
  - Masked email preview (e.g. `al***e@uncannycs.com`).
  - Individual digit input boxes with auto-focus advance, backspace navigation, paste support, and numeric keyboard mode on mobile devices.
  - Live countdown timer for OTP resend capability.
- **Audit Logging & Cleanup**:
  - Security audit log model (`Settings -> Technical -> OTP & Email Authentication -> Authentication Logs`).
  - Scheduled daily cron action (`Clean Expired OTP & Email Authentication Records`) to clean up expired challenge records and log history.

---

## Activation Rule

| Global OTP Setting | User OTP Setting | Resulting Login Flow |
| :--- | :--- | :--- |
| **Disabled** | Disabled | Standard Login (Normal) |
| **Disabled** | Enabled | Standard Login (Normal) |
| **Enabled** | **Disabled** | Standard Login (Normal) |
| **Enabled** | **Enabled** | **OTP & Email Authentication Required** |

---

## Installation

1. Place `otp_email_authentication_ucs` into your Odoo 17 `custom/apps` or `addons` directory.
2. Restart Odoo server and update App List (`Settings -> Activate Developer Mode -> Update Apps List`).
3. Search for **OTP & Email Authentication** and click **Install**.

---

## Configuration

1. Navigate to **Settings -> General Settings -> OTP & Email Authentication**:
   - **Enable OTP & Email Authentication**: Check to activate globally.
   - **OTP Length**: Choose 4, 6, or 8 digits (Default: `6`).
   - **OTP Expiration**: Set validity window in minutes (Default: `1`).
   - **Resend Cooldown**: Set delay before requesting another code in seconds (Default: `60`).
   - **Maximum Verification Attempts**: Set failed attempt limit before challenge invalidation (Default: `5`).
   - **Maximum Resend Attempts**: Set maximum resends per challenge (Default: `3`).
2. Navigate to **Settings -> Users & Companies -> Users**:
   - Open a user record.
   - Enable **Require OTP & Email Authentication** under security settings.

---

## Technical Architecture

- **Odoo 17 MFA Hooks**: Implements `_mfa_type()`, `_mfa_url()`, and `_check_credentials()` on `res.users`.
- **Session Isolation**: Keeps session in partial state (`pre_uid`) until server-side verification succeeds. `request.session.finalize()` is executed only upon valid OTP submission.
- **CSRF Protection**: All POST endpoints (`/web/otp/verify` and `/web/otp/resend`) mandate valid Odoo CSRF tokens.

---

## Automated Tests

Run the test suite using Odoo CLI:

```bash
python3 odoo-bin -c /etc/odoo.conf -d test_db -i otp_email_authentication_ucs --test-enable --stop-after-init
```

Tests cover:
- `test_otp_generation.py`: Length, cryptographic randomness, SHA-256 salt hashing.
- `test_otp_verification.py`: Token verification, failed attempt counter, max attempt lockout.
- `test_otp_expiration.py`: Expiration boundary enforcement.
- `test_otp_login.py`: End-to-end authentication flow, missing email edge cases, resend cooldowns, and session finalization.

---

## Compatibility

- **Odoo Version**: 17.0 (Community & Enterprise)
- **License**: LGPL-3

---

## Author & Support

**Uncanny Consulting Services LLP (UCS)**  
Website: [https://www.uncannycs.com](https://www.uncannycs.com)
