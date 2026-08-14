import TrendBadge from './TrendBadge';
import Skeleton from './Skeleton';

/**
 * Карточка метрики в стиле shadcn/ui «section card»:
 * - приглушённое описание сверху + outline-бейдж тренда в углу
 * - крупное число tabular-nums
 * - футер: строка-вывод (bold) + muted-подпись
 * - chrome: rounded-xl, тонкая граница, лёгкий градиент from-primary/5, shadow-sm
 */
export default function MetricCard({
  title,
  value,
  trend,
  subtitle,
  footerLabel,
  loading,
  variant = 'default',
}) {
  if (loading) {
    return (
      <div className="flex h-full min-w-0 flex-col gap-4 overflow-hidden rounded-xl border border-outline bg-white p-5 shadow-sm">
        <div className="flex min-w-0 items-start justify-between gap-2">
          <Skeleton className="h-4 min-w-0 flex-1 max-w-28" />
          {variant !== 'neutral' && <Skeleton className="h-5 w-14 shrink-0 rounded-md" />}
        </div>
        <Skeleton className="h-8 w-32" />
        {variant === 'neutral' ? (
          <Skeleton className="mt-auto h-3 w-44" />
        ) : (
          <div className="mt-auto space-y-1.5">
            <Skeleton className="h-4 w-36" />
            <Skeleton className="h-3 w-44" />
          </div>
        )}
      </div>
    );
  }

  if (variant === 'neutral') {
    return (
      <div className="flex h-full min-w-0 flex-col gap-3 overflow-hidden rounded-xl border border-outline bg-white p-5 shadow-sm">
        <p className="text-sm text-muted-foreground">{title}</p>
        <p className="text-2xl font-semibold tracking-tight tabular-nums text-on-surface">{value}</p>
        {subtitle && <p className="mt-auto text-xs text-muted-foreground">{subtitle}</p>}
      </div>
    );
  }

  const resolvedFooter =
    footerLabel ?? (trend?.isPositive ? 'Динамика растёт' : 'Требует внимания');

  return (
    <div className="flex h-full min-w-0 flex-col gap-4 overflow-hidden rounded-xl border border-outline bg-gradient-to-t from-[#5E44EB]/[0.04] to-white p-5 shadow-sm">
      <div className="flex min-w-0 items-start justify-between gap-2">
        <p className="min-w-0 flex-1 text-sm leading-snug text-muted-foreground">{title}</p>
        {trend && (
          <span className="shrink-0">
            <TrendBadge value={trend.value} isPositive={trend.isPositive} />
          </span>
        )}
      </div>

      <p className="text-2xl font-semibold tracking-tight tabular-nums text-on-surface">
        {value}
      </p>

      <div className="mt-auto flex flex-col gap-1 text-sm">
        <div className="flex items-center gap-1.5 font-medium text-on-surface">
          {resolvedFooter}
          <svg className="h-4 w-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            {trend?.isPositive ? (
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 17l6-6 4 4 8-8m0 0h-6m6 0v6" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 7l6 6 4-4 8 8m0 0h-6m6 0v-6" />
            )}
          </svg>
        </div>
        {subtitle && <div className="text-xs text-muted-foreground">{subtitle}</div>}
      </div>
    </div>
  );
}
