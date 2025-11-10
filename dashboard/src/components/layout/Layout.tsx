import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import Sidebar from './Sidebar';
import OfflineBanner from '@/components/network/OfflineBanner';
import { useWebsocketEvents } from '@/hooks/useWebsocketEvents';
import CommandPalette from '@/components/command/CommandPalette';

export default function Layout() {
  useWebsocketEvents();
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar />
        <OfflineBanner />
        
        <main className="flex-1 overflow-y-auto p-6">
          <CommandPalette />
          <Outlet />
        </main>
      </div>
    </div>
  );
}


