import { useAppStore } from '../../store/useAppStore';

export default function AiChatEntryCard({ context, hasVerdict = false }) {
  const openAiPanel = useAppStore((s) => s.openAiPanel);

  return (
    <section className="rounded-3xl border border-[#5E44EB]/14 bg-white/95 p-5 shadow-[0_18px_40px_rgba(17,28,55,0.06)]">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-2xl bg-[#5E44EB]/10 text-[#5E44EB]">
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 3C7.03 3 3 6.58 3 11c0 2.35 1.16 4.46 3 5.92V21l3.6-2.02c.77.2 1.58.3 2.4.3 4.97 0 9-3.58 9-8s-4.03-8-9-8z" />
              </svg>
            </span>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-gray-400">Chatico AI</p>
              <h2 className="text-base font-semibold text-on-surface">Вердикт и рекомендации в правом чате</h2>
            </div>
          </div>
          <p className="text-sm leading-6 text-gray-500">
            {context}
          </p>
          <div className="flex flex-wrap items-center gap-2 text-xs font-semibold">
            <span className="rounded-full bg-neutral-container px-3 py-1 text-gray-500">Контекст передан в чат</span>
            {hasVerdict && <span className="rounded-full bg-[#eef8d3] px-3 py-1 text-[#4f7a10]">Есть новый вывод</span>}
          </div>
        </div>
        <button
          type="button"
          onClick={openAiPanel}
          className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[#5E44EB] px-4 py-2.5 text-sm font-semibold text-white transition-transform duration-150 hover:-translate-y-0.5 hover:bg-[#5137da]"
        >
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 3C7.03 3 3 6.58 3 11c0 2.35 1.16 4.46 3 5.92V21l3.6-2.02c.77.2 1.58.3 2.4.3 4.97 0 9-3.58 9-8s-4.03-8-9-8z" />
          </svg>
          Открыть AI-чат
        </button>
      </div>
    </section>
  );
}
