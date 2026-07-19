import MetricCard from '../ui/MetricCard';

const METRIC_CONFIG = [
  { key: 'spent', title: 'Сколько потратили' },
  { key: 'leads', title: 'Сколько откликнулось' },
  { key: 'cpl', title: 'Цена за один отклик' },
  { key: 'impressions', title: 'Сколько раз показали' },
];

export default function KeyMetricsRow({ metrics, loading }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {METRIC_CONFIG.map((m) => (
        <MetricCard
          key={m.key}
          title={m.title}
          value={metrics?.[m.key].value}
          trend={metrics?.[m.key].trend}
          subtitle={metrics?.[m.key].subtitle}
          loading={loading}
        />
      ))}
    </div>
  );
}
