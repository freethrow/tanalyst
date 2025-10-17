# TA - Deployment Guide for Windows with Docker

This guide will walk you through deploying the TA (Trade Analyst) application on a Windows machine using Docker, leveraging your existing MongoDB and Redis containers.

## Overview

The deployment architecture consists of two layers:

### Layer 1: Infrastructure (Must be set up on host machine)
- **MongoDB Docker container** (port 7587) - Database server
- **Redis Docker container** (port 6379) - Cache and message broker

**These are NOT included in the GitHub repository** - they must be running on the deployment machine before starting the application.

### Layer 2: Application (From GitHub repository)
- **TA application containers** via Docker Compose:
  - `ta_web` - Django web application
  - `ta_celery_worker` - Background task processor
  - `ta_celery_beat` - Scheduled task manager

The application containers connect to MongoDB and Redis using `host.docker.internal`.

## Important: What's in GitHub vs What's Not

### ✅ Included in GitHub Repository:
- Application source code (Django, Celery, etc.)
- `Dockerfile` - Instructions to build application container
- `docker-compose.yml` - Configuration for application containers
- `requirements.txt` - Python dependencies
- Templates, static files, etc.

### ❌ NOT Included in GitHub Repository:
- MongoDB container (infrastructure dependency)
- Redis container (infrastructure dependency)
- Database data (must be restored from backup)
- `.env` file with secrets (must be created manually)

**Why?** MongoDB and Redis are infrastructure services that should already exist on the deployment machine. They're not part of the application code - they're services the application connects to.

## Prerequisites

### On the Deployment Machine (Fresh Setup)

If deploying to a new machine, you need:

1. **Docker Desktop for Windows**
   - Download from: https://www.docker.com/products/docker-desktop
   - Verify: `docker --version` and `docker-compose --version`
   - Ensure WSL 2 backend is enabled

2. **Git for Windows**
   - Download from: https://git-scm.com/download/win
   - Verify installation: `git --version`

3. **MongoDB Docker Container** (Must be set up separately)
   ```powershell
   # Start MongoDB container
   docker run -d --name mongodb-ta -p 7587:27017 mongodb/mongodb-atlas-local:8.0
   ```

4. **Redis Docker Container** (Must be set up separately)
   ```powershell
   # Start Redis container
   docker run -d --name redis-ta -p 6379:6379 redis:alpine
   ```

5. **MongoDB Tools** (for backup restoration)
   - Download MongoDB Shell: https://www.mongodb.com/try/download/shell
   - Download MongoDB Database Tools: https://www.mongodb.com/try/download/database-tools
   - These provide `mongosh` and `mongorestore` commands

### On Your Development Machine (Already Have These)

You already have:
- ✅ Docker Desktop
- ✅ MongoDB container (local6195) on port 7587
- ✅ Redis container on port 6379
- ✅ MongoDB tools installed

## Quick Start

### For Fresh Deployment (New Machine)

```powershell
# 1. Set up infrastructure containers (one-time setup)
docker run -d --name mongodb-ta -p 7587:27017 mongodb/mongodb-atlas-local:8.0
docker run -d --name redis-ta -p 6379:6379 redis:alpine

# 2. Clone and navigate
git clone https://github.com/yourusername/TA.git
cd TA

# 3. Restore database backup
mongorestore --host=localhost --port=7587 --archive=mongodb_backup.archive --db=analyst

# 4. Configure environment
Copy-Item env_template.txt .env
# Edit .env with your settings (SECRET_KEY, API keys, etc.)

# 5. Build and start application
docker-compose build
docker-compose up -d

# 6. Initialize application
docker exec ta_web python manage.py migrate
docker exec -it ta_web python manage.py createsuperuser
docker exec ta_web python manage.py collectstatic --noinput
docker exec ta_web python manage.py compilemessages

# 7. Access at http://localhost:8000
```

### For Existing Setup (Your Development Machine)

