# Quick Deploy Guide - Dynamic Configuration

## TL;DR

Run this one command to deploy everything:

```bash
./deploy_dynamic_config.sh
```

That's it! The script handles everything automatically.

---

## What It Does

1. ✅ Backs up your `.env` file
2. ✅ Starts dashboard-api and PostgreSQL
3. ✅ Runs database migration (adds 40+ settings)
4. ✅ Rebuilds nginx-rtmp with dynamic config
5. ✅ Restarts all affected services
6. ✅ Verifies everything is working

---

## Prerequisites

Before running the script, ensure:

- [ ] Docker and docker-compose installed
- [ ] `.env` file exists with required variables:
  - `API_TOKEN` - Set to a secure random token
  - `POSTGRES_PASSWORD` - Your database password
  - `YOUTUBE_STREAM_KEY` - Your YouTube stream key (will be migrated to DB)
- [ ] Dashboard is set up and working

---

## Step-by-Step Deployment

### 1. Make Script Executable (if needed)

```bash
chmod +x deploy_dynamic_config.sh
```

### 2. Run Deployment Script

```bash
./deploy_dynamic_config.sh
```

Watch for colored output:
- 🟢 Green ✅ = Success
- 🟡 Yellow ⚠️ = Warning (usually OK)
- 🔴 Red ❌ = Error (needs attention)

### 3. Verify Deployment

After script completes, check:

```bash
# All services running?
docker-compose ps

# nginx-rtmp fetching config?
docker logs radio_nginx_rtmp | grep "config"

# Expected: "Starting nginx push manager"
# Expected: "Successfully fetched configuration"

# metadata-watcher fetching config?
docker logs radio_metadata_watcher | grep "config"

# Expected: "[metadata-watcher] Successfully fetched configuration"
```

### 4. Test Configuration Changes

1. Login to dashboard: http://localhost:3001
2. Go to **Settings** → **Encoding**
3. Change `VIDEO_RESOLUTION` from `1280:720` to `1920:1080`
4. Click **Save**
5. Wait 60 seconds
6. Check logs:

```bash
docker logs radio_metadata_watcher --tail 20
# Should show: "Configuration changed" or similar
```

---

## Manual Deployment (If Script Fails)

If the automated script fails, deploy manually:

### Step 1: Database Migration

```bash
# Start dashboard
docker-compose up -d dashboard-api postgres

# Run migration
docker exec radio_dashboard_api python3 /app/migrations/add_missing_settings.py
```

### Step 2: Rebuild nginx-rtmp

```bash
# Build new image
docker-compose build nginx-rtmp

# Stop old container
docker-compose stop nginx-rtmp

# Start new container
docker-compose up -d nginx-rtmp
```

### Step 3: Restart metadata-watcher

```bash
docker-compose restart metadata-watcher
```

---

## Verification Commands

### Check Service Status
```bash
docker-compose ps
```

### Check nginx-rtmp Config Updater
```bash
docker logs radio_nginx_rtmp --tail 30 | grep -i "config"
```

### Check metadata-watcher Config Client
```bash
docker logs radio_metadata_watcher --tail 30 | grep -i "config"
```

### Check Database Settings
```bash
docker exec radio_postgres psql -U radio -d radio_db -c \
  "SELECT category, COUNT(*) FROM dashboard_settings GROUP BY category ORDER BY category;"
```

### Check Current Stream Key
```bash
docker exec radio_nginx_rtmp grep "rtmp://a.rtmp.youtube.com" /usr/local/nginx/conf/nginx.conf
```

### Check Stream Activity
```bash
curl -s http://localhost:8080/stat | grep -A10 "<stream>"
```

---

## Common Issues & Fixes

### Issue: Script says "dashboard-api failed to start"

**Fix:**
```bash
# Check logs
docker-compose logs dashboard-api

# Usually database not ready - wait and retry
sleep 10
docker-compose up -d dashboard-api
```

### Issue: Database migration fails

**Fix:**
```bash
# Check if database is accessible
docker exec radio_postgres psql -U radio -d radio_db -c "SELECT 1;"

# If fails, check PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Issue: nginx-rtmp not fetching config

**Check:**
```bash
# Verify DASHBOARD_API_URL is set
docker exec radio_nginx_rtmp env | grep DASHBOARD

# Verify API_TOKEN is set
docker exec radio_nginx_rtmp env | grep API_TOKEN

# Check if dashboard is reachable
docker exec radio_nginx_rtmp curl -I http://dashboard-api:9001/health
```

### Issue: Config changes not applying

**Check:**
```bash
# 1. Wait at least 60 seconds
sleep 60

# 2. Check auto-refresh logs
docker logs radio_nginx_rtmp --tail 50 | grep "config"

# 3. Manually trigger fetch (for testing)
docker exec radio_nginx_rtmp python3 /app/push_manager.py &
```

---

## Rollback

If something goes wrong:

### Quick Rollback
```bash
# Restart with old containers
docker-compose restart nginx-rtmp metadata-watcher
```

### Full Rollback
```bash
# Stop everything
docker-compose down

# Restore backup
cp .env.backup.* .env

# Restore docker-compose
git checkout docker-compose.yml

# Restore nginx-rtmp
cd nginx-rtmp
git checkout Dockerfile nginx.conf
rm -f push_manager.py requirements.txt nginx.conf.template start.sh
cd ..

# Restart
docker-compose up -d --build
```

---

## Post-Deployment

### Update Team
- [ ] Notify team of new configuration workflow
- [ ] Share dashboard URL: http://localhost:3001
- [ ] Explain: "Change settings via UI, no restarts needed!"

### Documentation
- [ ] Read `CONFIGURATION.md` for full guide
- [ ] Bookmark dashboard settings page
- [ ] Note: Changes apply within 60 seconds

### Monitoring
- [ ] Watch logs for config fetch errors
- [ ] Verify stream still working on YouTube
- [ ] Test changing different settings

---

## Success!

If you see:
- ✅ All services running (`docker-compose ps`)
- ✅ Logs show "Successfully fetched configuration"
- ✅ Dashboard shows all settings
- ✅ Stream working on YouTube

**You're done! 🎉**

Settings now update automatically via dashboard UI!

---

## Quick Reference

| Action | Command |
|--------|---------|
| Deploy everything | `./deploy_dynamic_config.sh` |
| Check all services | `docker-compose ps` |
| View nginx-rtmp logs | `docker logs radio_nginx_rtmp -f` |
| View metadata logs | `docker logs radio_metadata_watcher -f` |
| Access dashboard | http://localhost:3001 |
| Run migration again | `docker exec radio_dashboard_api python3 /app/migrations/add_missing_settings.py` |
| Restart everything | `docker-compose restart` |

---

## Help

- 📖 Full guide: `CONFIGURATION.md`
- 🔧 Troubleshooting: `DYNAMIC_CONFIG_MIGRATION_SUMMARY.md`
- 📋 File changes: `MIGRATION_FILES_SUMMARY.md`
- 🎯 Original plan: `MIGRATE_TO_DYNAMIC_CONFIG.md`


