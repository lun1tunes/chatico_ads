import { useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import AdSetCard from './AdSetCard';
import AdPreviewCard from './AdPreviewCard';
import CampaignMetricsStrip from './CampaignMetricsStrip';
import { TargetingDetails } from './TargetingLine';
import { aggregateAds } from '../../utils/campaignMetrics';
import { campaignAdsPath } from '../../utils/campaignNav';
import { formatMoney, formatNumber } from '../../utils/format';

function SectionTitle({ children, action }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex min-w-0 items-center gap-2">
        <span className="h-5 w-[4px] shrink-0 rounded-full bg-[#c2f913]" />
        <h2 className="text-sm font-bold uppercase tracking-wider text-gray-400">{children}</h2>
      </div>
      {action}
    </div>
  );
}

function adSetMetrics(adSet, currency = 'KZT') {
  const agg = aggregateAds(adSet?.ads, { currency });
  return {
    spent: { value: formatMoney(agg.spent, currency) },
    leads: { value: formatNumber(agg.leads) },
    cpl: { value: formatMoney(agg.cpl, currency) },
  };
}

/**
 * Контент страницы кампании или одной группы объявлений.
 */
export default function CampaignExplorer({ campaign, totalAds }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const adSetId = searchParams.get('adSet');

  const adSets = campaign.adSets ?? [];
  const resultLabel = campaign.resultLabel ?? 'Результаты';
  const currency = campaign.currency ?? 'KZT';
  const adSet = adSetId ? adSets.find((s) => s.id === adSetId) ?? null : null;

  useEffect(() => {
    if (!searchParams.get('ad')) return;
    const next = new URLSearchParams(searchParams);
    next.delete('ad');
    setSearchParams(next, { replace: true });
  }, [searchParams, setSearchParams]);

  if (adSet) {
    const ads = adSet.ads ?? [];
    return (
      <div className="space-y-5">
        <TargetingDetails targeting={adSet.targeting} />
        <CampaignMetricsStrip metrics={adSetMetrics(adSet, currency)} resultLabel={resultLabel} />
        <SectionTitle>Объявления · {ads.length}</SectionTitle>
        {ads.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-outline bg-white p-8 text-center">
            <p className="text-sm text-gray-400">В этой группе пока нет объявлений.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {ads.map((ad) => (
              <AdPreviewCard key={ad.id} ad={ad} resultLabel={resultLabel} currency={currency} />
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {campaign.metrics && (
        <CampaignMetricsStrip metrics={campaign.metrics} resultLabel={resultLabel} />
      )}

      {totalAds > 0 && (
        <Link
          to={campaignAdsPath(campaign.id)}
          className="flex items-center justify-between gap-4 rounded-xl border border-[#5E44EB]/20 bg-[#5E44EB]/[0.04] px-4 py-3.5 transition-colors hover:border-[#5E44EB]/40 hover:bg-[#5E44EB]/[0.07]"
        >
          <div>
            <p className="text-sm font-bold text-on-surface">Все объявления кампании</p>
            <p className="mt-0.5 text-xs text-gray-500">
              {totalAds} объявл. · фильтр по группам · отдельный экран
            </p>
          </div>
          <span className="shrink-0 text-sm font-semibold text-[#5E44EB]">Открыть →</span>
        </Link>
      )}

      <div id="ad-groups" className="scroll-mt-6 space-y-2.5">
        <SectionTitle
          action={
            totalAds > 0 ? (
              <Link
                to={campaignAdsPath(campaign.id)}
                className="shrink-0 text-xs font-semibold text-[#5E44EB] transition-colors hover:underline"
              >
                Все объявления кампании · {totalAds} →
              </Link>
            ) : null
          }
        >
          Группы объявлений · {adSets.length}
        </SectionTitle>

        {adSets.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-outline bg-white p-8 text-center">
            <p className="text-sm text-gray-400">В этой кампании пока нет групп объявлений.</p>
          </div>
        ) : (
          <div className="space-y-2.5">
            {adSets.map((s) => (
              <AdSetCard
                key={s.id}
                adSet={s}
                campaignId={campaign.id}
                resultLabel={resultLabel}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
