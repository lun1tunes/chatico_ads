import { useAppStore } from '../../store/useAppStore';
import AccountSwitcher from '../accounts/AccountSwitcher';

export default function Topbar() {
  const user = useAppStore((s) => s.user);

  return (
    <header className="flex h-16 shrink-0 items-center gap-4 border-b border-outline bg-surface px-4 lg:px-6">
      <AccountSwitcher />

      <div className="ml-auto flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-container text-sm font-semibold text-primary">
          {user?.name?.charAt(0) ?? '?'}
        </div>
        <span className="hidden text-sm font-medium text-on-surface lg:inline">{user?.name}</span>
      </div>
    </header>
  );
}
