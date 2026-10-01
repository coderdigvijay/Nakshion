# Optimal Zero-Cost Tech Stack — Cosmic Intelligence

**Master Agent Decision: BEST FREE SERVICES**
**Created:** 2026-03-29
**Status:** Production-Ready
**Cost:** $0/month (scales to 1000+ users)

---

## 🎯 Philosophy

**Use the BEST tools that happen to be FREE, not just "good enough free tools".**

This stack competes with paid stacks. Companies run production on these services.

---

## 🏆 **FINAL OPTIMAL STACK**

### **Frontend**

```yaml
Framework: React 18 + TypeScript + Vite
UI Library: shadcn/ui + Radix UI
Styling: Tailwind CSS
Animation:
  - Framer Motion (primary)
  - GSAP (hero sections)
  - Lenis (smooth scroll)
Icons: Lucide React 0.575.0
Charts: Recharts
Forms: React Hook Form + Zod
State: Zustand + React Query
Hosting: Vercel (FREE - unlimited, best DX)

Why Vercel:
✅ Zero config deploy
✅ Automatic HTTPS
✅ Global CDN
✅ 100GB bandwidth/month
✅ Preview deployments
✅ Best performance
```

---

### **Backend**

```yaml
Framework: FastAPI (Python 3.11+)
Server: Uvicorn (ASGI)
Language: Python (best for AI + astrology)
Validation: Pydantic v2
Hosting: Railway (FREE - $5/month credit, no cold starts)

Why Railway:
✅ No cold starts (unlike Render)
✅ PostgreSQL + Redis included
✅ Auto-deploy from GitHub
✅ Better DX than Fly.io
✅ $5 credit = 24/7 uptime for small service
```

---

### **Database**

```yaml
Primary: Supabase Postgres (FREE - 500MB)
ORM: SQLAlchemy 2.0 (async)
Migrations: Alembic

Why Supabase:
✅ PostgreSQL 15
✅ Built-in Auth (bonus)
✅ Built-in Storage (1GB)
✅ Realtime subscriptions (future feature)
✅ Auto backups
✅ Better dashboard than Neon
✅ 500MB enough for 10K users
```

---

### **Caching / Session**

```yaml
Cache: Upstash Redis (FREE - 10K commands/day)
Client: redis-py

Why Upstash:
✅ Serverless (no connection pooling needed)
✅ REST API option (lower latency on serverless)
✅ 10K commands = ~300 daily active users
✅ Better free tier than Redis Cloud
```

---

### **AI (CRITICAL CHOICE)**

```yaml
Primary: Google Gemini 2.0 Flash (FREE)
SDK: google-generativeai
Rate Limit: 15 RPM (requests per minute)
Backup: Groq (Llama 3.1 70B) if Gemini down

Why Gemini 2.0 Flash:
✅ FREE tier is generous (15 RPM = 900 requests/hour)
✅ Quality is excellent for astrology
✅ 1M tokens/min input, 32K context window
✅ Fast responses (~2-3 seconds)
✅ Google reliability
✅ No credit card needed

Rate Limit Strategy:
- 15 RPM = 1 request every 4 seconds
- Queue requests client-side if rate limit hit
- Show "AI is pondering your cosmic path..." (feels premium, not broken)
- For 100 daily users: ~5 messages/user = 500 requests/day = well under limit
```

**API Key:** https://aistudio.google.com/app/apikey

---

### **Geocoding / Location**

```yaml
Service: LocationIQ (FREE - 10K requests/day)
Fallback: Nominatim (unlimited, slower)

Why LocationIQ:
✅ 10K/day = more than enough
✅ Autocomplete support
✅ Timezone detection built-in
✅ Better accuracy than Nominatim
✅ Faster than OpenStreetMap direct
```

**Signup:** https://locationiq.com

---

### **Email (Transactional)**

```yaml
Service: Brevo (FREE - 300 emails/day)
SDK: sib-api-v3-sdk
Use Cases: Welcome, password reset, notifications

Why Brevo:
✅ 300/day = enough for 50+ signups/day
✅ SMTP + API
✅ Email templates
✅ Delivery tracking
✅ Better free tier than SendGrid
```

**Signup:** https://www.brevo.com

---

### **Astrology Calculations**

```yaml
Library: pyswisseph (FREE - open source)
Accuracy: Professional-grade (NASA-level)
Features: Natal charts, transits, aspects, houses

Why pyswisseph:
✅ Swiss Ephemeris = most accurate
✅ Used by professional astrologers
✅ Python native
✅ No API calls needed (runs locally)
✅ Fast (milliseconds)
```

