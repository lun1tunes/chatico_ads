/**
 * Mock-данные главного экрана «Главное» (M11, Этап 1).
 * Центр контроля аккаунта — без смешивания несопоставимых метрик.
 * TODO(api): заменить getMockOverviewMetrics на запрос к API с dateRange + compare.
 */

import { resolveMockPeriodKey } from '../utils/dateRange';

/** Базовые наборы по ключу периода. */
const OVERVIEW_CURRENT = {
  '7d': {
    spent: { value: '145 200 ₸', subtitle: 'За выбранный период' },
    activeCampaigns: { value: '5', subtitle: 'Из 7 кампаний' },
    conversations: { value: '263', subtitle: 'Сообщения и диалоги' },
    leads: { value: '104', subtitle: 'Заявки из лид-форм' },
    verdict: {
      status: 'good',
      text: 'Аккаунт работает стабильно: 5 кампаний активны, расходы в плане. Лучше всего идут кампании на сообщения и трафик. Следите за ростом цены в кампании на продажи — там уже виден перегрев креативов.',
    },
    attention: [
      {
        type: 'price_spike',
        campaignId: 'camp_002',
        text: 'Цена продажи выросла на 12% за последние 7 дней',
      },
      {
        type: 'paused',
        campaignId: 'camp_004',
        text: 'Кампания остановлена — акция «Скидка 20%» не работает',
      },
      {
        type: 'paused',
        campaignId: 'camp_007',
        text: 'Каталог продаж на паузе',
      },
    ],
    topCampaigns: [
      { campaignId: 'camp_001', highlight: '380 ₸ за диалог · лучшая в «Сообщения»' },
      { campaignId: 'camp_003', highlight: '35 ₸ за переход · лучшая в «Трафик»' },
    ],
  },
  '14d': {
    spent: { value: '310 500 ₸', subtitle: 'За выбранный период' },
    activeCampaigns: { value: '5', subtitle: 'Из 7 кампаний' },
    conversations: { value: '535', subtitle: 'Сообщения и диалоги' },
    leads: { value: '208', subtitle: 'Заявки из лид-форм' },
    verdict: {
      status: 'warning',
      text: '5 кампаний активны, 2 на паузе. Обращений и лидов достаточно, но кампания на женскую аудиторию дорожает — цена продажи выросла на 12%. Остановленная кампания в Messenger тоже требует решения: обновить оффер или закрыть.',
    },
    attention: [
      {
        type: 'price_spike',
        campaignId: 'camp_002',
        text: 'Резкий рост цены продажи — +12% за 14 дней',
      },
      {
        type: 'paused',
        campaignId: 'camp_004',
        text: 'Кампания на Messenger остановлена',
      },
      {
        type: 'paused',
        campaignId: 'camp_007',
        text: 'Каталог продаж на паузе — продажи не идут',
      },
    ],
    topCampaigns: [
      { campaignId: 'camp_001', highlight: '243 диалога · 380 ₸ за диалог' },
      { campaignId: 'camp_003', highlight: '1 240 переходов · 35 ₸ за клик' },
    ],
  },
  '30d': {
    spent: { value: '680 000 ₸', subtitle: 'За выбранный период' },
    activeCampaigns: { value: '5', subtitle: 'Из 7 кампаний' },
    conversations: { value: '1 120', subtitle: 'Сообщения и диалоги' },
    leads: { value: '416', subtitle: 'Заявки из лид-форм' },
    verdict: {
      status: 'good',
      text: 'За месяц аккаунт держит темп: 5 активных кампаний, расходы растут умеренно. Лидеры — сообщения в WhatsApp и ретаргетинг на сайт. Единственная зона риска — продажи через Reels, где цена результата ползёт вверх.',
    },
    attention: [
      {
        type: 'price_spike',
        campaignId: 'camp_002',
        text: 'Цена продажи выше среднего по категории на 18%',
      },
      {
        type: 'paused',
        campaignId: 'camp_004',
        text: 'Messenger-кампания остановлена с 18 июня',
      },
    ],
    topCampaigns: [
      { campaignId: 'camp_001', highlight: '520 диалогов · лучшая в «Сообщения»' },
      { campaignId: 'camp_003', highlight: '2 540 переходов · лучшая в «Трафик»' },
    ],
  },
  thisMonth: {
    spent: { value: '520 000 ₸', subtitle: 'За выбранный период' },
    activeCampaigns: { value: '5', subtitle: 'Из 7 кампаний' },
    conversations: { value: '870', subtitle: 'Сообщения и диалоги' },
    leads: { value: '332', subtitle: 'Заявки из лид-форм' },
    verdict: {
      status: 'good',
      text: 'С начала месяца аккаунт в рабочем режиме: расходы контролируемые, обращения и лиды идут. Две кампании на паузе — решите, перезапускать ли их до конца месяца.',
    },
    attention: [
      {
        type: 'paused',
        campaignId: 'camp_004',
        text: 'Акция в Messenger не запущена',
      },
      {
        type: 'paused',
        campaignId: 'camp_007',
        text: 'Каталог продаж на паузе',
      },
    ],
    topCampaigns: [
      { campaignId: 'camp_001', highlight: '400 диалогов · 380 ₸ за диалог' },
      { campaignId: 'camp_006', highlight: '332 заявки · лучшая в «Лиды»' },
    ],
  },
  lastMonth: {
    spent: { value: '590 000 ₸', subtitle: 'За выбранный период' },
    activeCampaigns: { value: '4', subtitle: 'Из 7 кампаний' },
    conversations: { value: '720', subtitle: 'Сообщения и диалоги' },
    leads: { value: '280', subtitle: 'Заявки из лид-форм' },
    verdict: {
      status: 'warning',
      text: 'В прошлом месяце часть кампаний работала дороже обычного. Сейчас ситуация улучшается, но стоит проверить кампании на паузе и перераспределить бюджет в пользу лидеров.',
    },
    attention: [
      {
        type: 'price_spike',
        campaignId: 'camp_002',
        text: 'Цена продажи выросла на 46% за месяц',
      },
      {
        type: 'no_results',
        campaignId: 'camp_007',
        text: 'Каталог расходовал бюджет с низкой отдачей',
      },
    ],
    topCampaigns: [
      { campaignId: 'camp_003', highlight: '1 890 переходов · лучшая в «Трафик»' },
      { campaignId: 'camp_001', highlight: '290 диалогов · лучшая в «Сообщения»' },
    ],
  },
};

