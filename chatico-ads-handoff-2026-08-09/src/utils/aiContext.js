import { SUGGESTED_QUESTIONS } from '../data/mockAiResponses';
import { resolveMockPeriodKey } from './dateRange';
import {
  buildCampaignVerdict,
  buildAdSetVerdict,
  buildAdsListVerdict,
  collectCampaignAds,
} from './campaignVerdict';

const TONE_META = {
  good: {
    title: 'Аккаунт работает стабильно',
    shortTitle: 'всё работает стабильно',
    border: 'border-emerald-400',
    dot: 'bg-emerald-500',
    titleClass: 'text-emerald-800',
  },
  attention: {
    title: 'Требуется внимание',
    shortTitle: 'требуется внимание',
    border: 'border-amber-400',
    dot: 'bg-amber-500',
    titleClass: 'text-amber-800',
  },
  problem: {
    title: 'Есть проблема',
    shortTitle: 'есть проблема',
    border: 'border-red-400',
    dot: 'bg-red-500',
    titleClass: 'text-red-800',
  },
};

const CAMPAIGN_TONE = {
  good: {
    title: 'Кампания работает хорошо',
    shortTitle: 'работает хорошо',
    border: 'border-emerald-400',
    dot: 'bg-emerald-500',
    titleClass: 'text-emerald-800',
  },
  warning: {
    title: 'Есть что улучшить',
    shortTitle: 'есть что улучшить',
    border: 'border-amber-400',
    dot: 'bg-amber-500',
    titleClass: 'text-amber-800',
  },
  problem: {
    title: 'Требует внимания',
    shortTitle: 'требует внимания',
    border: 'border-red-400',
    dot: 'bg-red-500',
    titleClass: 'text-red-800',
  },
};

const AD_SET_TONE = {
  good: {
    title: 'Группа работает хорошо',
    shortTitle: 'группа работает хорошо',
    border: 'border-emerald-400',
    dot: 'bg-emerald-500',
    titleClass: 'text-emerald-800',
  },
  warning: {
    title: 'Группу стоит проверить',
    shortTitle: 'есть что проверить',
    border: 'border-amber-400',
    dot: 'bg-amber-500',
    titleClass: 'text-amber-800',
  },
  problem: {
    title: 'Группа отстаёт',
    shortTitle: 'группа отстаёт',
    border: 'border-red-400',
    dot: 'bg-red-500',
    titleClass: 'text-red-800',
  },
};

const ADS_TONE = {
  good: {
    title: 'Объявления в хорошей форме',
    shortTitle: 'есть сильные объявления',
    border: 'border-emerald-400',
    dot: 'bg-emerald-500',
    titleClass: 'text-emerald-800',
  },
  warning: {
    title: 'Есть слабые объявления',
    shortTitle: 'есть слабые объявления',
    border: 'border-amber-400',
    dot: 'bg-amber-500',
    titleClass: 'text-amber-800',
  },
  problem: {
    title: 'Нужна чистка объявлений',
    shortTitle: 'нужна чистка',
    border: 'border-red-400',
    dot: 'bg-red-500',
    titleClass: 'text-red-800',
  },
};

const CAMPAIGN_QUESTIONS = [
  'Какая группа работает лучше?',
  'Куда добавить бюджет в этой кампании?',
  'Какие объявления стоит отключить?',
  'Что улучшить прямо сейчас?',
];

const AD_SET_QUESTIONS = [
  'Как эта группа сравнивается с другими?',
  'Какое объявление усилить в этой группе?',
  'Стоит ли расширить аудиторию?',
  'Что отключить в этой группе?',
];

const ADS_QUESTIONS = [
  'Какое объявление работает лучше всего?',
  'Что стоит отключить?',
  'Какие креативы протестировать?',
  'Где перераспределить бюджет между объявлениями?',
];

function firstSentence(text = '') {
  const match = text.match(/^[^.!?]+[.!?]?/);
  return match ? match[0].trim() : text;
}

