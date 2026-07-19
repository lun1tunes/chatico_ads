import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import { PLATFORMS, useAppStore } from '../../store/useAppStore';
import ComingSoonPlaceholder from '../platforms/ComingSoonPlaceholder';
import AIPanel from '../ai/AIPanel';
import ConnectAccountModal from '../accounts/ConnectAccountModal';

export default function AppLayout() {
  const selectedPlatform = useAppStore((s) => s.selectedPlatform);
  const isMeta = selectedPlatform === PLATFORMS.META;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-6">
          {isMeta ? <Outlet /> : <ComingSoonPlaceholder />}
        </main>
      </div>
      <AIPanel />
      <ConnectAccountModal />
    </div>
  );
}
