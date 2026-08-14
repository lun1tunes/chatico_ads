import { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useAppStore } from '../../store/useAppStore';
import {
  resolvePresetDates,
  formatPeriodLabel,
  getPreviousPeriod,
} from '../../utils/dateRange';

const MENU_ITEMS = [
  { key: '7d', label: 'Последние 7 дней' },
  { key: '14d', label: 'Последние 14 дней' },
  { key: '30d', label: 'Последние 30 дней' },
  { key: 'thisMonth', label: 'Этот месяц' },
  { key: 'lastMonth', label: 'Прошлый месяц' },
  { key: 'custom', label: 'Выбрать даты' },
];

const PANEL_WIDTH = 288;
const VIEWPORT_GAP = 16;

function computePanelLayout(triggerEl) {
  if (!triggerEl) return null;

  const rect = triggerEl.getBoundingClientRect();
  const width = Math.min(PANEL_WIDTH, Math.max(240, rect.right - VIEWPORT_GAP));
  const left = Math.max(VIEWPORT_GAP, rect.right - width);
  const top = rect.bottom + 8;
  const maxHeight = Math.max(220, window.innerHeight - top - VIEWPORT_GAP);

  return { top, left, width, maxHeight };
}

export default function PeriodControl() {
  const dateRange = useAppStore((s) => s.dateRange);
  const compareEnabled = useAppStore((s) => s.compareEnabled);
  const setDateRange = useAppStore((s) => s.setDateRange);
  const setCompareEnabled = useAppStore((s) => s.setCompareEnabled);
  const aiPanelOpen = useAppStore((s) => s.aiPanelOpen);

  const [open, setOpen] = useState(false);
  const [customOpen, setCustomOpen] = useState(false);
  const [draftFrom, setDraftFrom] = useState(dateRange.from);
  const [draftTo, setDraftTo] = useState(dateRange.to);
  const [panelLayout, setPanelLayout] = useState(null);

  const triggerRef = useRef(null);
  const panelRef = useRef(null);

  useEffect(() => {
    setDraftFrom(dateRange.from);
    setDraftTo(dateRange.to);
  }, [dateRange.from, dateRange.to]);

  const updatePanelLayout = useCallback(() => {
    setPanelLayout(computePanelLayout(triggerRef.current));
  }, []);

  useEffect(() => {
    if (!open) {
      setPanelLayout(null);
      return undefined;
    }

    updatePanelLayout();
    window.addEventListener('resize', updatePanelLayout);
    window.addEventListener('scroll', updatePanelLayout, true);
    return () => {
      window.removeEventListener('resize', updatePanelLayout);
      window.removeEventListener('scroll', updatePanelLayout, true);
    };
  }, [open, customOpen, aiPanelOpen, updatePanelLayout]);

  useEffect(() => {
    if (!open) return undefined;

    function onClickOutside(e) {
      const target = e.target;
      if (
        triggerRef.current?.contains(target) ||
        panelRef.current?.contains(target)
      ) {
        return;
      }
      setOpen(false);
      setCustomOpen(false);
    }

    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, [open]);

  const periodLabel = formatPeriodLabel(dateRange.from, dateRange.to);
  const previousPeriod = getPreviousPeriod(dateRange.from, dateRange.to);
  const compareLabel = formatPeriodLabel(previousPeriod.from, previousPeriod.to);

  const selectPreset = (preset) => {
    if (preset === 'custom') {
      setCustomOpen(true);
      setDraftFrom(dateRange.from);
      setDraftTo(dateRange.to);
      return;
    }
    const { from, to } = resolvePresetDates(preset);
    setDateRange({ preset, from, to });
    setOpen(false);
    setCustomOpen(false);
  };

  const applyCustom = () => {
    if (!draftFrom || !draftTo || draftFrom > draftTo) return;
    setDateRange({ preset: 'custom', from: draftFrom, to: draftTo });
    setOpen(false);
    setCustomOpen(false);
  };

  const menuPanel =
    open && panelLayout ? (
      <div
        ref={panelRef}
        className="fixed z-[100] flex flex-col overflow-hidden rounded-xl border border-outline bg-white shadow-lg"
        style={{
          top: panelLayout.top,
          left: panelLayout.left,
          width: panelLayout.width,
          maxHeight: panelLayout.maxHeight,
        }}
      >
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
          {!customOpen ? (
            <ul className="px-1 py-2" role="listbox">
              {MENU_ITEMS.map(({ key, label }) => {
                const isSelected =
                  key === 'custom'
                    ? dateRange.preset === 'custom'
                    : dateRange.preset === key;
                return (
                  <li key={key}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={isSelected}
                      onClick={() => selectPreset(key)}
                      className={`flex w-full rounded-lg px-3 py-2.5 text-left text-sm transition-colors ${
                        isSelected
                          ? 'bg-[#5E44EB]/10 font-semibold text-[#5E44EB]'
                          : 'text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      {label}
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : (
            <div className="px-4 py-3">
              <p className="text-xs font-bold text-on-surface">Выбрать даты</p>
              <div className="mt-3 space-y-3">
                <label className="block text-xs font-medium text-gray-500">
                  Начало
                  <input
                    type="date"
                    value={draftFrom}
                    onChange={(e) => setDraftFrom(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-outline px-3 py-2 text-sm"
                  />
                </label>
                <label className="block text-xs font-medium text-gray-500">
                  Конец
                  <input
                    type="date"
                    value={draftTo}
                    onChange={(e) => setDraftTo(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-outline px-3 py-2 text-sm"
                  />
                </label>
              </div>
            </div>
          )}
        </div>

        {customOpen && (
          <div className="flex shrink-0 justify-end gap-2 border-t border-outline px-4 py-3">
            <button
              type="button"
              onClick={() => setCustomOpen(false)}
              className="rounded-lg px-3 py-1.5 text-xs font-medium text-gray-500 hover:bg-gray-50"
            >
              Назад
            </button>
            <button
              type="button"
              onClick={applyCustom}
              className="rounded-lg bg-[#5E44EB] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#4e3ad4]"
            >
              Применить
            </button>
          </div>
        )}

        <div className="shrink-0 border-t border-outline px-4 py-3">
          <label className="flex cursor-pointer items-center justify-between gap-3">
            <span className="text-sm text-gray-700">Сравнивать с предыдущим периодом</span>
            <button
              type="button"
              role="switch"
              aria-checked={compareEnabled}
              onClick={() => setCompareEnabled(!compareEnabled)}
              className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors ${
                compareEnabled ? 'bg-[#5E44EB]' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                  compareEnabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </label>
        </div>
      </div>
    ) : null;

  return (
    <>
      <div className="relative shrink-0">
        <button
          ref={triggerRef}
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-haspopup="listbox"
          className="inline-flex max-w-full items-center gap-2 rounded-xl border border-outline bg-white px-4 py-2.5 text-sm font-semibold text-on-surface shadow-sm transition-colors hover:border-[#5E44EB]/30 hover:bg-[#5E44EB]/[0.03]"
        >
          <span className="truncate">{periodLabel}</span>
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

        {compareEnabled && !open && (
          <p className="pointer-events-none absolute right-0 top-full z-10 mt-1 max-w-xs truncate whitespace-nowrap text-right text-xs text-gray-500">
            Сравнение с{' '}
            <span className="font-medium text-gray-600">{compareLabel}</span>
          </p>
        )}
      </div>

      {menuPanel && createPortal(menuPanel, document.body)}
    </>
  );
}
