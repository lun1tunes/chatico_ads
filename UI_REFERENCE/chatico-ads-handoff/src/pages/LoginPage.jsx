import { Navigate } from 'react-router-dom';
import { useAppStore } from '../store/useAppStore';
import Logo from '../components/ui/Logo';

export default function LoginPage() {
  const token = useAppStore((s) => s.token);
  const login = useAppStore((s) => s.login);

  if (token) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-black p-6">
      <Logo height={44} className="mb-8" />
      <div className="w-full max-w-md rounded-card bg-surface p-8 shadow-card">
        <p className="text-center text-sm text-on-surface-variant">
          Вход в дашборд рекламной аналитики
        </p>
        <button
          type="button"
          onClick={() =>
            login({ id: 'demo', name: 'Демо-пользователь' }, 'demo-token')
          }
          className="mt-8 w-full rounded-btn bg-primary py-3 text-sm font-semibold text-white transition-colors hover:brightness-95"
        >
          Войти (демо)
        </button>
        <p className="mt-4 text-center text-xs text-on-surface-variant">
          Модуль M3 · Auth — будет доработан
        </p>
      </div>
    </div>
  );
}
