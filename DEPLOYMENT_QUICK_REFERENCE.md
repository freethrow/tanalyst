# TA Deployment - Quick Reference Card

## 🚀 One-Command Deployment

```powershell
# After cloning and copying .env from USB:
docker-compose up -d --build
```

## 📋 Pre-Deployment Checklist (Development Machine)

```powershell
# 1. Create MongoDB backup
mongodump --host=localhost --port=7587 --db=analyst --archive=mongodb_backup.archive

# 2. Prepare USB drive
New-Item -Path "E:\deployment" -ItemType Directory -Force
Copy-Item .env E:\deployment\.env
Copy-Item mongodb_backup.archive E:\deployment\mongodb_backup.archive

# 3. Push to GitHub
git add .
git commit -m "Update before deployment"
git push origin main
```

## 🖥️ New Machine Setup (5 Steps)

### 1. Install Prerequisites
- Docker Desktop: https://www.docker.com/products/docker-desktop
- Git: https://git-scm.com/download/win

### 2. Clone & Configure
```powershell
git clone https://github.com/yourusername/TA.git
cd TA
Copy-Item E:\deployment\.env .env
```

### 3. Start Services
```powershell
docker-compose up -d --build
```

### 4. Restore Database
```powershell
docker cp E:\deployment\mongodb_backup.archive ta_mongodb:/tmp/backup.archive
docker exec ta_mongodb mongorestore --archive=/tmp/backup.archive
```

### 5. Initialize Django
```powershell
docker exec ta_web python manage.py migrate
docker exec -it ta_web python manage.py createsuperuser
docker exec ta_web python manage.py collectstatic --noinput
docker exec ta_web python manage.py compilemessages
```

## 🐳 Docker Services

| Service | Container Name | Port | Purpose |
|---------|---------------|------|---------|
| MongoDB | ta_mongodb | 7587 | Database |
| Redis | ta_redis | 6379 | Cache/Broker |
| Web | ta_web | 8000 | Django App |
| Celery Worker | ta_celery_worker | - | Background Tasks |
| Celery Beat | ta_celery_beat | - | Scheduled Tasks |

## 🔧 Common Commands

```powershell
# View all services status
docker-compose ps

# View logs (all services)
docker-compose logs -f

# View logs (specific service)
docker-compose logs -f web
docker-compose logs -f celery_worker

# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart web

# Stop all services
docker-compose down

# Start services
docker-compose up -d

# Rebuild after code changes
docker-compose down
docker-compose up -d --build
```

## 🔍 Health Checks

```powershell
# Check MongoDB
docker exec ta_mongodb mongosh --eval "db.adminCommand('ping')"

# Check Redis
docker exec ta_redis redis-cli ping

# Check web app
curl http://localhost:8000

# Check article count
docker exec ta_mongodb mongosh --eval "use analyst; db.articles.countDocuments()"
```

## 💾 Backup & Restore

### Create Backup
```powershell
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
docker exec ta_mongodb mongodump --db=analyst --archive > "mongodb_backup_$timestamp.archive"
```

### Restore Backup
```powershell
docker cp backup.archive ta_mongodb:/tmp/backup.archive
docker exec ta_mongodb mongorestore --archive=/tmp/backup.archive
```

## 🆘 Troubleshooting

### Services won't start
```powershell
# Check Docker is running
docker version

# View error logs
docker-compose logs

# Check port conflicts
netstat -ano | findstr "7587 6379 8000"
```

### Can't access web app
```powershell
# Check web container is running
docker-compose ps web

# View web logs
docker-compose logs web

# Check health
docker exec ta_web curl -f http://localhost:8000/
```

### Database connection issues
```powershell
# Test from web container
docker exec ta_web python -c "from pymongo import MongoClient; client = MongoClient('mongodb://mongodb:27017/'); print(client.admin.command('ping'))"
```

## 📁 File Structure

```
TA/
├── .env                    # ❌ NOT in Git (from USB)
├── docker-compose.yml      # ✅ Defines all services
├── Dockerfile             # ✅ App container build
├── env_template.txt       # ✅ Template for .env
├── exampleenv.txt         # ✅ Example with values
├── requirements.txt       # ✅ Python dependencies
├── analyst/               # Django project
│   ├── settings.py       # ✅ Loads .env
│   ├── agents/           # AI agents
│   ├── scrapers/         # Web scrapers
│   └── emails/           # Email notifications
└── articles/             # Django app
    ├── models.py
    ├── views.py
    └── tasks.py          # Celery tasks
```

## 🌐 Access Points

- **Web App**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **Articles**: http://localhost:8000/articles/

## ⚙️ Environment Variables

Key variables in `.env`:
- `SECRET_KEY` - Django secret
- `DEBUG` - true/false
- `MONGODB_URI` - mongodb://mongodb:27017/...
- `REDIS_URL` - redis://redis:6379/0
- `NOMIC_API_KEY` - For embeddings
- `RESEND_API_KEY` - For emails
- `OPENROUTER_API_KEY` - For LLM
- `GROQ_API_KEY` - For LLM

## 📞 Support

1. Check logs: `docker-compose logs -f`
2. Review DEPLOYMENT.md for detailed guide
3. Check container health: `docker-compose ps`
4. Verify .env file is present and correct
