# TA - Deployment Guide for Windows with Docker

This guide provides step-by-step instructions for deploying the TA (Trade Analyst) application on a new Windows machine using Docker Compose.

## Overview

The deployment uses Docker Compose to orchestrate all services in a single stack:

### Services Included:
1. **MongoDB** (ta_mongodb) - Database server on port 7587
2. **Redis** (ta_redis) - Cache and message broker on port 6379
3. **Django Web** (ta_web) - Web application on port 8000
4. **Celery Worker** (ta_celery_worker) - Background task processor
5. **Celery Beat** (ta_celery_beat) - Scheduled task manager

All services are defined in `docker-compose.yml` and will be created automatically.

## What's Included in GitHub

### ✅ In Repository:
- Application source code (Django, Celery, agents, scrapers)
- `Dockerfile` - Container build instructions
- `docker-compose.yml` - Complete service orchestration (MongoDB, Redis, Web, Celery)
- `requirements.txt` - Python dependencies
- `env_template.txt` - Environment variable template
- Templates, static files, migrations

### ❌ NOT in Repository (Transfer via USB):
- `.env` file with your actual API keys and secrets
- `mongodb_backup.archive` - Your database backup
- Any custom configuration files

## Prerequisites

### Required Software on New Windows Machine:

1. **Docker Desktop for Windows**
   - Download: https://www.docker.com/products/docker-desktop
   - Install with WSL 2 backend enabled
   - Verify after installation:
     ```powershell
     docker --version
     docker-compose --version
     ```

2. **Git for Windows**
   - Download: https://git-scm.com/download/win
   - Verify: `git --version`

3. **MongoDB Database Tools** (for restoring backup)
   - Download: https://www.mongodb.com/try/download/database-tools
   - Extract to a folder (e.g., `C:\mongodb-tools`)
   - Add to PATH or use full path to `mongorestore.exe`

### USB Flash Drive Contents:

Prepare a USB drive with these files from your development machine:

1. **`.env`** - Your environment configuration with API keys
2. **`mongodb_backup.archive`** - Your MongoDB database backup

