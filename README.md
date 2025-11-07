# 24/7 FFmpeg YouTube Radio Stream

A fully automated, 24/7 YouTube radio stream system that combines AzuraCast-managed audio with per-track looping MP4 videos, featuring smooth transitions, auto-recovery, monitoring, and notifications.

## 🎯 Project Overview

This system creates a continuous YouTube video stream by:
- Playing audio from AzuraCast (your existing radio automation)
- Overlaying different looping MP4 videos for each track
- Switching videos smoothly when tracks change
- Providing fade in/out transitions at track boundaries
- Auto-recovering from failures
- Logging all activity and sending notifications
- Running 24/7 with minimal maintenance

## 📚 Documentation Structure

This project has been broken down into **12 development shards** that can be completed independently by AI agents or human developers. Here's your documentation roadmap:

### 🚀 Start Here
1. **[AI_AGENT_QUICKSTART.md](./AI_AGENT_QUICKSTART.md)** - Quick start guide for developers
   - Step-by-step workflow
   - Coding standards
   - Common pitfalls
   - Best practices

### 📋 Planning Documents
2. **[DEVELOPMENT_SHARDS.md](./DEVELOPMENT_SHARDS.md)** - Complete technical specifications
   - All 12 shards detailed
   - Technical requirements
   - Deliverables per shard
   - Testing criteria
   - Interface contracts

3. **[SHARD_DEPENDENCIES.md](./SHARD_DEPENDENCIES.md)** - Project management guide
   - Dependency graph
   - Parallel development streams
   - Optimal team assignments
   - Timeline estimation
   - Communication protocols

4. **[shards.json](./shards.json)** - Machine-readable task data
   - Programmatic task assignment
   - Dependency tracking
   - Resource requirements
   - Technology stack

### 📖 User Documentation (New!)

**For Deployment and Operations**:
5. **[docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md)** - Complete deployment guide
   - Prerequisites and system requirements
   - Step-by-step setup instructions
   - Post-deployment verification
   - Production hardening

6. **[docs/CONFIGURATION.md](./docs/CONFIGURATION.md)** - Configuration reference
   - All environment variables documented
   - FFmpeg encoding presets
   - Best practices and examples

7. **[docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md)** - Troubleshooting guide
   - Quick diagnostics
   - Common issues and solutions
   - Debugging tools and commands

8. **[docs/API.md](./docs/API.md)** - API documentation
   - Complete endpoint reference
   - Authentication methods
   - Code examples (Python, JavaScript, cURL)

9. **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)** - System architecture
   - Component diagrams
   - Data flow documentation
   - Design decisions

10. **[docs/FAQ.md](./docs/FAQ.md)** - Frequently asked questions
    - Common questions and answers
    - Best practices
    - Tips and tricks

**Specialized Guides**:
- **[docs/FFMPEG_TUNING.md](./docs/FFMPEG_TUNING.md)** - FFmpeg optimization
- **[docs/ASSET_PREPARATION.md](./docs/ASSET_PREPARATION.md)** - Video loop preparation
- **[docs/MONITORING.md](./docs/MONITORING.md)** - Monitoring and alerting
- **[docs/SECURITY.md](./docs/SECURITY.md)** - Security best practices
- **[docs/ADVANCED_TRANSITIONS.md](./docs/ADVANCED_TRANSITIONS.md)** - Advanced features

### 🎨 Dashboard Extension (Optional - New!)

**For adding a web-based management UI**:
11. **[DASHBOARD_INDEX.md](./DASHBOARD_INDEX.md)** - Dashboard documentation index
12. **[DASHBOARD_SHARDS.md](./DASHBOARD_SHARDS.md)** - Complete dashboard specifications
13. **[DASHBOARD_AI_PROMPTS.md](./DASHBOARD_AI_PROMPTS.md)** - AI agent prompts for dashboard shards
14. **[DASHBOARD_QUICKSTART.md](./DASHBOARD_QUICKSTART.md)** - Quick start for dashboard development

The dashboard provides:
- Web UI for starting/stopping streams
- Configuration management without editing files
- Track mapping interface with drag-and-drop
- Video asset uploads and management
- Real-time monitoring and metrics
- User authentication and role-based access

## 🏗️ Architecture Components

