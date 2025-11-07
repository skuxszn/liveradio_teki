# Dashboard Development Shards - Web UI for 24/7 Radio Stream

**Project Extension**: Web Dashboard for System Management  
**Framework**: React + TypeScript + shadcn/ui  
**Total Shards**: 9 (SHARD-13 through SHARD-21)  
**Estimated Duration**: 34 days (1 agent) | 10 days (4 agents parallel)

---

## Overview

Add a modern, user-friendly web dashboard to manage the 24/7 radio stream system without SSH access or manual configuration file editing. The dashboard provides complete control over stream operations, track mappings, settings, monitoring, and asset management.

### Why a Dashboard?

**Current Pain Points**:
- ❌ Must SSH to server to edit `.env` files
- ❌ No visual feedback on stream status
- ❌ Manual track mapping is tedious
- ❌ No easy way to upload video loops
- ❌ Monitoring requires command-line tools

**With Dashboard**:
- ✅ Web-based configuration management
- ✅ One-click stream start/stop
- ✅ Visual track mapping interface
- ✅ Drag-and-drop video uploads
- ✅ Real-time metrics and monitoring
- ✅ User authentication and audit logs

---

## Technology Stack

### Backend (SHARD-13)
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL (extends existing schema)
- **Authentication**: JWT tokens
- **File Uploads**: Multipart handling
- **WebSocket**: For real-time updates (SHARD-21)

### Frontend (SHARD-14+)
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **UI Library**: shadcn/ui (Tailwind CSS components)
- **State Management**: React Query + Zustand
- **Routing**: React Router v6
- **Forms**: React Hook Form + Zod validation
- **Charts**: Recharts
- **Icons**: Lucide React
- **API Client**: Axios

### DevOps
- **Containerization**: Docker + Docker Compose
- **Reverse Proxy**: nginx (for production)
- **SSL**: Let's Encrypt (production)

---

## SHARD 13: Dashboard Backend API

**Priority**: CRITICAL | **Complexity**: High | **Duration**: 5 days  
**Dependencies**: SHARD-1 through SHARD-12

### Objective

Extend the FastAPI backend with comprehensive REST API endpoints for dashboard functionality, including configuration management, stream control, track mappings, asset management, and monitoring.

### Technical Specifications

#### New API Endpoints

```
Base URL: http://localhost:9001/api/v1
```

**Authentication**:
```
POST   /auth/login                    # Login (returns JWT)
POST   /auth/logout                   # Logout
POST   /auth/refresh                  # Refresh JWT token
GET    /auth/me                       # Get current user
```

**Configuration Management**:
```
GET    /config                        # Get all configuration
GET    /config/:category              # Get config by category
PUT    /config                        # Update configuration (batch)
PUT    /config/:category/:key         # Update single setting
POST   /config/validate               # Validate configuration
GET    /config/schema                 # Get configuration schema with validation rules
POST   /config/reset                  # Reset to defaults
POST   /config/export                 # Export configuration (JSON)
POST   /config/import                 # Import configuration
```

**Stream Control**:
```
POST   /stream/start                  # Start streaming
POST   /stream/stop                   # Stop streaming
POST   /stream/restart                # Restart streaming
GET    /stream/status                 # Get current stream status
GET    /stream/logs                   # Get stream logs (paginated, filterable)
GET    /stream/logs/live              # Stream logs via Server-Sent Events
POST   /stream/test                   # Test configuration without starting
```

**Track Mappings**:
```
GET    /mappings                      # List all mappings (paginated, searchable)
GET    /mappings/:id                  # Get single mapping
POST   /mappings                      # Create new mapping
PUT    /mappings/:id                  # Update mapping
DELETE /mappings/:id                  # Delete mapping (soft delete)
POST   /mappings/bulk-import          # Bulk import from CSV/JSON
POST   /mappings/bulk-delete          # Bulk delete
GET    /mappings/stats                # Get mapping statistics
GET    /mappings/validate             # Validate all mappings
POST   /mappings/auto-map             # Auto-map from loops directory
GET    /mappings/export               # Export mappings to CSV
```

