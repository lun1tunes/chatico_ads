import { useAppStore } from '../../store/useAppStore';

/**
 * Компактный ИИ-статус для центра экрана (1–2 строки).
 * Полный вердикт — в правой панели чата.
 */
export default function CompactAiStatus({ compact, loading }) {
  const aiPanelOpen = useAppStore((s) => s.aiPanelOpen);
  const openAiPanel = useAppStore((s) => s.openAiPanel);

  if (loading) {
    return (
      <div className="space-y-1.5 py-1">
        <div className="h-4 w-48 animate-pulse rounded bg-muted" />
        <div className="h-3.5 w-72 max-w-full animate-pulse rounded bg-muted" />
      </div>
    );
  }

  if (!compact) return null;

  if (!aiPanelOpen) {
    return (
      <button
        type="button"
        onClick={openAiPanel}
        className="group inline-flex items-center gap-1.5 text-left text-sm text-gray-600 transition-colors hover:text-[#5E44EB]"
      >
        <span className="font-medium text-gray-500">ИИ-вывод:</span>
        <span className="font-semibold text-on-surface group-hover:text-[#5E44EB]">
          {compact.shortTitle}
        </span>
        <span className="text-[#5E44EB]">→</span>
      </button>
    );
  }

  return (
    <div
      className={`border-l-[3px] py-0.5 pl-3 ${compact.border ?? 'border-emerald-400'}`}
    >
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className={`inline-flex items-center gap-1.5 text-sm font-semibold ${compact.titleClass}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${compact.dot}`} />
          {compact.title}
        </span>
        <button
          type="button"
          onClick={openAiPanel}
          className="text-xs font-semibold text-[#5E44EB] hover:underline"
        >
          Подробнее в ИИ-консультанте →
        </button>
      </div>
      {compact.hint && (
        <p className="mt-0.5 text-sm leading-snug text-gray-500">{compact.hint}</p>
      )}
    </div>
  );
}
