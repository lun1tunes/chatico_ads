import { Link } from 'react-router-dom';
import { formatTenge, formatNumber, formatAdsCountLabel } from '../../utils/format';
import { campaignPath } from '../../utils/campaignNav';
import { aggregateAds } from '../../utils/campaignMetrics';
import { formatAudienceBrief } from './TargetingLine';

function MiniStat({ label, value }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] font-medium uppercase tracking-wide text-gray-400">{label}</span>
      <span className="text-sm font-bold tabular-nums text-on-surface">{value}</span>
    </div>
  );
}

/** Компактная карточка группы объявлений на странице кампании. */
export default function AdSetCard({ adSet, campaignId, resultLabel = 'Результаты' }) {
  const agg = aggregateAds(adSet.ads);
  const adsCount = adSet.ads?.length ?? 0;
  const audience = formatAudienceBrief(adSet.targeting);

  return (
    <Link
      to={campaignPath(campaignId, { adSetId: adSet.id })}
      className="group flex flex-col gap-3 rounded-xl border border-outline bg-white p-4 transition-all duration-150 hover:border-[#5E44EB]/40 hover:shadow-card sm:flex-row sm:items-center"
    >
      <div className="min-w-0 flex-1">
        <h3 className="truncate text-sm font-bold text-on-surface">{adSet.name}</h3>
        {audience && (
          <p className="mt-1 truncate text-xs text-gray-400">{audience}</p>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-4 sm:gap-5">
        <MiniStat label="Потрачено" value={formatTenge(agg.spent)} />
        <MiniStat label={resultLabel} value={formatNumber(agg.leads)} />
        <MiniStat label="Цена" value={formatTenge(agg.cpl)} />
      </div>

      <span className="shrink-0 text-xs font-semibold text-[#5E44EB] transition-colors group-hover:underline">
        {formatAdsCountLabel(adsCount)} →
      </span>
    </Link>
  );
}
