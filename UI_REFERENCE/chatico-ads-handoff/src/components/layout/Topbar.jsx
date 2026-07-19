import { useAppStore } from '../../store/useAppStore';
import AccountSwitcher from '../accounts/AccountSwitcher';

export default function Topbar() {
  const user = useAppStore((s) => s.user);
  const openAiPanel = useAppStore((s) => s.openAiPanel);
  const aiPanelOpen = useAppStore((s) => s.aiPanelOpen);

  return (
    <header className="flex h-16 shrink-0 items-center justify-between gap-3 border-b border-outline bg-surface px-6">
      <AccountSwitcher />

      <div className="flex items-center gap-3">
        {!aiPanelOpen && (
          <>
            <button
              type="button"
              onClick={openAiPanel}
              className="flex items-center gap-2 rounded-xl border border-[#5E44EB]/20 bg-[#5E44EB]/5 px-3 py-2 text-xs font-semibold text-[#5E44EB] transition-all duration-150 hover:bg-[#5E44EB]/10"
            >
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 3C7.03 3 3 6.58 3 11c0 2.35 1.16 4.46 3 5.92V21l3.6-2.02c.77.2 1.58.3 2.4.3 4.97 0 9-3.58 9-8s-4.03-8-9-8z" />
              </svg>
              Спросить AI
            </button>
            <div className="h-6 w-px bg-outline" />
          </>
        )}
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-container text-sm font-semibold text-primary">
          {user?.name?.charAt(0) ?? '?'}
        </div>
        <span className="hidden text-sm font-medium text-on-surface sm:inline">{user?.name}</span>
      </div>
    </header>
  );
}
