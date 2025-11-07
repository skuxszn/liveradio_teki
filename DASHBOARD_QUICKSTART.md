# Dashboard Development - Quick Start

**One-page guide to get started building the web dashboard**

---

## 🎯 What We're Building

A modern web dashboard to manage the 24/7 radio stream **without SSH or terminal access**.

### Before Dashboard ❌
```bash
# Edit configuration
ssh user@server
nano .env
docker-compose restart

# Check status
ssh user@server
docker-compose logs

# Add track mapping
ssh user@server
docker-compose exec postgres psql ...
```

### With Dashboard ✅
```
1. Open browser: http://your-server:3000
2. Click "Settings" → Edit values → Save
3. Click "Stream" → Start/Stop buttons
4. Click "Mappings" → Add → Upload video → Save
5. Real-time monitoring and logs
```

---

## 📊 Shard Overview

| Shard | Name | Priority | Days | Start After |
|-------|------|----------|------|-------------|
| **13** | Backend API | ⭐ Critical | 5 | - |
| **14** | Frontend Core | ⭐ Critical | 6 | 13 |
| **15** | Stream Control | ⭐ Critical | 3 | 13, 14 |
| **20** | Authentication | ⭐ Critical | 3 | 13 |
| **17** | Settings UI | 🔥 High | 3 | 14, 20 |
| **16** | Mappings UI | 🔥 High | 4 | 14, 20 |
| **18** | Monitoring UI | 🔥 High | 3 | 14 |
| **19** | Assets UI | 🟡 Medium | 4 | 14, 20 |
| **21** | WebSocket | 🟡 Medium | 3 | 13, 14 |

**Total**: 34 days (1 agent) | 10 days (4 agents)

---

## 🚀 Quick Start for AI Agents

### For SHARD-13 (Backend API)

```bash
# Copy and paste this prompt to AI agent:

You are developing SHARD-13: Dashboard Backend API.

Project: /home/danteszn/development/liveradio_teki

Read:
1. DASHBOARD_AI_PROMPTS.md (SHARD-13 section)
2. DASHBOARD_SHARDS.md (complete spec)

Build a FastAPI backend with:
- JWT authentication
- Configuration management API
- Stream control endpoints
- Track mapping CRUD
- Video asset uploads
- User management

Port: 9001 (avoid conflict with existing 9000)

Follow the complete prompt in DASHBOARD_AI_PROMPTS.md.
Start now.
```

### For SHARD-14 (Frontend Core)

```bash
You are developing SHARD-14: Dashboard Frontend Core.

Project: /home/danteszn/development/liveradio_teki

Read:
1. DASHBOARD_AI_PROMPTS.md (SHARD-14 section)
2. DASHBOARD_SHARDS.md (complete spec)

Build React + TypeScript dashboard with shadcn/ui:
- Vite build setup
- React Router routing
- shadcn/ui components
- Tailwind CSS styling
- Layout (Sidebar + Navbar)
- Authentication integration
- API client with Axios

URL: http://localhost:3000

Follow the complete prompt in DASHBOARD_AI_PROMPTS.md.
Start now.
```

### For SHARD-15 (Stream Control)

```bash
You are developing SHARD-15: Stream Control UI.

Dependencies: SHARD-13, SHARD-14 must be complete.

Build the main stream control page:
- Big Start/Stop buttons
- Current track display
- Live status indicators
- Log viewer
- Manual track switch

Read DASHBOARD_AI_PROMPTS.md (SHARD-15) for complete details.
Start now.
```

---

## 🎨 Tech Stack Reference

### Backend
```python
# dashboard_api/requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
```

### Frontend
```json
// dashboard/package.json dependencies
{
  "react": "^18.2.0",
  "react-router-dom": "^6.20.0",
  "@tanstack/react-query": "^5.0.0",
  "zustand": "^4.4.0",
  "axios": "^1.6.0",
  "react-hook-form": "^7.48.0",
  "zod": "^3.22.0",
  "recharts": "^2.10.0",
  "lucide-react": "latest"
}
```

### UI Components
```bash
# shadcn/ui components to install
npx shadcn-ui@latest add button card input select table 
npx shadcn-ui@latest add tabs toast dialog form label
npx shadcn-ui@latest add badge separator scroll-area alert
npx shadcn-ui@latest add dropdown-menu avatar switch slider
```

---

## 📁 Project Structure After Dashboard

```
liveradio_teki/
├── dashboard_api/              ⭐ NEW (SHARD-13)
│   ├── routes/
│   ├── models/
│   ├── middleware/
│   ├── services/
│   └── main.py
├── dashboard/                  ⭐ NEW (SHARD-14+)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── services/
│   └── package.json
├── metadata_watcher/           ✅ Existing
├── track_mapper/               ✅ Existing
├── docs/                       ✅ Complete
└── docker-compose.yml          🔄 Updated
```

---

## 🔗 Dependencies Graph

```
        SHARD-13 (Backend API)
              │
              ├──────────────────────┐
              │                      │
              ▼                      ▼
      SHARD-14 (Frontend)    SHARD-20 (Auth)
              │                      │
              ├──────┬───────┬───────┤
              ▼      ▼       ▼       ▼
          SHARD-15  SHARD-16  SHARD-17  SHARD-18
          (Stream)  (Mappings)(Settings)(Monitor)
                            │
                            ▼
                        SHARD-19
                        (Assets)
                            │
                            ▼
                        SHARD-21
                        (WebSocket)
```

