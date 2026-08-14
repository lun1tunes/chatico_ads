import { useEffect } from 'react';
import { useParams, Navigate, Link, useSearchParams } from 'react-router-dom';
import { getCampaignDetail } from '../data/mockCampaigns';
import CampaignAllAdsView from '../components/campaigns/CampaignAllAdsView';
import CampaignMetricsStrip from '../components/campaigns/CampaignMetricsStrip';
import AdsGroupFilter from '../components/campaigns/AdsGroupFilter';
import PeriodControl from '../components/layout/PeriodControl';
import { useAppStore } from '../store/useAppStore';
import { buildAdsAiContext } from '../utils/aiContext';
import { formatPeriodLabel } from '../utils/dateRange';
import { collectCampaignAds } from '../utils/campaignVerdict';
import { metricsStripFromAds } from '../utils/campaignMetrics';
import {
  campaignPath,
  campaignAdsPath,
  campaignHasAdsView,
  getCampaignAdsCount,
} from '../utils/campaignNav';
import { formatAdsCountLabel } from '../utils/format';

function SectionTitle({ children }) {
  return (
    <div className="flex min-w-0 items-center gap-2">
      <span className="h-5 w-[4px] shrink-0 rounded-full bg-[#c2f913]" />
      <h2 className="text-sm font-bold uppercase tracking-wider text-gray-400">{children}</h2>
    </div>
  );
}

export default function CampaignAdsPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const filterAdSetId = searchParams.get('adSet');
  const campaign = getCampaignDetail(id);

  const dateRange = useAppStore((s) => s.dateRange);
  const setAiContext = useAppStore((s) => s.setAiContext);
  const clearAiContext = useAppStore((s) => s.clearAiContext);
  const openAiPanel = useAppStore((s) => s.openAiPanel);

  const periodLabel = formatPeriodLabel(dateRange.from, dateRange.to);
  const hasDetails = Boolean(campaign?.metrics);
  const adSets = campaign?.adSets ?? [];
  const filterAdSet = filterAdSetId ? adSets.find((s) => s.id === filterAdSetId) ?? null : null;
  const ads = collectCampaignAds(adSets, filterAdSetId);
  const resultLabel = campaign?.resultLabel ?? 'Результаты';

  useEffect(() => {
    if (!hasDetails) return undefined;

    setAiContext(buildAdsAiContext(campaign, periodLabel, dateRange, filterAdSetId));
    openAiPanel();
    return () => clearAiContext();
  }, [
    campaign?.id,
    filterAdSetId,
    hasDetails,
    periodLabel,
    dateRange.from,
    dateRange.to,
    dateRange.preset,
  ]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!campaign) {
    return <Navigate to="/" replace />;
  }

  if (!campaignHasAdsView(campaign)) {
    const totalAds = getCampaignAdsCount(campaign);
    const message = !hasDetails
      ? 'Детальные данные по этой кампании пока недоступны — открыта страница кампании.'
      : totalAds === 0
        ? 'В этой кампании пока нет объявлений — открыта страница кампании.'
        : 'Для этой кампании недоступен просмотр объявлений — открыта страница кампании.';

    return <Navigate to={campaignPath(campaign.id)} replace state={{ fallbackMessage: message }} />;
  }

  if (filterAdSetId && !filterAdSet) {
    return <Navigate to={campaignAdsPath(campaign.id)} replace />;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="space-y-4">
        <Link
          to={campaignPath(campaign.id)}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-500 transition-colors hover:text-[#5E44EB]"
        >
          <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          К кампании
        </Link>

        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="h-5 w-[4px] shrink-0 rounded-full bg-[#c2f913]" />
            <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
              Объявления кампании
            </p>
          </div>
          <h1 className="mt-1.5 shrink-0 text-2xl font-bold tracking-tight text-on-surface">
            Все объявления в вашей кампании
          </h1>
          <p className="mt-1 truncate text-sm text-gray-500">
            {campaign.name} · {formatAdsCountLabel(ads.length)}
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <AdsGroupFilter campaign={campaign} selectedAdSetId={filterAdSetId} />
          <PeriodControl />
        </div>
      </header>

      {hasDetails ? (
        <div className="space-y-5">
          <CampaignMetricsStrip
            metrics={metricsStripFromAds(ads, campaign.currency)}
            resultLabel={resultLabel}
          />
          <SectionTitle>Объявления · {ads.length}</SectionTitle>
          <CampaignAllAdsView
            adSets={adSets}
            resultLabel={resultLabel}
            filterAdSetId={filterAdSetId}
            currency={campaign.currency}
          />
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-outline bg-white p-8 text-center">
          <p className="text-sm text-gray-400">
            Детальные данные по объявлениям появятся после подключения к Meta Ads.
          </p>
        </div>
      )}
    </div>
  );
}
