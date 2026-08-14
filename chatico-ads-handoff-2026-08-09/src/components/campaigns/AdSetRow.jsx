import TargetingLine from './TargetingLine';
import AdList from '../ads/AdList';
import { formatTenge, formatNumber } from '../../utils/format';

function SummaryChip({ label, value }) {
  return (
    <div className="flex flex-col items-end">
      <span className="text-[10px] font-medium uppercase tracking-wide text-gray-400">
        {label}
      </span>
      <span className="text-sm font-bold text-on-surface">{value}</span>
    </div>
  );
}

/**
 * Группа объявлений (Ad Set): шапка с названием, таргетингом и агрегированными
 * метриками + список объявлений внутри. Оформлена как карточка в стиле обзора.
 */
export default function AdSetRow({ adSet, resultLabel }) {
  const totalSpent = adSet.ads.reduce((sum, a) => sum + a.spent, 0);
  const totalLeads = adSet.ads.reduce((sum, a) => sum + a.leads, 0);
  const avgCpl = totalLeads > 0 ? Math.round(totalSpent / totalLeads) : 0;

  return (
    <div className="rounded-2xl border border-outline bg-white p-5 shadow-card">
      {/* Шапка группы */}
      <div className="flex flex-col gap-3 border-b border-outline pb-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary-container text-primary">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14-4H5m14 8H5m14 4H5" />
              </svg>
            </span>
            <h3 className="truncate text-sm font-bold text-on-surface" title={adSet.name}>
              {adSet.name}
            </h3>
          </div>
          <div className="mt-1.5 pl-9">
            <TargetingLine targeting={adSet.targeting} />
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-5 pl-9 sm:pl-0">
          <SummaryChip label="Потрачено" value={formatTenge(totalSpent)} />
          <SummaryChip label={resultLabel} value={formatNumber(totalLeads)} />
          <SummaryChip label="Ср. цена" value={formatTenge(avgCpl)} />
        </div>
      </div>

      {/* Объявления */}
      <div className="mt-4">
        <AdList ads={adSet.ads} resultLabel={resultLabel} />
      </div>
    </div>
  );
}
