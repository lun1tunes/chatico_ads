import { Link } from 'react-router-dom';
import { getCampaignDetail } from '../../data/mockCampaigns';
import { getMockCampaignListItems } from '../../data/mockCampaignList';

function SectionTitle({ children }) {
  return (
    <div className="flex items-center gap-2">
      <span className="h-5 w-[4px] rounded-full bg-[#c2f913]" />
      <h2 className="text-sm font-bold uppercase tracking-wider text-gray-400">{children}</h2>
    </div>
  );
}

/**
 * Лучшие кампании внутри своей цели — максимум 2, без сравнения разных типов результатов.
 */
export default function TopCampaignsBlock({ items = [], dateRange, loading }) {
  if (loading) {
    return (
      <div className="space-y-3">
        <SectionTitle>Лучшие кампании</SectionTitle>
        <div className="grid gap-3 sm:grid-cols-2">
          {[1, 2].map((i) => (
            <div key={i} className="h-28 animate-pulse rounded-xl border border-outline bg-white" />
          ))}
        </div>
      </div>
    );
  }

  const visible = items.slice(0, 2);
  if (visible.length === 0) return null;

  const listItems = getMockCampaignListItems(dateRange);
  const listById = Object.fromEntries(listItems.map((c) => [c.id, c]));

  return (
    <div className="space-y-3">
      <div>
        <SectionTitle>Лучшие кампании</SectionTitle>
        <p className="mt-1 text-xs text-gray-500">
          Лидеры внутри своей цели — без сравнения разных типов результатов
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {visible.map((item) => {
          const detail = getCampaignDetail(item.campaignId);
          const row = listById[item.campaignId];
          if (!detail) return null;

          return (
            <Link
              key={item.campaignId}
              to={`/campaigns/${item.campaignId}`}
              className="group flex flex-col rounded-xl border border-outline bg-white p-4 transition-all duration-150 hover:border-[#5E44EB]/40 hover:shadow-card"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="inline-flex rounded-full bg-[#5E44EB]/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[#5E44EB]">
                  {detail.objective}
                </span>
                <svg
                  className="h-4 w-4 shrink-0 text-gray-300 group-hover:text-[#5E44EB]"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2.5}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </div>
              <p className="mt-2 line-clamp-2 text-sm font-bold text-on-surface group-hover:text-[#5E44EB]">
                {detail.shortName ?? detail.name}
              </p>
              <p className="mt-2 text-xs font-medium text-gray-500">{item.highlight}</p>
              {row && (
                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-outline pt-3 text-xs">
                  <span className="text-gray-400">
                    {row.resultLabel}:{' '}
                    <span className="font-semibold text-on-surface">{row.results}</span>
                  </span>
                  <span className="text-gray-400">
                    {row.priceLabel}:{' '}
                    <span className="font-semibold text-on-surface">{row.price}</span>
                  </span>
                </div>
              )}
            </Link>
          );
        })}
      </div>
      <Link
        to="/campaigns"
        className="inline-flex items-center gap-1 text-sm font-semibold text-[#5E44EB] hover:underline"
      >
        Посмотреть всю рекламу
        <span aria-hidden>→</span>
      </Link>
    </div>
  );
}
