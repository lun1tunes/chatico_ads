import { useEffect } from 'react';
import { useAppStore } from '../../store/useAppStore';
import ChatWindow from './ChatWindow';

const BubbleIcon = ({ className }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24">
    <path d="M12 3C7.03 3 3 6.58 3 11c0 2.35 1.16 4.46 3 5.92V21l3.6-2.02c.77.2 1.58.3 2.4.3 4.97 0 9-3.58 9-8s-4.03-8-9-8z" />
  </svg>
);

/**
 * ИИ-консультант в трёхколоночной структуре.
 * - На широких экранах (≥ xl) — закреплённая колонка справа, сужающая контент.
 * - На узких экранах — выезжающая панель-overlay с затемнением.
 * По умолчанию открыт; можно свернуть в плавающую кнопку.
 */
export default function AIPanel() {
  const open = useAppStore((s) => s.aiPanelOpen);
  const openPanel = useAppStore((s) => s.openAiPanel);
  const closePanel = useAppStore((s) => s.closeAiPanel);

  // Закрытие по Esc (актуально для overlay-режима)
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') closePanel();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [closePanel]);

  // Свёрнуто — только плавающая кнопка-триггер
  if (!open) {
    return (
      <button
        type="button"
        onClick={openPanel}
        aria-label="Открыть ИИ-консультанта"
        className="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-[#5E44EB] text-white shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-xl"
      >
        <BubbleIcon className="h-6 w-6" />
        <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#c2f913] opacity-75" />
          <span className="relative inline-flex h-4 w-4 rounded-full border-2 border-white bg-[#c2f913]" />
        </span>
      </button>
    );
  }

  return (
    <>
      {/* Затемнение фона — только в overlay-режиме (узкие экраны) */}
      <div
        onClick={closePanel}
        className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[1px] xl:hidden"
        aria-hidden="true"
      />

      {/* Панель: docked-колонка на xl, overlay на узких экранах */}
      <aside
        className="flex h-full shrink-0 flex-col bg-background max-xl:fixed max-xl:inset-y-0 max-xl:right-0 max-xl:z-50 max-xl:w-full max-xl:max-w-md max-xl:animate-slide-in-right max-xl:shadow-2xl xl:w-[380px] xl:border-l xl:border-outline"
        role="dialog"
        aria-label="ИИ-консультант Chatico"
      >
        {/* Шапка панели */}
        <header className="flex shrink-0 items-center justify-between gap-3 border-b border-outline bg-white px-4 py-3.5">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#c2f913]">
                <BubbleIcon className="h-5 w-5 text-[#5E44EB]" />
              </div>
              <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-[#5a9c34]" />
            </div>
            <div className="flex flex-col">
              <p className="text-sm font-bold text-on-surface">ИИ-консультант</p>
              <p className="text-[11px] text-gray-400">Chatico AI · на связи</p>
            </div>
          </div>
          <button
            type="button"
            onClick={closePanel}
            aria-label="Свернуть консультанта"
            title="Свернуть"
            className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
            </svg>
          </button>
        </header>

        {/* Окно чата */}
        <div className="min-h-0 flex-1">
          <ChatWindow />
        </div>
      </aside>
    </>
  );
}
