/**
 * Компактная строка таргетинга под названием группы объявлений.
 * Показывает пол · возраст · город мелким приглушённым текстом — для контекста,
 * без раскрытия полных настроек Meta.
 */
export default function TargetingLine({ targeting }) {
  if (!targeting) return null;
  const parts = [targeting.gender, targeting.age, targeting.city].filter(Boolean);

  return (
    <div className="flex items-center gap-1.5 text-xs text-gray-400">
      <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
      <span className="truncate">{parts.join(' · ')}</span>
    </div>
  );
}
