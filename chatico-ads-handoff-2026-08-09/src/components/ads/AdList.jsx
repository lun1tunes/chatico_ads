import { useState } from 'react';
import AdCard from './AdCard';

/**
 * Список объявлений внутри группы с условным рендером (M6):
 * - 1 объявление    → карточка сразу
 * - 2–3 объявления  → все карточки
 * - 4+ объявлений   → топ-3 (по цене за результат) + кнопка «Показать ещё»
 *
 * Сортировка: дешевле за результат — выше. Объявления без данных уходят в конец.
 */
export default function AdList({ ads, resultLabel }) {
  const [expanded, setExpanded] = useState(false);

  const sorted = [...ads].sort((a, b) => {
    const aHas = a.cpl > 0;
    const bHas = b.cpl > 0;
    if (aHas && bHas) return a.cpl - b.cpl;
    return aHas ? -1 : bHas ? 1 : 0;
  });

  const bestId = sorted.find((a) => a.cpl > 0)?.id;
  const isManyAds = sorted.length >= 4;
  const visible = isManyAds && !expanded ? sorted.slice(0, 3) : sorted;
  const hiddenCount = sorted.length - 3;

  return (
    <div className="space-y-2.5">
      {visible.map((ad) => (
        <AdCard
          key={ad.id}
          ad={ad}
          resultLabel={resultLabel}
          isBest={ad.id === bestId}
        />
      ))}

      {isManyAds && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-dashed border-outline py-2.5 text-xs font-semibold text-gray-500 transition-colors hover:border-[#5E44EB]/40 hover:bg-gray-50 hover:text-[#5E44EB]"
        >
          {expanded ? 'Свернуть' : `Показать ещё ${hiddenCount}`}
          <svg
            className={`h-4 w-4 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2.5}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      )}
    </div>
  );
}
