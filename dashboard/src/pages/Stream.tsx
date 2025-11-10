import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { streamService } from '@/services/stream.service';
import { toast } from '@/components/feedback/ToastProvider';

export default function Stream() {
  const [message, setMessage] = useState('');
  const queryClient = useQueryClient();

  const { data: streamStatus, isLoading } = useQuery({
    queryKey: ['stream-status'],
    queryFn: () => streamService.getStatus(),
    refetchInterval: 3000,
  });

  const startMutation = useMutation({
    mutationFn: () => streamService.start(),
    onSuccess: () => {
      setMessage('Stream started successfully!');
      toast('Stream started', 'success')
      queryClient.invalidateQueries({ queryKey: ['stream-status'] });
    },
    onError: (error: any) => {
      const msg = `Error: ${error.response?.data?.detail || 'Failed to start stream'}`
      setMessage(msg);
      toast(msg, 'error')
    },
  });

  const stopMutation = useMutation({
    mutationFn: () => streamService.stop(),
    onSuccess: () => {
      setMessage('Stream stopped successfully!');
      toast('Stream stopped', 'success')
      queryClient.invalidateQueries({ queryKey: ['stream-status'] });
    },
    onError: (error: any) => {
      const msg = `Error: ${error.response?.data?.detail || 'Failed to stop stream'}`
      setMessage(msg);
      toast(msg, 'error')
    },
  });

  const restartMutation = useMutation({
    mutationFn: () => streamService.restart(),
    onSuccess: () => {
      setMessage('Stream restarted successfully!');
      toast('Stream restarted', 'success')
      queryClient.invalidateQueries({ queryKey: ['stream-status'] });
    },
    onError: (error: any) => {
      const msg = `Error: ${error.response?.data?.detail || 'Failed to restart stream'}`
      setMessage(msg);
      toast(msg, 'error')
    },
  });

  const isRunning = streamStatus?.running;
  const isMutating = startMutation.isPending || stopMutation.isPending || restartMutation.isPending;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Stream Control</h1>
        <p className="text-gray-500">Manage your FFmpeg radio stream</p>
      </div>

      {message && (
        <div className={`p-4 rounded-md ${message.startsWith('Error') ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'}`}>
          {message}
        </div>
      )}

      {/* Stream Controls */}
      <Card>
        <CardHeader>
          <CardTitle>Stream Controls</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-4">
            <Button
              size="lg"
              onClick={() => startMutation.mutate()}
              disabled={isRunning || isMutating || isLoading}
              className="bg-green-600 hover:bg-green-700"
            >
              {startMutation.isPending ? 'Starting...' : 'Start Stream'}
            </Button>

            <Button
              size="lg"
              variant="destructive"
              onClick={() => stopMutation.mutate()}
              disabled={!isRunning || isMutating || isLoading}
            >
              {stopMutation.isPending ? 'Stopping...' : 'Stop Stream'}
            </Button>

            <Button
              size="lg"
              variant="outline"
              onClick={() => restartMutation.mutate()}
              disabled={!isRunning || isMutating || isLoading}
            >
              {restartMutation.isPending ? 'Restarting...' : 'Restart Stream'}
            </Button>
          </div>

          <div className="pt-4 border-t">
            <div className="flex items-center gap-2">
              <div className={`h-3 w-3 rounded-full ${isRunning ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
              <span className="font-medium">
                Status: {isRunning ? 'Live' : 'Offline'}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Current Track */}
      {streamStatus?.current_track && (
        <Card>
          <CardHeader>
            <CardTitle>Currently Playing</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <p className="text-sm text-gray-500">Artist</p>
                <p className="text-lg font-semibold">{streamStatus.current_track.artist}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Title</p>
                <p className="text-lg font-semibold">{streamStatus.current_track.title}</p>
              </div>
              <div className="grid grid-cols-2 gap-4 pt-2 text-sm">
                <div>
                  <p className="text-gray-500">Uptime</p>
                  <p className="font-medium">
                    {Math.floor(streamStatus.current_track.uptime_seconds / 60)}m {streamStatus.current_track.uptime_seconds % 60}s
                  </p>
                </div>
                <div>
                  <p className="text-gray-500">Track Key</p>
                  <p className="font-medium font-mono text-xs">{streamStatus.current_track.track_key}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}


