import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

const ALL_GROUPS_LABEL = 'Все группы';

/**
 * Фильтр групп на странице всех объявлений («Показывать объявления: … ▾»).
 * Меняет query-параметр на той же странице /campaigns/:id/ads.
 */
export default function AdsGroupFilter({ campaign, selectedAdSetId }) {
  const [open, setOpen] = useState(false);
  const panelRef = useRef(null);
  const [, setSearchParams] = useSearchParams();
  const adSets = campaign.adSets ?? [];

  const selectedAdSet = selectedAdSetId
    ? adSets.find((s) => s.id === selectedAdSetId) ?? null
    : null;
  const selectedLabel = selectedAdSet?.name ?? ALL_GROUPS_LABEL;

  useEffect(() => {
    function onClickOutside(e) {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  const selectAllGroups = () => {
    setSearchParams({}, { replace: true });
    setOpen(false);
  };

  const selectAdSet = (adSetId) => {
    setSearchParams({ adSet: adSetId }, { replace: true });
    setOpen(false);
  };

  return (
    <div ref={panelRef} className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="listbox"
        className="inline-flex max-w-full items-center gap-1.5 rounded-lg border border-outline bg-white px-3 py-2 text-sm font-semibold text-gray-700 shadow-sm transition-colors hover:bg-gray-50 hover:text-[#5E44EB]"
      >
        <span className="whitespace-nowrap">
          {selectedAdSet ? (
            <span className="text-on-surface">{selectedLabel}</span>
          ) : (
            <>
              Показывать объявления:{' '}
              <span className="text-on-surface">{selectedLabel}</span>
            </>
          )}
        </span>
        <svg
          className={`h-4 w-4 shrink-0 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <ul
          role="listbox"
          className="absolute right-0 top-full z-50 mt-1.5 max-h-64 w-72 overflow-y-auto rounded-xl border border-outline bg-white p-1.5 shadow-lg"
        >
          <li>
            <button
              type="button"
              role="option"
              aria-selected={!selectedAdSetId}
              onClick={selectAllGroups}
              className={`block w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                !selectedAdSetId
                  ? 'bg-[#5E44EB]/10 font-semibold text-[#5E44EB]'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              {ALL_GROUPS_LABEL}
            </button>
          </li>
          {adSets.map((adSet) => {
            const isSelected = selectedAdSetId === adSet.id;
            return (
              <li key={adSet.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => selectAdSet(adSet.id)}
                  className={`block w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                    isSelected
                      ? 'bg-[#5E44EB]/10 font-semibold text-[#5E44EB]'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <span className="line-clamp-2">{adSet.name}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
