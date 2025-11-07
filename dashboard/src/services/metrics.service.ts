/**
 * Monitoring and metrics service.
 */

import api from './api';

export interface CurrentMetrics {
  timestamp: string;
  system: {
    cpu_percent: number;
    memory_percent: number;
    memory_used_mb: number;
    memory_total_mb: number;
    disk_percent: number;
    disk_used_gb: number;
    disk_total_gb: number;
  };
  stream: {
    status: string;
    pid: number | null;
    uptime_seconds: number;
  };
  tracks: {
    today: number;
    total_mappings: number;
  };
}

export interface MetricsHistory {
  period_hours: number;
  datapoints: Array<{
    timestamp: string;
    cpu_percent: number;
    memory_percent: number;
    tracks_played: number;
  }>;
}

export interface MetricsSummary {
  tracks: {
    total: number;
    most_played: {
      artist: string;
      title: string;
      play_count: number;
    } | null;
  };
  assets: {
    total: number;
  };
  activity: {
    last_24h: number;
    active_users_7d: number;
  };
}

export interface Activity {
  id: number;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: any;
  timestamp: string;
  success: boolean;
  username: string;
}

export const metricsService = {
  /**
   * Get current metrics.
   */
  async getCurrent(): Promise<CurrentMetrics> {
    const response = await api.get<CurrentMetrics>('/metrics/current');
    return response.data;
  },

  /**
   * Get historical metrics.
   */
  async getHistory(hours: number = 24): Promise<MetricsHistory> {
    const response = await api.get<MetricsHistory>('/metrics/history', {
      params: { hours },
    });
    return response.data;
  },

  /**
   * Get metrics summary.
   */
  async getSummary(): Promise<MetricsSummary> {
    const response = await api.get<MetricsSummary>('/metrics/summary');
    return response.data;
  },

  /**
   * Get recent activity.
   */
  async getActivity(limit: number = 50): Promise<{ activities: Activity[]; count: number }> {
    const response = await api.get('/metrics/activity', {
      params: { limit },
    });
    return response.data;
  },
};

export default metricsService;


