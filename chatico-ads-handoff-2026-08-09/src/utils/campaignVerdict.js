import { summarizeAudiencePlain } from './audienceSummary';
import { aggregateAds } from './campaignMetrics';
import { formatTenge } from './format';

function trendLine(metric, { upGood, label }) {
  const t = metric?.trend;
  if (!t?.value) return null;
  const verb = t.isPositive
    ? upGood
      ? 'вырос'
      : 'снизился'
    : upGood
      ? 'снизился'
      : 'вырос';
  return `${label} ${verb} на ${t.value}`;
}

function formatTargetingSummary(targeting = {}) {
  const summary = summarizeAudiencePlain(targeting);
  if (summary) return summary;

  const parts = [];
  if (targeting.city) parts.push(targeting.city);
  if (targeting.age) parts.push(targeting.age);
  if (targeting.gender && targeting.gender !== 'Все') parts.push(targeting.gender.toLowerCase());
  if (targeting.audienceType) parts.push(targeting.audienceType.toLowerCase());
  if (targeting.interests) parts.push(targeting.interests.toLowerCase());
  return parts.length ? parts.join(' · ') : 'аудитория не указана';
}

export function rankAdSets(adSets = []) {
  return adSets
    .map((adSet) => ({ adSet, ...aggregateAds(adSet.ads ?? []) }))
    .filter((row) => row.leads > 0)
    .sort((a, b) => a.cpl - b.cpl);
}

export function rankAds(ads = []) {
  return (ads ?? [])
    .filter((ad) => (ad.leads ?? 0) > 0)
    .sort((a, b) => a.cpl - b.cpl);
}

function deriveStatus(cpl, benchmarkCpl, leads) {
  if (!leads) return 'warning';
  if (!benchmarkCpl) return 'good';
  if (cpl <= benchmarkCpl * 0.92) return 'good';
  if (cpl >= benchmarkCpl * 1.12) return 'problem';
  return 'warning';
}

function shortAdSetName(name = '') {
  const cut = name.indexOf(' · ');
  return cut > 0 ? name.slice(0, cut) : name;
}

/** Вердикт уровня кампании. */
export function buildCampaignVerdict(campaign) {
  const metrics = campaign.metrics ?? {};
  const resultLabel = (campaign.resultLabel ?? 'Результаты').toLowerCase();
  const rankings = rankAdSets(campaign.adSets ?? []);
  const best = rankings[0];
  const worst = rankings.length > 1 ? rankings[rankings.length - 1] : null;

  const parts = [];

  const leadsTrend = trendLine(metrics.leads, { upGood: true, label: `Объём ${resultLabel}` });
  const cplTrend = trendLine(metrics.cpl, { upGood: false, label: 'Цена результата' });
  if (leadsTrend) parts.push(`${leadsTrend}.`);
  if (cplTrend) parts.push(`${cplTrend}.`);

  if (best) {
    parts.push(
      `Лучшая группа — «${shortAdSetName(best.adSet.name)}» (${formatTenge(best.cpl)} за результат).`,
    );
  }
  if (worst && worst.adSet.id !== best?.adSet.id) {
    parts.push(
      `Слабее остальных — «${shortAdSetName(worst.adSet.name)}» (${formatTenge(worst.cpl)}).`,
    );
  }

  if (best) {
    parts.push(`Рекомендую усилить бюджет группы «${shortAdSetName(best.adSet.name)}».`);
  } else {
    parts.push('Пока мало данных по группам — стоит дождаться накопления статистики.');
  }

  const status = campaign.verdict?.status ?? deriveCampaignStatus(metrics);

  return {
    status,
    body: parts.join(' '),
  };
}

function deriveCampaignStatus(metrics = {}) {
  const cpl = metrics.cpl?.trend;
  const leads = metrics.leads?.trend;
  if (cpl?.isPositive && leads?.isPositive) return 'good';
  if (cpl && leads && !cpl.isPositive && !leads.isPositive) return 'problem';
  if (cpl?.isPositive || leads?.isPositive) return 'warning';
  return 'good';
}

