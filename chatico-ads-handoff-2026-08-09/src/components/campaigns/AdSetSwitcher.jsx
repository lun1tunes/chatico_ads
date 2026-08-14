import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { campaignPath, campaignAdsPath } from '../../utils/campaignNav';

const ALL_GROUPS_LABEL = 'Все группы';

/**
 * Переключатель группы на странице одной группы («Сменить группу ▾»).
 */
export default function AdSetSwitcher({ campaign, selectedAdSetId }) {
  const [open, setOpen] = useState(false);
  const panelRef = useRef(null);
  const adSets = campaign.adSets ?? [];

  useEffect(() => {
    function onClickOutside(e) {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  return (
    <div ref={panelRef} className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="listbox"
        className="inline-flex items-center gap-1.5 rounded-lg border border-outline bg-white px-3 py-2 text-sm font-semibold text-gray-700 shadow-sm transition-colors hover:bg-gray-50 hover:text-[#5E44EB]"
      >
        Сменить группу
        <svg
          className={`h-4 w-4 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
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
            <Link
              to={campaignAdsPath(campaign.id)}
              onClick={() => setOpen(false)}
              className="block rounded-lg px-3 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-50"
            >
              {ALL_GROUPS_LABEL}
            </Link>
          </li>
          {adSets.map((adSet) => {
            const isSelected = selectedAdSetId === adSet.id;
            return (
              <li key={adSet.id}>
                <Link
                  to={campaignPath(campaign.id, { adSetId: adSet.id })}
                  onClick={() => setOpen(false)}
                  className={`block rounded-lg px-3 py-2 text-sm transition-colors ${
                    isSelected
                      ? 'bg-[#5E44EB]/10 font-semibold text-[#5E44EB]'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <span className="line-clamp-2">{adSet.name}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