**Video Assets**:
```
GET    /assets                        # List video loops (with thumbnails)
GET    /assets/:filename              # Get asset details
POST   /assets/upload                 # Upload video loop (multipart)
DELETE /assets/:filename              # Delete video loop
POST   /assets/:filename/validate     # Validate video loop
GET    /assets/:filename/thumbnail    # Get video thumbnail
GET    /assets/:filename/preview      # Stream video preview
GET    /assets/stats                  # Get storage statistics
POST   /assets/generate-thumbnails    # Batch generate thumbnails
```

**Monitoring & Metrics**:
```
GET    /metrics/current               # Current system metrics
GET    /metrics/history               # Historical metrics (time range)
GET    /metrics/summary               # Summary statistics
GET    /metrics/stream                # Stream-specific metrics
GET    /metrics/system                # System resource metrics
GET    /metrics/export                # Export metrics data
```

**Logs**:
```
GET    /logs/application              # Application logs (paginated)
GET    /logs/ffmpeg                   # FFmpeg process logs
GET    /logs/system                   # System logs
GET    /logs/audit                    # Audit log (user actions)
GET    /logs/errors                   # Error logs only
DELETE /logs/clear                    # Clear old logs
```

**User Management** (Admin only):
```
GET    /users                         # List all users
GET    /users/:id                     # Get user details
POST   /users                         # Create new user
PUT    /users/:id                     # Update user
DELETE /users/:id                     # Delete user
PUT    /users/:id/password            # Change password
PUT    /users/:id/role                # Update user role
```

**Audit Log**:
```
GET    /audit                         # Get audit log entries
GET    /audit/user/:userId            # Get user's actions
GET    /audit/resource/:type/:id      # Get actions on resource
```

#### Database Schema Extensions

