import { Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from './components/layout/ProtectedRoute';
import AppLayout from './components/layout/AppLayout';
import LoginPage from './pages/LoginPage';
import WelcomePage from './pages/WelcomePage';
import CampaignDetailPage from './pages/CampaignDetailPage';
import CampaignAdsPage from './pages/CampaignAdsPage';
import CampaignsPage from './pages/CampaignsPage';
import AccountsPage from './pages/AccountsPage';
import SettingsPage from './pages/SettingsPage';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<WelcomePage />} />
        <Route path="campaigns" element={<CampaignsPage />} />
        <Route path="campaigns/:id/ads" element={<CampaignAdsPage />} />
        <Route path="campaigns/:id" element={<CampaignDetailPage />} />
        <Route path="accounts" element={<AccountsPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