const OVERVIEW_COMPARE = {
  '7d': {
    spent: { value: '12%', isPositive: false },
    activeCampaigns: { value: '0', isPositive: true },
    conversations: { value: '18%', isPositive: true },
    leads: { value: '9%', isPositive: true },
  },
  '14d': {
    spent: { value: '8%', isPositive: true },
    activeCampaigns: { value: '0', isPositive: true },
    conversations: { value: '14%', isPositive: true },
    leads: { value: '11%', isPositive: true },
  },
  '30d': {
    spent: { value: '15%', isPositive: true },
    activeCampaigns: { value: '+1', isPositive: true },
    conversations: { value: '22%', isPositive: true },
    leads: { value: '16%', isPositive: true },
  },
  thisMonth: {
    spent: { value: '11%', isPositive: true },
    activeCampaigns: { value: '0', isPositive: true },
    conversations: { value: '20%', isPositive: true },
    leads: { value: '13%', isPositive: true },
  },
  lastMonth: {
    spent: { value: '5%', isPositive: false },
    activeCampaigns: { value: '−1', isPositive: false },
    conversations: { value: '3%', isPositive: false },
    leads: { value: '2%', isPositive: false },
  },
};

function buildCompareSubtitle(key, trend) {
  if (!trend || key === 'activeCampaigns') return null;
  const { value, isPositive } = trend;
  const more = isPositive ? 'больше' : 'меньше';
  switch (key) {
    case 'spent':
      return `На ${value} ${more} прошлого периода`;
    case 'conversations':
      return `На ${value} ${more} обращений`;
    case 'leads':
      return `На ${value} ${more} лидов`;
    default:
      return null;
  }
}

function withTrends(current, compareKey, compareEnabled) {
  const keys = ['spent', 'activeCampaigns', 'conversations', 'leads'];
  const result = { ...current };
  keys.forEach((key) => {
    if (!result[key]) return;
    const base = { ...result[key] };
    const compare = OVERVIEW_COMPARE[compareKey]?.[key];
    if (compareEnabled && compare) {
      base.trend = compare;
      const compareSubtitle = buildCompareSubtitle(key, compare);
      if (compareSubtitle) base.compareSubtitle = compareSubtitle;
    }
    result[key] = base;
  });
  return result;
}

/**
 * Возвращает mock-данные главного экрана для глобального периода.
 * @param {object} dateRange — { preset, from, to }
 * @param {boolean} compareEnabled
 */
export function getMockOverviewMetrics(dateRange, compareEnabled = true) {
  const key = resolveMockPeriodKey(dateRange);
  const current = OVERVIEW_CURRENT[key] ?? OVERVIEW_CURRENT['14d'];
  const compareKey = key in OVERVIEW_COMPARE ? key : '14d';
  return withTrends(current, compareKey, compareEnabled);
}

/** @deprecated Используйте getMockOverviewMetrics. Оставлено для совместимости. */
export const MOCK_METRICS_BY_PERIOD = {
  7: getMockOverviewMetrics({ preset: '7d', from: '', to: '' }, true),
  14: getMockOverviewMetrics({ preset: '14d', from: '', to: '' }, true),
  30: getMockOverviewMetrics({ preset: '30d', from: '', to: '' }, true),
};
