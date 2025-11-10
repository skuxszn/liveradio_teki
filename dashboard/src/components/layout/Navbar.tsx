import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/store/authStore';
import { authService } from '@/services/auth.service';
import GlobalStatus from './GlobalStatus';
import NotificationsCenter from '@/components/notifications/NotificationsCenter';

export default function Navbar() {
  const navigate = useNavigate();
  const { user, refreshToken, logout } = useAuthStore();

  const handleLogout = async () => {
    try {
      if (refreshToken) {
        await authService.logout(refreshToken);
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      logout();
      navigate('/login');
    }
  };

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1">
          <GlobalStatus />
        </div>
        <div className="flex items-center gap-3">
          <NotificationsCenter />
          <span className="text-sm text-gray-600 hidden sm:inline">{user?.username}</span>
          <Button variant="outline" onClick={handleLogout} aria-label="Logout">
            Logout
          </Button>
        </div>
      </div>
    </header>
  );
}