```powershell
# 1. Clone and navigate
git clone https://github.com/yourusername/TA.git
cd TA

# 2. Ensure MongoDB and Redis are running
docker start local6195  # Your MongoDB container
docker start redis      # Your Redis container

# 3. Configure environment
Copy-Item env_template.txt .env
# Edit .env with your settings

# 4. Restore database (if needed)
mongorestore --host=localhost --port=7587 --archive=mongodb_backup.archive --db=analyst

# 5. Build and start
docker-compose build
docker-compose up -d

# 6. Initialize
docker exec ta_web python manage.py migrate
docker exec -it ta_web python manage.py createsuperuser
docker exec ta_web python manage.py collectstatic --noinput
docker exec ta_web python manage.py compilemessages

# 7. Access at http://localhost:8000
```

## Detailed Step-by-Step Guide

## Step 1: Clone the Repository

Open PowerShell or Command Prompt and navigate to your desired directory:

```powershell
cd C:\Users\YourUsername\Projects
git clone https://github.com/yourusername/TA.git
cd TA
```

## Step 2: Use Existing MongoDB Docker Container

If you already have MongoDB running in Docker (recommended approach):

1. **Check if MongoDB container is running:**
   ```powershell
   docker ps | Select-String mongodb
   ```

2. **If not running, start it:**
   ```powershell
   # Find your MongoDB container name
   docker ps -a | Select-String mongodb
   
   # Start the container (replace 'local6195' with your container name)
   docker start local6195
   ```

3. **Verify it's accessible:**
   ```powershell
   # Test connection (adjust port if different)
   mongosh "mongodb://localhost:7587" --eval "db.adminCommand('ping')"
   ```

4. **Note your MongoDB connection details:**
   - Host: `localhost`
   - Port: Usually `7587` or `27017` (check with `docker ps`)
   - Connection string: `mongodb://localhost:7587/?directConnection=true`

### Alternative: Set Up New MongoDB (Only if needed)

<details>
<summary>Click to expand if you need to install MongoDB from scratch</summary>

#### Option A: Using MongoDB Atlas Local

1. **Start MongoDB Atlas Local:**
   ```powershell
   atlas deployments setup local
   ```

2. **Start the local deployment:**
   ```powershell
   atlas deployments start local
   ```

3. **Note the connection string** (usually `mongodb://localhost:27017`)

#### Option B: Using Docker (New Container)

```powershell
docker run -d --name mongodb-ta -p 7587:27017 mongodb/mongodb-atlas-local:8.0
```

</details>

## Step 3: Restore MongoDB Database from Backup

If you have a `mongodb_backup.archive` file:

1. **Place the backup file** in your project directory or a known location

2. **Restore using mongorestore:**
   ```powershell
   # If using MongoDB Atlas Local (default port 27017)
   mongorestore --archive=mongodb_backup.archive --nsInclude="analyst.*"

   # If using custom port (e.g., 7587)
   mongorestore --host=localhost --port=7587 --archive=mongodb_backup.archive --nsInclude="analyst.*"

   # If the archive includes specific database
   mongorestore --host=localhost --port=7587 --archive=mongodb_backup.archive --db=analyst
   ```

3. **Verify the restore:**
   ```powershell
   # Connect to MongoDB
   mongosh "mongodb://localhost:7587"

   # Check databases
   show dbs

   # Use the analyst database
   use analyst

   # Check collections
   show collections

   # Count articles
   db.articles.countDocuments()
   ```

## Step 4: Configure Environment Variables

1. **Copy the environment template:**
   ```powershell
   Copy-Item env_template.txt .env
   ```

2. **Edit the `.env` file** with your configuration:
   ```env
   # Django Settings
   SECRET_KEY=your-secret-key-here-generate-a-new-one
   DEBUG=False
   ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

   # MongoDB Configuration
   DB_HOST=localhost
   DB_PORT=7587
   DB_NAME=analyst
   COLLECTION_NAME=articles
   MONGODB_URI=mongodb://localhost:7587/?directConnection=true

   # Redis Configuration
   REDIS_URL=redis://localhost:6379/0

   # API Keys
   OPENROUTER_API_KEY=your-openrouter-api-key
   NOMIC_API_KEY=your-nomic-api-key
   RESEND_API_KEY=your-resend-api-key

   # LLM Configuration
   LLM_MODEL=meta-llama/llama-3.1-70b-instruct

   # Email Configuration
   DEFAULT_FROM_EMAIL=noreply@yourdomain.com
   RECIPIENT_EMAIL=recipient@example.com

   # Celery Configuration
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   ```