### Core Services
- **AzuraCast** - Radio automation & audio source
- **Metadata Watcher** - Track change detection & orchestration
- **FFmpeg Engine** - Video encoding & streaming
- **nginx-rtmp** - RTMP relay buffer
- **PostgreSQL** - Track mappings & analytics
- **Prometheus** - Metrics & monitoring

### Support Services
- **Notification System** - Discord/Slack alerts
- **Asset Manager** - Video validation & overlays
- **Security Layer** - Authentication & licensing
- **Logging Module** - Structured logs & analytics

## 📦 The Development Shards

### Core System (Shards 1-12) ✅ COMPLETE

| Shard | Name | Priority | Complexity | Duration | Status |
|-------|------|----------|------------|----------|--------|
| **1** | Core Infrastructure | CRITICAL | Medium | 2 days | ✅ |
| **2** | Metadata Watcher | CRITICAL | Medium | 2 days | ✅ |
| **3** | Track Mapping | CRITICAL | Low | 2 days | ✅ |
| **4** | FFmpeg Manager | CRITICAL | High | 4 days | ✅ |
| **5** | Logging & Analytics | HIGH | Medium | 2 days | ✅ |
| **6** | Notifications | MEDIUM | Low | 2 days | ✅ |
| **7** | Monitoring | HIGH | High | 3 days | ✅ |
| **8** | Asset Management | MEDIUM | Medium | 3 days | ✅ |
| **9** | Advanced Transitions | LOW | Very High | 4 days | ✅ |
| **10** | Security | MEDIUM | Low | 2 days | ✅ |
| **11** | Testing Suite | MEDIUM | High | 5 days | ✅ |
| **12** | Documentation | HIGH | Low | 6 days | ✅ |

### Dashboard Extension (Shards 13-21) 🆕 PLANNED

| Shard | Name | Priority | Complexity | Duration | Status |
|-------|------|----------|------------|----------|--------|
| **13** | Dashboard Backend API | CRITICAL | High | 5 days | 📋 |
| **14** | Frontend Core (React + shadcn/ui) | CRITICAL | High | 6 days | 📋 |
| **15** | Stream Control UI | CRITICAL | Medium | 3 days | 📋 |
| **16** | Track Mapping UI | HIGH | Medium | 4 days | 📋 |
| **17** | Settings & Config UI | HIGH | Medium | 3 days | 📋 |
| **18** | Monitoring Dashboard | HIGH | Medium | 3 days | 📋 |
| **19** | Video Asset Manager | MEDIUM | Medium | 4 days | 📋 |
| **20** | Authentication & Users | HIGH | Medium | 3 days | 📋 |
| **21** | WebSocket Real-time | MEDIUM | High | 3 days | 📋 |

**Dashboard Total**: 34 days (1 agent) | 10 days (4 agents parallel)

## 🚦 Getting Started

### For End Users (Deploy the System)
**Start here if you want to run a 24/7 radio stream:**
1. Read [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) - Complete deployment guide
2. Configure using [docs/CONFIGURATION.md](./docs/CONFIGURATION.md)
3. Troubleshoot with [docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md)
4. Check [docs/FAQ.md](./docs/FAQ.md) for common questions

### For Project Managers
1. Read [SHARD_DEPENDENCIES.md](./SHARD_DEPENDENCIES.md) for team assignment strategy
2. Review [shards.json](./shards.json) for programmatic tracking
3. Choose between **MVP** (7 days, 1 agent) or **Full** (21 days, 4 agents)

### For Developers
1. Read [AI_AGENT_QUICKSTART.md](./AI_AGENT_QUICKSTART.md) for workflow
2. Get your shard assignment (shard-1 through shard-12)
3. Read your shard spec in [DEVELOPMENT_SHARDS.md](./DEVELOPMENT_SHARDS.md)
4. Follow the development workflow

### For Technical Leads
1. Review all documentation
2. Verify dependencies are met for each phase
3. Monitor integration points between shards
4. Resolve interface conflicts early

## 🎯 MVP vs Full Deployment

### MVP (1 Week, 1-2 Agents)
**Goal**: Get a working stream quickly
- ✅ Shard 1: Core Infrastructure
- ✅ Shard 3: Track Mapping (basic)
- ✅ Shard 4: FFmpeg Manager (basic, no fades)
- ✅ Shard 2: Metadata Watcher (basic)
- ✅ Shard 5: Logging (console only)
- ✅ Shard 12: Basic README

