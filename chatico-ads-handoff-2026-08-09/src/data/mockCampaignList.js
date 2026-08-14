/**
 * Mock-сводки кампаний для списка «Моя реклама» (M11, Этап 1).
 * TODO(api): заменить getMockCampaignListItems на API с dateRange.
 */

import { MOCK_CAMPAIGNS, getCampaignDetail } from './mockCampaigns';
import { resolveMockPeriodKey } from '../utils/dateRange';

/** Периодные mock-числа по id кампании (не привязаны к реальному API). */
const LIST_BY_PERIOD = {
  '7d': {
    camp_001: { spent: '48 200 ₸', results: '128', price: '376 ₸' },
    camp_002: { spent: '62 100 ₸', results: '86', price: '722 ₸' },
    camp_003: { spent: '22 400 ₸', results: '640', price: '35 ₸' },
    camp_004: { spent: '31 200 ₸', results: '65', price: '480 ₸' },
    camp_005: { spent: '19 800 ₸', results: '49 200', price: '0,40 ₸' },
    camp_006: { spent: '68 000 ₸', results: '104', price: '654 ₸' },
    camp_007: { spent: '29 400 ₸', results: '45', price: '653 ₸' },
  },
  '14d': {
    camp_001: { spent: '92 400 ₸', results: '243', price: '380 ₸' },
    camp_002: { spent: '118 700 ₸', results: '164', price: '724 ₸' },
    camp_003: { spent: '43 800 ₸', results: '1 240', price: '35 ₸' },
    camp_004: { spent: '61 500 ₸', results: '128', price: '480 ₸' },
    camp_005: { spent: '38 200 ₸', results: '96 400', price: '0,40 ₸' },
    camp_006: { spent: '134 000 ₸', results: '208', price: '644 ₸' },
    camp_007: { spent: '57 900 ₸', results: '89', price: '650 ₸' },
  },
  '30d': {
    camp_001: { spent: '198 000 ₸', results: '520', price: '381 ₸' },
    camp_002: { spent: '245 000 ₸', results: '340', price: '721 ₸' },
    camp_003: { spent: '89 000 ₸', results: '2 540', price: '35 ₸' },
    camp_004: { spent: '122 000 ₸', results: '254', price: '480 ₸' },
    camp_005: { spent: '76 000 ₸', results: '190 000', price: '0,40 ₸' },
    camp_006: { spent: '268 000 ₸', results: '416', price: '644 ₸' },
    camp_007: { spent: '115 000 ₸', results: '178', price: '646 ₸' },
  },
  thisMonth: {
    camp_001: { spent: '152 000 ₸', results: '400', price: '380 ₸' },
    camp_002: { spent: '198 000 ₸', results: '274', price: '722 ₸' },
    camp_003: { spent: '72 000 ₸', results: '2 050', price: '35 ₸' },
    camp_004: { spent: '98 000 ₸', results: '204', price: '480 ₸' },
    camp_005: { spent: '61 000 ₸', results: '152 000', price: '0,40 ₸' },
    camp_006: { spent: '214 000 ₸', results: '332', price: '644 ₸' },
    camp_007: { spent: '92 000 ₸', results: '142', price: '648 ₸' },
  },
  lastMonth: {
    camp_001: { spent: '175 000 ₸', results: '290', price: '603 ₸' },
    camp_002: { spent: '210 000 ₸', results: '198', price: '1 061 ₸' },
    camp_003: { spent: '80 000 ₸', results: '1 890', price: '42 ₸' },
    camp_004: { spent: '110 000 ₸', results: '180', price: '611 ₸' },
    camp_005: { spent: '68 000 ₸', results: '140 000', price: '0,49 ₸' },
    camp_006: { spent: '230 000 ₸', results: '280', price: '821 ₸' },
    camp_007: { spent: '98 000 ₸', results: '120', price: '817 ₸' },
  },
};

/**
 * Список кампаний для страницы «Моя реклама» с mock-метриками за период.
 */
export function getMockCampaignListItems(dateRange) {
  const key = resolveMockPeriodKey(dateRange);
  const metrics = LIST_BY_PERIOD[key] ?? LIST_BY_PERIOD['14d'];

  return MOCK_CAMPAIGNS.map((base) => {
    const detail = getCampaignDetail(base.id);
    const row = metrics[base.id] ?? { spent: '—', results: '—', price: '—' };
    return {
      ...base,
      objective: detail?.objective ?? '—',
      resultLabel: detail?.resultLabel ?? 'Результат',
      resultType: detail?.resultLabel ?? 'Результат',
      priceLabel: detail?.metrics?.cpl?.subtitle ?? 'Цена результата',
      spent: row.spent,
      results: row.results,
      price: row.price,
    };
  });
}
