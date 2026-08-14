import { Link } from 'react-router-dom';
import { getCampaignById } from '../../data/mockCampaigns';

const TYPE_STYLES = {
  price_spike: {
    icon: '↗',
    badge: 'bg-amber-50 text-amber-800',
    dot: 'bg-amber-500',
  },
  paused: {
    icon: '⏸',
    badge: 'bg-neutral-container text-gray-600',
    dot: 'bg-gray-400',
  },
  no_results: {
    icon: '!',
    badge: 'bg-red-50 text-red-800',
    dot: 'bg-red-500',
  },
};

function SectionTitle({ children }) {
  return (
    <div className="flex items-center gap-2">
      <span className="h-5 w-[4px] rounded-full bg-[#c2f913]" />
      <h2 className="text-sm font-bold uppercase tracking-wider text-gray-400">{children}</h2>
    </div>
  );
}

export default function AttentionBlock({ items = [], loading }) {
  if (loading) {
    return (
      <div className="space-y-3">
        <SectionTitle>Что требует внимания</SectionTitle>
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-xl border border-outline bg-white" />
          ))}
        </div>
      </div>
    );
  }

  const visible = items.slice(0, 3);
  if (visible.length === 0) return null;

  return (
    <div className="space-y-3">
      <SectionTitle>Что требует внимания</SectionTitle>
      <ul className="space-y-2">
        {visible.map((item) => {
          const campaign = getCampaignById(item.campaignId);
          const style = TYPE_STYLES[item.type] ?? TYPE_STYLES.price_spike;
          return (
            <li key={`${item.campaignId}-${item.type}`}>
              <Link
                to={`/campaigns/${item.campaignId}`}
                className="group flex items-start gap-3 rounded-xl border border-outline bg-white p-4 transition-all duration-150 hover:border-[#5E44EB]/40 hover:shadow-card"
              >
                <span
                  className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-sm font-bold ${style.badge}`}
                >
                  {style.icon}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-bold text-on-surface group-hover:text-[#5E44EB]">
                    {campaign?.shortName ?? campaign?.name ?? 'Кампания'}
                  </p>
                  <p className="mt-0.5 text-sm text-gray-500">{item.text}</p>
                </div>
                <svg
                  className="mt-1 h-4 w-4 shrink-0 text-gray-300 group-hover:text-[#5E44EB]"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2.5}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
