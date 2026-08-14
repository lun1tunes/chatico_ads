import KeyMetricsRow from '../overview/KeyMetricsRow';

/**
 * Сводка по конкретной кампании — те же 4 метрики, что и на экране обзора,
 * для полного визуального единообразия (M5).
 */
export default function CampaignSummary({ metrics }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <span className="h-5 w-[4px] rounded-full bg-[#c2f913]" />
        <h2 className="text-sm font-bold uppercase tracking-wider text-gray-400">
          Показатели кампании
        </h2>
      </div>
      <KeyMetricsRow metrics={metrics} loading={false} />
    </div>
  );
}
