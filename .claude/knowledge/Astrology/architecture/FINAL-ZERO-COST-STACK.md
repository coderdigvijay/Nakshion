# FINAL ZERO-COST STACK — Cosmic Intelligence
## 100% FREE, NO CREDIT CARD REQUIRED

**Master Agent Decision: LOCKED IN**
**Created:** 2026-03-29
**Total Cost:** $0/month (TRUE zero cost)
**Credit Card:** NOT required

---

## 🎯 **FINAL STACK (PRODUCTION-READY)**

```yaml
Frontend:
  Hosting: Vercel (FREE - unlimited)
  Framework: React 18 + TypeScript + Vite
  UI: shadcn/ui + Radix UI + Tailwind
  Animation: Framer Motion + GSAP + Lenis
  Icons: Lucide React 0.575.0
  Charts: Recharts
  Forms: React Hook Form + Zod
  State: Zustand + React Query

Backend:
  Hosting: Render.com (FREE - 750 hours/month)
  Framework: FastAPI + Python 3.11
  Server: Uvicorn (ASGI)
  Validation: Pydantic v2

Database:
  Provider: Neon (FREE - 3GB storage)
  Type: PostgreSQL 16 (serverless)
  ORM: SQLAlchemy 2.0 (async)
  Migrations: Alembic

Cache/Sessions:
  Provider: Upstash Redis (FREE - 10K commands/day)
  Client: redis-py

AI:
  Provider: Google Gemini 2.0 Flash (FREE - 15 RPM)
  SDK: google-generativeai
  Backup: Groq (Llama 3.1 70B) - FREE

Astrology:
  Library: pyswisseph (FREE - open source)
  Accuracy: NASA-level Swiss Ephemeris

Geocoding:
  Provider: LocationIQ (FREE - 10K requests/day)
  Fallback: Nominatim (unlimited, slower)

Email:
  Provider: Brevo (FREE - 300 emails/day)
  SDK: sib-api-v3-sdk

File Storage:
  Provider: Cloudflare R2 (FREE - 10GB)
  Alternative: Store in PostgreSQL as base64

Auth:
  Method: JWT (self-hosted, python-jose)
  Password: bcrypt (passlib)
  OAuth: authlib (Google/Facebook)

Monitoring:
  Errors: Sentry (FREE - 5K errors/month)
  Logging: Loguru (Python)
  Uptime: UptimeRobot (FREE - 50 monitors)

Keep-Awake:
  Service: cron-job.org (FREE)
  Ping: Every 14 minutes
  Purpose: Prevent Render cold starts
```

**Total Monthly Cost: $0.00 💰**

---

## 🔥 **WHY THIS STACK IS OPTIMAL**

### **Render.com (Backend Hosting)**
✅ **750 hours/month FREE** = 31 days × 24 hours (perfect for 24/7)
✅ **No credit card** required
✅ **Auto-deploy** from GitHub
✅ **HTTPS** included
✅ **Custom domain** support (free)
✅ **Environment variables** management
✅ **Build logs** & monitoring

**Cold Start Issue → SOLVED:**
- Render sleeps after 15 min inactivity
- cron-job.org pings every 14 min → stays awake
- Users never experience 30s delay

---

### **Neon (Database)**
✅ **3GB storage FREE** (6x more than Supabase!)
✅ **PostgreSQL 16** (latest)
✅ **Serverless** (scales to zero)
✅ **Branching** (like git branches for DB)
✅ **Auto-suspend** when inactive (saves resources)
✅ **No credit card** required

---

### **Upstash Redis (Cache)**
✅ **10K commands/day FREE** = ~300 DAU (daily active users)
✅ **Serverless** Redis
✅ **REST API** option (no connection pooling)
✅ **Global** replication
✅ **No credit card** required

---

### **Vercel (Frontend Hosting)**
✅ **Unlimited** deployments
✅ **100GB** bandwidth/month
✅ **Global CDN**
✅ **Automatic HTTPS**
✅ **Preview** deployments
✅ **Zero-config** deploy

---

## 📦 **INSTALLATION & SETUP**

### **1. Backend Setup (Render + Neon + Upstash)**

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install fastapi[all] uvicorn[standard]
pip install sqlalchemy[asyncio] alembic asyncpg
pip install redis python-jose[cryptography] passlib[bcrypt]
pip install google-generativeai pyswisseph
pip install python-multipart slowapi sentry-sdk loguru
pip install python-dotenv pytest pytest-asyncio httpx

