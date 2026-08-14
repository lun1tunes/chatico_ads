/**
 * ИИ-Вердикт в стиле shadcn/ui card:
 * rounded-xl, тонкая граница, лёгкий индиго-градиент, shadow-sm.
 * Иконка-чип + outline-бейдж статуса, текст вывода — muted-foreground.
 */
export default function VerdictCard({ verdict, loading }) {
  if (loading) {
    return (
      <div className="rounded-xl border border-outline bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 animate-pulse rounded-lg bg-muted" />
          <div className="h-4 w-40 animate-pulse rounded bg-muted" />
        </div>
        <div className="mt-4 h-4 w-full animate-pulse rounded bg-muted" />
        <div className="mt-2 h-4 w-3/4 animate-pulse rounded bg-muted" />
      </div>
    );
  }

  const isGood = verdict?.status === 'good';

  return (
    <div className="rounded-xl border border-outline bg-gradient-to-t from-[#5E44EB]/[0.06] to-white p-6 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#5E44EB]/10 text-[#5E44EB]">
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.4 6.6L22 12l-6.6 2.4L13 21l-2.4-6.6L4 12l6.6-2.4L13 3z" />
            </svg>
          </div>
          <p className="text-sm font-semibold text-on-surface">ИИ-Вердикт Chatico</p>
        </div>
        <span
          className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium ${
            isGood
              ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
              : 'border-amber-200 bg-amber-50 text-amber-700'
          }`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${isGood ? 'bg-emerald-500' : 'bg-amber-500'}`} />
          {isGood ? 'Всё отлично' : 'Есть нюанс'}
        </span>
      </div>

      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
        {verdict?.text}
      </p>
    </div>
  );
}
