import { NavLink } from 'react-router-dom';
import { cn } from '@/utils/cn';
import { useAuthStore } from '@/store/authStore';

const navigation = [
  { name: 'Dashboard', to: '/', icon: '📊' },
  { name: 'Stream Control', to: '/stream', icon: '📻' },
  { name: 'Track Mappings', to: '/mappings', icon: '🎵' },
  { name: 'Settings', to: '/settings', icon: '⚙️' },
  { name: 'Video Assets', to: '/assets', icon: '🎬' },
  { name: 'Monitoring', to: '/monitoring', icon: '📈' },
  { name: 'Users', to: '/users', icon: '👥', adminOnly: true },
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
              <span className="text-xl">{item.icon}</span>
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

