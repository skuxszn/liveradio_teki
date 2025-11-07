/**
 * Shared TypeScript types for the dashboard.
 */

export interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  role: 'admin' | 'operator' | 'viewer';
  is_active: boolean;
  last_login?: string;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface StreamStatus {
  status: string;
  running: boolean;
  process?: any;
  current_track?: CurrentTrack;
  timestamp: string;
}

export interface CurrentTrack {
  track_key: string;
  artist: string;
  title: string;
  uptime_seconds: number;
  started_at: string;
  pid?: number;
}

export interface Setting {
  id: number;
  category: string;
  key: string;
  value?: string;
  value_type: string;
  default_value?: string;
  description?: string;
  is_secret: boolean;
  is_required: boolean;
  requires_restart: boolean;
}

export interface ApiError {
  detail: string;
  message?: string;
}