```bash
pip install pyswisseph
```

---

### **File Storage (Optional)**

```yaml
Service: Supabase Storage (FREE - 1GB)
Use: User avatars, generated chart images

Why Supabase Storage:
✅ Included with Supabase DB
✅ CDN included
✅ Image transformations
✅ Public + private buckets
```

---

### **Monitoring / Error Tracking**

```yaml
Errors: Sentry (FREE - 5K errors/month)
Logging: Loguru (Python) - local logs
Uptime: UptimeRobot (FREE - 50 monitors)

Why Sentry:
✅ Best error tracking
✅ Source maps support
✅ Performance monitoring
✅ 5K errors/month = more than enough
```

**Signup:** https://sentry.io

---

### **Authentication**

```yaml
Method: JWT tokens (self-hosted)
Library: python-jose + passlib
OAuth: Supabase Auth (Google/Facebook login)

Why Self-hosted JWT:
✅ Zero external dependencies
✅ Full control
✅ No rate limits
✅ Supabase Auth as bonus for OAuth
```

---

### **Background Jobs (Optional MVP, needed later)**

```yaml
Queue: Celery + Redis (Upstash)
Use: Daily horoscopes, email sending

Implementation:
- Start without background jobs (run sync for MVP)
- Add Celery when daily horoscope feature launches
```

---

## 📦 **Complete Installation**

### **Frontend Setup**

```bash
# Create project
npm create vite@latest frontend -- --template react-ts
cd frontend

# Install Tailwind
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Initialize shadcn/ui
npx shadcn-ui@latest init

# Install core dependencies
npm install framer-motion gsap @studio-freight/lenis
npm install lucide-react@0.575.0 recharts
npm install react-hook-form @hookform/resolvers zod
npm install axios @tanstack/react-query zustand
npm install react-router-dom date-fns
npm install clsx tailwind-merge class-variance-authority

# Add shadcn components
npx shadcn-ui@latest add button card input label dialog tabs badge avatar dropdown-menu

# Deploy to Vercel
# Connect GitHub repo → Vercel auto-deploys on push
```

---

### **Backend Setup**

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install fastapi[all] uvicorn[standard]
pip install sqlalchemy[asyncio] alembic asyncpg
pip install redis python-jose[cryptography] passlib[bcrypt]
pip install google-generativeai  # Gemini
pip install pyswisseph  # Astrology
pip install python-multipart slowapi
pip install sentry-sdk loguru python-dotenv
pip install pytest pytest-asyncio httpx

# Set up Supabase
# 1. Create project at supabase.com
# 2. Get DATABASE_URL from Settings → Database
# 3. Copy to .env

# Set up Upstash Redis
# 1. Create database at upstash.com
# 2. Get REDIS_URL
# 3. Copy to .env

# Deploy to Railway
# 1. Connect GitHub repo
# 2. Railway auto-deploys on push
# 3. Set environment variables in Railway dashboard
```

---

### **Environment Variables**

```bash
# .env (Backend)

# App
APP_NAME="Cosmic Intelligence"
ENVIRONMENT=production
SECRET_KEY=generate-with-openssl-rand-hex-32

# Supabase Database
DATABASE_URL=postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres

# Upstash Redis
REDIS_URL=redis://default:[password]@[region].upstash.io:6379

# JWT
JWT_SECRET_KEY=generate-with-openssl-rand-hex-32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Gemini AI (FREE)
GEMINI_API_KEY=get-from-aistudio.google.com

# LocationIQ (FREE)
LOCATIONIQ_API_KEY=get-from-locationiq.com

# Brevo Email (FREE)
BREVO_API_KEY=get-from-brevo.com
FROM_EMAIL=noreply@yourdomain.com

# Sentry (FREE)
SENTRY_DSN=get-from-sentry.io

# CORS
CORS_ORIGINS=["https://yourapp.vercel.app","http://localhost:5173"]
```

---

## 🚀 **Deployment Strategy**

### **Frontend (Vercel)**

```bash
# 1. Push to GitHub
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/cosmic-frontend.git
git push -u origin main

# 2. Connect to Vercel
# Go to vercel.com → New Project → Import from GitHub
# Framework: Vite
# Build Command: npm run build
# Output Directory: dist
# Auto-deploy on every push