**Defer**: Notifications, monitoring, security, testing, advanced features

### Full Production (3 Weeks, 4 Agents)
**Goal**: Enterprise-ready, 24/7 reliable system
- Week 1: Core functionality (Shards 1-6)
- Week 2: Reliability & monitoring (Shards 7, 8, 10, 11)
- Week 3: Polish & advanced (Shards 9, 12)

## 🔧 Technology Stack

- **Languages**: Python 3.11+, Bash
- **Web Framework**: FastAPI (async)
- **Database**: PostgreSQL 15+
- **ORM**: SQLAlchemy
- **Infrastructure**: Docker, Docker Compose
- **Video**: FFmpeg 6.0+, Pillow
- **RTMP**: nginx-rtmp-module
- **Monitoring**: Prometheus, Grafana
- **Testing**: pytest, locust
- **Notifications**: Discord/Slack webhooks

## 💻 Resource Requirements

### Minimum (720p, CPU encoding)
- CPU: 4 cores
- RAM: 4 GB
- Disk: 50 GB
- Upload: 5 Mbps

### Recommended (1080p, CPU encoding)
- CPU: 8 cores
- RAM: 8 GB
- Disk: 100 GB SSD
- Upload: 10 Mbps

### Optimal (1080p60, GPU encoding)
- CPU: 4 cores
- GPU: NVIDIA GTX 1650+ (4GB VRAM)
- RAM: 8 GB
- Disk: 100 GB NVMe SSD
- Upload: 15 Mbps

## 📊 Development Timeline

### Parallel Development (4 Agents)
```
Week 1: Foundation & Core
├─ Agent 1: SHARD-1 → SHARD-3 → SHARD-4 (Critical path)
├─ Agent 2: SHARD-5 → SHARD-6 → SHARD-2
├─ Agent 3: SHARD-12 → SHARD-8 → SHARD-10
└─ Agent 4: SHARD-11 (testing framework)

Week 2: Integration & Reliability
├─ Agent 1: SHARD-2 completion → SHARD-9
├─ Agent 2: SHARD-7 (monitoring)
├─ Agent 3: SHARD-7 (monitoring) + SHARD-12
└─ Agent 4: SHARD-11 (integration tests)

Week 3: Polish & Launch
└─ All: Bug fixes, performance tuning, launch prep
```

### Serial Development (1 Agent)
```
MVP Track: SHARD-1 → SHARD-3 → SHARD-4 → SHARD-2 (7 days)
Full Track: Add SHARD-5,6,7,8,10,11,12 (21 days total)
```

## 🎯 Success Criteria

The system is production-ready when:
- ✅ 24-hour continuous stream test passes
- ✅ Track switches are smooth (<200ms gap)
- ✅ Auto-recovery works for all failure scenarios
- ✅ Monitoring dashboard shows all metrics
- ✅ Documentation enables new user deployment
- ✅ Security audit passes
- ✅ Error rate <0.1% over 7 days
- ✅ Resource usage within budget

## 🔐 Security Considerations

- Webhook authentication (secret tokens)
- API bearer token authentication
- Rate limiting on all endpoints
- License manifest tracking
- Secrets management (env vars, never in code)
- Non-root container execution
- Read-only filesystems where possible

## 📈 Monitoring & Observability

- Real-time Prometheus metrics
- Grafana dashboards (pre-built)
- Structured JSON logging
- Track play history & analytics
- Error tracking with context
- Auto-recovery with notifications
- Health check endpoints

## 🔄 Data Flow

```
AzuraCast Track Change
    ↓
Metadata Watcher receives webhook
    ↓
Query Track Mapping database
    ↓
Spawn new FFmpeg process (with fade-in)
    ↓
FFmpeg: Loop Video + Live Audio → RTMP
    ↓
nginx-rtmp relay → YouTube
    ↓
Log event + Update analytics + Send notification
```

## 🚀 Quick Commands

### Start Infrastructure
```bash
docker-compose up -d
```

### Run Tests
```bash
pytest tests/ -v --cov
```

### View Logs
```bash
docker-compose logs -f metadata-watcher
```

### Check Stream
```bash
ffplay rtmp://localhost/live/stream
```

### Database Access
```bash
docker-compose exec postgres psql -U radio -d radio_db
```

## 📞 Support & Communication

