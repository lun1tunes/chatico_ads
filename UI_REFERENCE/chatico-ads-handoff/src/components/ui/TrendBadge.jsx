/**
 * Бейдж тренда в стиле shadcn/ui (variant="outline"):
 * тонкая граница, скругление rounded-md, иконка направления, нейтральная типографика
 * с лёгкой цветовой семантикой (рост — зелёный, падение — красный).
 */
export default function TrendBadge({ value, isPositive }) {
  const isNeutral = value === 0 || value === '0%';

  if (isNeutral) {
    return (
      <span className="inline-flex items-center gap-1 rounded-md border border-outline px-1.5 py-0.5 text-xs font-medium text-muted-foreground">
        {value}
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-xs font-medium ${
        isPositive
          ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
          : 'border-red-200 bg-red-50 text-red-700'
      }`}
    >
      <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
        {isPositive ? (
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 17l6-6 4 4 8-8m0 0h-6m6 0v6" />
        ) : (
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 7l6 6 4-4 8 8m0 0h-6m6 0v-6" />
        )}
      </svg>
      {value}
    </span>
  );
}
