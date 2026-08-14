import { useState, useEffect, useRef } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { ALL_ACCOUNTS } from '../../data/mockAccounts';
import AccountAvatar from './AccountAvatar';

const FacebookIcon = ({ className }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24">
    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
  </svg>
);

export default function ConnectAccountModal() {
  const open = useAppStore((s) => s.connectModalOpen);
  const close = useAppStore((s) => s.closeConnectModal);
  const connectedIds = useAppStore((s) => s.connectedAccountIds);
  const connectAccount = useAppStore((s) => s.connectAccount);

  const [step, setStep] = useState('intro'); // intro | loading | list
  const timerRef = useRef(null);

  useEffect(() => {
    if (open) setStep('intro');
    return () => clearTimeout(timerRef.current);
  }, [open]);

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && close();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [close]);

  if (!open) return null;

  const available = ALL_ACCOUNTS.filter((a) => !connectedIds.includes(a.id));

  const startConnect = () => {
    setStep('loading');
    timerRef.current = setTimeout(() => setStep('list'), 900);
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={close}
        aria-hidden="true"
      />

      <div
        className="relative w-full max-w-md overflow-hidden rounded-modal bg-white shadow-2xl"
        role="dialog"
        aria-label="Подключить рекламный кабинет"
      >
        {/* Шапка */}
        <div className="flex items-center justify-between border-b border-outline px-5 py-4">
          <h2 className="text-base font-bold text-on-surface">Подключить кабинет</h2>
          <button
            type="button"
            onClick={close}
            aria-label="Закрыть"
            className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-5">
          {step === 'intro' && (
            <div className="flex flex-col items-center text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#1877F2]/10">
                <FacebookIcon className="h-8 w-8 text-[#1877F2]" />
              </div>
              <p className="mt-4 text-sm font-medium text-on-surface">
                Войдите через Facebook, чтобы Chatico получил доступ к вашим рекламным кабинетам Meta.
              </p>
              <p className="mt-2 text-xs text-gray-400">
                Мы работаем через официальный API Meta и видим только рекламную статистику.
              </p>
              <button
                type="button"
                onClick={startConnect}
                className="mt-5 flex w-full items-center justify-center gap-2 rounded-btn bg-[#1877F2] py-3 text-sm font-semibold text-white transition-all hover:brightness-110"
              >
                <FacebookIcon className="h-5 w-5" />
                Продолжить с Facebook
              </button>
            </div>
          )}

          {step === 'loading' && (
            <div className="flex flex-col items-center py-8 text-center">
              <div className="h-9 w-9 animate-spin rounded-full border-[3px] border-gray-200 border-t-[#5E44EB]" />
              <p className="mt-4 text-sm text-gray-500">Получаем список ваших кабинетов…</p>
            </div>
          )}

          {step === 'list' && (
            <div>
              {available.length > 0 ? (
                <>
                  <p className="mb-3 text-xs font-semibold text-gray-500">
                    Доступные кабинеты в вашем Facebook Business:
                  </p>
                  <ul className="space-y-2">
                    {available.map((acc) => (
                      <li
                        key={acc.id}
                        className="flex items-center gap-3 rounded-xl border border-outline p-3"
                      >
                        <AccountAvatar account={acc} size="sm" />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold text-on-surface">{acc.name}</p>
                          <p className="truncate text-xs text-gray-400">{acc.handle}</p>
                        </div>
                        <button
                          type="button"
                          onClick={() => connectAccount(acc.id, { activate: true })}
                          className="shrink-0 rounded-btn bg-[#5E44EB] px-3 py-1.5 text-xs font-semibold text-white transition-all hover:brightness-110"
                        >
                          Подключить
                        </button>
                      </li>
                    ))}
                  </ul>
                </>
              ) : (
                <div className="flex flex-col items-center py-6 text-center">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-success-container">
                    <svg className="h-6 w-6 text-[#3f7a2a]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p className="mt-3 text-sm font-medium text-on-surface">
                    Все доступные кабинеты уже подключены
                  </p>
                </div>
              )}

              <button
                type="button"
                onClick={close}
                className="mt-4 w-full rounded-btn border border-outline py-2.5 text-sm font-semibold text-gray-600 transition-colors hover:bg-gray-50"
              >
                Готово
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
