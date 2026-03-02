# SSL Certificates for Database Connection

## Production CA Certificate

The production compose file (`compose.production.yaml`) expects a CA certificate at:

```
backend/certs/prod-ca-2021.crt
```

This certificate is required when `DB_SSL_MODE=verify-full` to verify the
PostgreSQL server's identity.

## Setup Instructions

### For Supabase

1. Download the Supabase CA certificate from your Supabase project dashboard:
   - Go to **Settings → Database → Connection Info**
   - Download the **CA Certificate**

2. Save it as `prod-ca-2021.crt` in this directory:
   ```bash
   cp ~/Downloads/supabase-ca.crt backend/certs/prod-ca-2021.crt
   chmod 644 backend/certs/prod-ca-2021.crt
   ```

### For Other PostgreSQL Providers

1. Obtain the CA certificate from your database provider
2. Save it as `prod-ca-2021.crt` in this directory

### Generate a Self-Signed CA (Development/Testing Only)

```bash
openssl req -new -x509 -days 3650 -nodes \
  -out backend/certs/prod-ca-2021.crt \
  -keyout backend/certs/prod-ca.key \
  -subj "/CN=Floodingnaque Dev CA"
```

> **WARNING**: Self-signed certificates should NEVER be used in production.
> Always use your database provider's official CA certificate.

## Security Notes

- **Do NOT commit** the actual CA certificate to version control
- The `.gitignore` should exclude `*.crt` and `*.key` files (except `.gitkeep`)
- In CI/CD, provision the certificate via secrets or secure file transfer
- The certificate file should be readable by the container user (UID 1000)
