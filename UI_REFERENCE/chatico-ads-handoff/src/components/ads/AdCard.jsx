import { formatTenge, formatNumber } from '../../utils/format';
import CreativePreview from './CreativePreview';

function Stat({ label, value, accent }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] font-medium uppercase tracking-wide text-gray-400">
        {label}
      </span>
      <span className={`mt-0.5 text-sm font-bold ${accent ?? 'text-on-surface'}`}>
        {value}
      </span>
    </div>
  );
}

/**
 * Карточка объявления (M6).
 * Слева — крупное превью креатива (чтобы баннер был узнаваем визуально),
 * справа — название и метрики. Лидер группы помечается лаймовым бейджем.
 */
export default function AdCard({ ad, resultLabel = 'Результаты', isBest }) {
  const hasData = ad.spent > 0 || ad.leads > 0;

  return (
    <div
      className={`relative overflow-hidden rounded-xl border bg-white p-4 transition-all duration-150 hover:shadow-card ${
        isBest ? 'border-[#5E44EB]/40 shadow-card' : 'border-outline'
      }`}
    >
      {isBest && (
        <div className="absolute left-0 top-4 bottom-4 z-10 w-[4px] rounded-r-md bg-[#c2f913]" />
      )}

      <div className="flex flex-col gap-4 sm:flex-row">
        <CreativePreview id={ad.id} name={ad.name} format={ad.format} />

        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex items-start justify-between gap-3">
            <p className="text-sm font-semibold text-on-surface" title={ad.name}>
              {ad.name}
            </p>
            {isBest && (
              <span className="shrink-0 rounded-full bg-[#c2f913] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[#1C1B1F]">
                Лучший результат
              </span>
            )}
          </div>

          {hasData ? (
            <div className="mt-auto grid grid-cols-3 gap-2 border-t border-outline pt-3">
              <Stat label="Потрачено" value={formatTenge(ad.spent)} />
              <Stat label={resultLabel} value={formatNumber(ad.leads)} />
              <Stat
                label="Цена"
                value={formatTenge(ad.cpl)}
                accent={isBest ? 'text-[#5E44EB]' : undefined}
              />
            </div>
          ) : (
            <div className="mt-auto border-t border-outline pt-3">
              <p className="text-xs text-gray-400">
                Показов пока не было — данные появятся после запуска
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
