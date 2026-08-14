/**
 * Чипы-подсказки с примерами вопросов.
 * Исчезают после начала диалога (по логике из ARCHITECTURE.md).
 */
export default function SuggestedChips({ questions, onPick }) {
  if (!questions || questions.length === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      <p className="px-1 text-[10px] font-bold uppercase tracking-wider text-gray-400">
        Спросите, например
      </p>
      <div className="flex flex-wrap gap-2">
        {questions.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onPick(q)}
            className="rounded-full border border-outline bg-white px-3 py-1.5 text-left text-xs font-medium text-gray-600 transition-all duration-150 hover:border-[#5E44EB]/40 hover:bg-[#5E44EB]/5 hover:text-[#5E44EB]"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
