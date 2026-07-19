import { useAppStore } from '../store/useAppStore';
import { getAccountById } from '../data/mockAccounts';
import AccountAvatar from '../components/accounts/AccountAvatar';

function Metric({ label, value }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] font-medium uppercase tracking-wide text-gray-400">{label}</span>
      <span className="mt-0.5 text-sm font-bold text-on-surface">{value}</span>
    </div>
  );
}

function AccountCard({ account, isActive, onActivate, onDisconnect }) {
  return (
    <div
      className={`relative overflow-hidden rounded-2xl border bg-white p-5 shadow-card transition-all duration-150 ${
        isActive ? 'border-[#5E44EB]/40' : 'border-outline hover:shadow-card-hover'
      }`}
    >
      {isActive && <div className="absolute left-0 top-5 bottom-5 w-[4px] rounded-r-md bg-[#c2f913]" />}

      <div className="flex items-start gap-3">
        <AccountAvatar account={account} size="lg" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-sm font-bold text-on-surface">{account.name}</h3>
            {isActive && (
              <span className="shrink-0 rounded-full bg-[#5E44EB] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
                Активный
              </span>
            )}
          </div>
          <p className="truncate text-xs text-gray-400">{account.handle}</p>
          <span
            className={`mt-1.5 inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-semibold ${
              account.status === 'active'
                ? 'bg-success-container text-[#3f7a2a]'
                : 'bg-neutral-container text-gray-500'
            }`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${account.status === 'active' ? 'bg-[#5a9c34]' : 'bg-gray-400'}`} />
            {account.status === 'active' ? 'Показы идут' : 'На паузе'}
          </span>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 border-t border-outline pt-3">
        <Metric label="За месяц" value={account.spentMonth} />
        <Metric label="Контакты" value={account.leadsMonth} />
        <Metric label="Кампаний" value={account.campaigns} />
      </div>

      <div className="mt-4 flex items-center gap-2">
        {isActive ? (
          <button
            type="button"
            disabled
            className="flex-1 cursor-default rounded-btn bg-[#5E44EB]/8 py-2 text-xs font-semibold text-[#5E44EB]"
          >
            Сейчас выбран
          </button>
        ) : (
          <button
            type="button"
            onClick={onActivate}
            className="flex-1 rounded-btn bg-[#5E44EB] py-2 text-xs font-semibold text-white transition-all hover:brightness-110"
          >
            Сделать активным
          </button>
        )}
        <button
          type="button"
          onClick={onDisconnect}
          className="rounded-btn border border-outline px-3 py-2 text-xs font-semibold text-gray-500 transition-colors hover:border-error-container hover:bg-error-container hover:text-[#b3261e]"
        >
          Отключить
        </button>
      </div>
    </div>
  );
}

export default function AccountsPage() {
  const connectedIds = useAppStore((s) => s.connectedAccountIds);
  const selectedId = useAppStore((s) => s.selectedAccountId);
  const setAccount = useAppStore((s) => s.setAccount);
  const disconnectAccount = useAppStore((s) => s.disconnectAccount);
  const openConnectModal = useAppStore((s) => s.openConnectModal);

  const accounts = connectedIds.map(getAccountById).filter(Boolean);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Шапка */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-5 w-[4px] rounded-full bg-[#c2f913]" />
            <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
              Управление
            </p>
          </div>
          <h1 className="mt-1.5 text-2xl font-bold tracking-tight text-on-surface">
            Рекламные кабинеты
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Подключено: {accounts.length}. Переключайтесь между кабинетами Meta в один клик.
          </p>
        </div>
        <button
          type="button"
          onClick={openConnectModal}
          className="flex items-center justify-center gap-2 rounded-btn bg-[#5E44EB] px-4 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Подключить кабинет
        </button>
      </div>

      {accounts.length > 0 ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {accounts.map((acc) => (
            <AccountCard
              key={acc.id}
              account={acc}
              isActive={acc.id === selectedId}
              onActivate={() => setAccount(acc.id)}
              onDisconnect={() => disconnectAccount(acc.id)}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-outline bg-white p-10 text-center">
          <p className="text-sm font-medium text-on-surface">Нет подключённых кабинетов</p>
          <p className="mt-1 text-xs text-gray-400">
            Подключите рекламный кабинет Meta, чтобы видеть аналитику.
          </p>
          <button
            type="button"
            onClick={openConnectModal}
            className="mt-4 rounded-btn bg-[#5E44EB] px-4 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110"
          >
            Подключить кабинет
          </button>
        </div>
      )}
    </div>
  );
}
