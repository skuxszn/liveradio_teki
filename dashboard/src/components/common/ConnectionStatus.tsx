/**
 * WebSocket connection status indicator.
 * Shows current connection state in the UI.
 */

import { Wifi, WifiOff } from 'lucide-react';

interface ConnectionStatusProps {
  isConnected: boolean;
  reconnectCount?: number;
}

export function ConnectionStatus({ isConnected, reconnectCount = 0 }: ConnectionStatusProps) {
  if (isConnected) {
    return (
      <div className="flex items-center gap-2 text-green-600 text-sm">
        <Wifi className="w-4 h-4" />
        <span>Connected</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-gray-500 text-sm">
      <WifiOff className="w-4 h-4" />
      <span>
        {reconnectCount > 0 ? `Reconnecting... (${reconnectCount})` : 'Disconnected'}
      </span>
    </div>
  );
}

export default ConnectionStatus;



