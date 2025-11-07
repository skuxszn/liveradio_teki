# Security Best Practices Guide

**24/7 FFmpeg YouTube Radio Stream - Security Documentation**

This document outlines security best practices for deploying and operating the radio stream system.

## Table of Contents

1. [Authentication & Authorization](#authentication--authorization)
2. [Token Management](#token-management)
3. [Rate Limiting](#rate-limiting)
4. [License Compliance](#license-compliance)
5. [Network Security](#network-security)
6. [Docker Security](#docker-security)
7. [Secrets Management](#secrets-management)
8. [Monitoring & Auditing](#monitoring--auditing)
9. [Incident Response](#incident-response)
10. [Security Checklist](#security-checklist)

---

## Authentication & Authorization

### Webhook Authentication

The system validates incoming webhooks from AzuraCast using a shared secret.

#### Best Practices

1. **Generate Strong Secrets**
   ```bash
   # Generate 64-character webhook secret
   python scripts/generate_token.py --type webhook --length 64
   ```

2. **Configure AzuraCast Webhook**
   - In AzuraCast: Settings → Webhooks → Add Webhook
   - URL: `http://your-server:9000/webhook/azuracast`
   - Add Custom Header: `X-Webhook-Secret: <your-generated-secret>`
   - Triggers: "Song Change"

3. **Validate All Incoming Webhooks**
   ```python
   from security.auth import validate_webhook_secret
   from fastapi import Depends
   
   @app.post("/webhook/azuracast")
   async def webhook(
       payload: dict,
       authenticated: bool = Depends(validate_webhook_secret)
   ):
       # Process only if authenticated=True
       pass
   ```

4. **Use Constant-Time Comparison**
   - The system uses `secrets.compare_digest()` to prevent timing attacks
   - Never use `==` for secret comparison

### API Authentication

Manual control endpoints use Bearer token authentication.

#### Best Practices

1. **Generate Strong API Tokens**
   ```bash
   # Generate 64-character API token
   python scripts/generate_token.py --type api --length 64
   ```

2. **Protect All Management Endpoints**
   ```python
   from security.auth import require_api_token
   from fastapi import Depends
   
   @app.post("/manual/switch")
   async def manual_switch(
       track_id: str,
       authenticated: bool = Depends(require_api_token)
   ):
       # Only authenticated users can trigger manual switches
       pass
   ```

3. **Use HTTPS in Production**
   - Bearer tokens are sent in headers
   - Always use HTTPS to prevent token interception
   - Set up reverse proxy (nginx) with SSL/TLS

4. **Client Authentication Example**
   ```bash
   # Correct way to call API
   curl -H "Authorization: Bearer your-api-token-here" \
        -X POST http://localhost:9000/manual/switch \
        -d '{"track_id": "track_123"}'
   ```

---

## Token Management

### Token Generation

**NEVER** use predictable or weak tokens.

#### ✅ Good
```bash
# Use the provided script
python scripts/generate_token.py --both

# Or generate manually with strong randomness
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

#### ❌ Bad
```bash
# DO NOT use weak tokens
WEBHOOK_SECRET=password123
API_TOKEN=12345678901234567890123456789012
```

### Token Storage

1. **Environment Variables** (Recommended for production)
   ```bash
   # In .env file (never commit this file!)
   WEBHOOK_SECRET=<generated-secret>
   API_TOKEN=<generated-token>
   ```

2. **Docker Secrets** (Best for orchestration)
   ```yaml
   # docker-compose.yml
   services:
     metadata-watcher:
       secrets:
         - webhook_secret
         - api_token
   
   secrets:
     webhook_secret:
       file: ./secrets/webhook_secret.txt
     api_token:
       file: ./secrets/api_token.txt
   ```

3. **AWS Secrets Manager / HashiCorp Vault** (Enterprise)
   - Use for distributed deployments
   - Automatic rotation support
   - Audit logging built-in

### Token Rotation

Rotate tokens regularly to limit exposure window.

**Recommended Schedule**:
- Development: Every 180 days
- Production: Every 90 days
- After security incident: Immediately

**Rotation Process**:
1. Generate new tokens
   ```bash
   python scripts/generate_token.py --both
   ```

2. Update `.env` file with new tokens

3. Update AzuraCast webhook configuration

4. Restart services
   ```bash
   docker-compose restart metadata-watcher
   ```

5. Test webhooks and API endpoints

6. Invalidate old tokens (remove from backup configs)

---

## Rate Limiting

Prevent abuse and DoS attacks with rate limiting.

### Configuration

```bash
# In .env
WEBHOOK_RATE_LIMIT=10        # Max 10 webhook requests per minute
API_RATE_LIMIT=60            # Max 60 API requests per minute
ENABLE_RATE_LIMITING=true
```

### Best Practices

1. **Set Appropriate Limits**
   - Webhook: 10-20 requests/minute (tracks change ~3-5 times/min typically)
   - API: 60-100 requests/minute (manual control is infrequent)

2. **Monitor Rate Limit Violations**
   ```python
   from security.rate_limiter import RateLimitExceeded
   
   try:
       limiter.check_rate_limit(request)
   except RateLimitExceeded as e:
       logger.warning(
           "rate_limit_exceeded",
           ip=request.client.host,
           endpoint=request.url.path,
           retry_after=e.headers.get('Retry-After')
       )
       raise
   ```

3. **Handle Proxy Headers**
   - The rate limiter automatically checks `X-Forwarded-For`
   - Ensure your reverse proxy sets this header correctly

4. **Bypass for Trusted IPs** (Optional)
   ```python
   TRUSTED_IPS = ["10.0.0.1", "192.168.1.100"]
   
   if request.client.host in TRUSTED_IPS:
       # Skip rate limiting
       pass
   else:
       limiter.check_rate_limit(request)
   ```

5. **Use Redis for Distributed Systems**
   - Current implementation is in-memory (single instance)
   - For multi-instance deployments, use Redis backend

### Dealing with Rate Limit Attacks

If you detect abuse:

1. **Identify the attacker**
   ```bash
   # Check logs for repeated 429 errors
   grep "rate_limit_exceeded" /var/log/radio/app.log | \
     jq -r '.ip' | sort | uniq -c | sort -rn
   ```

2. **Block at firewall level**
   ```bash
   # Using iptables
   sudo iptables -A INPUT -s <attacker-ip> -j DROP
   
   # Using fail2ban (recommended)
   # Add custom filter for rate limit violations
   ```

3. **Temporarily disable public access**
   ```bash
   # Whitelist only AzuraCast IP
   WEBHOOK_WHITELIST=10.0.0.5
   ```

---

## License Compliance

Ensure all played music has proper licensing.

### Setup

1. **Create License Manifest**
   ```bash
   python scripts/validate_licenses.py
   # Creates empty manifest at /srv/config/license_manifest.json
   ```

2. **Add Track Licenses**
   ```python
   from security.license_manager import LicenseManager, TrackLicense
   
   manager = LicenseManager("/srv/config/license_manifest.json")
   
   license_info = TrackLicense(
       id="track_123",
       artist="Artist Name",
       title="Song Title",
       license="Creative Commons BY 4.0",
       license_url="https://creativecommons.org/licenses/by/4.0/",
       acquired_date="2025-01-15",
       notes="Licensed from artist website"
   )
   
   manager.add_license(license_info)
   manager.save_manifest()
   ```

### Best Practices

1. **Validate Before Adding to Rotation**
   - Never add tracks without license verification
   - Keep copies of license agreements
   - Document source URLs

2. **Common License Types**
   - **Creative Commons BY**: Attribution required (artist/title in description)
   - **Creative Commons BY-SA**: Attribution + ShareAlike
   - **Public Domain**: No restrictions (CC0, expired copyright)
   - **Royalty-Free**: Licensed for commercial use (keep receipt)
   - **Custom License**: Direct artist permission (get written agreement)

3. **Monthly Compliance Reports**
   ```bash
   # Generate compliance report
   python scripts/validate_licenses.py --check-played
   
   # Export for auditing
   python scripts/validate_licenses.py --export monthly_report.csv
   ```

4. **Handle Unlicensed Tracks**
   ```python
   if not license_manager.validate_track(track_id, artist, title):
       # Log warning
       logger.warning(f"Unlicensed track: {track_id}")
       
       # Optional: Skip playback
       return get_default_loop()
   ```

5. **YouTube Compliance**
   - Add license information to stream description
   - Use YouTube's "Show more" for full attribution
   - Update description monthly with current tracks

### License Audit Process

**Quarterly Audit**:
1. Generate compliance report
2. Review unlicensed tracks
3. Contact artists for missing licenses
4. Remove tracks without licenses
5. Update manifest
6. Export report for records

**Example Audit Script**:
```bash
#!/bin/bash
# quarterly_license_audit.sh

echo "Generating compliance report..."
python scripts/validate_licenses.py --check-played > audit_report.txt

echo "Exporting licenses..."
python scripts/validate_licenses.py --export licenses_$(date +%Y%m%d).csv

echo "Checking for unlicensed tracks..."
python -c "
from security.license_manager import LicenseManager
manager = LicenseManager('/srv/config/license_manifest.json')
# Get played tracks from DB
played = get_played_tracks()  # Implement this
unlicensed = manager.get_unlicensed_tracks(played)
if unlicensed:
    print(f'WARNING: {len(unlicensed)} unlicensed tracks')
    for track_id in unlicensed[:10]:
        print(f'  - {track_id}')
"
```

---

## Network Security

### Firewall Configuration

Only expose necessary ports:

```bash
# UFW (Ubuntu)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp      # SSH (restrict to your IP if possible)
sudo ufw allow 9000/tcp    # Metadata Watcher (or use reverse proxy)
sudo ufw allow 1935/tcp    # RTMP (local only if using nginx-rtmp relay)
sudo ufw enable

# Restrict to specific IPs
sudo ufw allow from 10.0.0.5 to any port 9000  # AzuraCast only
```

### Reverse Proxy with SSL/TLS

**Recommended**: Use nginx as reverse proxy with Let's Encrypt SSL.

```nginx
# /etc/nginx/sites-available/radio-stream
server {
    listen 443 ssl http2;
    server_name stream.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/stream.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/stream.yourdomain.com/privkey.pem;

    # Strong SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    location /webhook/azuracast {
        proxy_pass http://localhost:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Rate limiting at nginx level
        limit_req zone=webhook burst=5 nodelay;
    }

    location /manual/ {
        proxy_pass http://localhost:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Require client certificate for extra security (optional)
        # ssl_client_certificate /etc/nginx/client_certs/ca.crt;
        # ssl_verify_client on;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name stream.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### Network Isolation

**Docker Network Isolation**:

```yaml
# docker-compose.yml
services:
  nginx-rtmp:
    networks:
      - internal
      - external  # Only RTMP needs external access
  
  metadata-watcher:
    networks:
      - internal
      - webhook_net  # Separate network for webhooks
  
  postgres:
    networks:
      - internal  # Database should be internal only

networks:
  internal:
    internal: true  # No internet access
  external:
    driver: bridge
  webhook_net:
    driver: bridge
```

---

## Docker Security

### Run as Non-Root User

**CRITICAL**: Never run containers as root.

```dockerfile
# In Dockerfile
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r radio && useradd -r -g radio radio

# Set up application
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY --chown=radio:radio . .

# Switch to non-root user
USER radio

CMD ["python", "app.py"]
```

### Read-Only Filesystem

Make filesystem read-only where possible:

```yaml
# docker-compose.yml
services:
  metadata-watcher:
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
    volumes:
      - ./logs:/var/log/radio:rw  # Only logs need write access
```

### Resource Limits

Prevent resource exhaustion:

```yaml
# docker-compose.yml
services:
  metadata-watcher:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          memory: 256M
```

### Security Scanning

Scan Docker images regularly:

```bash
# Using Docker Scout
docker scout cves radio-stream-watcher:latest

# Using Trivy
trivy image radio-stream-watcher:latest

# Using Snyk
snyk container test radio-stream-watcher:latest
```

### Keep Images Updated

```bash
# Update base images weekly
docker pull python:3.11-slim
docker-compose build --no-cache
docker-compose up -d

# Check for security updates
docker run --rm -it python:3.11-slim apt-get update && apt-get upgrade --dry-run
```

---

## Secrets Management

### Never Commit Secrets

**Add to `.gitignore`**:
```
.env
.env.local
.env.production
secrets/
*.key
*.pem
config/license_manifest.json
```

### Environment-Specific Secrets

```bash
# Directory structure
secrets/
  ├── dev/
  │   ├── webhook_secret.txt
  │   └── api_token.txt
  ├── staging/
  │   ├── webhook_secret.txt
  │   └── api_token.txt
  └── production/
      ├── webhook_secret.txt
      └── api_token.txt

# Load based on environment
export ENV=production
docker-compose --env-file secrets/$ENV/.env up -d
```

### Encrypt Secrets at Rest

```bash
# Using gpg
gpg --symmetric --cipher-algo AES256 .env
# Creates .env.gpg (commit this, not .env)

# Decrypt on deployment
gpg --decrypt .env.gpg > .env
```

### Secrets Rotation Automation

```bash
#!/bin/bash
# rotate_secrets.sh

# Generate new tokens
NEW_WEBHOOK=$(python scripts/generate_token.py --type webhook --quiet)
NEW_API=$(python scripts/generate_token.py --type api --quiet)

# Update .env
sed -i "s/WEBHOOK_SECRET=.*/WEBHOOK_SECRET=$NEW_WEBHOOK/" .env
sed -i "s/API_TOKEN=.*/API_TOKEN=$NEW_API/" .env

# Restart services
docker-compose restart

# Update AzuraCast (manual step - notify admin)
echo "IMPORTANT: Update AzuraCast webhook with new secret:"
echo "  $NEW_WEBHOOK"
```

---

## Monitoring & Auditing

### Security Event Logging

Log all security-relevant events:

```python
# Log authentication failures
logger.warning(
    "auth_failed",
    event_type="webhook_auth_failure",
    ip=request.client.host,
    user_agent=request.headers.get("User-Agent"),
    endpoint=request.url.path
)

# Log successful authentications (for audit trail)
logger.info(
    "auth_success",
    event_type="webhook_auth_success",
    ip=request.client.host,
    endpoint=request.url.path
)

# Log rate limit violations
logger.warning(
    "rate_limit_exceeded",
    ip=request.client.host,
    endpoint=request.url.path,
    limit=config.webhook_rate_limit
)
```

### Prometheus Metrics

Monitor security metrics:

```python
from prometheus_client import Counter, Histogram

# Define metrics
auth_failures = Counter(
    'security_auth_failures_total',
    'Total authentication failures',
    ['endpoint', 'reason']
)

rate_limit_violations = Counter(
    'security_rate_limit_violations_total',
    'Total rate limit violations',
    ['endpoint', 'ip']
)

# Use in code
try:
    validate_webhook_secret(secret)
except WebhookAuthError:
    auth_failures.labels(endpoint='webhook', reason='invalid_secret').inc()
```

### Alerting Rules

**Prometheus Alert Rules** (`/etc/prometheus/rules/security.yml`):

```yaml
groups:
  - name: security_alerts
    rules:
      - alert: HighAuthFailureRate
        expr: rate(security_auth_failures_total[5m]) > 5
        for: 5m
        annotations:
          summary: "High authentication failure rate detected"
          description: "More than 5 auth failures per minute for 5 minutes"

      - alert: RateLimitAttack
        expr: rate(security_rate_limit_violations_total[1m]) > 10
        for: 2m
        annotations:
          summary: "Possible DoS attack detected"
          description: "High rate of rate limit violations"
```

### Log Analysis

**Daily Security Report**:

```bash
#!/bin/bash
# daily_security_report.sh

echo "=== Daily Security Report $(date) ==="

echo -e "\n--- Authentication Failures ---"
grep "auth_failed" /var/log/radio/app.log | tail -20

echo -e "\n--- Rate Limit Violations ---"
grep "rate_limit_exceeded" /var/log/radio/app.log | tail -20

echo -e "\n--- Top Failed IPs ---"
grep "auth_failed" /var/log/radio/app.log | \
  jq -r '.ip' | sort | uniq -c | sort -rn | head -10

echo -e "\n--- License Compliance ---"
python scripts/validate_licenses.py --check-played
```

---

## Incident Response

### Suspected Compromise

If you suspect a security breach:

1. **Immediate Actions**
   ```bash
   # Stop all services
   docker-compose down
   
   # Rotate all tokens immediately
   python scripts/generate_token.py --both
   
   # Block suspicious IPs
   sudo ufw deny from <suspicious-ip>
   ```

2. **Investigation**
   ```bash
   # Check logs for unusual activity
   grep -i "error\|failed\|denied" /var/log/radio/app.log
   
   # Check for unauthorized API calls
   grep "manual" /var/log/radio/app.log | grep -v "authenticated"
   
   # Review recent Docker logs
   docker-compose logs --since 24h
   ```

3. **Recovery**
   - Generate new tokens
   - Update all configurations
   - Review and update firewall rules
   - Scan for malware
   - Restore from known-good backup if needed

4. **Post-Incident**
   - Document the incident
   - Update security procedures
   - Implement additional monitoring
   - Notify stakeholders if data was accessed

### Backup & Recovery

**Regular Backups**:

```bash
#!/bin/bash
# backup_security.sh

BACKUP_DIR=/backup/security/$(date +%Y%m%d)
mkdir -p $BACKUP_DIR

# Backup license manifest
cp /srv/config/license_manifest.json $BACKUP_DIR/

# Backup logs (encrypted)
tar czf - /var/log/radio/ | gpg --symmetric --cipher-algo AES256 > $BACKUP_DIR/logs.tar.gz.gpg

# Backup database (if contains security data)
docker-compose exec postgres pg_dump -U radio radio_db | gzip > $BACKUP_DIR/database.sql.gz

# Rotate old backups (keep 30 days)
find /backup/security/ -type d -mtime +30 -exec rm -rf {} +
```

---

## Security Checklist

Use this checklist for deployments and audits:

### Pre-Deployment

- [ ] All tokens generated using `generate_token.py`
- [ ] `.env` file not committed to git
- [ ] `.gitignore` includes `.env` and `secrets/`
- [ ] Webhook secret configured in AzuraCast
- [ ] Rate limits set appropriately
- [ ] SSL/TLS configured (if using HTTPS)
- [ ] Firewall rules configured
- [ ] Docker containers run as non-root
- [ ] Resource limits set on containers

### Post-Deployment

- [ ] Webhook authentication tested
- [ ] API authentication tested
- [ ] Rate limiting verified (test with high request volume)
- [ ] HTTPS redirect working (if applicable)
- [ ] License manifest created and validated
- [ ] Logs being written correctly
- [ ] Prometheus metrics exposed
- [ ] Alerts configured and tested
- [ ] Backup script scheduled
- [ ] Security report automation working

### Monthly Maintenance

- [ ] Review authentication failure logs
- [ ] Review rate limit violation logs
- [ ] Generate license compliance report
- [ ] Update base Docker images
- [ ] Security scan Docker images
- [ ] Review and update firewall rules
- [ ] Test backup restoration
- [ ] Review and update documentation

### Quarterly Audit

- [ ] Rotate all tokens
- [ ] Full license audit
- [ ] Review access logs
- [ ] Update dependencies
- [ ] Security vulnerability scan
- [ ] Penetration testing (if applicable)
- [ ] Review incident response plan
- [ ] Update security documentation

---

## Additional Resources

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **Docker Security Best Practices**: https://docs.docker.com/engine/security/
- **Python Security Guide**: https://python.readthedocs.io/en/stable/library/security_warnings.html
- **FastAPI Security**: https://fastapi.tiangolo.com/tutorial/security/

---

**Document Version**: 1.0  
**Last Updated**: November 5, 2025  
**Maintained By**: Security Module (SHARD-10)  
**Review Schedule**: Quarterly



