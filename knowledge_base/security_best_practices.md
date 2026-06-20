# Security Best Practices Guide

## Account Security

### Password Best Practices
- Use unique passwords for AdSparkX (do not reuse passwords).
- Minimum 12 characters with mixed case, numbers, and symbols.
- Change passwords every 90 days.
- Use a password manager (e.g., 1Password, Bitwarden, LastPass).

### Two-Factor Authentication (2FA)
- Enable 2FA for all accounts (see Two-Factor Authentication guide).
- Prefer authenticator apps over SMS.
- Store backup codes in a secure offline location.

### API Key Security
- Never commit API keys to version control (git).
- Use environment variables for API keys.
- Rotate keys every 90 days.
- Use separate keys for development and production.
- Revoke unused keys immediately.

## Data Security

### Encryption
- Data in transit: TLS 1.3 (all API endpoints).
- Data at rest: AES-256 encryption.
- Database encryption: Transparent Data Encryption (TDE).

### Data Access
- Follow the principle of least privilege.
- Grant minimum permissions required for each role.
- Review access logs monthly.
- Remove access immediately when team members leave.

## Network Security

### IP Whitelisting
- Restrict API access to trusted IP ranges.
- Update IP whitelists when team locations change.
- Use VPN for remote access to the AdSparkX dashboard.

### Audit Logging
- All API requests are logged with timestamp, IP, and user ID.
- Logs are retained for 90 days.
- Download audit logs from Dashboard > Settings > Audit Log.

## Incident Response
If you suspect a security breach:
1. Immediately reset your password and revoke all API keys.
2. Contact security@adsparkx.ai with details.
3. The security team responds within 1 hour for critical incidents.
4. A full investigation is completed within 72 hours.
