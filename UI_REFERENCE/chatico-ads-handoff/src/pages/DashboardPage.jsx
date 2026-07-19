import { useState, useEffect } from 'react';
import PeriodSwitcher from '../components/overview/PeriodSwitcher';
import KeyMetricsRow from '../components/overview/KeyMetricsRow';
import VerdictCard from '../components/overview/VerdictCard';
import TrendChart from '../components/overview/TrendChart';
import { MOCK_METRICS_BY_PERIOD } from '../data/mockMetrics';

export default function DashboardPage() {
  const [period, setPeriod] = useState(7);
  const [loading, setLoading] = useState(false);
  const [metrics, setMetrics] = useState(MOCK_METRICS_BY_PERIOD[7]);

  // Симулируем задержку сети при смене периода, чтобы показать скелетоны и анимацию
  useEffect(() => {
    setLoading(true);
    const timer = setTimeout(() => {
      setMetrics(MOCK_METRICS_BY_PERIOD[period]);
      setLoading(false);
    }, 400);

    return () => clearTimeout(timer);
  }, [period]);

  const chartData = metrics?.chartData ?? [];
  const rangeLabel =
    chartData.length > 0
      ? `${chartData[0].date} — ${chartData[chartData.length - 1].date}`
      : null;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Шапка экрана «Обзор аккаунта» */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-5 w-[4px] rounded-full bg-[#c2f913]" />
            <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
              Meta Ads · Facebook / Instagram
            </p>
          </div>
          <h1 className="mt-1.5 text-2xl font-bold tracking-tight text-on-surface">
            Обзор аккаунта
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Главные показатели рекламы простым языком
            {rangeLabel && (
              <>
                {' · '}
                <span className="font-semibold text-gray-700">{rangeLabel}</span>
              </>
            )}
          </p>
        </div>
        <PeriodSwitcher selectedPeriod={period} onPeriodChange={setPeriod} />
      </div>

      {/* ИИ-вердикт — «герой» в стиле активного пункта меню */}
      <VerdictCard verdict={metrics?.verdict} loading={loading} />

      {/* Ключевые метрики */}
      <KeyMetricsRow metrics={metrics} loading={loading} />

      {/* График динамики */}
      <TrendChart data={chartData} loading={loading} />
    </div>
  );
}
