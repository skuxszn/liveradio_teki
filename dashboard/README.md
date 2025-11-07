# Radio Stream Dashboard

React + TypeScript + Vite web dashboard for the 24/7 FFmpeg YouTube Radio Stream project.

## Features

- **Authentication**: Secure login with JWT tokens
- **Dashboard Overview**: Stream status and metrics at a glance
- **Stream Control**: Start, stop, and restart FFmpeg stream
- **Real-time Updates**: Auto-refreshing status every 3-5 seconds
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Modern UI**: Built with Tailwind CSS and custom components

## Tech Stack

- **React 18**: Modern React with hooks
- **TypeScript**: Type-safe development
- **Vite**: Fast build tool and dev server
- **Tailwind CSS**: Utility-first CSS framework
- **React Router**: Client-side routing
- **React Query**: Server state management
- **Zustand**: Client state management
- **Axios**: HTTP client with interceptors

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Dashboard API running on `http://localhost:9001`

### Installation

1. **Install dependencies:**

```bash
cd dashboard
npm install
```

2. **Configure environment:**

Create `.env` file:

```bash
VITE_API_URL=http://localhost:9001/api/v1
```

3. **Run development server:**

```bash
npm run dev
```

The dashboard will be available at http://localhost:5173

### Building for Production

```bash
npm run build
```

The production build will be in the `dist/` directory.

## Project Structure

```
dashboard/
├── src/
│   ├── components/
│   │   ├── ui/              # Reusable UI components
│   │   ├── layout/          # Layout components (Sidebar, Navbar)
│   │   └── auth/            # Auth components
│   ├── pages/               # Page components
│   │   ├── Login.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Stream.tsx
│   │   ├── Settings.tsx
│   │   └── Users.tsx
│   ├── services/            # API services
│   │   ├── api.ts
│   │   ├── auth.service.ts
│   │   └── stream.service.ts
│   ├── store/               # Zustand stores
│   │   └── authStore.ts
│   ├── types/               # TypeScript types
│   ├── utils/               # Utility functions
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── Dockerfile
└── README.md
```

## Available Pages

### Login (`/login`)
- Username/password authentication
- JWT token management
- Default credentials: `admin` / `admin123`

### Dashboard (`/`)
- Stream status overview
- Current track information
- Quick stats cards
- Auto-refreshing every 5 seconds

### Stream Control (`/stream`)
- Start/Stop/Restart buttons
- Real-time status indicator
- Current track details
- Auto-refreshing every 3 seconds

### Settings (`/settings`)
- Configuration management (coming in SHARD-17)

### Users (`/users`)
- User management (coming in SHARD-20)
- Admin only

## Usage

### Login

1. Navigate to http://localhost:5173
2. Enter credentials (default: `admin` / `admin123`)
3. Click Login

### Control Stream

1. Go to Stream Control page
2. Click "Start Stream" to begin broadcasting
3. Click "Stop Stream" to halt broadcasting
4. Click "Restart Stream" to restart the FFmpeg process

### Monitor Status

- Dashboard page shows overall status
- Stream status updates automatically
- Current track displays artist and title

## Docker Deployment

### Build Image

```bash
docker build -t radio-dashboard-ui .
```

### Run Container

```bash
docker run -d \
  -p 3000:80 \
  -e VITE_API_URL=http://localhost:9001/api/v1 \
  --name dashboard-ui \
  radio-dashboard-ui
```

Or use docker-compose (see main project).

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

### Code Style

- TypeScript strict mode enabled
- ESLint for code quality
- Prettier for formatting (recommended)

### Adding New Pages

1. Create component in `src/pages/`
2. Add route in `src/App.tsx`
3. Add navigation link in `src/components/layout/Sidebar.tsx`

### Adding New API Calls

1. Add service function in `src/services/`
2. Define TypeScript types in `src/types/`
3. Use with React Query in components

## API Integration

The dashboard communicates with the backend API at `/api/v1`:

- Authentication: `/auth/*`
- Stream Control: `/stream/*`
- Configuration: `/config/*`
- User Management: `/users/*`

All authenticated requests include JWT token in `Authorization` header.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:9001/api/v1` |

## Authentication Flow

1. User submits login form
2. POST `/auth/login` with credentials
3. Receive access token and refresh token
4. Store tokens in localStorage via Zustand
5. Add access token to all API requests
6. Auto-refresh when token expires
7. Logout revokes refresh token

## State Management

- **Server State**: React Query for API data
- **Client State**: Zustand for auth and UI state
- **Local Storage**: Persists auth tokens and user info

## Styling

- Tailwind CSS utility classes
- Custom CSS variables for theming
- Responsive breakpoints: mobile (320px+), tablet (768px+), desktop (1024px+)

## Browser Support

- Chrome/Edge (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)

## Troubleshooting

### Cannot connect to API

Ensure:
- Dashboard API is running on port 9001
- CORS is configured to allow `http://localhost:5173`
- Environment variable `VITE_API_URL` is set correctly

### Login fails

- Check default credentials: `admin` / `admin123`
- Ensure database is initialized with default user
- Check browser console for errors

### Stream control not working

- Ensure user has operator or admin role
- Check FFmpeg is available on the server
- Review backend logs for errors

## Next Steps

This is the MVP frontend (SHARD-14). Additional features coming:

- **SHARD-15**: Enhanced stream control UI with logs
- **SHARD-17**: Full settings management interface
- **SHARD-20**: Complete user management with CRUD

## License

Part of the 24/7 FFmpeg YouTube Radio Stream project.

## Support

See main project documentation for support information.
