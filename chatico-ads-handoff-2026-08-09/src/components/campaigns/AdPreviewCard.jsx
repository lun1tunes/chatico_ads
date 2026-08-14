import { formatMoney, formatNumber } from '../../utils/format';
import CreativePreview, { inferFormat, FORMAT_META } from '../ads/CreativePreview';

function AdStatusBadge({ status }) {
  const isActive = status !== 'paused';
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
        isActive ? 'bg-success-container text-[#3f7a2a]' : 'bg-neutral-container text-gray-500'
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${isActive ? 'bg-[#5a9c34]' : 'bg-gray-400'}`} />
      {isActive ? 'Активно' : 'На паузе'}
    </span>
  );
}

function Stat({ label, value, accent }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] font-medium uppercase tracking-wide text-gray-400">{label}</span>
      <span className={`text-sm font-bold tabular-nums ${accent ?? 'text-on-surface'}`}>{value}</span>
    </div>
  );
}

/** Карточка объявления в списке группы. */
export default function AdPreviewCard({
  ad,
  resultLabel = 'Результаты',
  adSetName,
  currency = 'KZT',
}) {
  const formatKey = ad.format ?? inferFormat(ad.name);
  const formatLabel = FORMAT_META[formatKey]?.label ?? 'Баннер';
  const hasData = ad.spent > 0 || ad.leads > 0;

  return (
    <div className="overflow-hidden rounded-xl border border-outline bg-white p-3 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <CreativePreview
          id={ad.id}
          name={ad.name}
          format={formatKey}
          variant="default"
          thumbnailUrl={ad.thumbnailUrl}
        />

        <div className="flex min-w-0 flex-1 flex-col gap-2">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-on-surface" title={ad.name}>
                {ad.name}
              </p>
              <p className="mt-0.5 text-xs text-gray-400">
                {formatLabel}
                {adSetName && (
                  <>
                    {' · '}
                    <span className="text-gray-500">{adSetName}</span>
                  </>
                )}
              </p>
            </div>
            <AdStatusBadge status={ad.status} />
          </div>

          {hasData ? (
            <div className="grid grid-cols-3 gap-2 border-t border-outline pt-2">
              <Stat label="Потрачено" value={formatMoney(ad.spent, currency)} />
              <Stat label={resultLabel} value={formatNumber(ad.leads)} />
              <Stat label="Цена" value={formatMoney(ad.cpl, currency)} />
            </div>
          ) : (
            <p className="border-t border-outline pt-2 text-xs text-gray-400">
              Показов пока не было — данные появятся после запуска
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
