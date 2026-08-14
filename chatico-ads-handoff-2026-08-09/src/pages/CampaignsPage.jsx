import { Link } from 'react-router-dom';
import { getMockCampaignListItems } from '../data/mockCampaignList';
import { useAppStore } from '../store/useAppStore';
import PageHeader from '../components/layout/PageHeader';

function StatusBadge({ status }) {
  const isActive = status === 'active';
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
        isActive ? 'bg-success-container text-[#3f7a2a]' : 'bg-neutral-container text-gray-500'
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${isActive ? 'bg-[#5a9c34]' : 'bg-gray-400'}`} />
      {isActive ? 'Активна' : 'На паузе'}
    </span>
  );
}

function MetricCol({ label, value }) {
  return (
    <div className="flex min-h-[2.75rem] flex-col items-center justify-end text-center">
      <p className="max-w-full text-[10px] font-medium uppercase leading-tight tracking-wide text-gray-400">
        {label}
      </p>
      <p className="mt-0.5 text-sm font-bold tabular-nums text-on-surface">{value}</p>
    </div>
  );
}

/**
 * Раздел «Рекламные кампании» — список кампаний (Этап 1).
 * Метрики — mock по глобальному периоду; TODO(api): фильтрация по dateRange + accountId.
 */
export default function CampaignsPage() {
  const dateRange = useAppStore((s) => s.dateRange);
  const campaigns = getMockCampaignListItems(dateRange);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Meta Ads · Facebook / Instagram"
        title="Мои рекламные кампании"
        subtitle="Всё, что сейчас запущено в рекламном аккаунте"
      />

      <div className="space-y-2.5">
        {campaigns.map((c) => (
          <Link
            key={c.id}
            to={`/campaigns/${c.id}`}
            className="group flex flex-col gap-4 rounded-xl border border-outline bg-white p-4 transition-all duration-150 hover:border-[#5E44EB]/40 hover:shadow-card lg:flex-row lg:items-center lg:justify-between"
          >
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="truncate text-sm font-bold text-on-surface group-hover:text-[#5E44EB]">
                  {c.name}
                </h2>
                <StatusBadge status={c.status} />
              </div>
              <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500">
                <span>
                  Цель: <span className="font-medium text-gray-700">{c.objective}</span>
                </span>
                <span>
                  Результат: <span className="font-medium text-gray-700">{c.resultType}</span>
                </span>
              </div>
            </div>
            <div className="grid shrink-0 grid-cols-[6.75rem_5.25rem_8.75rem_1rem] items-center gap-x-3 sm:gap-x-4">
              <MetricCol label="Потрачено" value={c.spent} />
              <MetricCol label={c.resultLabel} value={c.results} />
              <MetricCol label={c.priceLabel} value={c.price} />
              <svg className="mx-auto h-4 w-4 text-gray-300 group-hover:text-[#5E44EB]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