3. **Generate a new SECRET_KEY:**
   ```powershell
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

## Step 5: Ensure Required Services are Running

### Use Existing Redis Docker Container

If you already have Redis running in Docker:

1. **Check if Redis container is running:**
   ```powershell
   docker ps | Select-String redis
   ```

2. **If not running, start it:**
   ```powershell
   # Find your Redis container name
   docker ps -a | Select-String redis
   
   # Start the container (replace with your container name)
   docker start redis
   ```

3. **Verify Redis is accessible:**
   ```powershell
   # Test connection
   docker exec redis redis-cli ping
   # Should return: PONG
   ```

### Alternative: Start New Redis Container (Only if needed)

<details>
<summary>Click to expand if you need to create a new Redis container</summary>

```powershell
# Start a new Redis container
docker run -d --name redis-ta -p 6379:6379 redis:alpine

# Verify it's running
docker ps | Select-String redis
```

</details>

### Verify All Services are Running

```powershell
# Check MongoDB is accessible
mongosh "mongodb://localhost:7587" --eval "db.adminCommand('ping')"

# Check Redis is accessible
docker exec redis redis-cli ping

# List all running containers
docker ps
```

You should see both MongoDB and Redis containers running.

## Step 6: Build and Run with Docker Compose

1. **Update docker-compose.yml** (if needed):
   - The file is already configured to use `host.docker.internal` for MongoDB and Redis
   - Verify ports match your local services

2. **Build the Docker images:**
   ```powershell
   docker-compose build
   ```

3. **Start all services:**
   ```powershell
   docker-compose up -d
   ```

4. **Check container status:**
   ```powershell
   docker-compose ps
   ```

   You should see three containers running:
   - `ta_web` (Django application)
   - `ta_celery_worker` (Background tasks)
   - `ta_celery_beat` (Scheduled tasks)

## Step 7: Initialize the Application

1. **Run Django migrations:**
   ```powershell
   docker exec ta_web python manage.py migrate
   ```

2. **Create a superuser:**
   ```powershell
   docker exec -it ta_web python manage.py createsuperuser
   ```
   Follow the prompts to create your admin account.

3. **Collect static files:**
   ```powershell
   docker exec ta_web python manage.py collectstatic --noinput
   ```

4. **Compile translation messages:**
   ```powershell
   docker exec ta_web python manage.py compilemessages
   ```

## Step 8: Verify the Deployment

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

## Step 9: Configure Scheduled Tasks (Optional)

The application uses Celery Beat for scheduled tasks. To configure:

1. **Access Django admin:**
   - Go to: http://localhost:8000/admin
   - Navigate to "Periodic Tasks" under "Django Celery Beat"

2. **Configure tasks:**
   - **Article Translation**: Runs every 60 seconds
   - **Embedding Generation**: Runs every 60 seconds
   - **Weekly Summary**: Configure as needed

## Troubleshooting

### MongoDB Connection Issues

If containers can't connect to MongoDB:

1. **Check MongoDB is running:**
   ```powershell
   mongosh "mongodb://localhost:7587" --eval "db.adminCommand('ping')"
   ```

2. **Verify `.env` file:**
   - Ensure `MONGODB_URI=mongodb://localhost:7587/?directConnection=true`
   - For local development: use `localhost`
   - Docker handles the translation to `host.docker.internal`

3. **Check Docker network:**
   ```powershell
   docker network inspect ta_network
   ```

### Redis Connection Issues

1. **Verify Redis is running:**
   ```powershell
   docker ps | Select-String redis
   ```

2. **Test Redis connection:**
   ```powershell
   docker exec ta_web python -c "import redis; r = redis.from_url('redis://host.docker.internal:6379/0'); print(r.ping())"
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

Create regular backups:

```powershell
# Create backup
mongodump --host=localhost --port=7587 --db=analyst --archive=mongodb_backup_$(Get-Date -Format "yyyyMMdd").archive

# With compression
mongodump --host=localhost --port=7587 --db=analyst --archive=mongodb_backup_$(Get-Date -Format "yyyyMMdd").archive --gzip
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

---

**Last Updated**: October 2025
**Version**: 1.0