**Critical Path**: 13 → 14 → 15 (Stream Control)  
**Can Start in Parallel**: 13, 20  
**Dependent on Frontend**: 15, 16, 17, 18, 19  
**Final Enhancement**: 21

---

## ⚙️ Development Workflow

### 1. Backend First Approach (Recommended)

```
Day 1-5:   SHARD-13 (Backend API)
Day 6-11:  SHARD-14 (Frontend Core)
Day 12-14: SHARD-15 (Stream Control)
Day 15-17: SHARD-20 (Authentication)
Day 18-20: SHARD-17 (Settings)
Day 21-24: SHARD-16 (Mappings)
Day 25-27: SHARD-18 (Monitoring)
Day 28-31: SHARD-19 (Assets)
Day 32-34: SHARD-21 (WebSocket)
```

### 2. Parallel Development (4 Agents)

**Week 1 (Days 1-7):**
- Agent 1: SHARD-13 (Backend) → SHARD-21 Backend
- Agent 2: SHARD-14 (Frontend)
- Agent 3: SHARD-20 (Auth Backend + Frontend)
- Agent 4: Documentation and testing setup

**Week 2 (Days 8-14):**
- Agent 1: SHARD-15 (Stream Control)
- Agent 2: SHARD-17 (Settings)
- Agent 3: SHARD-16 (Mappings)
- Agent 4: SHARD-18 (Monitoring)

**Week 3 (Days 15-17):**
- Agent 1: SHARD-19 (Assets)
- Agent 2: SHARD-21 Frontend
- Agent 3: Integration testing
- Agent 4: Polish and bug fixes

---

## 🧪 Testing Each Shard

### After SHARD-13 (Backend)
```bash
cd /home/danteszn/development/liveradio_teki
source venv/bin/activate

# Run backend API
cd dashboard_api
uvicorn main:app --reload --port 9001

# Test endpoints
curl http://localhost:9001/api/v1/config
curl http://localhost:9001/api/v1/stream/status
```

### After SHARD-14 (Frontend)
```bash
cd dashboard
npm run dev

# Open browser: http://localhost:5173
# Should see login page and dashboard
```

### After SHARD-15 (Stream Control)
```bash
# Frontend should be running
# Navigate to http://localhost:5173/stream
# Should see Start/Stop buttons
```

---

## 🐛 Common Issues

### Backend Issues

**Port 9001 already in use:**
```bash
# Change port in dashboard_api/main.py
# Or kill process: sudo lsof -ti:9001 | xargs kill
```

**Database connection errors:**
```bash
# Verify postgres is running
docker-compose ps postgres

# Check connection string
echo $DATABASE_URL
```

### Frontend Issues

**shadcn/ui components not found:**
```bash
# Reinstall shadcn/ui
npx shadcn-ui@latest init
npx shadcn-ui@latest add button card
```

**API calls fail (CORS):**
```python
# In dashboard_api/main.py, add CORS:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📚 Essential Documentation

**For Backend Development:**
- FastAPI docs: https://fastapi.tiangolo.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- JWT: https://python-jose.readthedocs.io/

**For Frontend Development:**
- shadcn/ui: https://ui.shadcn.com/
- React Query: https://tanstack.com/query/latest
- React Router: https://reactrouter.com/
- Recharts: https://recharts.org/

---

## 🎉 Success Indicators

### Minimum Viable Dashboard (MVD)

After SHARD-13, 14, 15:
- ✅ Can login to dashboard
- ✅ Can see stream status
- ✅ Can start/stop stream with button click
- ✅ Current track displays
- ✅ Basic monitoring visible

### Full Dashboard

After all shards:
- ✅ Everything above, plus:
- ✅ Can manage all settings via UI
- ✅ Can upload and manage video loops
- ✅ Can add/edit track mappings
- ✅ Real-time updates (WebSocket)
- ✅ User management
- ✅ Comprehensive monitoring
- ✅ Audit trail

---

## 🚢 Deployment

### Development
```bash
# Backend
cd dashboard_api
source ../venv/bin/activate
uvicorn main:app --reload --port 9001

# Frontend
cd dashboard
npm run dev
```

### Production
```bash
# Build and start all services
docker-compose build
docker-compose up -d

# Access dashboard
http://your-server:3000

# API docs
http://your-server:9001/docs
```

---

## 💡 Pro Tips

1. **Start with SHARD-13 and SHARD-14** - They're foundational
2. **Test each shard independently** before moving on
3. **Use the OpenAPI docs** at /docs for API reference
4. **Mock data initially** if backend isn't ready
5. **shadcn/ui examples** are your friend - copy and customize
6. **React Query devtools** - Install for debugging API calls
7. **Docker logs** - `docker-compose logs -f dashboard-api` for debugging

---

**Need Help?**

- Check DASHBOARD_SHARDS.md for detailed specs
- Check DASHBOARD_AI_PROMPTS.md for complete prompts
- Check docs/TROUBLESHOOTING.md for common issues
- Existing code in metadata_watcher/ is a good reference

---

**Last Updated**: November 5, 2025  
**Ready to Start?** Pick a shard, copy the prompt from DASHBOARD_AI_PROMPTS.md, and assign to an AI agent! 🚀


