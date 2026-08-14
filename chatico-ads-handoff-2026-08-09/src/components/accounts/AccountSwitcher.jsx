import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../../store/useAppStore';
import { getAccountById } from '../../data/mockAccounts';
import AccountAvatar from './AccountAvatar';

/** Переключатель активного рекламного кабинета в топбаре. */
export default function AccountSwitcher() {
  const navigate = useNavigate();
  const connectedIds = useAppStore((s) => s.connectedAccountIds);
  const selectedId = useAppStore((s) => s.selectedAccountId);
  const setAccount = useAppStore((s) => s.setAccount);
  const openConnectModal = useAppStore((s) => s.openConnectModal);

  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const current = getAccountById(selectedId);
  const accounts = connectedIds.map(getAccountById).filter(Boolean);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2.5 rounded-xl border border-outline bg-white px-2.5 py-1.5 text-left transition-colors hover:bg-gray-50"
      >
        {current ? (
          <>
            <AccountAvatar account={current} size="sm" />
            <div className="hidden flex-col sm:flex">
              <span className="text-[10px] leading-none text-gray-400">Рекламный аккаунт</span>
              <span className="mt-0.5 max-w-[160px] truncate text-sm font-semibold text-on-surface">
                {current.name}
              </span>
            </div>
          </>
        ) : (
          <span className="px-1 text-sm font-medium text-gray-500">Нет кабинета</span>
        )}
        <svg
          className={`h-4 w-4 text-gray-400 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-72 rounded-2xl border border-outline bg-white p-1.5 shadow-lg">
          <p className="px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider text-gray-400">
            Ваши кабинеты
          </p>
          <ul className="max-h-72 space-y-0.5 overflow-y-auto">
            {accounts.map((acc) => {
              const isActive = acc.id === selectedId;
              return (
                <li key={acc.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setAccount(acc.id);
                      setOpen(false);
                    }}
                    className={`flex w-full items-center gap-2.5 rounded-xl px-2 py-2 text-left transition-colors ${
                      isActive ? 'bg-[#5E44EB]/8' : 'hover:bg-gray-50'
                    }`}
                  >
                    <AccountAvatar account={acc} size="sm" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-on-surface">{acc.name}</p>
                      <p className="truncate text-xs text-gray-400">{acc.handle}</p>
                    </div>
                    {isActive && (
                      <svg className="h-4 w-4 shrink-0 text-[#5E44EB]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="my-1.5 h-px bg-outline" />

          <button
            type="button"
            onClick={() => {
              setOpen(false);
              openConnectModal();
            }}
            className="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-sm font-semibold text-[#5E44EB] transition-colors hover:bg-[#5E44EB]/5"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Подключить кабинет
          </button>
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              navigate('/accounts');
            }}
            className="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-sm font-medium text-gray-500 transition-colors hover:bg-gray-50"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
            Управление кабинетами
          </button>
        </div>
      )}
    </div>
  );
}
