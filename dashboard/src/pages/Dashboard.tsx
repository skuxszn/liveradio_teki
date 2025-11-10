import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { streamService } from '@/services/stream.service';
import { CardSkeleton } from '@/components/skeletons/CardSkeleton';
import { Radio, Music, Timer, MonitorCheck } from 'lucide-react';
import OnboardingChecklist from '@/components/dashboard/OnboardingChecklist';
import { QueryError } from '@/components/common/QueryError';

export default function Dashboard() {
  const { data: streamStatus, isLoading, error, refetch } = useQuery({
    queryKey: ['stream-status'],
    queryFn: () => streamService.getStatus(),
    refetchInterval: 5000, // Poll every 5 seconds
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-gray-500">Operational overview and quick actions</p>
        </div>
        <OnboardingChecklist />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-gray-500">Operational overview and quick actions</p>
      </div>

      {error && (
        <QueryError message={(error as any)?.message} onRetry={() => refetch()} />
      )}

      <OnboardingChecklist />

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Stream Status</CardTitle>
            <Radio className="w-5 h-5 text-gray-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {streamStatus?.running ? (
                <span className="text-green-600">Live</span>
              ) : (
                <span className="text-gray-600">Offline</span>
              )}
            </div>
            <p className="text-xs text-gray-500">
              {streamStatus?.status || 'Unknown'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Current Track</CardTitle>
            <Music className="w-5 h-5 text-gray-600" />
          </CardHeader>
          <CardContent>
            <div className="text-sm font-semibold truncate">
              {streamStatus?.current_track?.artist || 'N/A'}
            </div>
            <p className="text-xs text-gray-500 truncate">
              {streamStatus?.current_track?.title || 'No track playing'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Uptime</CardTitle>
            <Timer className="w-5 h-5 text-gray-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {streamStatus?.current_track?.uptime_seconds
                ? `${Math.floor(streamStatus.current_track.uptime_seconds / 60)}m`
                : '0m'}
            </div>
            <p className="text-xs text-gray-500">Current track</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">System</CardTitle>
            <MonitorCheck className="w-5 h-5 text-gray-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">OK</div>
            <p className="text-xs text-gray-500">All services running</p>
          </CardContent>
        </Card>
      </div>

      {/* Current Track Details */}
      {streamStatus?.current_track && (
        <Card>
          <CardHeader>
            <CardTitle>Now Playing</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <h3 className="text-xl font-semibold">
                {streamStatus.current_track.title}
              </h3>
              <p className="text-gray-600">{streamStatus.current_track.artist}</p>
              <p className="text-sm text-gray-500">
                Track Key: {streamStatus.current_track.track_key}
              </p>
              {streamStatus.current_track.pid && (
                <p className="text-sm text-gray-500">
                  Process ID: {streamStatus.current_track.pid}
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}


