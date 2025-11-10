/**
 * Monitoring Dashboard page.
 * Real-time metrics, charts, and activity feed.
 */

import { useQuery } from '@tanstack/react-query';
import { Activity, TrendingUp, TrendingDown, Minus, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import metricsService from '@/services/metrics.service';
import { formatDistanceToNow } from 'date-fns';
import { CardSkeleton } from '@/components/skeletons/CardSkeleton';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import LogsTab from '@/components/monitoring/LogsTab';
import { useSearchParams } from 'react-router-dom';
import { QueryError } from '@/components/common/QueryError';

export default function Monitoring() {
  // Fetch current metrics (refresh every 10 seconds)
  const { data: current } = useQuery({
    queryKey: ['metrics-current'],
    queryFn: () => metricsService.getCurrent(),
    refetchInterval: 10000,
  });

  // Fetch historical data (24 hours)
  const { data: history } = useQuery({
    queryKey: ['metrics-history'],
    queryFn: () => metricsService.getHistory(24),
    refetchInterval: 60000, // Refresh every minute
  });

  // Fetch summary
  const { data: summary } = useQuery({
    queryKey: ['metrics-summary'],
    queryFn: () => metricsService.getSummary(),
  });

  // Fetch activity feed (refresh every 30 seconds)
  const { data: activityData } = useQuery({
    queryKey: ['metrics-activity'],
    queryFn: () => metricsService.getActivity(20),
    refetchInterval: 30000,
  });

  // Get trend indicator
  const getTrendIndicator = (value: number, threshold: number = 70) => {
    if (value > threshold) {
      return <TrendingUp className="w-4 h-4 text-red-500" />;
    } else if (value > threshold * 0.7) {
      return <Minus className="w-4 h-4 text-yellow-500" />;
    } else {
      return <TrendingDown className="w-4 h-4 text-green-500" />;
    }
  };

  // Format timestamp for chart
  const formatChartTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return `${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`;
  };

  const isLoading = !current || !history || !summary || !activityData;
  const isError = false; // placeholder for finer-grained error checks
  const [sp] = useSearchParams();
  const initialTab = sp.get('tab') === 'logs' ? 'logs' : 'metrics'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Monitoring</h1>
        <p className="text-gray-500">System telemetry, metrics, and activity</p>
      </div>

      <Tabs defaultValue={initialTab} className="space-y-6">
        <TabsList>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
        </TabsList>

        <TabsContent value="metrics" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {isLoading ? (<>
              <CardSkeleton />
              <CardSkeleton />
              <CardSkeleton />
              <CardSkeleton />
            </>) : (<>
            <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">CPU Usage</CardTitle>
            {current && getTrendIndicator(current.system.cpu_percent)}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {current?.system.cpu_percent.toFixed(1) || 0}%
            </div>
            <p className="text-xs text-gray-500 mt-1">System load</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Memory Usage</CardTitle>
            {current && getTrendIndicator(current.system.memory_percent)}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {current?.system.memory_percent.toFixed(1) || 0}%
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {current?.system.memory_used_mb.toFixed(0) || 0} /
              {current?.system.memory_total_mb.toFixed(0) || 0} MB
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Disk Usage</CardTitle>
            {current && getTrendIndicator(current.system.disk_percent)}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {current?.system.disk_percent.toFixed(1) || 0}%
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {current?.system.disk_used_gb.toFixed(1) || 0} /
              {current?.system.disk_total_gb.toFixed(1) || 0} GB
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Tracks Today</CardTitle>
            <Activity className="w-4 h-4 text-gray-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{current?.tracks.today || 0}</div>
            <p className="text-xs text-gray-500 mt-1">
              {current?.tracks.total_mappings || 0} total
            </p>
          </CardContent>
        </Card>
        </>)}
          </div>

          {/* Error banner for metrics fetch failures (simplified) */}
          {isError && (
            <QueryError message="Failed to load metrics" onRetry={() => window.location.reload()} />
          )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>CPU & Memory (24h)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={history?.datapoints || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={formatChartTime}
                  fontSize={12}
                />
                <YAxis fontSize={12} />
                <Tooltip
                  labelFormatter={formatChartTime}
                  formatter={(value: number) => [`${value}%`, '']}
                />
                <Area
                  type="monotone"
                  dataKey="cpu_percent"
                  stroke="#3b82f6"
                  fill="#3b82f6"
                  fillOpacity={0.3}
                  name="CPU"
                />
                <Area
                  type="monotone"
                  dataKey="memory_percent"
                  stroke="#10b981"
                  fill="#10b981"
                  fillOpacity={0.3}
                  name="Memory"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Tracks Played (24h)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={history?.datapoints || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={formatChartTime}
                  fontSize={12}
                />
                <YAxis fontSize={12} />
                <Tooltip labelFormatter={formatChartTime} />
                <Line
                  type="monotone"
                  dataKey="tracks_played"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  dot={false}
                  name="Tracks"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Summary Stats */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Most Played Track</CardTitle>
            </CardHeader>
            <CardContent>
              {summary.tracks.most_played ? (
                <div>
                  <p className="font-medium truncate">
                    {summary.tracks.most_played.artist}
                  </p>
                  <p className="text-sm text-gray-600 truncate">
                    {summary.tracks.most_played.title}
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    {summary.tracks.most_played.play_count} plays
                  </p>
                </div>
              ) : (
                <p className="text-sm text-gray-500">No data</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Total Assets</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.assets.total}</div>
              <p className="text-xs text-gray-500 mt-1">Video loops</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Activity (24h)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{summary.activity.last_24h}</div>
              <p className="text-xs text-gray-500 mt-1">
                {summary.activity.active_users_7d} active users (7d)
              </p>
            </CardContent>
          </Card>
        </div>
      )}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {activityData?.activities && activityData.activities.length > 0 ? (
              activityData.activities.map((activity) => (
                <div
                  key={activity.id}
                  className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg"
                >
                  <Activity className="w-4 h-4 text-gray-500 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{activity.username}</span>
                      <span className="text-sm text-gray-600">{activity.action}</span>
                      {activity.resource_type && (
                        <span className="text-xs bg-gray-200 px-2 py-0.5 rounded">
                          {activity.resource_type}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <Clock className="w-3 h-3 text-gray-400" />
                      <span className="text-xs text-gray-500">
                        {formatDistanceToNow(new Date(activity.timestamp), {
                          addSuffix: true,
                        })}
                      </span>
                    </div>
                  </div>
                  <div>
                    {activity.success ? (
                      <span className="text-green-500 text-xs">✓</span>
                    ) : (
                      <span className="text-red-500 text-xs">✗</span>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-center text-gray-500 py-8">No recent activity</p>
            )}
          </div>
        </CardContent>
      </Card>
        </TabsContent>

        <TabsContent value="logs">
          <LogsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}


