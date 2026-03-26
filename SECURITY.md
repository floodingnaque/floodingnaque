# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Currently supported versions:

| Version | Supported          |
| ------- | ------------------ |
| 2.x.x   | :white_check_mark: |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of the following methods:

### 1. Private Security Advisory (Preferred)

- Go to the [Security tab](https://github.com/floodingnaque/floodingnaque/security/advisories)
- Click "Report a vulnerability"
- Fill out the form with details

### 2. Email

Send details to: **security@floodingnaque.com**

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Every 5-7 days
- **Resolution**: Depends on severity
  - Critical: 1-7 days
  - High: 7-30 days
  - Medium/Low: 30-90 days

## Security Best Practices for Contributors

### API Keys and Secrets

- **NEVER** commit API keys, tokens, or secrets to the repository
- Use `.env.development` files for local development (already in `.gitignore`)
- Use `.env.example` with **placeholder values only**
- Rotate any accidentally exposed credentials immediately

### Environment Variables

Required secrets (store in `.env.development`, never commit):

- `WORLDTIDES_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GOOGLE_APPLICATION_CREDENTIALS` (path to service account JSON)
- `SECRET_KEY` (Flask/API secret)

### Dependencies

- Keep dependencies updated
- Run `pip audit` regularly to check for vulnerabilities
- Review security advisories from Dependabot

## Disclosure Policy

When we receive a security report:

1. We confirm the vulnerability
2. We develop and test a fix
3. We release the patch
4. We publicly disclose the vulnerability after the fix is deployed

## Security Features

This project implements:

- Rate limiting on API endpoints
- CORS protection
- Input validation and sanitization
- Secure password hashing (if applicable)
- API key authentication

## Questions?

For security-related questions that aren't vulnerabilities, open a discussion or contact iamdefinitely.ramil@gmail.com
