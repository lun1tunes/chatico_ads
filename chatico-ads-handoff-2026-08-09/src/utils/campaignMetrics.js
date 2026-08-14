import { formatMoney, formatNumber } from './format';

/** Агрегация метрик по списку объявлений группы. */
export function aggregateAds(ads = [], { currency = 'KZT' } = {}) {
  const spent = ads.reduce((s, a) => s + (a.spent ?? 0), 0);
  const leads = ads.reduce((s, a) => s + (a.leads ?? 0), 0);
  const rawCpl = leads > 0 ? spent / leads : 0;
  const cpl =
    currency === 'USD'
      ? Math.round(rawCpl * 100) / 100
      : Math.round(rawCpl);
  return { spent, leads, cpl };
}

/** Метрики для CampaignMetricsStrip по списку объявлений. */
export function metricsStripFromAds(ads = [], currency = 'KZT') {
  const agg = aggregateAds(ads, { currency });
  return {
    spent: { value: formatMoney(agg.spent, currency) },
    leads: { value: formatNumber(agg.leads) },
    cpl: { value: formatMoney(agg.cpl, currency) },
  };
}