# Create requirements.txt
pip freeze > requirements.txt
```

**requirements.txt:**
```txt
fastapi==0.110.0
uvicorn[standard]==0.27.0
pydantic==2.6.0
pydantic-settings==2.1.0
sqlalchemy[asyncio]==2.0.27
alembic==1.13.1
asyncpg==0.29.0
redis==5.0.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
google-generativeai==0.3.2
pyswisseph==2.10.3.2
python-multipart==0.0.9
slowapi==0.1.9
sentry-sdk==1.40.5
loguru==0.7.2
python-dotenv==1.0.1
pytest==8.0.1
pytest-asyncio==0.23.5
httpx==0.26.0
```

---

### **2. Database Setup (Neon)**

**Step 1: Create Neon Project**
1. Go to https://neon.tech
2. Sign up (FREE, no card)
3. Click "Create Project"
4. Copy connection string

**Connection String Format:**
```
postgresql://user:password@ep-xxx-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
```

**Step 2: Test Connection**
```bash
# Test locally
export DATABASE_URL="postgresql://..."
python -c "from sqlalchemy import create_engine; engine = create_engine('$DATABASE_URL'); print('✅ Connected!')"
```

---

### **3. Redis Setup (Upstash)**

**Step 1: Create Upstash Database**
1. Go to https://upstash.com
2. Sign up (FREE, no card)
3. Click "Create Database"
4. Copy REDIS_URL

**Connection String Format:**
```
redis://default:password@region.upstash.io:6379
```

---

### **4. Environment Variables (.env)**

```bash
# App
APP_NAME="Cosmic Intelligence"
ENVIRONMENT=production
SECRET_KEY=your-secret-key-generate-with-openssl-rand-hex-32
DEBUG=False

# Neon Database
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require

# Upstash Redis
REDIS_URL=redis://default:pass@region.upstash.io:6379

# JWT
JWT_SECRET_KEY=your-jwt-secret-generate-with-openssl-rand-hex-32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Gemini AI (FREE)
GEMINI_API_KEY=get-from-aistudio.google.com

# LocationIQ (FREE)
LOCATIONIQ_API_KEY=get-from-locationiq.com

# Brevo Email (FREE)
BREVO_API_KEY=get-from-brevo.com
FROM_EMAIL=noreply@cosmicapp.com

# Sentry (FREE)
SENTRY_DSN=get-from-sentry.io

# CORS (update with your Vercel domain)
CORS_ORIGINS=["https://cosmic-intelligence.vercel.app","http://localhost:5173"]
```

---

### **5. Deploy to Render**

**Step 1: Create render.yaml (in repo root)**
```yaml
services:
  - type: web
    name: cosmic-backend
    runtime: python
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: REDIS_URL
        sync: false
      - key: GEMINI_API_KEY
        sync: false
      - key: JWT_SECRET_KEY
        sync: false
      - key: SECRET_KEY
        sync: false
      - key: LOCATIONIQ_API_KEY
        sync: false
      - key: BREVO_API_KEY
        sync: false
      - key: SENTRY_DSN
        sync: false
      - key: CORS_ORIGINS
        sync: false
```

**Step 2: Deploy**
1. Push code to GitHub
2. Go to https://render.com
3. Click "New +" → "Web Service"
4. Connect GitHub repo
5. Render auto-detects Python
6. Set environment variables in dashboard
7. Click "Create Web Service"
8. **Deploy URL:** `https://cosmic-backend.onrender.com`

---

### **6. Keep Backend Awake (Prevent Cold Starts)**

**Use cron-job.org (FREE):**

1. Go to https://cron-job.org/en/
2. Sign up (FREE)
3. Create new cron job:
   - **URL:** `https://cosmic-backend.onrender.com/health`
   - **Schedule:** Every 14 minutes
   - **Method:** GET
4. Save

**Result:** Backend stays awake 24/7, no cold starts!

**Alternative:** UptimeRobot (also FREE, 50 monitors)

---

### **7. Frontend Setup (Vercel)**

```bash
# Create React app
npm create vite@latest frontend -- --template react-ts
cd frontend

# Install dependencies
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Initialize shadcn/ui
npx shadcn-ui@latest init

# Install core packages
npm install framer-motion gsap @studio-freight/lenis
npm install lucide-react@0.575.0 recharts
npm install react-hook-form @hookform/resolvers zod
npm install axios @tanstack/react-query zustand
npm install react-router-dom date-fns
npm install clsx tailwind-merge class-variance-authority

# Add shadcn components
npx shadcn-ui@latest add button card input label dialog tabs badge avatar dropdown-menu
```