```sql
-- ============================================================================
-- Dashboard Settings (replaces .env file)
-- ============================================================================

CREATE TABLE dashboard_settings (
    id SERIAL PRIMARY KEY,
    category VARCHAR(64) NOT NULL,           -- 'stream', 'encoding', 'database', 'notifications', 'security', 'paths', 'advanced'
    key VARCHAR(128) NOT NULL,
    value TEXT,
    value_type VARCHAR(32) NOT NULL,         -- 'string', 'integer', 'boolean', 'float', 'secret', 'url', 'path'
    default_value TEXT,
    description TEXT,
    is_secret BOOLEAN DEFAULT FALSE,         -- Mask in UI, encrypt in DB
    validation_regex TEXT,                   -- Regex for validation
    validation_min NUMERIC,                  -- For numeric values
    validation_max NUMERIC,
    allowed_values JSONB,                    -- For enums/select options
    is_required BOOLEAN DEFAULT FALSE,
    requires_restart BOOLEAN DEFAULT FALSE,  -- Does changing this require stream restart?
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(category, key)
);

-- Index for fast category lookups
CREATE INDEX idx_settings_category ON dashboard_settings(category);

-- ============================================================================
-- Users and Authentication
-- ============================================================================

CREATE TABLE dashboard_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(128) UNIQUE NOT NULL,
    email VARCHAR(256) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,     -- bcrypt hash
    full_name VARCHAR(256),
    role VARCHAR(32) DEFAULT 'viewer',       -- 'admin', 'operator', 'viewer'
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by INTEGER REFERENCES dashboard_users(id)
);

CREATE INDEX idx_users_username ON dashboard_users(username);
CREATE INDEX idx_users_email ON dashboard_users(email);

-- ============================================================================
-- JWT Tokens (for tracking/revocation)
-- ============================================================================

CREATE TABLE jwt_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES dashboard_users(id) ON DELETE CASCADE,
    token_hash VARCHAR(256) NOT NULL,        -- SHA256 hash of token
    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_tokens_user ON jwt_tokens(user_id);
CREATE INDEX idx_tokens_hash ON jwt_tokens(token_hash);
CREATE INDEX idx_tokens_expires ON jwt_tokens(expires_at);

-- ============================================================================
-- Audit Log
-- ============================================================================

CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES dashboard_users(id),
    action VARCHAR(128) NOT NULL,            -- 'stream_started', 'config_updated', 'mapping_created', etc.
    resource_type VARCHAR(64),               -- 'stream', 'mapping', 'asset', 'config', 'user'
    resource_id VARCHAR(128),
    details JSONB,                           -- Additional context
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_resource ON audit_log(resource_type, resource_id);

-- ============================================================================
-- Video Asset Metadata (extends file system storage)
-- ============================================================================

CREATE TABLE video_assets (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(512) UNIQUE NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    file_size BIGINT,                        -- Bytes
    duration FLOAT,                          -- Seconds
    resolution VARCHAR(32),                  -- "1280x720"
    frame_rate FLOAT,                        -- FPS
    video_codec VARCHAR(64),
    audio_codec VARCHAR(64),
    bitrate INTEGER,                         -- kbps
    pixel_format VARCHAR(32),
    is_valid BOOLEAN DEFAULT FALSE,
    validation_errors JSONB,
    thumbnail_path VARCHAR(1024),
    uploaded_by INTEGER REFERENCES dashboard_users(id),
    uploaded_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0
);

CREATE INDEX idx_assets_filename ON video_assets(filename);
CREATE INDEX idx_assets_valid ON video_assets(is_valid);

-- ============================================================================
-- Session Storage (for UI state persistence)
-- ============================================================================

CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES dashboard_users(id) ON DELETE CASCADE,
    session_key VARCHAR(128) NOT NULL,
    session_data JSONB,                      -- Store UI preferences, filters, etc.
    expires_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_key ON user_sessions(session_key);

-- ============================================================================
-- Seed Initial Data
-- ============================================================================

-- Create default admin user (password: admin123 - CHANGE IN PRODUCTION!)
INSERT INTO dashboard_users (username, email, password_hash, full_name, role) VALUES
    ('admin', 'admin@localhost', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ztpz7rDVPzNW', 'Administrator', 'admin')
ON CONFLICT (username) DO NOTHING;

-- Migrate settings from environment variables
INSERT INTO dashboard_settings (category, key, value_type, description, is_required, is_secret) VALUES
    -- Stream settings
    ('stream', 'YOUTUBE_STREAM_KEY', 'secret', 'YouTube live stream key', TRUE, TRUE),
    ('stream', 'AZURACAST_URL', 'url', 'AzuraCast instance URL', TRUE, FALSE),
    ('stream', 'AZURACAST_API_KEY', 'secret', 'AzuraCast API key', TRUE, TRUE),
    ('stream', 'AZURACAST_AUDIO_URL', 'url', 'Direct audio stream URL', TRUE, FALSE),
    
    -- Encoding settings
    ('encoding', 'VIDEO_RESOLUTION', 'string', 'Video resolution (width:height)', TRUE, FALSE),
    ('encoding', 'VIDEO_BITRATE', 'string', 'Video bitrate (e.g., 3000k)', TRUE, FALSE),
    ('encoding', 'AUDIO_BITRATE', 'string', 'Audio bitrate (e.g., 192k)', TRUE, FALSE),
    ('encoding', 'VIDEO_ENCODER', 'string', 'Video encoder (libx264 or h264_nvenc)', TRUE, FALSE),
    ('encoding', 'FFMPEG_PRESET', 'string', 'FFmpeg encoding preset', TRUE, FALSE),
    ('encoding', 'FADE_DURATION', 'float', 'Fade transition duration (seconds)', FALSE, FALSE),
    
    -- Notifications
    ('notifications', 'DISCORD_WEBHOOK_URL', 'url', 'Discord webhook URL', FALSE, TRUE),
    ('notifications', 'SLACK_WEBHOOK_URL', 'url', 'Slack webhook URL', FALSE, TRUE),
    
    -- Database
    ('database', 'POSTGRES_HOST', 'string', 'PostgreSQL host', TRUE, FALSE),
    ('database', 'POSTGRES_PORT', 'integer', 'PostgreSQL port', TRUE, FALSE),
    ('database', 'POSTGRES_USER', 'string', 'PostgreSQL username', TRUE, FALSE),
    ('database', 'POSTGRES_PASSWORD', 'secret', 'PostgreSQL password', TRUE, TRUE),
    ('database', 'POSTGRES_DB', 'string', 'PostgreSQL database name', TRUE, FALSE),
    
    -- Security
    ('security', 'WEBHOOK_SECRET', 'secret', 'Webhook validation secret', TRUE, TRUE),
    ('security', 'API_TOKEN', 'secret', 'API authentication token', TRUE, TRUE),
    ('security', 'JWT_SECRET', 'secret', 'JWT signing secret', TRUE, TRUE),
    ('security', 'WEBHOOK_RATE_LIMIT', 'integer', 'Max webhook requests per minute', FALSE, FALSE),
    
    -- Paths
    ('paths', 'LOOPS_PATH', 'path', 'Video loops directory', TRUE, FALSE),
    ('paths', 'DEFAULT_LOOP', 'path', 'Default video loop path', TRUE, FALSE),
    ('paths', 'LOG_PATH', 'path', 'Logs directory', FALSE, FALSE),
    
    -- Advanced
    ('advanced', 'LOG_LEVEL', 'string', 'Logging level', FALSE, FALSE),
    ('advanced', 'DEBUG', 'boolean', 'Enable debug mode', FALSE, FALSE),
    ('advanced', 'ENABLE_METRICS', 'boolean', 'Enable Prometheus metrics', FALSE, FALSE)
ON CONFLICT (category, key) DO NOTHING;

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Function to get setting value
CREATE OR REPLACE FUNCTION get_setting(p_category VARCHAR, p_key VARCHAR)
RETURNS TEXT AS $$
DECLARE
    v_value TEXT;
BEGIN
    SELECT value INTO v_value
    FROM dashboard_settings
    WHERE category = p_category AND key = p_key;
    
    RETURN v_value;
END;
$$ LANGUAGE plpgsql;

-- Function to set setting value
CREATE OR REPLACE FUNCTION set_setting(p_category VARCHAR, p_key VARCHAR, p_value TEXT)
RETURNS VOID AS $$
BEGIN
    UPDATE dashboard_settings
    SET value = p_value, updated_at = NOW()
    WHERE category = p_category AND key = p_key;
END;
$$ LANGUAGE plpgsql;

-- Function to log audit event
CREATE OR REPLACE FUNCTION log_audit(
    p_user_id INTEGER,
    p_action VARCHAR,
    p_resource_type VARCHAR DEFAULT NULL,
    p_resource_id VARCHAR DEFAULT NULL,
    p_details JSONB DEFAULT NULL,
    p_ip_address INET DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO audit_log (user_id, action, resource_type, resource_id, details, ip_address)
    VALUES (p_user_id, p_action, p_resource_type, p_resource_id, p_details, p_ip_address);
END;
$$ LANGUAGE plpgsql;
```