### Daily Standup Format
Each team member reports:
1. **Yesterday**: Completed shards/tasks
2. **Today**: Current shard/tasks
3. **Blockers**: Dependencies waiting

### Issue Reporting
Use templates in [SHARD_DEPENDENCIES.md](./SHARD_DEPENDENCIES.md):
- Shard completion notifications
- Integration issues
- Blocker escalation

## 🎓 Learning Resources

- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [nginx-rtmp Module](https://github.com/arut/nginx-rtmp-module)
- [AzuraCast API](https://www.azuracast.com/api/)
- [YouTube Live Streaming](https://support.google.com/youtube/answer/2907883)
- [FastAPI Guide](https://fastapi.tiangolo.com/)
- [Docker Compose](https://docs.docker.com/compose/)

## 🤝 Contributing

### Development Workflow
1. Get assigned a shard
2. Create feature branch: `shard-X-name`
3. Implement following [AI_AGENT_QUICKSTART.md](./AI_AGENT_QUICKSTART.md)
4. Write tests (≥80% coverage)
5. Submit Pull Request
6. Pass code review
7. Merge to main

### Code Standards
- Python 3.11+ with type hints
- Black formatter (line length 100)
- Flake8 linting (zero errors)
- mypy type checking (strict mode)
- Google-style docstrings
- Comprehensive error handling

## 📝 License & Legal

- Ensure all audio tracks have proper licenses
- Maintain license manifest (see Shard 10)
- Log all plays for compliance
- Secure API endpoints
- Rate limit public endpoints

## 🎉 Acknowledgments

Architecture based on best practices for:
- 24/7 live streaming reliability
- FFmpeg video processing
- Microservices architecture
- Observability & monitoring
- DevOps automation

---

## 📁 Project Structure (After Completion)

```
liveradio_teki/
├── README.md                      # This file
├── DEVELOPMENT_SHARDS.md          # Technical specifications
├── SHARD_DEPENDENCIES.md          # Project management guide
├── AI_AGENT_QUICKSTART.md         # Developer quick start
├── shards.json                    # Machine-readable tasks
├── docker-compose.yml             # Service orchestration
├── .env.example                   # Environment template
│
├── metadata_watcher/              # Shard 2
│   ├── app.py
│   ├── ffmpeg_manager.py
│   ├── track_resolver.py
│   └── tests/
│
├── track_mapper/                  # Shard 3
│   ├── mapper.py
│   ├── schema.sql
│   └── migrations/
│
├── ffmpeg_manager/                # Shard 4
│   ├── process_manager.py
│   ├── command_builder.py
│   ├── log_parser.py
│   └── tests/
│
├── logging_module/                # Shard 5
│   ├── logger.py
│   ├── analytics.py
│   └── schema.sql
│
├── notifier/                      # Shard 6
│   ├── discord.py
│   ├── slack.py
│   └── notifier.py
│
├── monitoring/                    # Shard 7
│   ├── metrics.py
│   ├── health_checks.py
│   ├── ffmpeg_monitor.py
│   └── auto_recovery.py
│
├── asset_manager/                 # Shard 8
│   ├── validator.py
│   ├── overlay_generator.py
│   └── templates/
│
├── advanced/                      # Shard 9
│   ├── dual_input_ffmpeg.py
│   └── filter_graph_builder.py
│
├── security/                      # Shard 10
│   ├── auth.py
│   ├── rate_limiter.py
│   └── license_manager.py
│
├── tests/                         # Shard 11
│   ├── unit/
│   ├── integration/
│   ├── load/
│   └── failover/
│
├── docs/                          # Shard 12
│   ├── DEPLOYMENT.md
│   ├── CONFIGURATION.md
│   ├── TROUBLESHOOTING.md
│   ├── API.md
│   ├── ARCHITECTURE.md
│   └── FAQ.md
│
├── nginx-rtmp/                    # Shard 1
│   └── nginx.conf
│
├── scripts/
│   ├── seed_mappings.py
│   ├── validate_loops.py
│   └── run_all_tests.sh
│
└── grafana/
    └── dashboard.json
```

---

**Status**: Planning Complete ✅  
**Next Step**: Begin Shard 1 (Core Infrastructure)  
**Last Updated**: November 3, 2025  
**Version**: 1.0.0  

For questions or issues, refer to [AI_AGENT_QUICKSTART.md](./AI_AGENT_QUICKSTART.md) → Getting Help section.