/** Вердикт уровня группы объявлений. */
export function buildAdSetVerdict(campaign, adSet) {
  const adSets = campaign.adSets ?? [];
  const rankings = rankAdSets(adSets);
  const current = aggregateAds(adSet.ads ?? []);
  const campaignAgg = rankings.reduce(
    (acc, row) => ({
      spent: acc.spent + row.spent,
      leads: acc.leads + row.leads,
    }),
    { spent: 0, leads: 0 },
  );
  const campaignAvgCpl = campaignAgg.leads > 0 ? Math.round(campaignAgg.spent / campaignAgg.leads) : 0;

  const parts = [];
  parts.push(`Аудитория: ${formatTargetingSummary(adSet.targeting)}.`);

  if (current.leads > 0) {
    parts.push(`Цена результата — ${formatTenge(current.cpl)}.`);
    if (campaignAvgCpl > 0) {
      const diff = current.cpl - campaignAvgCpl;
      if (Math.abs(diff) >= 15) {
        parts.push(
          diff < 0
            ? `Это на ${formatTenge(Math.abs(diff))} дешевле среднего по кампании.`
            : `Это на ${formatTenge(diff)} дороже среднего по кампании.`,
        );
      } else {
        parts.push('Показатели близки к среднему по кампании.');
      }
    }

    const betterGroups = rankings.filter((r) => r.adSet.id !== adSet.id && r.cpl < current.cpl);
    const worseGroups = rankings.filter((r) => r.adSet.id !== adSet.id && r.cpl > current.cpl);
    if (betterGroups.length) {
      parts.push(
        `Дешевле этой группы: «${shortAdSetName(betterGroups[0].adSet.name)}».`,
      );
    }
    if (worseGroups.length) {
      parts.push(
        `Дороже этой группы: «${shortAdSetName(worseGroups[worseGroups.length - 1].adSet.name)}».`,
      );
    }
  } else {
    parts.push('За период результатов пока нет — проверьте статус группы и объявлений.');
  }

  const adRankings = rankAds(adSet.ads ?? []);
  if (adRankings.length) {
    const bestAd = adRankings[0];
    const worstAd = adRankings[adRankings.length - 1];
    parts.push(`Лучшее объявление — «${bestAd.name}» (${formatTenge(bestAd.cpl)}).`);
    if (worstAd.id !== bestAd.id) {
      parts.push(`Слабое — «${worstAd.name}» (${formatTenge(worstAd.cpl)}).`);
    }
  }

  const pausedHeavy = (adSet.ads ?? []).filter((a) => a.status === 'paused' && (a.spent ?? 0) > 0);
  if (pausedHeavy.length) {
    parts.push('На паузе есть объявления с историей трат — имеет смысл проверить, стоит ли их возвращать.');
  }

  return {
    status: deriveStatus(current.cpl, campaignAvgCpl, current.leads),
    body: parts.join(' '),
  };
}

/** Вердикт уровня списка объявлений. */
export function buildAdsListVerdict(campaign, ads, { scopeLabel } = {}) {
  const resultLabel = (campaign.resultLabel ?? 'результат').toLowerCase();
  const activeAds = ads.filter((a) => (a.leads ?? 0) > 0);
  const rankings = rankAds(activeAds);
  const parts = [];

  if (scopeLabel) {
    parts.push(`Смотрю ${scopeLabel.toLowerCase()}.`);
  }

  if (!rankings.length) {
    parts.push(`За период нет ${resultLabel} — проверьте статусы объявлений и креативы.`);
    return { status: 'warning', body: parts.join(' ') };
  }

  const best = rankings[0];
  const worst = rankings[rankings.length - 1];
  parts.push(`Лучшее объявление — «${best.name}» (${formatTenge(best.cpl)} за результат).`);

  if (worst.id !== best.id) {
    parts.push(`Слабое — «${worst.name}» (${formatTenge(worst.cpl)}).`);
  }

  parts.push(`Усилить стоит «${best.name}» — у него лучшая цена результата.`);

  const toReview = rankings.filter((a) => a.cpl >= best.cpl * 1.35);
  if (toReview.length > 1) {
    parts.push(
      `Проверить: ${toReview.slice(1, 3).map((a) => `«${a.name}»`).join(', ')} — цена заметно выше лидера.`,
    );
  }

  const toPause = ads.filter((a) => a.status !== 'paused' && (a.leads ?? 0) > 0 && a.cpl >= best.cpl * 1.5);
  if (toPause.length) {
    parts.push(
      `Отключить или поставить на паузу: «${toPause[toPause.length - 1].name}» — перерасход бюджета без отдачи.`,
    );
  }

  const pausedWithSpend = ads.filter((a) => a.status === 'paused');
  if (pausedWithSpend.length) {
    parts.push(`${pausedWithSpend.length} объяв. уже на паузе — перед возвратом обновите оффер или креатив.`);
  }

  const avgCpl = Math.round(
    rankings.reduce((s, a) => s + a.cpl, 0) / rankings.length,
  );

  return {
    status: deriveStatus(worst.cpl, avgCpl, worst.leads),
    body: parts.join(' '),
  };
}

export function collectCampaignAds(adSets = [], filterAdSetId = null) {
  const sets = filterAdSetId ? adSets.filter((s) => s.id === filterAdSetId) : adSets;
  return sets.flatMap((s) =>
    (s.ads ?? []).map((ad) => ({ ...ad, adSetName: s.name, adSetId: s.id })),
  );
}
