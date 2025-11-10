import { Activity, Wifi, WifiOff, Radio } from 'lucide-react'
import Breadcrumbs from './Breadcrumbs'
import { useWsStore } from '@/store/wsStore'
import { useQuery } from '@tanstack/react-query'
import { streamService } from '@/services/stream.service'

export default function GlobalStatus() {
  const connected = useWsStore((s) => s.connected)
  const { data: streamStatus } = useQuery({ queryKey: ['stream-status'], queryFn: () => streamService.getStatus(), refetchInterval: 5000 })

  return (
    <div className="flex items-center justify-between">
      <Breadcrumbs />
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm">
          {connected ? <Wifi className="w-4 h-4 text-green-600" /> : <WifiOff className="w-4 h-4 text-gray-500" />}
          <span className={connected ? 'text-green-700' : 'text-gray-600'}>
            {connected ? 'WS Connected' : 'WS Disconnected'}
          </span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <Radio className={`w-4 h-4 ${streamStatus?.running ? 'text-green-600' : 'text-gray-500'}`} />
          <span className={streamStatus?.running ? 'text-green-700' : 'text-gray-600'}>
            {streamStatus?.running ? 'Stream: Live' : 'Stream: Offline'}
          </span>
        </div>
        {streamStatus?.current_track && (
          <div className="flex items-center gap-2 text-sm text-gray-700">
            <Activity className="w-4 h-4" />
            <span className="truncate max-w-[22ch]" title={`${streamStatus.current_track.artist} - ${streamStatus.current_track.title}`}>
              {streamStatus.current_track.artist} — {streamStatus.current_track.title}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}