# Done! Live at: https://cosmic-intelligence.vercel.app
```

---

### **Backend (Railway)**

```bash
# 1. Push to GitHub
git init
git add .
git commit -m "Initial backend"
git remote add origin https://github.com/yourusername/cosmic-backend.git
git push -u origin main

# 2. Connect to Railway
# Go to railway.app → New Project → Deploy from GitHub
# Select repo → Railway auto-detects Python/FastAPI
# Add environment variables from .env
# Railway assigns public URL

# Done! API live at: https://cosmic-backend.up.railway.app
```

---

### **Database (Supabase)**

```bash
# 1. Create project at supabase.com
# 2. Copy connection string from Settings → Database
# 3. Run migrations locally:

alembic upgrade head

# Migrations apply to Supabase Postgres
```

---

## 📊 **Cost Breakdown**

| Service | Free Tier | Paid Upgrade | When to Upgrade |
|---------|-----------|--------------|-----------------|
| Vercel | Unlimited | $20/mo | Never (unless team features) |
| Railway | $5/mo credit | $5/mo | When usage > $5 (~1000 users) |
| Supabase | 500MB DB | $25/mo | When DB > 500MB (~10K users) |
| Upstash Redis | 10K cmd/day | $10/mo | When DAU > 300 |
| Gemini | 15 RPM free | $0.075/1K tokens | When > 20K messages/day |
| LocationIQ | 10K/day | $50/mo | When > 10K searches/day |
| Brevo | 300 emails/day | $25/mo | When > 300 emails/day |
| Sentry | 5K errors/mo | $26/mo | When bugs > 5K/mo (fix bugs!) |

**First upgrade needed:** Railway at ~1000 active users (~$10-20/mo)

---

## ⚠️ **Limitations & Solutions**

### **Gemini 15 RPM Limit**

**Problem:** Only 15 requests per minute
**Solution:**
```typescript
// Frontend: Queue requests client-side
const requestQueue = [];
const RATE_LIMIT_MS = 4000; // 1 request every 4 seconds

async function sendMessage(msg) {
  await delay(RATE_LIMIT_MS);
  return api.post('/chat/message', msg);
}
```

**UX:** Show "AI is contemplating your cosmic question..." (4 sec feels premium, not slow)

---

### **Railway $5 Credit**

**Problem:** Might exceed $5/month with 24/7 uptime
**Solution:**
- Optimize Docker image (smaller = cheaper)
- Use async FastAPI (handles more requests per instance)
- Monitor usage in Railway dashboard
- If exceeded: upgrade to $5/mo plan (still cheap!)

---

### **Supabase 500MB**

**Problem:** Might exceed with lots of users
**Solution:**
- Compress old chat messages (archive to JSON)
- Delete conversations > 90 days
- 500MB = ~10K users with full chat history
- Upgrade to $25/mo when needed

---

## 🎯 **Why This Stack is OPTIMAL**

### **1. Best Free Services Available**
- Vercel = Industry standard (Stripe, TikTok use it)
- Railway = Better than Render (no cold starts)
- Supabase = Better than Neon (more features)
- Gemini 2.0 = Better than GPT-3.5 (and free!)

### **2. Production-Ready**
- Not a "toy" stack
- Companies run production on these
- Can scale to 10K users before paid upgrades

### **3. Great Developer Experience**
- Auto-deploy on git push
- Good dashboards
- Fast iteration
- Modern tooling

### **4. Easy to Scale**
- Upgrade path is clear
- No major rewrites needed
- Just increase paid tiers

---

## 📝 **Agents Using This Stack**

- **Backend Elite Engineer** → Uses FastAPI + Gemini + pyswisseph
- **Frontend Elite Engineer** → Uses React + Vercel deploy
- **Database Architect** → Uses Supabase Postgres
- **AI/GenAI Specialist** → Uses Gemini 2.0 Flash
- **Security Specialist** → Reviews JWT + Supabase Auth

---

## ✅ **Final Checklist**

```
[ ] Frontend deployed to Vercel
[ ] Backend deployed to Railway
[ ] Supabase database created
[ ] Upstash Redis created
[ ] Gemini API key obtained
[ ] LocationIQ API key obtained
[ ] Brevo account created
[ ] Sentry project created
[ ] Environment variables set
[ ] CORS configured
[ ] Domain connected (optional)
```

---

**Master Agent Approval: STACK LOCKED IN ✅**

This is the best possible free stack for Cosmic Intelligence.
Ready to build! 🚀
