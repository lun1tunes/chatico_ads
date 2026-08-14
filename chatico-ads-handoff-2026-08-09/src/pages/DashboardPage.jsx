import { useState, useEffect } from 'react';
import MainMetricsRow from '../components/overview/MainMetricsRow';
import CompactAiStatus from '../components/overview/CompactAiStatus';
import AttentionBlock from '../components/overview/AttentionBlock';
import TopCampaignsBlock from '../components/overview/TopCampaignsBlock';
import PageHeader from '../components/layout/PageHeader';
import { getMockOverviewMetrics } from '../data/mockMetrics';
import { useAppStore } from '../store/useAppStore';
import { formatPeriodLabel } from '../utils/dateRange';
import { buildOverviewAiContext } from '../utils/aiContext';

export default function DashboardPage() {
  const dateRange = useAppStore((s) => s.dateRange);
  const compareEnabled = useAppStore((s) => s.compareEnabled);
  const aiContext = useAppStore((s) => s.aiContext);
  const setAiContext = useAppStore((s) => s.setAiContext);
  const clearAiContext = useAppStore((s) => s.clearAiContext);

  const [loading, setLoading] = useState(false);
  const [metrics, setMetrics] = useState(() =>
    getMockOverviewMetrics(dateRange, compareEnabled),
  );

  const periodLabel = formatPeriodLabel(dateRange.from, dateRange.to);

  useEffect(() => {
    setLoading(true);
    const timer = setTimeout(() => {
      setMetrics(getMockOverviewMetrics(dateRange, compareEnabled));
      setLoading(false);
    }, 400);
    return () => clearTimeout(timer);
  }, [dateRange, compareEnabled]);

  useEffect(() => {
    if (!loading && metrics?.verdict) {
      setAiContext(buildOverviewAiContext(metrics, dateRange, periodLabel));
    }
    return () => clearAiContext();
  }, [loading, metrics, dateRange, compareEnabled, periodLabel, setAiContext, clearAiContext]);

  const compact = aiContext?.compact;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Meta Ads · Facebook / Instagram"
        title="Главное по рекламе"
        subtitle="Общее состояние рекламного аккаунта за выбранный период"
      />

      <CompactAiStatus compact={compact} loading={loading} />
      <MainMetricsRow metrics={metrics} loading={loading} compareEnabled={compareEnabled} />
      <AttentionBlock items={metrics?.attention} loading={loading} />
      <TopCampaignsBlock items={metrics?.topCampaigns} dateRange={dateRange} loading={loading} />
    </div>
  );
}
