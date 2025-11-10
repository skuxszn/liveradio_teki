import { NavLink } from 'react-router-dom';
import { cn } from '@/utils/cn';
import { useAuthStore } from '@/store/authStore';
import { LayoutDashboard, Radio, ListMusic, Settings as Cog, Film, ActivitySquare, Users } from 'lucide-react';

const navigation = [
  { name: 'Dashboard', to: '/', icon: <LayoutDashboard className="w-4 h-4" /> },
  { name: 'Stream', to: '/stream', icon: <Radio className="w-4 h-4" /> },
  { name: 'Track Mappings', to: '/mappings', icon: <ListMusic className="w-4 h-4" /> },
  { name: 'Settings', to: '/settings', icon: <Cog className="w-4 h-4" /> },
  { name: 'Video Assets', to: '/assets', icon: <Film className="w-4 h-4" /> },
  { name: 'Monitoring', to: '/monitoring', icon: <ActivitySquare className="w-4 h-4" /> },
  { name: 'Users', to: '/users', icon: <Users className="w-4 h-4" />, adminOnly: true },
];

export default function Sidebar() {
  const user = useAuthStore((state) => state.user);
  const isAdmin = user?.role === 'admin';

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-6">
        <h1 className="text-xl font-bold text-gray-900">
          Radio Stream
        </h1>
        <p className="text-sm text-gray-500">Dashboard</p>
      </div>
      
      <nav className="flex-1 px-3 space-y-1">
        {navigation.map((item) => {
          if (item.adminOnly && !isAdmin) return null;
          
          return (
            <NavLink
              key={item.name}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-gray-100 text-gray-900'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                )
              }
            >
              <span aria-hidden className="text-xl">{item.icon}</span>
              {item.name}
            </NavLink>
          );
        })}
      </nav>
      
      <div className="p-4 border-t">
        <div className="text-sm text-gray-600">
          <p className="font-medium">{user?.username}</p>
          <p className="text-xs text-gray-500">{user?.role}</p>
        </div>
      </div>
    </aside>
  );
}