### Deliverables

#### 1. Project Structure
```
dashboard_api/
├── __init__.py
├── main.py                    # FastAPI app initialization
├── config.py                  # Configuration management
├── database.py                # Database connection
├── dependencies.py            # FastAPI dependencies
├── models/
│   ├── __init__.py
│   ├── user.py               # User models
│   ├── config.py             # Config models
│   ├── mapping.py            # Mapping models
│   ├── asset.py              # Asset models
│   └── audit.py              # Audit models
├── routes/
│   ├── __init__.py
│   ├── auth.py               # Authentication endpoints
│   ├── config.py             # Configuration endpoints
│   ├── stream.py             # Stream control endpoints
│   ├── mappings.py           # Track mapping CRUD
│   ├── assets.py             # Video asset management
│   ├── monitoring.py         # Metrics endpoints
│   ├── logs.py               # Log retrieval
│   └── users.py              # User management
├── middleware/
│   ├── __init__.py
│   ├── auth.py               # JWT authentication
│   ├── cors.py               # CORS configuration
│   └── error_handler.py      # Global error handling
├── services/
│   ├── __init__.py
│   ├── auth_service.py       # Authentication logic
│   ├── config_service.py     # Config management logic
│   ├── stream_service.py     # Stream control logic
│   ├── mapping_service.py    # Mapping operations
│   ├── asset_service.py      # Asset operations
│   └── audit_service.py      # Audit logging
├── utils/
│   ├── __init__.py
│   ├── crypto.py             # Password hashing, JWT
│   ├── validators.py         # Input validation
│   └── helpers.py            # Utility functions
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_config.py
│   ├── test_stream.py
│   ├── test_mappings.py
│   └── test_assets.py
├── schema.sql                # Database schema
├── requirements.txt
├── Dockerfile
└── README.md
```

