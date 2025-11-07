# Dashboard API

FastAPI backend for the 24/7 FFmpeg YouTube Radio Stream web dashboard.

## Features

- **JWT Authentication**: Secure token-based authentication with access and refresh tokens
- **Role-Based Access Control**: Admin, Operator, and Viewer roles
- **Stream Control**: Start, stop, restart, and monitor FFmpeg stream
- **Configuration Management**: Web-based configuration editing
- **User Management**: CRUD operations for user accounts
- **Audit Logging**: Track all user actions
- **RESTful API**: Clean, documented API endpoints

## Tech Stack

- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: Database ORM
- **PostgreSQL**: Database
- **JWT**: Authentication tokens
- **Pydantic**: Data validation
- **pytest**: Testing framework

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL database
- FFmpeg (for stream control)

### Setup

1. **Install dependencies:**

```bash
cd dashboard_api
pip install -r requirements.txt
```

2. **Configure environment:**

Copy `env.example` to `.env` and update values:

```bash
# Database
POSTGRES_USER=radio
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=radio_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Security
JWT_SECRET=your-random-jwt-secret-key

# CORS
CORS_ORIGINS=["http://localhost:3000"]
```

3. **Initialize database:**

```bash
# Run schema.sql to create tables
psql -U radio -d radio_db -f schema.sql
```

4. **Run the server:**

```bash
python -m dashboard_api.main
```

Or with uvicorn:

```bash
uvicorn dashboard_api.main:app --host 0.0.0.0 --port 9001 --reload
```

## API Documentation

Once running, access interactive API documentation at:

- **Swagger UI**: http://localhost:9001/docs
- **ReDoc**: http://localhost:9001/redoc
- **OpenAPI JSON**: http://localhost:9001/openapi.json

## API Endpoints

### Authentication (`/api/v1/auth`)

- `POST /login` - Login with username/password
- `POST /refresh` - Refresh access token
- `POST /logout` - Logout and revoke token
- `GET /me` - Get current user info

### Stream Control (`/api/v1/stream`)

- `GET /status` - Get stream status
- `POST /start` - Start FFmpeg stream (operator+)
- `POST /stop` - Stop FFmpeg stream (operator+)
- `POST /restart` - Restart FFmpeg stream (operator+)
- `POST /switch` - Manual track switch (operator+)

### Configuration (`/api/v1/config`)

- `GET /` - Get all settings
- `GET /{category}` - Get settings by category
- `PUT /{category}/{key}` - Update single setting (operator+)
- `POST /bulk-update` - Bulk update settings (operator+)
- `GET /export` - Export configuration (admin)

### User Management (`/api/v1/users`)

- `GET /` - List all users (admin)
- `GET /{user_id}` - Get user by ID (admin)
- `POST /` - Create new user (admin)
- `PUT /{user_id}` - Update user (admin)
- `DELETE /{user_id}` - Delete user (admin)

## Authentication

All endpoints except `/login` require authentication.

1. **Login** to get tokens:

```bash
curl -X POST http://localhost:9001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

2. **Use access token** in requests:

```bash
curl http://localhost:9001/api/v1/stream/status \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

3. **Refresh token** when expired:

```bash
curl -X POST http://localhost:9001/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'
```

## Default Credentials

**⚠️ CHANGE THESE IN PRODUCTION!**

- Username: `admin`
- Password: `admin123`

## User Roles

- **Admin**: Full access to everything
- **Operator**: Can control stream, manage settings, view monitoring
- **Viewer**: Read-only access

## Testing

Run tests with pytest:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dashboard_api --cov-report=html

# Run specific test file
pytest dashboard_api/tests/test_auth.py
```

## Docker Deployment

Build and run with Docker:

```bash
# Build image
docker build -t radio-dashboard-api .

# Run container
docker run -d \
  -p 9001:9001 \
  -e POSTGRES_PASSWORD=your-password \
  -e JWT_SECRET=your-jwt-secret \
  --name dashboard-api \
  radio-dashboard-api
```

Or use docker-compose (see main project docker-compose.yml).

## Project Structure

```
dashboard_api/
├── __init__.py
├── main.py                 # FastAPI app
├── config.py               # Configuration
├── database.py             # Database connection
├── dependencies.py         # FastAPI dependencies
├── models/                 # Database & Pydantic models
│   ├── user.py
│   ├── config.py
│   ├── audit.py
│   └── asset.py
├── routes/                 # API endpoints
│   ├── auth.py
│   ├── stream.py
│   ├── config.py
│   └── users.py
├── middleware/             # Custom middleware
│   └── error_handler.py
├── services/               # Business logic
│   ├── auth_service.py
│   └── stream_service.py
├── utils/                  # Utilities
│   ├── crypto.py
│   ├── validators.py
│   └── helpers.py
├── tests/                  # Tests
│   ├── conftest.py
│   ├── test_auth.py
│   └── test_stream.py
├── schema.sql              # Database schema
├── requirements.txt
├── Dockerfile
└── README.md
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_USER` | Database user | `radio` |
| `POSTGRES_PASSWORD` | Database password | *required* |
| `POSTGRES_DB` | Database name | `radio_db` |
| `POSTGRES_HOST` | Database host | `postgres` |
| `POSTGRES_PORT` | Database port | `5432` |
| `JWT_SECRET` | JWT signing secret | *required* |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token expiry | `60` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiry | `7` |
| `CORS_ORIGINS` | Allowed CORS origins | `["http://localhost:3000"]` |
| `DEBUG` | Enable debug mode | `false` |
| `ENVIRONMENT` | Environment name | `production` |
| `PORT` | Server port | `9001` |

## Security Considerations

- Change default admin password immediately
- Use strong JWT secret (32+ characters, random)
- Enable HTTPS in production
- Restrict CORS origins to your frontend domain
- Set secure database password
- Review audit logs regularly
- Keep dependencies updated

## Troubleshooting

### Database Connection Error

Ensure PostgreSQL is running and credentials are correct:

```bash
psql -U radio -d radio_db -h localhost
```

### JWT Token Error

Ensure `JWT_SECRET` is set in environment variables.

### FFmpeg Not Found

Install FFmpeg:

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

## Development

### Code Style

- Use Black for formatting
- Follow PEP 8
- Type hints encouraged

### Adding New Endpoints

1. Create route in `routes/`
2. Add service logic in `services/`
3. Add models in `models/` if needed
4. Write tests in `tests/`
5. Update this README

## License

Part of the 24/7 FFmpeg YouTube Radio Stream project.

## Support

See main project documentation for support information.


