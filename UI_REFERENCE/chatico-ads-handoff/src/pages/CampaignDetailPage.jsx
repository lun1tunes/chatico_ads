import { useParams, Navigate, Link } from 'react-router-dom';
import { getCampaignDetail } from '../data/mockCampaigns';
import VerdictCard from '../components/overview/VerdictCard';
import CampaignSummary from '../components/campaigns/CampaignSummary';
import AdSetList from '../components/campaigns/AdSetList';

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

export default function CampaignDetailPage() {
  const { id } = useParams();
  const campaign = getCampaignDetail(id);

  if (!campaign) {
    return <Navigate to="/" replace />;
  }

  const adSets = campaign.adSets ?? [];
  const adsCount = adSets.reduce((sum, s) => sum + s.ads.length, 0);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Кнопка назад */}
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-500 transition-colors hover:text-[#5E44EB]"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        Обзор аккаунта
      </Link>

      {/* Шапка кампании */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <span className="h-5 w-[4px] rounded-full bg-[#c2f913]" />
          <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
            Кампания{campaign.objective ? ` · цель: ${campaign.objective}` : ''}
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h1 className="text-2xl font-bold tracking-tight text-on-surface">
            {campaign.name}
          </h1>
          <StatusBadge status={campaign.status} />
        </div>
        {adSets.length > 0 && (
          <p className="text-sm text-gray-500">
            {adSets.length}{' '}
            {adSets.length === 1 ? 'группа объявлений' : 'групп(ы) объявлений'} ·{' '}
            {adsCount} объявлен{adsCount === 1 ? 'ие' : 'ий'}
          </p>
        )}
      </div>

      {/* ИИ-вердикт по кампании */}
      {campaign.verdict && <VerdictCard verdict={campaign.verdict} loading={false} />}

      {/* Сводка показателей */}
      {campaign.metrics && <CampaignSummary metrics={campaign.metrics} />}

      {/* Группы объявлений и объявления */}
      {campaign.metrics ? (
        <AdSetList adSets={adSets} resultLabel={campaign.resultLabel} />
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