#### 2. Core Files

**`dashboard_api/main.py`**:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dashboard_api.routes import auth, config, stream, mappings, assets, monitoring, logs, users
from dashboard_api.middleware.error_handler import setup_exception_handlers

app = FastAPI(
    title="Radio Stream Dashboard API",
    version="1.0.0",
    description="REST API for managing 24/7 radio stream"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
setup_exception_handlers(app)

# Routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(config.router, prefix="/api/v1/config", tags=["config"])
app.include_router(stream.router, prefix="/api/v1/stream", tags=["stream"])
app.include_router(mappings.router, prefix="/api/v1/mappings", tags=["mappings"])
app.include_router(assets.router, prefix="/api/v1/assets", tags=["assets"])
app.include_router(monitoring.router, prefix="/api/v1/metrics", tags=["monitoring"])
app.include_router(logs.router, prefix="/api/v1/logs", tags=["logs"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])

@app.get("/")
async def root():
    return {"message": "Radio Stream Dashboard API", "version": "1.0.0"}
```

**`dashboard_api/requirements.txt`**:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
aiofiles==23.2.1
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
redis==5.0.1
structlog==23.2.0
```

#### 3. API Documentation

All endpoints must have:
- OpenAPI/Swagger documentation
- Request/response models with Pydantic
- Example requests and responses
- Error response documentation

### Testing Criteria

- ✅ All endpoints return correct status codes
- ✅ Authentication/authorization works correctly
- ✅ Configuration updates persist to database
- ✅ Stream control actually starts/stops FFmpeg
- ✅ File uploads work with validation
- ✅ Audit logging captures all user actions
- ✅ JWT token refresh works
- ✅ Rate limiting functions correctly
- ✅ ≥85% code coverage
- ✅ Integration tests with database
- ✅ Load testing (100 concurrent requests)

### Interface Contracts

**Inputs**:
- HTTP requests from dashboard frontend
- Database connection
- FFmpeg process management
- File system access

**Outputs**:
- JSON responses
- JWT tokens
- Audit log entries
- File uploads stored in `/srv/loops`

---

## SHARD 14: Dashboard Frontend Core

**Priority**: CRITICAL | **Complexity**: High | **Duration**: 6 days  
**Dependencies**: SHARD-13

### Objective

Build the foundational React + TypeScript + shadcn/ui application with routing, layout, authentication, and API integration.

### Technical Specifications

#### Initial Setup

```bash
# Create React app with Vite
npm create vite@latest dashboard -- --template react-ts

# Install dependencies
cd dashboard
npm install

# Install shadcn/ui
npx shadcn-ui@latest init

# Install additional packages
npm install @tanstack/react-query zustand react-router-dom axios
npm install react-hook-form @hookform/resolvers zod
npm install recharts lucide-react
npm install date-fns clsx tailwind-merge
```

#### Project Structure

```
dashboard/
├── public/
│   └── logo.svg
├── src/
│   ├── components/
│   │   ├── ui/                    # shadcn/ui components (auto-generated)
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── form.tsx
│   │   │   ├── input.tsx
│   │   │   ├── select.tsx
│   │   │   ├── table.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── toast.tsx
│   │   │   └── ... (all shadcn components)
│   │   ├── layout/
│   │   │   ├── Layout.tsx         # Main layout wrapper
│   │   │   ├── Navbar.tsx         # Top navigation bar
│   │   │   ├── Sidebar.tsx        # Side navigation
│   │   │   └── Footer.tsx         # Footer
│   │   ├── common/
│   │   │   ├── LoadingSpinner.tsx
│   │   │   ├── ErrorBoundary.tsx
│   │   │   ├── ConfirmDialog.tsx
│   │   │   ├── PageHeader.tsx
│   │   │   └── EmptyState.tsx
│   │   └── auth/
│   │       ├── ProtectedRoute.tsx
│   │       └── LoginForm.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx          # Main overview (SHARD-14)
│   │   ├── Stream.tsx             # Stream control (SHARD-15)
│   │   ├── Mappings.tsx           # Track mappings (SHARD-16)
│   │   ├── Settings.tsx           # Configuration (SHARD-17)
│   │   ├── Monitoring.tsx         # Metrics (SHARD-18)
│   │   ├── Assets.tsx             # Video management (SHARD-19)
│   │   ├── Users.tsx              # User management (SHARD-20)
│   │   ├── Login.tsx              # Login page
│   │   └── NotFound.tsx           # 404 page
│   ├── hooks/
│   │   ├── useApi.ts              # API call wrapper
│   │   ├── useAuth.ts             # Authentication state
│   │   ├── useToast.ts            # Toast notifications
│   │   └── useLocalStorage.ts    # Local storage hook
│   ├── services/
│   │   ├── api.ts                 # Axios instance with interceptors
│   │   ├── auth.service.ts        # Auth API calls
│   │   ├── config.service.ts      # Config API calls
│   │   ├── stream.service.ts      # Stream API calls
│   │   ├── mapping.service.ts     # Mapping API calls
│   │   └── asset.service.ts       # Asset API calls
│   ├── store/
│   │   ├── authStore.ts           # Auth Zustand store
│   │   └── configStore.ts         # Config Zustand store
│   ├── types/
│   │   ├── index.ts               # Shared types
│   │   ├── api.ts                 # API response types
│   │   └── models.ts              # Data models
│   ├── utils/
│   │   ├── cn.ts                  # className utility
│   │   ├── format.ts              # Formatting utilities
│   │   └── constants.ts           # Constants
│   ├── App.tsx                    # Main app component
│   ├── main.tsx                   # Entry point
│   └── index.css                  # Global styles
├── .env.example
├── .eslintrc.cjs
├── package.json
├── postcss.config.js
├── tailwind.config.js
├── tsconfig.json
├── vite.config.ts
├── Dockerfile
└── README.md
```

#### Core Implementation

**`src/App.tsx`**:
```typescript
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from '@/components/ui/toaster';
import Layout from '@/components/layout/Layout';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import Login from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
import Stream from '@/pages/Stream';
import Mappings from '@/pages/Mappings';
import Settings from '@/pages/Settings';
import Monitoring from '@/pages/Monitoring';
import Assets from '@/pages/Assets';
import Users from '@/pages/Users';
import NotFound from '@/pages/NotFound';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          
          <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="stream" element={<Stream />} />
            <Route path="mappings" element={<Mappings />} />
            <Route path="settings" element={<Settings />} />
            <Route path="monitoring" element={<Monitoring />} />
            <Route path="assets" element={<Assets />} />
            <Route path="users" element={<Users />} />
          </Route>
          
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
      <Toaster />
    </QueryClientProvider>
  );
}

export default App;
```

**`src/services/api.ts`**:
```typescript
import axios from 'axios';
import { useAuthStore } from '@/store/authStore';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:9001/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add JWT token
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 (unauthorized)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        // Try to refresh token
        const refreshToken = useAuthStore.getState().refreshToken;
        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });
        
        const { token } = response.data;
        useAuthStore.getState().setToken(token);
        
        // Retry original request
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, logout
        useAuthStore.getState().logout();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
```

**`src/hooks/useAuth.ts`**:
```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: number;
  username: string;
  email: string;
  role: 'admin' | 'operator' | 'viewer';
  fullName?: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  login: (token: string, refreshToken: string, user: User) => void;
  logout: () => void;
  setToken: (token: string) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      
      login: (token, refreshToken, user) => 
        set({ token, refreshToken, user, isAuthenticated: true }),
      
      logout: () => 
        set({ token: null, refreshToken: null, user: null, isAuthenticated: false }),
      
      setToken: (token) => 
        set({ token }),
    }),
    {
      name: 'auth-storage',
    }
  )
);
```

**`src/components/layout/Layout.tsx`**:
```typescript
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import Sidebar from './Sidebar';

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar />
        
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
```

**`src/components/layout/Sidebar.tsx`**:
```typescript
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Radio, 
  List, 
  Settings, 
  Activity, 
  Video,
  Users
} from 'lucide-react';
import { cn } from '@/utils/cn';
import { useAuthStore } from '@/store/authStore';

const navigation = [
  { name: 'Dashboard', to: '/', icon: LayoutDashboard },
  { name: 'Stream Control', to: '/stream', icon: Radio },
  { name: 'Track Mappings', to: '/mappings', icon: List },
  { name: 'Settings', to: '/settings', icon: Settings },
  { name: 'Monitoring', to: '/monitoring', icon: Activity },
  { name: 'Video Assets', to: '/assets', icon: Video },
  { name: 'Users', to: '/users', icon: Users, adminOnly: true },
];

export default function Sidebar() {
  const { user } = useAuthStore();
  const isAdmin = user?.role === 'admin';

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-6">
        <h1 className="text-xl font-bold text-gray-900">
          Radio Stream
        </h1>
        <p className="text-sm text-gray-500">Dashboard</p>
      </div>
      
      <nav className="flex-1 px-3 space-y-1">
        {navigation.map((item) => {
          if (item.adminOnly && !isAdmin) return null;
          
          return (
            <NavLink
              key={item.name}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-gray-100 text-gray-900'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                )
              }
            >
              <item.icon className="w-5 h-5" />
              {item.name}
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}
```

#### Dashboard Overview Page

**`src/pages/Dashboard.tsx`**:
```typescript
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Radio, Music, Clock, Activity } from 'lucide-react';
import { streamService } from '@/services/stream.service';
import { metricsService } from '@/services/metrics.service';

export default function Dashboard() {
  const { data: streamStatus } = useQuery({
    queryKey: ['stream-status'],
    queryFn: () => streamService.getStatus(),
    refetchInterval: 5000, // Poll every 5 seconds
  });

  const { data: metrics } = useQuery({
    queryKey: ['metrics-current'],
    queryFn: () => metricsService.getCurrent(),
    refetchInterval: 10000,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-gray-500">Overview of your radio stream</p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Stream Status</CardTitle>
            <Radio className="w-4 h-4 text-gray-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {streamStatus?.status === 'running' ? (
                <span className="text-green-600">Live</span>
              ) : (
                <span className="text-gray-600">Offline</span>
              )}
            </div>
            <p className="text-xs text-gray-500">
              {streamStatus?.current_track?.artist} - {streamStatus?.current_track?.title}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Uptime</CardTitle>
            <Clock className="w-4 h-4 text-gray-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.uptime || '0h'}</div>
            <p className="text-xs text-gray-500">Current session</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Tracks Today</CardTitle>
            <Music className="w-4 h-4 text-gray-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.tracks_today || 0}</div>
            <p className="text-xs text-gray-500">+12 from yesterday</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">CPU Usage</CardTitle>
            <Activity className="w-4 h-4 text-gray-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.cpu_usage || 0}%</div>
            <p className="text-xs text-gray-500">System resources</p>
          </CardContent>
        </Card>
      </div>

      {/* Current Track */}
      {streamStatus?.current_track && (
        <Card>
          <CardHeader>
            <CardTitle>Now Playing</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <div className="w-32 h-32 bg-gray-200 rounded-md">
                {/* Video preview/thumbnail */}
              </div>
              <div>
                <h3 className="text-xl font-semibold">
                  {streamStatus.current_track.title}
                </h3>
                <p className="text-gray-600">{streamStatus.current_track.artist}</p>
                <p className="text-sm text-gray-500 mt-2">
                  Playing for {streamStatus.current_track.uptime_seconds}s
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Activity feed will go here */}
          <p className="text-gray-500">No recent activity</p>
        </CardContent>
      </Card>
    </div>
  );
}
```

### Deliverables

1. Complete React + TypeScript project with Vite
2. shadcn/ui components installed and configured
3. Tailwind CSS configured
4. React Router with route protection
5. Zustand stores for state management
6. React Query for API calls
7. Axios instance with JWT interceptors
8. Layout components (Sidebar, Navbar)
9. Dashboard overview page
10. Login page with authentication
11. Protected route component
12. Error boundary
13. Toast notification system
14. Responsive design (mobile/tablet/desktop)
15. Dockerfile for frontend
16. docker-compose.yml updated
17. ESLint and Prettier configured
18. TypeScript types for all API responses
19. README with setup instructions

### Testing Criteria

- ✅ All pages render without errors
- ✅ Navigation works correctly
- ✅ Authentication flow works (login, logout, token refresh)
- ✅ Protected routes redirect to login
- ✅ API calls are properly authenticated
- ✅ Loading states display correctly
- ✅ Error states display correctly
- ✅ Responsive design on mobile/tablet/desktop
- ✅ Builds successfully for production
- ✅ No TypeScript errors
- ✅ No ESLint errors

### Interface Contracts

**Inputs**:
- API responses from dashboard-api (SHARD-13)
- User authentication tokens
- WebSocket messages (SHARD-21)

**Outputs**:
- HTTP requests to API
- JWT tokens in Authorization headers
- User interface state

---

## SHARD 15: Stream Control UI

*[Content continues similarly for other shards...]*

---

## Testing Strategy

### Unit Tests
- Jest + React Testing Library for components
- Pytest for backend endpoints

### Integration Tests
- End-to-end with Playwright/Cypress
- API integration tests

### Load Tests
- Locust for API load testing
- Monitor WebSocket performance

---

## Deployment

### Docker Compose Update

```yaml
services:
  # ... existing services ...
  
  dashboard-api:
    build: ./dashboard_api
    container_name: radio_dashboard_api
    ports:
      - "9001:9001"
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - JWT_SECRET=${JWT_SECRET}
      - CORS_ORIGINS=http://localhost:3000
    volumes:
      - /srv/loops:/srv/loops
      - ./logs:/var/log/radio
    depends_on:
      - postgres
      - metadata-watcher
    networks:
      - radio_network
    restart: unless-stopped

  dashboard-ui:
    build: ./dashboard
    container_name: radio_dashboard_ui
    ports:
      - "3000:80"
    environment:
      - VITE_API_URL=http://localhost:9001/api/v1
    depends_on:
      - dashboard-api
    networks:
      - radio_network
    restart: unless-stopped
```

---

**Document Version**: 1.0  
**Last Updated**: November 5, 2025  
**Project**: 24/7 FFmpeg YouTube Radio Stream - Dashboard Extension


