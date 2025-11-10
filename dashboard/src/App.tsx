import { Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import Layout from '@/components/layout/Layout';
import Login from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
import Stream from '@/pages/Stream';
import Settings from '@/pages/Settings';
import Users from '@/pages/Users';
import Mappings from '@/pages/Mappings';
import Assets from '@/pages/Assets';
import Monitoring from '@/pages/Monitoring';
import VideoAssetsPage from '@/pages/assets/videos/VideoAssetsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Routes>
        <Route path="/login" element={<Login />} />
        
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="stream" element={<Stream />} />
          <Route path="mappings" element={<Mappings />} />
          <Route path="settings" element={<Settings />} />
          <Route path="assets" element={<Assets />} />
          <Route path="assets/videos" element={<VideoAssetsPage />} />
          <Route path="monitoring" element={<Monitoring />} />
          <Route path="users" element={<Users />} />
        </Route>
        
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </QueryClientProvider>
  );
}

export default App;