function toneFromVerdict(status) {
  if (status === 'good') return 'good';
  if (status === 'warning') return 'attention';
  return 'problem';
}

function compactHint(text = '', tone) {
  const sentences = text.match(/[^.!?]+[.!?]+/g) ?? [];
  if (tone === 'good' && sentences.length > 1) {
    return sentences[1].trim();
  }
  return firstSentence(text);
}

function periodKey(dateRange) {
  const preset = resolveMockPeriodKey(dateRange);
  return `${preset}:${dateRange.from}:${dateRange.to}`;
}

function buildAiContext({ key, introPrefix, body, status, toneMap, questions }) {
  const meta = toneMap[status] ?? toneMap.good;
  const tone = status === 'good' ? 'good' : status === 'warning' ? 'attention' : 'problem';
  const fullText = `${introPrefix} ${body}`.trim();
  const hint = compactHint(body, tone);

  return {
    key,
    intro: fullText,
    verdict: { status: status === 'warning' ? 'warning' : status },
    compact: {
      title: meta.title,
      shortTitle: meta.shortTitle,
      hint,
      tone,
      border: meta.border,
      dot: meta.dot,
      titleClass: meta.titleClass,
    },
    questions,
  };
}

export function buildOverviewAiContext(metrics, dateRange, periodLabel) {
  const verdict = metrics?.verdict;
  const tone = toneFromVerdict(verdict?.status);
  const meta = TONE_META[tone];
  const hint = compactHint(verdict?.text ?? '', tone);

  return {
    key: `account:${periodKey(dateRange)}`,
    intro: `Проверил аккаунт за ${periodLabel}. ${verdict?.text ?? ''}`,
    verdict: { status: verdict?.status ?? 'good' },
    compact: {
      title: meta.title,
      shortTitle: meta.shortTitle,
      hint,
      tone,
      ...meta,
    },
    questions: SUGGESTED_QUESTIONS,
  };
}

/** aiContext для страницы кампании (уровень кампании). */
export function buildCampaignAiContext(campaign, periodLabel, dateRange) {
  const { status, body } = buildCampaignVerdict(campaign);
  return buildAiContext({
    key: `campaign:${campaign.id}:${periodKey(dateRange)}`,
    introPrefix: `Разобрал кампанию «${campaign.name}» за ${periodLabel}.`,
    body,
    status,
    toneMap: CAMPAIGN_TONE,
    questions: CAMPAIGN_QUESTIONS,
  });
}

/** aiContext для страницы группы объявлений. */
export function buildAdSetAiContext(campaign, adSet, periodLabel, dateRange) {
  const { status, body } = buildAdSetVerdict(campaign, adSet);
  return buildAiContext({
    key: `adset:${campaign.id}:${adSet.id}:${periodKey(dateRange)}`,
    introPrefix: `Разобрал группу объявлений «${adSet.name}» за ${periodLabel}.`,
    body,
    status,
    toneMap: AD_SET_TONE,
    questions: AD_SET_QUESTIONS,
  });
}

/** aiContext для страницы объявлений кампании (/campaigns/:id/ads). */
export function buildAdsAiContext(campaign, periodLabel, dateRange, filterAdSetId = null) {
  const adSets = campaign.adSets ?? [];
  const ads = collectCampaignAds(adSets, filterAdSetId);
  const filterAdSet = filterAdSetId ? adSets.find((s) => s.id === filterAdSetId) : null;
  const scopeLabel = filterAdSet
    ? `объявления группы «${filterAdSet.name}»`
    : `все ${ads.length} объявления кампании`;

  const { status, body } = buildAdsListVerdict(campaign, ads, { scopeLabel });

  return buildAiContext({
    key: `ads:${campaign.id}:${filterAdSetId ?? 'all'}:${periodKey(dateRange)}`,
    introPrefix: `Сравнил объявления${filterAdSet ? ` группы «${filterAdSet.name}»` : ' кампании'} за ${periodLabel}.`,
    body,
    status,
    toneMap: ADS_TONE,
    questions: ADS_QUESTIONS,
  });
}

export { TONE_META };