**Deploy to Vercel:**
1. Push to GitHub
2. Go to https://vercel.com
3. Click "New Project"
4. Import GitHub repo
5. Framework: Vite
6. Build: `npm run build`
7. Output: `dist`
8. Environment variables:
   ```
   VITE_API_URL=https://cosmic-backend.onrender.com
   ```
9. Deploy!

**Live at:** `https://cosmic-intelligence.vercel.app`

---

## 🔧 **Backend Project Structure**

```
backend/
├── app/
│   ├── main.py              # FastAPI app entry
│   ├── config.py            # Settings (env vars)
│   ├── database.py          # SQLAlchemy setup
│   ├── dependencies.py      # Dependency injection
│   │
│   ├── models/              # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── birth_chart.py
│   │   ├── conversation.py
│   │   └── message.py
│   │
│   ├── schemas/             # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── chart.py
│   │   └── chat.py
│   │
│   ├── routers/             # API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py          # /api/auth/*
│   │   ├── chart.py         # /api/chart/*
│   │   ├── chat.py          # /api/chat/*
│   │   └── health.py        # /health (for cron ping)
│   │
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── chart_service.py
│   │   ├── ai_service.py
│   │   └── astrology_service.py
│   │
│   └── core/                # Core utilities
│       ├── __init__.py
│       ├── security.py      # JWT, password hashing
│       ├── cache.py         # Redis client
│       └── exceptions.py    # Custom exceptions
│
├── alembic/                 # Database migrations
├── tests/
├── requirements.txt
├── render.yaml              # Render deployment config
├── .env
├── .gitignore
└── README.md
```

---

## 🚀 **API Endpoints**

```python
# Health check (for cron ping)
GET  /health

# Authentication
POST /api/auth/register
POST /api/auth/login
POST /api/auth/refresh
GET  /api/auth/me

# Birth Charts
POST /api/chart/generate
GET  /api/chart/{user_id}
PUT  /api/chart/{user_id}

# AI Chat
POST /api/chat/message
GET  /api/chat/conversations
GET  /api/chat/conversations/{id}

# Geocoding
GET  /api/geocoding/search?query={location}

# Horoscopes
GET  /api/horoscope/daily
```

---

## ⚠️ **Limitations & Workarounds**

### **1. Render Cold Starts (15 min idle → 30s wake)**
**Solution:** cron-job.org pings every 14 min → stays awake 24/7

### **2. Gemini 15 RPM (requests per minute)**
**Solution:** Queue requests client-side, show "AI is pondering..." (4 sec delay feels premium)

### **3. Neon 3GB Database**
**Solution:** Archive old conversations, 3GB = 10K+ users

### **4. Upstash 10K commands/day**
**Solution:** 10K = ~300 DAU, optimize queries, upgrade when needed

---

## 📊 **When to Upgrade (Scale Path)**

| Users | Cost | Upgrades Needed |
|-------|------|-----------------|
| 0-1000 | **$0** | None |
| 1K-5K | **$0-10** | Maybe Render paid ($7/mo for no sleep) |
| 5K-10K | **$10-25** | Neon Pro ($25/mo for 10GB) |
| 10K-50K | **$50-100** | Gemini paid, Upstash Pro |
| 50K+ | **$200+** | Full paid stack |

**For MVP (0-1000 users): $0/month guaranteed**

---

## ✅ **FINAL CHECKLIST**

```
Backend:
[ ] Neon database created
[ ] Upstash Redis created
[ ] Gemini API key obtained
[ ] LocationIQ API key obtained
[ ] Brevo account created
[ ] Sentry project created
[ ] GitHub repo created
[ ] Render web service deployed
[ ] Environment variables set in Render
[ ] cron-job.org ping configured (every 14 min)
[ ] Health endpoint working: /health

Frontend:
[ ] Vercel project deployed
[ ] Environment variable VITE_API_URL set
[ ] Custom domain connected (optional)
[ ] API calls working to backend

Testing:
[ ] Backend health check: curl https://cosmic-backend.onrender.com/health
[ ] Frontend loads: https://cosmic-intelligence.vercel.app
[ ] API connection working
```

---

## 🎯 **SUCCESS CRITERIA**

✅ Backend hosted on Render (FREE)
✅ Frontend hosted on Vercel (FREE)
✅ Database on Neon (FREE - 3GB)
✅ Redis on Upstash (FREE - 10K/day)
✅ No cold starts (cron keeps awake)
✅ No credit card required
✅ $0/month cost
✅ Production-ready
✅ Can scale to 1000+ users

---

**Master Agent: STACK FINALIZED ✅**
**Ready to build! 🚀**