To create the backup on your development machine:
```powershell
# Navigate to your project directory
cd C:\Users\DELL\Desktop\TA

# Create MongoDB backup
mongodump --host=localhost --port=7587 --db=analyst --archive=mongodb_backup.archive

# Copy .env and backup to USB
Copy-Item .env E:\deployment\
Copy-Item mongodb_backup.archive E:\deployment\
```
(Replace `E:\` with your USB drive letter)

## Quick Start - Complete Deployment

On the new Windows machine with Docker Desktop and Git installed:

```powershell
# 1. Clone repository
git clone https://github.com/yourusername/TA.git
cd TA

# 2. Copy .env from USB drive
Copy-Item E:\deployment\.env .env

# 3. Build and start all services (MongoDB, Redis, Web, Celery)
docker-compose up -d

# 4. Wait for services to be healthy (about 60 seconds)
docker-compose ps

# 5. Restore database from USB backup
docker exec -i ta_mongodb mongorestore --archive < E:\deployment\mongodb_backup.archive

# 6. Run Django setup
docker exec ta_web python manage.py migrate
docker exec -it ta_web python manage.py createsuperuser
docker exec ta_web python manage.py collectstatic --noinput
docker exec ta_web python manage.py compilemessages

# 7. Access application at http://localhost:8000
```

That's it! All services (MongoDB, Redis, Django, Celery) are now running.

## Detailed Step-by-Step Guide

### Step 1: Prepare on Development Machine

Before going to the new machine, prepare your USB drive:

```powershell
# On your development machine
cd C:\Users\DELL\Desktop\TA

# Create MongoDB backup
mongodump --host=localhost --port=7587 --db=analyst --archive=mongodb_backup.archive

# Create deployment folder on USB (replace E: with your USB drive)
New-Item -Path "E:\deployment" -ItemType Directory -Force

# Copy files to USB
Copy-Item .env E:\deployment\.env
Copy-Item mongodb_backup.archive E:\deployment\mongodb_backup.archive
```

### Step 2: Install Prerequisites on New Machine

On the new Windows machine:

1. **Install Docker Desktop:**
   - Download and install from https://www.docker.com/products/docker-desktop
   - Enable WSL 2 backend during installation
   - Restart computer if prompted
   - Verify installation:
     ```powershell
     docker --version
     docker-compose --version
     ```

2. **Install Git:**
   - Download from https://git-scm.com/download/win
   - Use default settings during installation
   - Verify: `git --version`

### Step 3: Clone Repository

```powershell
# Navigate to desired location
cd C:\Users\YourUsername\Projects

# Clone the repository (replace with your GitHub URL)
git clone https://github.com/yourusername/TA.git

# Navigate into project
cd TA
```

### Step 4: Transfer Files from USB

```powershell
# Copy .env from USB to project root (replace E: with your USB drive)
Copy-Item E:\deployment\.env .env

# Verify .env exists
Test-Path .env
# Should return: True
```

### Step 5: Start All Services with Docker Compose

```powershell
# Build and start all containers (MongoDB, Redis, Web, Celery Worker, Celery Beat)
docker-compose up -d --build

# This will:
# 1. Pull MongoDB and Redis images
# 2. Build the Django application image
# 3. Create all 5 containers
# 4. Start them with proper dependencies
```

### Step 6: Wait for Services to be Healthy

```powershell
# Check status (wait until all show "healthy" or "running")
docker-compose ps

# Watch logs to see startup progress
docker-compose logs -f

# Press Ctrl+C to stop watching logs
```

Expected output after ~60 seconds:
```
NAME               STATUS
ta_mongodb         Up (healthy)
ta_redis           Up (healthy)
ta_web             Up (healthy)
ta_celery_worker   Up
ta_celery_beat     Up
```

### Step 7: Restore Database from USB Backup

```powershell
# Restore MongoDB backup into the running container
# Method 1: Using docker exec with input redirection
Get-Content E:\deployment\mongodb_backup.archive | docker exec -i ta_mongodb mongorestore --archive

# Method 2: Copy file into container first, then restore
docker cp E:\deployment\mongodb_backup.archive ta_mongodb:/tmp/backup.archive
docker exec ta_mongodb mongorestore --archive=/tmp/backup.archive

# Verify restoration
docker exec ta_mongodb mongosh --eval "use analyst; db.articles.countDocuments()"
```

### Step 8: Initialize Django Application

```powershell
# Run database migrations
docker exec ta_web python manage.py migrate

# Create superuser account (interactive)
docker exec -it ta_web python manage.py createsuperuser
# Follow prompts to create admin user

# Collect static files
docker exec ta_web python manage.py collectstatic --noinput

# Compile translation messages
docker exec ta_web python manage.py compilemessages
```

### Step 9: Verify the Deployment

1. **Access the application:**
   - Open your browser and navigate to: http://localhost:8000
   - Login with your superuser credentials

2. **Check the admin panel:**
   - Navigate to: http://localhost:8000/admin

3. **Verify Celery is working:**
   ```powershell
   # Check Celery worker logs
   docker logs ta_celery_worker

   # Check Celery beat logs
   docker logs ta_celery_beat
   ```

4. **Test MongoDB connection:**
   - Navigate to: http://localhost:8000/articles/
   - You should see your restored articles

### Step 10: Configure Scheduled Tasks (Optional)

The application uses Celery Beat for scheduled tasks. To configure:

1. **Access Django admin:**
   - Go to: http://localhost:8000/admin
   - Navigate to "Periodic Tasks" under "Django Celery Beat"

2. **Configure tasks:**
   - **Article Translation**: Runs every 60 seconds
   - **Embedding Generation**: Runs every 60 seconds
   - **Weekly Summary**: Configure as needed

## Troubleshooting

### All Services Not Starting

If `docker-compose up -d` fails:

1. **Check Docker Desktop is running:**
   - Look for Docker icon in system tray
   - Should show "Docker Desktop is running"

2. **View error logs:**
   ```powershell
   docker-compose logs
   ```

3. **Check for port conflicts:**
   ```powershell
   # Check if ports 7587, 6379, or 8000 are in use
   netstat -ano | findstr "7587 6379 8000"
   ```

### MongoDB Connection Issues

1. **Check MongoDB container is healthy:**
   ```powershell
   docker-compose ps mongodb
   # Should show "Up (healthy)"
   ```

2. **View MongoDB logs:**
   ```powershell
   docker-compose logs mongodb
   ```

3. **Test MongoDB connection from host:**
   ```powershell
   docker exec ta_mongodb mongosh --eval "db.adminCommand('ping')"
   ```

4. **Test MongoDB connection from web container:**
   ```powershell
   docker exec ta_web python -c "from pymongo import MongoClient; client = MongoClient('mongodb://mongodb:27017/'); print(client.admin.command('ping'))"
   ```

### Redis Connection Issues

1. **Check Redis container is healthy:**
   ```powershell
   docker-compose ps redis
   ```

2. **Test Redis connection:**
   ```powershell
   docker exec ta_redis redis-cli ping
   # Should return: PONG
   ```

3. **Test from web container:**
   ```powershell
   docker exec ta_web python -c "import redis; r = redis.from_url('redis://redis:6379/0'); print(r.ping())"
   ```

### Database Restore Issues

If mongorestore fails:

1. **Verify backup file exists:**
   ```powershell
   Test-Path E:\deployment\mongodb_backup.archive
   ```

2. **Try alternative restore method:**
   ```powershell
   # Copy file into container
   docker cp E:\deployment\mongodb_backup.archive ta_mongodb:/tmp/backup.archive
   
   # Restore from inside container
   docker exec ta_mongodb mongorestore --archive=/tmp/backup.archive --verbose
   ```

3. **Check MongoDB logs during restore:**
   ```powershell
   docker logs -f ta_mongodb
   ```

### Container Logs

View logs for debugging:

```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f celery_worker
docker-compose logs -f celery_beat
```

### Port Conflicts

If ports are already in use:

1. **Check what's using the port:**
   ```powershell
   netstat -ano | findstr :8000
   ```

2. **Change ports in docker-compose.yml:**
   ```yaml
   ports:
     - "8080:8000"  # Change 8000 to 8080
   ```

## Maintenance

### Backup MongoDB

Create regular backups from the running container:

```powershell
# Create backup with timestamp
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
docker exec ta_mongodb mongodump --db=analyst --archive > "mongodb_backup_$timestamp.archive"

# Or with compression
docker exec ta_mongodb mongodump --db=analyst --archive --gzip > "mongodb_backup_$timestamp.archive.gz"

# Backup to specific location
docker exec ta_mongodb mongodump --db=analyst --archive > "C:\Backups\mongodb_backup_$timestamp.archive"
```

### Update the Application

```powershell
# Pull latest changes
git pull origin main

# Rebuild containers
docker-compose down
docker-compose build
docker-compose up -d

# Run migrations
docker exec ta_web python manage.py migrate

# Collect static files
docker exec ta_web python manage.py collectstatic --noinput
```

### View Application Logs

```powershell
# Real-time logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Specific service
docker-compose logs -f web
```

### Restart Services

```powershell
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart web
docker-compose restart celery_worker
```

## Production Deployment Considerations

For production deployment, consider:

1. **Use a production-grade web server:**
   - The Dockerfile already uses Gunicorn
   - Consider adding Nginx as a reverse proxy

2. **Enable HTTPS:**
   - Use Let's Encrypt for SSL certificates
   - Configure Nginx with SSL

3. **Database Security:**
   - Use MongoDB authentication
   - Update connection string: `mongodb://username:password@host:port/database`

4. **Environment Variables:**
   - Set `DEBUG=False`
   - Use strong `SECRET_KEY`
   - Restrict `ALLOWED_HOSTS`

5. **Monitoring:**
   - Set up application monitoring (e.g., Sentry)
   - Monitor Docker container health
   - Set up log aggregation

6. **Backups:**
   - Automate MongoDB backups
   - Store backups in a secure location
   - Test restore procedures regularly

## Additional Resources

- **Django Documentation**: https://docs.djangoproject.com/
- **Docker Documentation**: https://docs.docker.com/
- **MongoDB Documentation**: https://docs.mongodb.com/
- **Celery Documentation**: https://docs.celeryproject.org/

## Support

For issues or questions:
1. Check the logs: `docker-compose logs -f`
2. Review the troubleshooting section
3. Check GitHub issues
4. Contact the development team

## Summary - Complete Deployment Checklist

### On Development Machine (Before Transfer):
- [ ] Create MongoDB backup: `mongodump --host=localhost --port=7587 --db=analyst --archive=mongodb_backup.archive`
- [ ] Copy `.env` and `mongodb_backup.archive` to USB drive
- [ ] Push latest code to GitHub: `git push origin main`

### On New Windows Machine:
- [ ] Install Docker Desktop (with WSL 2)
- [ ] Install Git for Windows
- [ ] Clone repository: `git clone https://github.com/yourusername/TA.git`
- [ ] Copy `.env` from USB to project root
- [ ] Start all services: `docker-compose up -d --build`
- [ ] Wait for healthy status: `docker-compose ps`
- [ ] Restore database: `docker cp E:\deployment\mongodb_backup.archive ta_mongodb:/tmp/backup.archive && docker exec ta_mongodb mongorestore --archive=/tmp/backup.archive`
- [ ] Run migrations: `docker exec ta_web python manage.py migrate`
- [ ] Create superuser: `docker exec -it ta_web python manage.py createsuperuser`
- [ ] Collect static: `docker exec ta_web python manage.py collectstatic --noinput`
- [ ] Compile messages: `docker exec ta_web python manage.py compilemessages`
- [ ] Access application: http://localhost:8000

### Services Running:
- **ta_mongodb** - MongoDB database (port 7587)
- **ta_redis** - Redis cache/broker (port 6379)
- **ta_web** - Django web app (port 8000)
- **ta_celery_worker** - Background tasks
- **ta_celery_beat** - Scheduled tasks

### Key Commands:
```powershell
# View all services
docker-compose ps

# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop all services
docker-compose down

# Start services
docker-compose up -d

# Backup database
docker exec ta_mongodb mongodump --db=analyst --archive > backup.archive
```

---

**Last Updated**: October 2025
**Version**: 2.0 - Complete Docker Compose Stack
