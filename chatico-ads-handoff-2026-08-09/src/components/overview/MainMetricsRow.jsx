import MetricCard from '../ui/MetricCard';

const METRIC_CONFIG = [
  { key: 'spent', title: 'Потрачено всего' },
  { key: 'activeCampaigns', title: 'Активных кампаний' },
  { key: 'conversations', title: 'Получено обращений', emptyLabel: 'Нет данных' },
  { key: 'leads', title: 'Получено лидов', emptyLabel: 'Нет данных' },
];

export default function MainMetricsRow({ metrics, loading, compareEnabled }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 [&>*]:min-w-0">
      {METRIC_CONFIG.map((m) => {
        const raw = metrics?.[m.key];
        const value = raw?.value ?? (loading ? undefined : m.emptyLabel ?? '0');
        const subtitle =
          compareEnabled && raw?.compareSubtitle ? raw.compareSubtitle : raw?.subtitle;
        return (
          <MetricCard
            key={m.key}
            title={m.title}
            value={value}
            subtitle={subtitle}
            loading={loading}
            variant="neutral"
          />
        );
      })}
    </div>
  );
}
