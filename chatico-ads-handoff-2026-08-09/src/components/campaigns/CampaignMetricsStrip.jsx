import TrendBadge from '../ui/TrendBadge';
import Skeleton from '../ui/Skeleton';

function MetricCell({ label, value, trend, loading }) {
  if (loading) {
    return (
      <div className="flex min-w-0 flex-1 flex-col gap-2 rounded-xl border border-outline bg-white p-4 shadow-sm">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-7 w-24" />
      </div>
    );
  }

  return (
    <div className="flex min-w-0 flex-1 flex-col gap-1.5 rounded-xl border border-outline bg-white p-4 shadow-sm">
      <div className="flex min-w-0 items-start justify-between gap-2">
        <p className="min-w-0 flex-1 text-xs font-medium leading-snug text-muted-foreground">{label}</p>
        {trend && (
          <span className="shrink-0">
            <TrendBadge value={trend.value} isPositive={trend.isPositive} />
          </span>
        )}
      </div>
      <p className="text-xl font-semibold tracking-tight tabular-nums text-on-surface">{value}</p>
    </div>
  );
}

/** Три ключевые метрики: потрачено, результаты, цена результата. */
export default function CampaignMetricsStrip({ metrics, resultLabel = 'Результаты', loading }) {
  const items = [
    { key: 'spent', label: 'Потрачено' },
    { key: 'leads', label: resultLabel },
    { key: 'cpl', label: 'Цена результата' },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-3 [&>*]:min-w-0">
      {items.map(({ key, label }) => (
        <MetricCell
          key={key}
          label={label}
          value={metrics?.[key]?.value}
          trend={metrics?.[key]?.trend}
          loading={loading}
        />
      ))}
    </div>
  );
}
