import { useEffect } from 'react';
import { useParams, Navigate, Link, useSearchParams, useLocation } from 'react-router-dom';
import { getCampaignDetail } from '../data/mockCampaigns';
import CampaignExplorer from '../components/campaigns/CampaignExplorer';
import AdSetSwitcher from '../components/campaigns/AdSetSwitcher';
import PageHeader from '../components/layout/PageHeader';
import { useAppStore } from '../store/useAppStore';
import { buildCampaignAiContext, buildAdSetAiContext } from '../utils/aiContext';
import { formatPeriodLabel } from '../utils/dateRange';
import {
  campaignPath,
  campaignAdsPath,
  campaignAdGroupsPath,
  getCampaignAdsCount,
  CAMPAIGN_AD_GROUPS_ANCHOR,
} from '../utils/campaignNav';

function StatusBadge({ status }) {
  const isActive = status === 'active';
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${
        isActive ? 'bg-success-container text-[#3f7a2a]' : 'bg-neutral-container text-gray-500'
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${isActive ? 'bg-[#5a9c34]' : 'bg-gray-400'}`} />
      {isActive ? 'Активна' : 'На паузе'}
    </span>
  );
}

function LevelFallbackNotice({ message }) {
  if (!message) return null;
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      {message}
    </div>
  );
}

export default function CampaignDetailPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const view = searchParams.get('view');
  const adSetId = searchParams.get('adSet');
  const campaign = getCampaignDetail(id);

  const dateRange = useAppStore((s) => s.dateRange);
  const setAiContext = useAppStore((s) => s.setAiContext);
  const clearAiContext = useAppStore((s) => s.clearAiContext);
  const openAiPanel = useAppStore((s) => s.openAiPanel);

  const periodLabel = formatPeriodLabel(dateRange.from, dateRange.to);
  const adSet = adSetId ? campaign?.adSets?.find((s) => s.id === adSetId) ?? null : null;
  const hasDetails = Boolean(campaign?.metrics);
  const fallbackMessage = location.state?.fallbackMessage ?? null;
  const totalAds = campaign ? getCampaignAdsCount(campaign) : 0;

  useEffect(() => {
    if (!hasDetails) return undefined;

    const ctx = adSet
      ? buildAdSetAiContext(campaign, adSet, periodLabel, dateRange)
      : buildCampaignAiContext(campaign, periodLabel, dateRange);

    setAiContext(ctx);
    openAiPanel();
    return () => clearAiContext();
  }, [
    campaign?.id,
    adSet?.id,
    hasDetails,
    periodLabel,
    dateRange.from,
    dateRange.to,
    dateRange.preset,
  ]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (adSet) return;
    if (location.hash !== `#${CAMPAIGN_AD_GROUPS_ANCHOR}`) return;

    const scrollToGroups = () => {
      const el = document.getElementById(CAMPAIGN_AD_GROUPS_ANCHOR);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };

    requestAnimationFrame(() => requestAnimationFrame(scrollToGroups));
  }, [location.hash, adSet, campaign?.id]);

  if (!campaign) {
    return <Navigate to="/" replace />;
  }

  if (view === 'ads') {
    const legacyFilter = searchParams.get('adSet');
    return (
      <Navigate
        to={campaignAdsPath(campaign.id, { adSetId: legacyFilter || undefined })}
        replace
      />
    );
  }

  if (adSetId && !adSet) {
    return (
      <Navigate
        to={campaignPath(campaign.id)}
        replace
        state={{ fallbackMessage: 'Группа объявлений не найдена — открыта страница кампании.' }}
      />
    );
  }

  if (adSet) {
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <PageHeader
          back={
            <Link
              to={campaignAdGroupsPath(campaign.id)}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-500 transition-colors hover:text-[#5E44EB]"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
              </svg>
              К кампании
            </Link>
          }
          eyebrow="Группа объявлений"
          title={
            <div className="flex items-start justify-between gap-4">
              <h1 className="min-w-0 flex-1 text-2xl font-bold tracking-tight text-on-surface">
                {adSet.name}
              </h1>
              <AdSetSwitcher campaign={campaign} selectedAdSetId={adSet.id} />
            </div>
          }
        />

        {hasDetails ? (
          <CampaignExplorer campaign={campaign} totalAds={totalAds} />
        ) : (
          <div className="rounded-2xl border border-dashed border-outline bg-white p-8 text-center">
            <p className="text-sm text-gray-400">
              Детальные данные по этой группе появятся после подключения к Meta Ads.
            </p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        back={
          <Link
            to="/campaigns"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-500 transition-colors hover:text-[#5E44EB]"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
            Все рекламные кампании
          </Link>
        }
        eyebrow={
          campaign.objective
            ? `Рекламная кампания · цель: ${campaign.objective}`
            : 'Рекламная кампания'
        }
        title={campaign.name}
        trailing={<StatusBadge status={campaign.status} />}
      />

      <LevelFallbackNotice message={fallbackMessage} />

      {hasDetails ? (
        <CampaignExplorer campaign={campaign} totalAds={totalAds} />
      ) : (
        <div className="rounded-2xl border border-dashed border-outline bg-white p-8 text-center">
          <p className="text-sm text-gray-400">
            Детальные данные по этой кампании появятся после подключения к Meta Ads.
          </p>
        </div>
      )}
    </div>
  );
}
